# store.py — ذخیره‌سازی CSV سیگنال‌ها/رویدادها + نگهداری غلتان 90 روزه

import csv
import os
import threading
from datetime import timedelta

from . import settings
from .utils import tehran_now, parse_tehran

_lock = threading.Lock()

SIGNAL_HEADERS = [
    "signal_id", "issued_at_tehran", "candle_close_tehran", "symbol", "direction",
    "scenario_id", "entry_price", "stop_loss", "take_profit", "exit_mode",
    "exit_param", "sl_atr_mult", "cm_candles", "atr", "entry_candle_ts", "position_size_usd",
    "risk_pct", "status", "exit_price", "exit_time_tehran", "exit_reason",
    "pnl_usd", "return_pct", "fee_usd", "r_multiple", "be_armed", "be_price",
    "telegram_message_id", "settle_message_id", "last_check_ts", "notes",
]

EVENT_HEADERS = [
    "ts_tehran", "signal_id", "event", "detail", "message_id", "reply_to_message_id",
]


def _ensure(path, headers):
    if not os.path.isfile(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)


def init():
    _ensure(settings.SIGNALS_CSV, SIGNAL_HEADERS)
    _ensure(settings.EVENTS_CSV, EVENT_HEADERS)


def read_all(path, headers):
    init()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def _write_all(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in headers})


def append_signal(row: dict) -> str:
    init()
    with _lock:
        with open(settings.SIGNALS_CSV, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SIGNAL_HEADERS, extrasaction="ignore")
            w.writerow({h: row.get(h, "") for h in SIGNAL_HEADERS})
    return settings.SIGNALS_CSV


def append_event(ts_tehran: str, signal_id: str, event: str, detail: str = "",
                 message_id: str = "", reply_to: str = ""):
    init()
    with _lock:
        with open(settings.EVENTS_CSV, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([ts_tehran, signal_id, event, detail,
                                    message_id, reply_to])


def update_signal(signal_id: str, **fields):
    """به‌روزرسانی ردیف سیگنال (وضعیت، خروج، message_id و ...)"""
    init()
    with _lock:
        rows = read_all(settings.SIGNALS_CSV, SIGNAL_HEADERS)
        for r in rows:
            if r.get("signal_id") == signal_id:
                for k, v in fields.items():
                    r[k] = str(v)
        _write_all(settings.SIGNALS_CSV, SIGNAL_HEADERS, rows)


def get_signal(signal_id: str):
    for r in read_all(settings.SIGNALS_CSV, SIGNAL_HEADERS):
        if r.get("signal_id") == signal_id:
            return r
    return None


def open_signals():
    return [r for r in read_all(settings.SIGNALS_CSV, SIGNAL_HEADERS)
            if (r.get("status") or "OPEN") == "OPEN"]


def all_signals():
    return read_all(settings.SIGNALS_CSV, SIGNAL_HEADERS)


def signals_for_date(date_str: str):
    """سیگنال‌های صادرشده در تاریخ تهران مشخص"""
    return [r for r in all_signals()
            if (r.get("issued_at_tehran") or "").startswith(date_str)]


def has_open(symbol: str, scenario_id: str) -> bool:
    for r in open_signals():
        if r.get("symbol") == symbol and r.get("scenario_id") == scenario_id:
            return True
    return False


def last_signal_time(symbol: str, scenario_id: str):
    """آخرین زمان صدور سیگنال (برای کول‌داون)"""
    best = None
    for r in all_signals():
        if r.get("symbol") == symbol and r.get("scenario_id") == scenario_id:
            t = parse_tehran(r.get("issued_at_tehran", ""))
            if t and (best is None or t > best):
                best = t
    return best


def rotate_90d(keep_days=None) -> dict:
    """چرخش غلتان: ردیف‌های قدیمی‌تر از keep_days به آرشیو می‌روند."""
    keep_days = keep_days or settings.CSV_KEEP_DAYS
    cutoff = tehran_now() - timedelta(days=keep_days)
    moved = {"signals": 0, "events": 0}
    with _lock:
        for path, headers, key in (
            (settings.SIGNALS_CSV, SIGNAL_HEADERS, "issued_at_tehran"),
            (settings.EVENTS_CSV, EVENT_HEADERS, "ts_tehran"),
        ):
            if not os.path.isfile(path):
                continue
            rows = read_all(path, headers)
            keep, old = [], []
            for r in rows:
                t = parse_tehran(r.get(key, ""))
                (old if (t and t < cutoff) else keep).append(r)
            if old:
                arch = os.path.join(settings.ARCHIVE_DIR,
                                    os.path.basename(path).replace(".csv", "_archive.csv"))
                _ensure(arch, headers)
                with open(arch, "a", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
                    for r in old:
                        w.writerow({h: r.get(h, "") for h in headers})
                _write_all(path, headers, keep)
                moved["signals" if "signals" in os.path.basename(path) else "events"] = len(old)
    return moved
