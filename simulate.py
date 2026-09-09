# simulate.py — شبیه‌سازی یک روز کامل ربات با دیتای واقعی KuCoin
#
#   python simulate.py --date 2026-09-07 [--out sim_result.json]
#
# پنجره: 07:00 تا 24:00 تهران
#  • کندل‌های بسته‌شده 30m واقعی KuCoin (به‌علاوه ~32 روز lookback برای اندیکاتورها)
#  • همان کد Engine ربات زنده اجرا می‌شود (بدون آینده‌نگری: هر تیک فقط کندل‌های بسته‌شده تا آن لحظه را می‌بیند)
#  • خروجی: JSON پیام‌های تلگرام + رویدادها + آمار روز

import os
import sys
import json
import argparse
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

# دیتای شبیه‌سازی جدا از ربات زنده نگهداری می‌شود
os.environ.setdefault("PS_DATA_DIR", os.path.join(BASE, "data_sim"))

from pentasignal import settings, kucoin, scenarios  # noqa: E402
from pentasignal.engine import Engine  # noqa: E402
from pentasignal.utils import tehran_str, ts_to_tehran, utc_ts  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

TEHRAN = ZoneInfo("Asia/Tehran")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="تاریخ تهران مثل 2026-09-07")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-cache", action="store_true")
    return ap.parse_args()


def fetch_all(day_start_ts: int, day_end_ts: int, use_cache=True) -> dict:
    """کندل 30m همه نمادها برای پنجره روز + lookback، و 4h BTC"""
    lb_start = day_start_ts - settings.LOOKBACK_DAYS_30M * 86400
    candles30 = {}
    for i, sym in enumerate(scenarios.UNION_SYMBOLS):
        for attempt in range(3):
            try:
                candles30[sym] = kucoin.chunked_candles(
                    sym, settings.CANDLE_TYPE_30M, lb_start, day_end_ts,
                    chunk_days=25) if use_cache else \
                    kucoin.chunked_candles(sym, settings.CANDLE_TYPE_30M,
                                           lb_start, day_end_ts, chunk_days=25)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  !! fetch failed {sym}: {e}")
                    candles30[sym] = []
                time.sleep(2)
        time.sleep(0.12)
        print(f"  fetched 30m {sym} ({len(candles30[sym])} bars)")
    btc4h = kucoin.chunked_candles("BTC-USDT", settings.CANDLE_TYPE_4H,
                                   day_start_ts - settings.LOOKBACK_DAYS_4H * 86400,
                                   day_end_ts, chunk_days=30)
    print(f"  fetched 4h BTC ({len(btc4h)} bars)")
    return {"candles30": candles30, "btc4h": btc4h}


def make_entry_lookup(data):
    """ورود = بازِ کندل بعد از کندل سیگنال (t == ts سیگنال). اگر نبود: کلوز کندل سیگنال."""
    idx = {}
    for sym, cs in data["candles30"].items():
        idx[sym] = {c["t"]: c for c in cs}

    def lookup(symbol: str, at_ts: int):
        c = idx.get(symbol, {}).get(at_ts)
        if c:
            return c["o"]
        cs = data["candles30"].get(symbol) or []
        prev = [x for x in cs if x["t"] < at_ts]
        return prev[-1]["c"] if prev else None
    return lookup


def slice_ctx(data, close_ts: int) -> scenarios.MarketContext:
    """فقط کندل‌های بسته‌شده تا close_ts (بدون آینده‌نگری)"""
    cut = close_ts  # t + 1800 <= close_ts → t < close_ts
    c30 = {sym: [c for c in cs if c["t"] < cut]
           for sym, cs in data["candles30"].items()}
    btc4h = [c for c in data["btc4h"]
             if c["t"] + 4 * 3600 <= close_ts + 1800]
    return scenarios.MarketContext(c30, btc_4h=btc4h)


def main():
    args = parse_args()
    day = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=TEHRAN)
    day_start = int(day.timestamp())                     # 00:00 تهران
    day_end = day_start + 86400                          # 24:00 تهران
    win_start = day_start + settings.NEW_SIGNAL_START_HOUR * 3600  # 07:00

    print(f"== PentaSignal v{settings.VERSION} simulate {args.date} "
          f"07:00→24:00 Tehran ==")
    print("fetching real KuCoin candles ...")
    data = fetch_all(day_start, day_end, use_cache=not args.no_cache)

    # تیک‌ها: بسته‌شدن کندل‌های 30m از 07:00 تا 23:30 + تیک 24:00 (بسته‌شدن در 00:00 روز بعد)
    ticks = []
    t = win_start
    while t < day_end:
        ticks.append(t)
        t += 1800
    ticks.append(day_end)  # تیک 24:00

    engine = Engine(sender=None, entry_price_provider=make_entry_lookup(data))
    messages = []
    for ts in ticks:
        close_dt = ts_to_tehran(ts)
        label = "24:00" if ts == day_end else close_dt.strftime("%H:%M")
        ctx = slice_ctx(data, ts)
        logs = engine.on_candle_close(close_dt, ctx, run_nightly=(ts == day_end))
        print(f"  tick {label} → {len(logs)} message(s)")
        for lg in logs:
            messages.append({
                "tick": label,
                "ts_tehran": lg.ts,
                "kind": lg.kind,
                "reply_to": lg.reply_to,
                "message_id": lg.message_id,
                "signal_id": lg.signal_id,
                "text": lg.text,
                "meta": lg.meta,
            })

    # آمار نهایی از CSV شبیه‌سازی
    from pentasignal import store, report
    report_date = args.date
    issued, settled, still_open = report.collect_day(report_date)
    stats = {
        "issued": len(issued),
        "settled": len(settled),
        "still_open": len(still_open),
        "pnl_total": round(sum(float(r["pnl_usd"] or 0) for r in settled), 4),
        "tp": sum(1 for r in settled if r["status"] == "TP_HIT"),
        "sl": sum(1 for r in settled if r["status"] == "SL_HIT"),
        "be": sum(1 for r in settled if r["status"] == "BE_HIT"),
        "cm": sum(1 for r in settled if r["status"] == "CM_CLOSED"),
    }
    payload = {
        "version": settings.VERSION,
        "date": report_date,
        "window": "07:00 → 24:00 Tehran",
        "ticks": len(ticks),
        "messages": messages,
        "stats": stats,
        "issued_rows": issued,
        "settled_rows": settled,
        "still_open_rows": still_open,
        "report_text": report.build_report_message(report_date),
    }
    out = args.out or os.path.join(BASE, "sim_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"saved → {out}")
    print("stats:", json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
