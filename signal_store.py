import os
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

SIGNALS_DIR = "signals"

# ستون‌های CSV — scenario به‌جای risk_level
CSV_HEADERS = [
    "symbol", "direction", "scenario_id", "scenario_name",
    "entry_price", "stop_loss", "take_profit",
    "issued_at_tehran", "status", "hit_time_tehran", "hit_price",
    "broker_fee", "final_pnl_usd", "position_size_usd", "return_pct",
    "signal_source"
]


def ensure_dir():
    if not os.path.isdir(SIGNALS_DIR):
        os.makedirs(SIGNALS_DIR, exist_ok=True)


def tehran_date_str(dt=None):
    tz = ZoneInfo("Asia/Tehran")
    now = datetime.now(tz) if dt is None else dt.astimezone(tz)
    return now.strftime("%Y-%m-%d")


def tehran_time_str(dt=None):
    tz = ZoneInfo("Asia/Tehran")
    now = datetime.now(tz) if dt is None else dt.astimezone(tz)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def daily_csv_path(date_str=None):
    ensure_dir()
    d = tehran_date_str() if date_str is None else date_str
    return os.path.join(SIGNALS_DIR, f"{d}.csv")


def append_signal_row(
    symbol,
    direction,
    entry_price,
    stop_loss,
    take_profit,
    issued_at_tehran,
    signal_source,
    scenario_id="",
    scenario_name="",
    position_size_usd=10.0,
    # سازگاری با فراخوانی قدیمی
    risk_level_name=None,
):
    """ثبت یک سیگنال در CSV روزانه. risk_level_name نادیده گرفته می‌شود (حذف شده)."""
    path = daily_csv_path()
    file_exists = os.path.isfile(path)

    # اگر فایل قدیمی با هدر risk_level وجود دارد، با همان هدر جدید می‌نویسیم
    # (فایل‌های جدید همیشه هدر جدید دارند)
    row = {
        "symbol": symbol,
        "direction": direction,
        "scenario_id": scenario_id or "",
        "scenario_name": scenario_name or "",
        "entry_price": f"{entry_price:.8f}",
        "stop_loss": f"{stop_loss:.8f}",
        "take_profit": f"{take_profit:.8f}",
        "issued_at_tehran": issued_at_tehran,
        "status": "OPEN",
        "hit_time_tehran": "",
        "hit_price": "",
        "broker_fee": "",
        "final_pnl_usd": "",
        "position_size_usd": f"{position_size_usd:.2f}",
        "return_pct": "",
        "signal_source": signal_source,
    }

    # اگر فایل از قبل با هدر قدیمی است، ستون‌های موجود را حفظ کن
    write_headers = CSV_HEADERS
    if file_exists:
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                existing = next(reader, None)
            if existing:
                write_headers = existing
                # پر کردن فیلدهای مفقود
                for h in write_headers:
                    if h not in row:
                        row[h] = ""
                # map قدیمی risk_level اگر لازم
                if "risk_level" in write_headers and "risk_level" not in row:
                    row["risk_level"] = ""
        except Exception:
            write_headers = CSV_HEADERS

    with open(path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=write_headers, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow({h: row.get(h, "") for h in write_headers})

    return path
