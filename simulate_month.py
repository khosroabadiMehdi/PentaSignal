# simulate_month.py — شبیه‌سازی 30 روز گذشته ربات با دیتای واقعی KuCoin
#
#   python simulate_month.py [--start 2026-08-09] [--end 2026-09-07] [--out month_result.json]
#
# همان Engine ربات زنده (بدون آینده‌نگری) روی تیک‌های 30m؛ پنجره سیگنال و
# گزارش شبانه و تسویه‌ها دقیقاً مثل ربات. برای سرعت: پنجره 600 کندلی هر تیک.

import os
import sys
import json
import time
import argparse
import bisect
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

os.environ["PS_DATA_DIR"] = os.path.join(BASE, "data_sim_month")

from pentasignal import settings, kucoin, scenarios  # noqa: E402
from pentasignal.engine import Engine  # noqa: E402
from pentasignal.utils import ts_to_tehran  # noqa: E402

TEHRAN = ZoneInfo("Asia/Tehran")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-08-09")
    ap.add_argument("--end", default="2026-09-07")
    ap.add_argument("--out", default=os.path.join(BASE, "month_result.json"))
    ap.add_argument("--fetch-only", action="store_true",
                    help="فقط دریافت و کش دیتا (بدون اجرای موتور)")
    return ap.parse_args()


def fetch_all(start_ts: int, end_ts: int):
    lb = start_ts - settings.LOOKBACK_DAYS_30M * 86400
    candles30 = {}
    for sym in scenarios.UNION_SYMBOLS:
        for attempt in range(3):
            try:
                candles30[sym] = kucoin.chunked_candles(
                    sym, settings.CANDLE_TYPE_30M, lb, end_ts, chunk_days=25)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  !! fetch failed {sym}: {e}")
                    candles30[sym] = []
                time.sleep(2)
        time.sleep(0.1)
        print(f"  fetched 30m {sym} ({len(candles30[sym])} bars)", flush=True)
    btc4h = kucoin.chunked_candles("BTC-USDT", settings.CANDLE_TYPE_4H,
                                   start_ts - settings.LOOKBACK_DAYS_4H * 86400,
                                   end_ts, chunk_days=30)
    print(f"  fetched 4h BTC ({len(btc4h)} bars)")
    return {"candles30": candles30, "btc4h": btc4h}


class Windowed:
    """پنجره‌ی 600 کندلی هر تیک با جست‌وجوی دودویی (سرعت)"""

    def __init__(self, data):
        self.ts30 = {s: [c["t"] for c in cs] for s, cs in data["candles30"].items()}
        self.ts4h = [c["t"] for c in data["btc4h"]]
        self.data = data

    def ctx(self, close_ts: int):
        c30 = {}
        for sym, ts in self.ts30.items():
            i = bisect.bisect_left(ts, close_ts)   # t < close_ts → بسته‌شده
            c30[sym] = self.data["candles30"][sym][max(0, i - 600):i]
        j = bisect.bisect_left(self.ts4h, close_ts + 1800 - 4 * 3600)
        return scenarios.MarketContext(c30, btc_4h=self.data["btc4h"][:j])


def main():
    args = parse_args()
    d0 = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=TEHRAN)
    d1 = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=TEHRAN)
    start_ts = int(d0.timestamp())
    end_ts = int((d1 + timedelta(days=1)).timestamp())   # 24:00 روز آخر

    n_days = (end_ts - start_ts) // 86400
    print(f"== PentaSignal v{settings.VERSION} — شبیه‌سازی {n_days} روزه "
          f"{args.start} → {args.end} تهران ==")
    print("fetching real KuCoin candles ...", flush=True)
    data = fetch_all(start_ts, end_ts)
    if args.fetch_only:
        print("fetch-only done — cache warm.")
        return
    win = Windowed(data)
    idx = {s: {c["t"]: c for c in cs} for s, cs in data["candles30"].items()}

    def entry_lookup(symbol, at_ts):
        c = idx.get(symbol, {}).get(at_ts)
        if c:
            return c["o"]
        cs = data["candles30"].get(symbol) or []
        prev = [x for x in cs if x["t"] < at_ts]
        return prev[-1]["c"] if prev else None

    engine = Engine(sender=None, entry_price_provider=entry_lookup, light=True)

    t0 = time.time()
    ticks = list(range(start_ts, end_ts + 1, 1800))
    for k, ts in enumerate(ticks):
        close_dt = ts_to_tehran(ts)
        logs = engine.on_candle_close(close_dt, win.ctx(ts))
        if k % 96 == 0:
            print(f"  … {close_dt.strftime('%Y-%m-%d %H:%M')} "
                  f"({k}/{len(ticks)} ticks, {time.time()-t0:.0f}s)", flush=True)

    print(f"loop done in {time.time()-t0:.0f}s — aggregating from CSV ...")
    from pentasignal import store, report
    rows = store.all_signals()
    by_date = {}
    for r in rows:
        dt = r["issued_at_tehran"][:10]
        s = by_date.setdefault(dt, {"issued": 0})
        s["issued"] += 1
    from datetime import datetime as DT
    settled_by_date = {}
    for r in rows:
        if r["status"] in ("TP_HIT", "SL_HIT", "BE_HIT", "CM_CLOSED"):
            et = DT.strptime(r["exit_time_tehran"], "%Y-%m-%d %H:%M:%S") - timedelta(seconds=1)
            dt = et.strftime("%Y-%m-%d")
            s = settled_by_date.setdefault(dt, {"n": 0, "pnl": 0.0, "tp": 0, "sl": 0, "be": 0, "cm": 0, "wins": 0})
            pnl = float(r["pnl_usd"] or 0)
            s["n"] += 1
            s["pnl"] += pnl
            s[r["exit_reason"].lower() if r["exit_reason"] != "CM" else "cm"] += 1
            s["wins"] += 1 if pnl > 0 else 0

    # مرجع بازار: تغییر روزانه BTC
    btc = data["candles30"]["BTC-USDT"]
    btc_daily = {}
    for day in range(n_days):
        midnight = start_ts + day * 86400
        prev = [c for c in btc if c["t"] < midnight]
        if len(prev) >= 2:
            c_now, c_prev = prev[-1]["c"], prev[-2]["c"] if day else prev[-1]["c"]
            # تغییر نسبت به روز قبل: از کندل 48 قبلی
            if len(prev) >= 49:
                c_prev = prev[-49]["c"]
            btc_daily[ts_to_tehran(midnight).strftime("%Y-%m-%d")] = \
                round((c_now / c_prev - 1) * 100, 2)

    days = []
    cum = 0.0
    peak = 0.0
    maxdd = 0.0
    for day in range(n_days):
        dt = ts_to_tehran(start_ts + day * 86400).strftime("%Y-%m-%d")
        iss = by_date.get(dt, {}).get("issued", 0)
        st = settled_by_date.get(dt, {"n": 0, "pnl": 0.0, "tp": 0, "sl": 0, "be": 0, "cm": 0, "wins": 0})
        cum += st["pnl"]
        peak = max(peak, cum)
        maxdd = min(maxdd, cum - peak)
        days.append({
            "date": dt, "issued": iss, "settled": st["n"],
            "tp": st["tp"], "sl": st["sl"], "be": st["be"], "cm": st["cm"],
            "wins": st["wins"], "pnl": round(st["pnl"], 4),
            "cum": round(cum, 4), "btc_chg": btc_daily.get(dt),
        })

    by_sc = {}
    for r in rows:
        s = by_sc.setdefault(r["scenario_id"], {"issued": 0, "settled": 0, "tp": 0, "sl": 0,
                                                "be": 0, "cm": 0, "pnl": 0.0, "wins": 0, "fees": 0.0})
        s["issued"] += 1
        if r["status"] in ("TP_HIT", "SL_HIT", "BE_HIT", "CM_CLOSED"):
            s["settled"] += 1
            pnl = float(r["pnl_usd"] or 0)
            s["pnl"] += pnl
            s["fees"] += float(r["fee_usd"] or 0)
            s[r["exit_reason"].lower() if r["exit_reason"] != "CM" else "cm"] += 1
            s["wins"] += 1 if pnl > 0 else 0
    for s in by_sc.values():
        for k2 in ("pnl", "fees"):
            s[k2] = round(s[k2], 4)

    still_open = [r for r in rows if r["status"] == "OPEN"]
    total_settled = sum(d["settled"] for d in days)
    total_wins = sum(d["wins"] for d in days)
    total_pnl = round(sum(d["pnl"] for d in days), 4)
    payload = {
        "version": settings.VERSION,
        "start": args.start, "end": args.end, "days": n_days,
        "totals": {
            "signals": len(rows), "settled": total_settled,
            "wins": total_wins,
            "wr": round(100.0 * total_wins / total_settled, 1) if total_settled else 0.0,
            "pnl": total_pnl, "maxdd": round(maxdd, 4),
            "still_open": len(still_open),
            "fees": round(sum(s["fees"] for s in by_sc.values()), 4),
            "days_positive": sum(1 for d in days if d["pnl"] > 0),
            "days_negative": sum(1 for d in days if d["pnl"] < 0),
            "days_flat": sum(1 for d in days if d["pnl"] == 0),
        },
        "by_scenario": by_sc,
        "days": days,
        "still_open_rows": [{k: r[k] for k in ("signal_id", "symbol", "direction",
                                               "scenario_id", "entry_price", "issued_at_tehran")}
                            for r in still_open],
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("saved →", args.out)
    print("totals:", json.dumps(payload["totals"], ensure_ascii=False))
    print("by_scenario:", json.dumps(payload["by_scenario"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
