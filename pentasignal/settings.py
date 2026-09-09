# settings.py — PentaSignal v2.1
# تنظیمات سراسری: نسخه، مسیرها، پنجره‌های زمانی تهران، کارمزد و سایز پوزیشن

import os

VERSION = "3.1.3"

# ---------- مسیرها ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # root پروژه
# برای تست/شبیه‌سازی می‌توان دایرکتوری داده ایزوله تعریف کرد: PS_DATA_DIR=/path
DATA_DIR = os.environ.get("PS_DATA_DIR") or os.path.join(BASE_DIR, "data")
SIGNALS_DIR = os.path.join(DATA_DIR, "signals")
# سازگاری نام‌های قدیمی (دیگر استفاده عملی ندارند)
SIGNALS_CSV = os.path.join(DATA_DIR, "signals.csv")
EVENTS_CSV = os.path.join(DATA_DIR, "events.csv")
EVENTS_DIR = os.path.join(DATA_DIR, "events")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
STATE_JSON = os.path.join(DATA_DIR, "state.json")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
LOG_FILE = os.path.join(DATA_DIR, "bot_log.txt")

for _d in (DATA_DIR, SIGNALS_DIR, REPORTS_DIR, ARCHIVE_DIR, CACHE_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------- تلگرام ----------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# DRY_RUN=1 → پیام‌ها به‌جای ارسال واقعی، در کنسول و فایل لاگ می‌روند
DRY_RUN = os.getenv("DRY_RUN", "1") == "1"

# ---------- بازار / KuCoin ----------
KUCOIN_BASE = "https://api.kucoin.com"
KUCOIN_CANDLES = "/api/v1/market/candles"
KUCOIN_TICKER = "/api/v1/market/orderbook/level1"
CANDLE_TYPE_30M = "30min"
CANDLE_TYPE_4H = "4hour"

# ---------- زمان‌بندی (تهران) ----------
# سیگنال جدید: فقط بین 07:00 تا قبل از 20:00
# 20:00 تا 24:00: فقط تعیین تکلیف سیگنال‌های باز (هیچ سیگنال جدیدی صادر نمی‌شود)
# 24:00 (00:00 تهران روز بعد): اجرای شبانه + گزارش کامل روز گذشته
NEW_SIGNAL_START_HOUR = 7    # inclusive
NEW_SIGNAL_END_HOUR = 20     # exclusive → آخرین کندلِ مجاز: بسته‌شده در 19:30
NIGHTLY_REPORT_HOUR = 2      # گزارش شبانه دقیقاً ساعت 02:00 تهران
SETTLE_ONLY_START_HOUR = 20  # از 20:00 تا 01:00 فقط تعیین تکلیف
SETTLE_ONLY_END_HOUR = 1     # پایان پنجره تسویه در 01:00 روز بعد
SETTLE_ONLY_AFTER_HOUR = 20  # سازگاری با کدهای قدیمی؛ از این ساعت فقط تعیین تکلیف

# ---------- ریسک ----------
POSITION_SIZE_USD = 10.0
FEE_RT = 0.002               # کارمزد رفت‌وبرگشت 0.2٪ (مطابق بک‌تست پنتا)
LOOKBACK_DAYS_30M = 32       # تاریخچه 30m برای اندیکاتورها
LOOKBACK_DAYS_4H = 35        # تاریخچه 4h برای گیت رژیم BTC

# ---------- نگهداری CSV ----------
CSV_KEEP_DAYS = 90           # فایل‌های سیگنال/رویداد 90 روزه غلتان می‌شوند

# ---------- آرشیو OHLCV یک‌دقیقه‌ای ----------
OHLCV_RECENT_MINUTES = 45          # در هر تیک زنده چند دقیقه اخیر را از API می‌گیریم
OHLCV_RETENTION_DAYS = 90          # نگه‌داری غلتان آرشیو 1m
OHLCV_BACKFILL_CHUNK_MINUTES = 720 # اندازه هر تکه در bootstrap (دقیقه)

# ---------- اجرا ----------
LOOP_TICK_SECONDS = 20       # هر 20 ثانیه بیدار شو؛ در بستن کندل 30m عمل کن
CANDLE_CLOSE_SKEW = 4        # چند ثانیه بعد از :00/:30 صبر کن تا کندل بسته شود
