# diagnose_yesterday.py — چرا روز 2026-09-07 منفی شد؟ تحلیل معامله‌به‌معامله
import json
import os
from collections import defaultdict

d = json.load(open(os.path.join(os.path.dirname(__file__), "sim_result.json"), encoding="utf-8"))
rows = d["settled_rows"]

by_sc = defaultdict(lambda: {"n": 0, "pnl": 0.0, "wins": 0})
print("== معامله‌های تعیین‌تکلیف‌شده دیروز ==")
for r in sorted(rows, key=lambda x: x["exit_time_tehran"]):
    pnl = float(r["pnl_usd"] or 0)
    s = by_sc[r["scenario_id"]]
    s["n"] += 1
    s["pnl"] += pnl
    s["wins"] += 1 if pnl > 0 else 0
    print(f'{r["exit_time_tehran"][11:16]} #{r["scenario_id"]} {r["symbol"]:<11} {r["direction"]:<5} '
          f'{r["exit_reason"]:<3} held={r.get("cm_candles")} pnl={pnl:+.3f}$ ret={float(r["return_pct"]):+.3f}% '
          f'entry={float(r["entry_price"]):.6g} exit={float(r["exit_price"]):.6g}')

print("\n== جمع‌بندی سناریو ==")
for sid, s in by_sc.items():
    print(f'#{sid}: n={s["n"]} wins={s["wins"]} pnl={s["pnl"]:+.3f}$')

fees = sum(float(r["fee_usd"] or 0) for r in rows)
print(f"\nکارمزد کل: {fees:.3f}$ | تعداد کل: {len(rows)}")

# چند تا از خروج‌های SL در واقع با سود بسته شدند؟ (تریلینگ)
sl_rows = [r for r in rows if r["exit_reason"] == "SL"]
sl_profit = [r for r in sl_rows if float(r["pnl_usd"]) > 0]
print(f"خروج‌های SL(تریلینگ): {len(sl_rows)} | از اینها با سود: {len(sl_profit)}")
# طول نگهداری
import statistics
mins = []
for r in rows:
    from datetime import datetime
    t1 = datetime.strptime(r["issued_at_tehran"], "%Y-%m-%d %H:%M:%S")
    t2 = datetime.strptime(r["exit_time_tehran"], "%Y-%m-%d %H:%M:%S")
    mins.append((t2 - t1).total_seconds() / 60)
print(f"میانه نگهداری: {statistics.median(mins):.0f} دقیقه | میانگین: {statistics.mean(mins):.0f} دقیقه")
