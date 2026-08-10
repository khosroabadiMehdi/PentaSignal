# bot.py — PentaSignal
# رفتار و زمان‌بندی دقیقاً مطابق پروژه قبلی

import aiohttp
import asyncio
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from config import SYMBOLS, SCENARIOS, ACTIVE_SCENARIOS
from indicators import calculate_rsi, calculate_ema, calculate_macd, calculate_atr
from rules import generate_signal

# ========== تنظیمات لاگ ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot_log.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

KUCOIN_URL = "https://api.kucoin.com/api/v1/market/candles"

intervals = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1hour",
    "4h": "4hour"
}


async def fetch_timeframe(session, symbol, tf, days):
    api_tf = intervals[tf]
    end_time = int(datetime.utcnow().timestamp())
    start_time = end_time - days * 24 * 3600
    params = {"symbol": symbol, "type": api_tf, "startAt": start_time, "endAt": end_time}
    try:
        async with session.get(KUCOIN_URL, params=params, timeout=30) as resp:
            if resp.status == 200:
                data = await resp.json()
                candles_raw = data.get("data", [])
                parsed = [
                    {'t': int(c[0]), 'o': float(c[1]), 'c': float(c[2]),
                     'h': float(c[3]), 'l': float(c[4]), 'v': float(c[5])}
                    for c in candles_raw
                ]
                return tf, list(reversed(parsed))
            else:
                logger.warning(f"خطای HTTP {resp.status} برای {symbol} {tf}")
                return tf, []
    except Exception as e:
        logger.error(f"خطا در دریافت {symbol} {tf}: {e}")
        return tf, []


async def fetch_all_timeframes(session, symbol):
    settings = {
        "1m": 1,
        "5m": 3,
        "15m": 5,
        "30m": 7,
        "1h": 14,
        "4h": 45
    }
    tasks = [fetch_timeframe(session, symbol, tf, days) for tf, days in settings.items()]
    results = await asyncio.gather(*tasks)
    data = {}
    for tf, candles in results:
        data[tf] = candles
    return data


async def process_symbol(symbol, data, idx, total):
    logger.info(f"[{idx}/{total}] بررسی {symbol} ...")

    if not data.get("30m") or len(data["30m"]) < 60:
        logger.warning(f"داده ۳۰ دقیقه ناکافی برای {symbol}")
        return

    closes_30 = [c['c'] for c in data["30m"]]
    ema21_30m = calculate_ema(closes_30, 21)
    ema50_30m = calculate_ema(closes_30, 50)
    ema8_30m = calculate_ema(closes_30, 8)

    if ema21_30m is None or ema50_30m is None:
        logger.warning(f"EMA ناکافی برای {symbol}")
        return

    direction = "LONG" if ema21_30m > ema50_30m else "SHORT"

    candle_1m = data.get("1m", [{}])[-1] if data.get("1m") else {}
    open_1m = candle_1m.get("o", closes_30[-1])
    close_1m = candle_1m.get("c", closes_30[-1])
    high_1m = candle_1m.get("h", closes_30[-1])
    low_1m = candle_1m.get("l", closes_30[-1])

    candle_5m = data.get("5m", [{}])[-1] if data.get("5m") else {}
    open_5m = candle_5m.get("o", closes_30[-1])
    close_5m = candle_5m.get("c", closes_30[-1])
    high_5m = candle_5m.get("h", closes_30[-1])
    low_5m = candle_5m.get("l", closes_30[-1])

    closes_1h = [c['c'] for c in data.get("1h", [])]
    ema21_1h = calculate_ema(closes_1h, 21) if closes_1h else None
    ema50_1h = calculate_ema(closes_1h, 50) if closes_1h else None

    closes_4h = [c['c'] for c in data.get("4h", [])]
    ema21_4h = calculate_ema(closes_4h, 21) if closes_4h else None
    ema50_4h = calculate_ema(closes_4h, 50) if closes_4h else None
    ema200_4h = calculate_ema(closes_4h, 200) if closes_4h else None

    macd_30m = calculate_macd(closes_30)
    rsi_30m = calculate_rsi(closes_30)
    atr_30m = calculate_atr(data["30m"]) if "30m" in data else None
    price_30m = closes_30[-1]

    candle_15 = data.get("15m", [{}])[-1] if data.get("15m") else {}
    open_15m = candle_15.get("o", price_30m)
    close_15m = candle_15.get("c", price_30m)
    high_15m = candle_15.get("h", price_30m)
    low_15m = candle_15.get("l", price_30m)

    # اجرای هر ۵ سناریو برای این نماد
    for scenario_id in ACTIVE_SCENARIOS:
        scenario = SCENARIOS.get(scenario_id)
        if not scenario:
            continue

        # فیلتر نماد: فقط اگر در لیست سناریو باشد
        symbols_list = scenario.get("symbols_list") or []
        if symbol not in symbols_list:
            continue

        # اگر سناریو فقط یک جهت دارد و جهت فعلی فرق دارد، رد
        direction_only = scenario.get("direction_only")
        if direction_only and direction != direction_only:
            continue

        prefer_risk = "LOW" if scenario.get("rule_profile", "strict") == "strict" else "MEDIUM"

        try:
            signal = await generate_signal(
                symbol=symbol,
                direction=direction,
                prefer_risk=prefer_risk,
                price_30m=price_30m,
                open_15m=open_15m, close_15m=close_15m,
                high_15m=high_15m, low_15m=low_15m,
                open_5m=open_5m, close_5m=close_5m,
                high_5m=high_5m, low_5m=low_5m,
                open_1m=open_1m, close_1m=close_1m,
                high_1m=high_1m, low_1m=low_1m,
                ema21_30m=ema21_30m, ema50_30m=ema50_30m, ema8_30m=ema8_30m,
                ema21_1h=ema21_1h, ema50_1h=ema50_1h,
                ema21_4h=ema21_4h, ema50_4h=ema50_4h, ema200_4h=ema200_4h,
                macd_line_30m=macd_30m.get("macd") if macd_30m else None,
                hist_30m=macd_30m.get("histogram") if macd_30m else None,
                rsi_30m=rsi_30m,
                atr_val_30m=atr_30m or 0.0,
                curr_vol=data["30m"][-1].get("v", 0.0),
                avg_vol_30m=0.0,
                divergence_detected=False,
                candles=data["30m"],
                prices_series_30m=closes_30[-120:],
                closes_by_tf=data,
                scenario_id=scenario_id,
            )
            if signal and signal.get("status") == "SIGNAL":
                logger.info(
                    f"✅ [{scenario_id}] سیگنال {symbol}: {signal['direction']} | "
                    f"قیمت={signal['price']:.4f} | {scenario['name_fa']}"
                )
            else:
                logger.info(f"📭 [{scenario_id}] بدون سیگنال برای {symbol}")
        except Exception as e:
            logger.error(f"❌ خطا در سناریو {scenario_id} برای {symbol}: {e}")


async def main_async():
    logger.info("=" * 60)
    logger.info("PentaSignal — شروع سیکل بررسی")
    logger.info(f"سناریوهای فعال: {', '.join(ACTIVE_SCENARIOS)}")
    logger.info(f"تعداد نماد: {len(SYMBOLS)}")
    logger.info("=" * 60)

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_all_timeframes(session, sym) for sym in SYMBOLS]
        results = await asyncio.gather(*tasks)
        for idx, data in enumerate(results, 1):
            await process_symbol(SYMBOLS[idx - 1], data, idx, len(SYMBOLS))

    logger.info("پایان سیکل PentaSignal")


if __name__ == "__main__":
    asyncio.run(main_async())
