# monitor_nightly.py — PentaSignal
# بررسی امروز + دو روز قبل | CLOSED_MANUAL فقط بعد از بیش از ۲ روز
# گزارش: ۶ پیام (کلیات + ۵ سناریو)

import csv
import os
import time
import requests
import logging
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SCENARIOS, ACTIVE_SCENARIOS

KUCOIN_URL = "https://api.kucoin.com/api/v1/market/candles"
SIGNALS_DIR = "signals"

BROKER_FEE_RATE = 0.001
POSITION_SIZE_USD = 10.0
MAX_OPEN_DAYS = 2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def tehran_now():
    return datetime.now(ZoneInfo("Asia/Tehran"))


def parse_tehran_time(s: str):
    tz = ZoneInfo("Asia/Tehran")
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).replace(tzinfo=tz)
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
        except Exception:
            return None


def daily_csv_path(date_str: str) -> str:
    return os.path.join(SIGNALS_DIR, f"{date_str}.csv")


def fetch_kucoin_1m(symbol, start_at_unix, end_at_unix):
    params = {
        "symbol": symbol,
        "type": "1min",
        "startAt": int(start_at_unix),
        "endAt": int(end_at_unix),
    }
    try:
        r = requests.get(KUCOIN_URL, params=params, timeout=20)
        if r.status_code == 200:
            data = r.json().get("data", [])
            candles = [{
                "t": int(c[0]),
                "o": float(c[1]),
                "c": float(c[2]),
                "h": float(c[3]),
                "l": float(c[4]),
                "v": float(c[5]),
            } for c in data]
            return list(reversed(candles))
        if r.status_code == 429:
            time.sleep(10)
            return fetch_kucoin_1m(symbol, start_at_unix, end_at_unix)
    except Exception as e:
        print(f"error fetch 1m {symbol}: {e}")
    return []


def compute_pnl_usd(direction, entry_price, exit_price, position_size_usd=POSITION_SIZE_USD, fee_rate=BROKER_FEE_RATE):
    fee_total = position_size_usd * fee_rate * 2.0
    if direction == "LONG":
        ret_pct = (exit_price - entry_price) / entry_price if entry_price else 0.0
    else:
        ret_pct = (entry_price - exit_price) / entry_price if entry_price else 0.0
    gross = position_size_usd * ret_pct
    net = gross - fee_total
    return net, ret_pct * 100.0, fee_total


async def send_to_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("telegram config missing")
        print(text)
        return
    import aiohttp
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = []
    while text:
        if len(text) <= 4000:
            chunks.append(text)
            break
        cut = text.rfind("\n", 0, 4000)
        if cut < 500:
            cut = 4000
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    async with aiohttp.ClientSession() as session:
        for ch in chunks:
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": ch}
            try:
                async with session.post(url, json=payload, timeout=20) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(f"telegram {resp.status}: {body[:200]}")
                    else:
                        logger.info("nightly message sent")
            except Exception as e:
                logger.error(f"telegram error: {e}")
            await asyncio.sleep(0.4)


def read_csv_rows(date_str: str):
    path = daily_csv_path(date_str)
    if not os.path.isfile(path):
        return [], None
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    return rows, fieldnames


def write_csv_rows(date_str: str, fieldnames, rows):
    path = daily_csv_path(date_str)
    os.makedirs(SIGNALS_DIR, exist_ok=True)
    headers = list(fieldnames or [])
    for col in [
        "scenario_id", "scenario_name", "symbol", "direction", "entry_price",
        "stop_loss", "take_profit", "issued_at_tehran", "status",
        "hit_time_tehran", "hit_price", "broker_fee", "final_pnl_usd",
        "position_size_usd", "return_pct", "signal_source",
    ]:
        if col not in headers:
            headers.append(col)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


def _f(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def update_open_rows_for_date(date_str: str, now_tehran: datetime):
    rows, fieldnames = read_csv_rows(date_str)
    if not rows:
        return []

    updated = []
    for row in rows:
        status = (row.get("status") or "").strip()
        if status != "OPEN":
            updated.append(row)
            continue

        issued = parse_tehran_time(row.get("issued_at_tehran", ""))
        symbol = row.get("symbol", "")
        direction = row.get("direction", "LONG")
        entry = _f(row.get("entry_price"))
        sl = _f(row.get("stop_loss"))
        tp = _f(row.get("take_profit"))
        pos = _f(row.get("position_size_usd"), POSITION_SIZE_USD)

        if not issued or not symbol or entry <= 0:
            updated.append(row)
            continue

        age_days = (now_tehran - issued).total_seconds() / 86400.0
        start_unix = int(issued.timestamp())
        end_unix = int(now_tehran.timestamp())
        candles = fetch_kucoin_1m(symbol, start_unix, end_unix)
        time.sleep(0.25)

        hit_status = None
        hit_time = ""
        hit_price = None

        for c in candles:
            t = datetime.fromtimestamp(c["t"], tz=ZoneInfo("Asia/Tehran"))
            if t < issued:
                continue
            if direction == "LONG":
                if c["l"] <= sl:
                    hit_status, hit_price, hit_time = "STOP_HIT", sl, t.strftime("%Y-%m-%d %H:%M:%S")
                    break
                if c["h"] >= tp:
                    hit_status, hit_price, hit_time = "TP_HIT", tp, t.strftime("%Y-%m-%d %H:%M:%S")
                    break
            else:
                if c["h"] >= sl:
                    hit_status, hit_price, hit_time = "STOP_HIT", sl, t.strftime("%Y-%m-%d %H:%M:%S")
                    break
                if c["l"] <= tp:
                    hit_status, hit_price, hit_time = "TP_HIT", tp, t.strftime("%Y-%m-%d %H:%M:%S")
                    break

        if hit_status is None and age_days > MAX_OPEN_DAYS:
            exit_price = candles[-1]["c"] if candles else entry
            hit_status = "CLOSED_MANUAL"
            hit_price = exit_price
            hit_time = now_tehran.strftime("%Y-%m-%d %H:%M:%S")

        if hit_status:
            net, ret_pct, fee = compute_pnl_usd(direction, entry, float(hit_price), pos)
            row["status"] = hit_status
            row["hit_time_tehran"] = hit_time
            row["hit_price"] = f"{float(hit_price):.8f}"
            row["broker_fee"] = f"{fee:.6f}"
            row["final_pnl_usd"] = f"{net:.6f}"
            row["return_pct"] = f"{ret_pct:.4f}"
            print(f"  {symbol} {direction} -> {hit_status} | PnL={net:+.4f}")

        updated.append(row)

    write_csv_rows(date_str, fieldnames, updated)
    return updated


def scenario_key_from_row(row):
    sid = (row.get("scenario_id") or "").strip()
    if sid in SCENARIOS:
        return sid
    name = (row.get("scenario_name") or "").strip()
    for k, sc in SCENARIOS.items():
        label = f"{sc['name_fa']} ({sc['name_en']})"
        if name == label or sc["name_fa"] in name:
            return k
    return "UNKNOWN"


def collect_rows_for_report(date_list):
    all_rows = []
    for d in date_list:
        rows, _ = read_csv_rows(d)
        for r in rows:
            r["_file_date"] = d
            all_rows.append(r)
    return all_rows


def fmt_signal_line(r):
    sym = r.get("symbol", "")
    direction = r.get("direction", "")
    entry = r.get("entry_price", "")
    status = r.get("status", "")
    pnl = r.get("final_pnl_usd") or "0"
    ret = r.get("return_pct") or "0"
    issued = (r.get("issued_at_tehran") or "")[:16]
    try:
        pnl_s = f"{float(pnl):+.4f}$"
    except Exception:
        pnl_s = f"{pnl}$"
    try:
        ret_s = f"{float(ret):+.3f}%"
    except Exception:
        ret_s = f"{ret}%"
    try:
        entry_s = f"{float(entry):.4f}"
    except Exception:
        entry_s = str(entry)
    return f"• {sym} {direction} @ {entry_s} → {status} | PnL {pnl_s} | بازده {ret_s} | {issued}"


def build_six_messages(report_date: str, rows):
    today_rows = [r for r in rows if r.get("_file_date") == report_date]

    def stats(rs):
        tp = sum(1 for r in rs if r.get("status") == "TP_HIT")
        sl = sum(1 for r in rs if r.get("status") == "STOP_HIT")
        man = sum(1 for r in rs if r.get("status") == "CLOSED_MANUAL")
        op = sum(1 for r in rs if r.get("status") == "OPEN")
        closed = tp + sl
        wr = (100.0 * tp / closed) if closed else 0.0
        pnl = sum(_f(r.get("final_pnl_usd")) for r in rs if r.get("status") in ("TP_HIT", "STOP_HIT", "CLOSED_MANUAL"))
        return tp, sl, man, op, wr, pnl

    tp, sl, man, op, wr, pnl = stats(today_rows)
    msgs = []

    msg1 = (
        f"🌙 گزارش شبانه PentaSignal\n"
        f"📅 {report_date}\n\n"
        f"── خلاصه روز ──\n"
        f"سیگنال ثبت‌شده امروز: {len(today_rows)}\n"
        f"TP: {tp}\n"
        f"SL: {sl}\n"
        f"CLOSED_MANUAL: {man}\n"
        f"باز مانده: {op}\n"
        f"وین‌ریت : {wr:.1f}%\n"
        f"PnL تقریبی: {pnl:+.2f} USD\n"
        f"(فرض: پوزیشن 10$ | کارمزد 0.2%)\n"
    )
    if len(today_rows) == 0:
        msg1 += "\nامروز سیگنال جدیدی ثبت نشده است.\n"
    msgs.append(msg1)

    by_sc = defaultdict(list)
    for r in rows:
        by_sc[scenario_key_from_row(r)].append(r)

    for sid in ACTIVE_SCENARIOS:
        sc = SCENARIOS[sid]
        title = f"{sc['name_fa']} ({sc['name_en']})"
        personality = sc.get("personality", "")
        sc_rows_today = [r for r in by_sc.get(sid, []) if r.get("_file_date") == report_date]
        sc_rows_all = by_sc.get(sid, [])
        older_closed = [
            r for r in sc_rows_all
            if r.get("_file_date") != report_date and r.get("status") in ("TP_HIT", "STOP_HIT", "CLOSED_MANUAL")
        ]
        tp, sl, man, op, wr, pnl = stats(sc_rows_today)
        body = (
            f"🏆 سناریو {title}\n"
            f"🎭 {personality}\n\n"
            f"سیگنال امروز: {len(sc_rows_today)}\n"
            f"TP: {tp}\n"
            f"SL: {sl}\n"
            f"CLOSED_MANUAL: {man}\n"
            f"باز مانده: {op}\n"
            f"وین‌ریت : {wr:.1f}%\n"
            f"PnL تقریبی: {pnl:+.4f} USD\n"
        )
        if not sc_rows_today and not older_closed:
            body += "\nامروز و در پیگیری ۲ روزه موردی نبود.\n"
        else:
            body += "\nسیگنال‌ها:\n"
            for r in sorted(sc_rows_today, key=lambda x: x.get("issued_at_tehran") or ""):
                body += fmt_signal_line(r) + "\n"
            if older_closed:
                body += "\n── تعیین‌تکلیف از روزهای قبل ──\n"
                for r in sorted(older_closed, key=lambda x: x.get("issued_at_tehran") or ""):
                    body += fmt_signal_line(r) + "\n"
        msgs.append(body)

    return msgs


def cleanup_old_files(keep_days=10):
    if not os.path.isdir(SIGNALS_DIR):
        return 0
    now = tehran_now().date()
    deleted = 0
    for name in os.listdir(SIGNALS_DIR):
        if not name.endswith(".csv"):
            continue
        try:
            file_date = datetime.strptime(name.replace(".csv", ""), "%Y-%m-%d").date()
        except ValueError:
            continue
        if (now - file_date).days > keep_days:
            try:
                os.remove(os.path.join(SIGNALS_DIR, name))
                deleted += 1
                print(f"deleted old: {name}")
            except Exception as e:
                print(f"delete error {name}: {e}")
    return deleted


def main():
    now = tehran_now()
    report_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    d0 = report_date
    d1 = (now - timedelta(days=2)).strftime("%Y-%m-%d")
    d2 = (now - timedelta(days=3)).strftime("%Y-%m-%d")
    date_list = [d2, d1, d0]

    print("=" * 60)
    print(f"Nightly monitor — report_date={report_date}")
    print(f"Scanning: {date_list}")
    print("=" * 60)

    for d in date_list:
        print(f"\n--- update {d} ---")
        update_open_rows_for_date(d, now)

    rows = collect_rows_for_report(date_list)
    messages = build_six_messages(report_date, rows)

    async def send_all():
        for i, msg in enumerate(messages, 1):
            print(f"\n===== MSG {i}/{len(messages)} =====")
            print(msg[:800])
            await send_to_telegram(msg)
            await asyncio.sleep(0.5)

    asyncio.run(send_all())

    # نگهداری لاگ سیگنال: ۳ ماه غلتان
    deleted_signals = cleanup_old_files(90)
    print(f"signals cleanup: deleted {deleted_signals} files older than 90 days")

    # آپدیت فشرده OHLCV برای بک‌تست (Parquet) + trim ۹۰ روز
    try:
        from ohlcv_store import update_all_symbols
        print("\n--- OHLCV nightly update ---")
        ohlcv_summary = update_all_symbols()
        print(f"OHLCV summary: {ohlcv_summary}")
    except Exception as e:
        print(f"OHLCV update skipped/error: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
