# bootstrap_ohlcv.py — دریافت اولیه 90 روز دیتای 1m همه نمادها
# اجرای دستی: python bootstrap_ohlcv.py [--days 90]

import argparse
import os
import sys
import time
from datetime import timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from pentasignal import settings, scenarios, kucoin  # noqa: E402
from pentasignal.ohlcv_store import append_candles, prune  # noqa: E402
from pentasignal.utils import tehran_now  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=settings.OHLCV_RETENTION_DAYS)
    args = ap.parse_args()
    now = int(tehran_now().timestamp())
    end_ts = now - (now % 60)
    start_ts = end_ts - args.days * 86400
    chunk_seconds = settings.OHLCV_BACKFILL_CHUNK_MINUTES * 60
    print(f"PentaSignal v{settings.VERSION} — bootstrap {args.days}d 1m OHLCV")
    for n, sym in enumerate(scenarios.UNION_SYMBOLS, 1):
        cur = start_ts
        total = 0
        while cur < end_ts:
            nxt = min(cur + chunk_seconds, end_ts)
            try:
                candles = kucoin.fetch_candles(sym, "1min", cur, nxt, use_cache=False)
                total += append_candles(sym, candles, closed_before_ts=end_ts)
                print(f"[{n}/{len(scenarios.UNION_SYMBOLS)}] {sym}: {cur}->{nxt}, bars={len(candles)}")
            except Exception as e:
                print(f"!! {sym} {cur}->{nxt}: {e}", file=sys.stderr)
            cur = nxt
            time.sleep(0.12)
        print(f"DONE {sym}: new={total}")
    removed = prune(args.days)
    print(f"rotation removed {removed} old day files")


if __name__ == "__main__":
    main()
