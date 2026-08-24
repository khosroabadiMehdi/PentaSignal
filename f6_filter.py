# f6_filter.py — محدودیت کلاستر استاپ هم‌جهت در یک روز (Tehran)
# قانون: اگر در همان روز تهران، حداقل MAX_SL_SAME_DIR استاپ قطعی
# در یک جهت ثبت شده باشد، سیگنال جدید در همان جهت صادر نشود.
#
# بک‌تست تاریخی: WR≈76٪ با حفظ بخش عمده PnL و کاهش شدید ضرر روزهای کلاستر.

from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Tuple
from zoneinfo import ZoneInfo

SIGNALS_DIR = "signals"
MAX_SL_SAME_DIR = 2  # بعد از ۲ استاپ هم‌جهت در روز، جهت قفل می‌شود


def _tehran_today() -> str:
    return datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d")


def _daily_path(date_str: str | None = None) -> str:
    d = date_str or _tehran_today()
    return os.path.join(SIGNALS_DIR, f"{d}.csv")


def count_stop_hits_today(direction: str, date_str: str | None = None) -> int:
    """
    تعداد استاپ‌های یکتا (نماد+ورود+جهت) با status=STOP_HIT در همان روز.
    تکراری سناریو روی یک ورود، یک‌بار شمرده می‌شود.
    """
    path = _daily_path(date_str)
    if not os.path.isfile(path):
        return 0
    seen = set()
    count = 0
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row.get("direction") or "").upper() != direction.upper():
                    continue
                if (row.get("status") or "").upper() != "STOP_HIT":
                    continue
                key = (
                    row.get("symbol") or "",
                    row.get("entry_price") or "",
                    (row.get("direction") or "").upper(),
                )
                if key in seen:
                    continue
                seen.add(key)
                count += 1
    except Exception:
        return count
    return count


def is_f6_blocked(direction: str, date_str: str | None = None) -> Tuple[bool, int]:
    """
    Returns (blocked, stop_count).
    blocked=True یعنی نباید سیگنال جدید در این جهت صادر شود.
    """
    n = count_stop_hits_today(direction, date_str)
    return (n >= MAX_SL_SAME_DIR, n)
