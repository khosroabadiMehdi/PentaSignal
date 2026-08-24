# ohlcv_store.py — ذخیره فشرده کندل برای بک‌تست (Parquet) + آپدیت شبانه
# تایم‌فریم‌ها: 5m, 15m, 30m, 1h, 4h | نگهداری: ۹۰ روز غلتان

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pandas as pd
import requests

from config import SYMBOLS

KUCOIN_URL = "https://api.kucoin.com/api/v1/market/candles"
OHLCV_DIR = os.path.join("data", "ohlcv")
KEEP_DAYS = 90
TIMEFRAMES = {
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1hour",
    "4h": "4hour",
}
# حداکثر شمع در هر درخواست KuCoin
MAX_CANDLES_PER_REQ = 1500
SECONDS_PER_CANDLE = {
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
}


def ensure_dir() -> None:
    os.makedirs(OHLCV_DIR, exist_ok=True)


def parquet_path(symbol: str, tf: str) -> str:
    safe = symbol.replace("/", "-")
    return os.path.join(OHLCV_DIR, f"{safe}_{tf}.parquet")


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["t", "o", "h", "l", "c", "v"])


def load_ohlcv(symbol: str, tf: str) -> pd.DataFrame:
    path = parquet_path(symbol, tf)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return _empty_df()
    try:
        df = pd.read_parquet(path)
        if df is None or df.empty:
            return _empty_df()
        for col in ("t", "o", "h", "l", "c", "v"):
            if col not in df.columns:
                return _empty_df()
        df = df.sort_values("t").drop_duplicates(subset=["t"], keep="last")
        return df.reset_index(drop=True)
    except Exception as e:
        print(f"load_ohlcv error {symbol} {tf}: {e}")
        return _empty_df()


def save_ohlcv(symbol: str, tf: str, df: pd.DataFrame) -> str:
    ensure_dir()
    path = parquet_path(symbol, tf)
    if df is None or df.empty:
        return path
    df = df.sort_values("t").drop_duplicates(subset=["t"], keep="last").copy()
    df["t"] = pd.to_numeric(df["t"], errors="coerce")
    df = df.dropna(subset=["t"])
    df["t"] = df["t"].astype("int64")
    for col in ("o", "h", "l", "c", "v"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["o", "h", "l", "c"]).reset_index(drop=True)
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).timestamp())
    df = df[df["t"] >= cutoff].reset_index(drop=True)
    if df.empty:
        return path
    # نوشتن با pyarrow (در بعضی محیط‌ها pandas.to_parquet فایل صفر می‌سازد)
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, path, compression="snappy")
    except Exception as e:
        print(f"save_ohlcv pyarrow error {symbol} {tf}: {e}")
        # fallback: نوشتن در /tmp و کپی
        import tempfile
        import shutil
        fd, tmp_path = tempfile.mkstemp(suffix=".parquet")
        os.close(fd)
        try:
            df.to_parquet(tmp_path, index=False, compression="snappy")
            shutil.copyfile(tmp_path, path)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    return path


def fetch_kucoin_range(symbol: str, tf: str, start_ts: int, end_ts: int) -> List[dict]:
    """دریافت کندل با صفحه‌بندی تا پوشش کامل بازه."""
    api_type = TIMEFRAMES[tf]
    sec = SECONDS_PER_CANDLE[tf]
    all_rows: List[dict] = []
    cursor = int(start_ts)
    end_ts = int(end_ts)
    safety = 0
    while cursor < end_ts and safety < 200:
        safety += 1
        chunk_end = min(cursor + MAX_CANDLES_PER_REQ * sec, end_ts)
        params = {
            "symbol": symbol,
            "type": api_type,
            "startAt": cursor,
            "endAt": chunk_end,
        }
        try:
            r = requests.get(KUCOIN_URL, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(12)
                continue
            if r.status_code != 200:
                print(f"HTTP {r.status_code} {symbol} {tf} {cursor}-{chunk_end}")
                break
            data = r.json().get("data") or []
            if not data:
                cursor = chunk_end
                continue
            for c in data:
                all_rows.append(
                    {
                        "t": int(c[0]),
                        "o": float(c[1]),
                        "c": float(c[2]),
                        "h": float(c[3]),
                        "l": float(c[4]),
                        "v": float(c[5]),
                    }
                )
            # KuCoin معمولاً نزولی برمی‌گرداند
            oldest = min(int(c[0]) for c in data)
            newest = max(int(c[0]) for c in data)
            if newest < cursor + sec:
                cursor = chunk_end
            else:
                cursor = newest + sec
            time.sleep(0.15)
        except Exception as e:
            print(f"fetch error {symbol} {tf}: {e}")
            time.sleep(2)
            break
    return all_rows


def bootstrap_symbol_tf(symbol: str, tf: str, days: int = KEEP_DAYS) -> int:
    end_ts = int(datetime.now(timezone.utc).timestamp())
    start_ts = end_ts - days * 24 * 3600
    rows = fetch_kucoin_range(symbol, tf, start_ts, end_ts)
    if not rows:
        return 0
    df = pd.DataFrame(rows)
    save_ohlcv(symbol, tf, df)
    return len(df)


def update_symbol_tf(symbol: str, tf: str) -> int:
    """آپدیت از آخرین timestamp موجود تا الان؛ اگر فایل خالی بود bootstrap کوتاه."""
    df = load_ohlcv(symbol, tf)
    end_ts = int(datetime.now(timezone.utc).timestamp())
    if df.empty:
        return bootstrap_symbol_tf(symbol, tf, days=KEEP_DAYS)
    last_t = int(df["t"].max())
    # کمی همپوشانی برای کندل ناقص
    start_ts = max(0, last_t - SECONDS_PER_CANDLE[tf] * 2)
    if start_ts >= end_ts:
        save_ohlcv(symbol, tf, df)
        return 0
    rows = fetch_kucoin_range(symbol, tf, start_ts, end_ts)
    if not rows:
        save_ohlcv(symbol, tf, df)  # فقط trim قدیمی
        return 0
    new_df = pd.DataFrame(rows)
    merged = pd.concat([df, new_df], ignore_index=True)
    before = len(df)
    save_ohlcv(symbol, tf, merged)
    after = len(load_ohlcv(symbol, tf))
    return max(0, after - before)


def update_all_symbols(symbols: Optional[List[str]] = None) -> dict:
    symbols = symbols or list(SYMBOLS)
    summary = {"files": 0, "new_rows": 0, "errors": 0}
    for sym in symbols:
        for tf in TIMEFRAMES:
            try:
                n = update_symbol_tf(sym, tf)
                summary["files"] += 1
                summary["new_rows"] += n
                print(f"OHLCV update {sym} {tf}: +{n}")
            except Exception as e:
                summary["errors"] += 1
                print(f"OHLCV update fail {sym} {tf}: {e}")
    return summary


def bootstrap_all(symbols: Optional[List[str]] = None, days: int = KEEP_DAYS) -> dict:
    symbols = symbols or list(SYMBOLS)
    summary = {"ok": 0, "fail": 0, "rows": 0}
    for sym in symbols:
        for tf in TIMEFRAMES:
            try:
                n = bootstrap_symbol_tf(sym, tf, days=days)
                if n:
                    summary["ok"] += 1
                    summary["rows"] += n
                    print(f"bootstrap {sym} {tf}: {n} rows")
                else:
                    summary["fail"] += 1
                    print(f"bootstrap empty {sym} {tf}")
            except Exception as e:
                summary["fail"] += 1
                print(f"bootstrap fail {sym} {tf}: {e}")
            time.sleep(0.2)
    return summary
