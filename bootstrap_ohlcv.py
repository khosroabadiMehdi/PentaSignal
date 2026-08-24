#!/usr/bin/env python3
# bootstrap_ohlcv.py
# یک‌بار اجرا: دانلود ۳ ماه کندل همه نمادها × تایم‌فریم‌های بک‌تست → Parquet فشرده
#
# اجرا:
#   pip install -r requirements.txt
#   python bootstrap_ohlcv.py
#
# بعد از اتمام، پوشه data/ohlcv/ را commit کن.
# آپدیت‌های بعدی را monitor_nightly انجام می‌دهد.

from ohlcv_store import bootstrap_all, KEEP_DAYS, TIMEFRAMES, OHLCV_DIR
from config import SYMBOLS


def main():
    print("=" * 60)
    print("PentaSignal — Bootstrap OHLCV (one-time)")
    print(f"symbols: {len(SYMBOLS)}")
    print(f"timeframes: {list(TIMEFRAMES.keys())}")
    print(f"keep_days: {KEEP_DAYS}")
    print(f"output: {OHLCV_DIR}/")
    print("=" * 60)
    summary = bootstrap_all(days=KEEP_DAYS)
    print("=" * 60)
    print("DONE", summary)
    print("Commit folder data/ohlcv/ after this run.")
    print("=" * 60)


if __name__ == "__main__":
    main()
