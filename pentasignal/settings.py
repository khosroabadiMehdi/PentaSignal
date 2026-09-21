# settings.py — PentaSignal v3.4.0
# تنظیمات سراسری: نسخه، مسیرها، پنجره‌های زمانی تهران، کارمزد و سایز پوزیشن

import os

VERSION = "3.4.0"

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

# ---------- گاردهای پرتفویی W2 (از v3.3.0) ----------
# پورت هم‌معنای RiskEngine خوسرو در مسیر زنده پنتا:
#   • مدار قطع روزانه: بعد از ضرر تجمعی ≤ -MAX_DAILY_LOSS_R در یک روز تهران،
#     هیچ سیگنال جدیدی تا پایان آن روز صادر نمی‌شود (تسویه پوزیشن‌های باز ادامه دارد)
#   • سقف سراسری پوزیشن باز: با MAX_OPEN_TRADES پوزیشن باز (همه سناریوها)، صدور جدید متوقف می‌شود
# PORTFOLIO_GUARDS=0 → غیرفعال (فقط برای شبیه‌سازی/پژوهش؛ در تولید همیشه روشن بماند)
PORTFOLIO_GUARDS = os.getenv("PORTFOLIO_GUARDS", "1") == "1"
MAX_OPEN_TRADES = int(os.getenv("MAX_OPEN_TRADES", "5"))
MAX_DAILY_LOSS_R = float(os.getenv("MAX_DAILY_LOSS_R", "3.0"))

# ---------- کشف ترند + مشورت AI برای F1 (از v3.4.0) ----------
# خط لوله F1: ترند چندمنبعی (CoinGecko+Binance+F&G) → خواندن اخبار (RSS/CryptoPanic) →
# مشورت AI (تاییدیه نمادها و جهت‌ها) → انتخاب چند ارز → این انتخاب‌ها + ارزهای اصلی
# به چک و تولید سیگنال (RuleSignalEngine) می‌روند و حکم AI در fusion موتور ادغام می‌شود.
# بدون AI_API_KEY → فال‌بک: برترین‌های چندمنبعی + ارزهای اصلی (رایگان، هیچ‌چیز fatal نیست)
F1_DISCOVERY = os.getenv("F1_DISCOVERY", "1") == "1"
F1_MAIN_COINS = [s.strip().upper() for s in os.getenv(
    "F1_MAIN_COINS", "BTC,ETH,BNB,SOL,XRP").split(",") if s.strip()]
F1_DISCOVERY_TOP_N = int(os.getenv("F1_DISCOVERY_TOP_N", "8"))   # سقف انتخاب غیرِ اصلی
F1_AI_SELECT_MIN_CONF = int(os.getenv("F1_AI_SELECT_MIN_CONF", "55"))  # حداقل اطمینان AI برای انتخاب
F1_AI_TTL_HOURS = float(os.getenv("F1_AI_TTL_HOURS", "4.0"))     # کش حکم AI (کنترل هزینه LLM)
F1_NEWS_ENABLED = os.getenv("F1_NEWS_ENABLED", "1") == "1"
F1_NEWS_MAX = int(os.getenv("F1_NEWS_MAX", "10"))
F1_DISCOVERY_TIMEOUT = int(os.getenv("F1_DISCOVERY_TIMEOUT", "8"))  # ثانیه، هر درخواست

# ---------- نگهداری CSV ----------
CSV_KEEP_DAYS = 90           # فایل‌های سیگنال/رویداد 90 روزه غلتان می‌شوند

# ---------- آرشیو OHLCV یک‌دقیقه‌ای ----------
OHLCV_RECENT_MINUTES = 45          # در هر تیک زنده چند دقیقه اخیر را از API می‌گیریم
OHLCV_RETENTION_DAYS = 90          # نگه‌داری غلتان آرشیو 1m
OHLCV_BACKFILL_CHUNK_MINUTES = 720 # اندازه هر تکه در bootstrap (دقیقه)

# ---------- اجرا ----------
LOOP_TICK_SECONDS = 20       # هر 20 ثانیه بیدار شو؛ در بستن کندل 30m عمل کن
CANDLE_CLOSE_SKEW = 4        # چند ثانیه بعد از :00/:30 صبر کن تا کندل بسته شود
