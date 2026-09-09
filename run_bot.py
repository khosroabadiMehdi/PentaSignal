# run_bot.py — اجرای PentaSignal v3
# --mode signal : 07:00–20:00 تهران، تعیین تکلیف + صدور سیگنال
# --mode settle : 20:00–01:00 تهران، فقط تعیین تکلیف
# --mode nightly: 02:00 تهران، فقط گزارش شبانه
# --once         : یک اجرای امن برای GitHub Actions

import os
import sys
import time
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pentasignal import settings, kucoin, scenarios, state
from pentasignal.engine import Engine
from pentasignal.telegram import send_sync
from pentasignal.ohlcv_store import append_candles, load as load_ohlcv, prune as prune_ohlcv
from pentasignal.utils import tehran_now, ts_to_tehran

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(settings.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ps.run")


class LiveSender:
    def __init__(self):
        self.n = 0

    def __call__(self, text, reply_to=None):
        self.n += 1
        logger.info("--- TELEGRAM #%d (reply_to=%s) ---\n%s", self.n, reply_to, text)
        return send_sync(text, reply_to)


def current_mode(now=None):
    now = now or tehran_now()
    h, m = now.hour, now.minute
    if h == settings.NIGHTLY_REPORT_HOUR and 0 <= m < 30:
        return "nightly"
    if settings.NEW_SIGNAL_START_HOUR <= h < settings.NEW_SIGNAL_END_HOUR:
        return "signal"
    # 20:00 تا 00:59 فقط تسویه؛ 01:00 به بعد تا 01:59 هم تسویه نیست.
    if h >= settings.SETTLE_ONLY_START_HOUR or (h < settings.SETTLE_ONLY_END_HOUR) or (h == settings.SETTLE_ONLY_END_HOUR and m == 0):
        return "settle"
    return "idle"


def fetch_market(now_ts: int, mode: str) -> scenarios.MarketContext:
    """دریافت داده بسته‌شده؛ 30m برای تشخیص، 1m برای خروج و آرشیو."""
    candles30 = {}
    candles1m = {}

    # در پنجره عملیاتی، همه 21 نماد هر تیک داده 1m خود را تازه می‌کنند.
    for sym in scenarios.UNION_SYMBOLS:
        try:
            if mode == "signal":
                candles30[sym] = kucoin.fetch_recent(
                    sym, settings.CANDLE_TYPE_30M, settings.LOOKBACK_DAYS_30M,
                    now_ts=now_ts)
            # 45 دقیقه آخر کافی است برای به‌روزرسانی آرشیو؛ settlement تاریخچه را از data/ohlcv می‌خواند.
            c1 = kucoin.fetch_recent_minutes(
                sym, "1min", settings.OHLCV_RECENT_MINUTES, now_ts=now_ts)
            candles1m[sym] = c1
            append_candles(sym, c1, closed_before_ts=now_ts - (now_ts % 60))
        except Exception as e:
            logger.error("fetch 1m %s failed: %s", sym, e)
            candles1m[sym] = []
        if mode == "signal":
            time.sleep(0.10)

    btc4h = []
    if mode == "signal":
        try:
            btc4h = kucoin.fetch_recent("BTC-USDT", settings.CANDLE_TYPE_4H,
                                        settings.LOOKBACK_DAYS_4H, now_ts=now_ts)
        except Exception as e:
            logger.error("fetch 4h BTC failed: %s", e)

    # برای خروج، آرشیو محلی 90 روزه را با تکه تازه ادغام می‌کنیم.
    if mode in ("signal", "settle"):
        # فقط نمادهای دارای پوزیشن باز، تاریخچه 1m را کامل از آرشیو می‌گیرند؛
        # آرشیو همه 21 نماد همچنان در بالا به‌روز شده است.
        open_symbols = {r["symbol"] for r in __import__("pentasignal.store", fromlist=["open_signals"]).open_signals()}
        for sym in open_symbols:
            candles1m[sym] = load_ohlcv(sym)

    return scenarios.MarketContext(candles30, btc_4h=btc4h, candles1m=candles1m)


def live_entry_price(symbol: str, at_ts: int):
    try:
        px = kucoin.fetch_ticker(symbol)
        if px:
            return px
    except Exception:
        pass
    try:
        c = kucoin.fetch_recent(symbol, settings.CANDLE_TYPE_30M, 2)
        return c[-1]["c"] if c else None
    except Exception:
        return None


def run_once(engine: Engine, forced_mode: str | None = None) -> int:
    now = tehran_now()
    mode = forced_mode or current_mode(now)
    if mode == "idle":
        logger.info("outside operational windows @ %s — skip", now.strftime("%Y-%m-%d %H:%M:%S"))
        return 0

    # گزارش 02:00 مستقل از تیک‌های بازار است.
    if mode == "nightly":
        log = engine.nightly(now)
        if log:
            logger.info("nightly report sent → msg_id=%s", log.message_id)
            prune_ohlcv()
            return 1
        prune_ohlcv()
        return 0

    ts = int(now.timestamp())
    # نزدیک‌ترین مرز بسته‌شدن 30m برای تشخیص؛ برای settle، زمان فعلی کف دقیقه است.
    close_ts = ts - (ts % (1800 if mode == "signal" else 60))
    close_dt = ts_to_tehran(close_ts)
    ctx = fetch_market(ts, mode)
    if mode == "signal":
        logs = engine.on_candle_close(close_dt, ctx, allow_new=True, run_nightly=False)
    else:
        # در 20:00–01:00 هیچ سیگنال جدیدی صادر نمی‌شود.
        logs = engine.settle_all(close_dt, ctx)
    for lg in logs:
        logger.info("sent %s (%s) → msg_id=%s", lg.kind, lg.signal_id or "-", lg.message_id)
    prune_ohlcv()
    logger.info("tick mode=%s @ %s → %d event(s)", mode, now.strftime("%Y-%m-%d %H:%M:%S"), len(logs))
    return len(logs)


async def main_loop(engine: Engine):
    logger.info("PentaSignal v%s — live loop start | DRY_RUN=%s", settings.VERSION, settings.DRY_RUN)
    state.set_key("last_start", tehran_now().strftime("%Y-%m-%d %H:%M:%S"))
    while True:
        try:
            now = tehran_now()
            secs = now.minute * 60 + now.second
            since_boundary = secs % 1800
            wait = (settings.CANDLE_CLOSE_SKEW - since_boundary) if since_boundary < settings.CANDLE_CLOSE_SKEW else (1800 - since_boundary + settings.CANDLE_CLOSE_SKEW)
            await asyncio.sleep(max(1, wait))
            run_once(engine)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.exception("tick error: %s", e)
            await asyncio.sleep(30)


def main():
    sender = LiveSender()
    engine = Engine(sender=sender, entry_price_provider=live_entry_price)
    forced = None
    if "--signal" in sys.argv:
        forced = "signal"
    elif "--settle" in sys.argv:
        forced = "settle"
    elif "--nightly" in sys.argv:
        forced = "nightly"
    if "--once" in sys.argv:
        n = run_once(engine, forced_mode=forced)
        logger.info("one-shot done: %d event(s)", n)
    else:
        asyncio.run(main_loop(engine))


if __name__ == "__main__":
    main()
