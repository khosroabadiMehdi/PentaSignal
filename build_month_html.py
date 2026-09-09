# build_month_html.py — گزارش HTML ۳۰ روزه از month_result.json
import os
import sys
import json

BASE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(BASE, "month_result.json"), encoding="utf-8"))
t = d["totals"]
days = d["days"]
sc = d["by_scenario"]
sc_names = {"F1": "شکست دونچیان + گیت رژیم", "F2": "کرش-شورت با گیت افت",
            "F3": "سوئینگ کافمن ER", "F4": "شورت مومنتوم جدیدها", "F5": "کپیتولیشن لانگ"}

# ---------- منحنی سرمایه SVG ----------
W, H, PAD = 780, 220, 34
eq = [x["cum"] for x in days]
lo, hi = min(eq + [0]), max(eq + [0])
rng = (hi - lo) or 1
def px(i): return PAD + i * (W - 2 * PAD) / max(1, len(eq) - 1)
def py(v): return H - PAD - (v - lo) * (H - 2 * PAD) / rng
pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(eq))
zero_y = py(0)
area = f"{px(0):.1f},{zero_y:.1f} " + pts + f" {px(len(eq)-1):.1f},{zero_y:.1f}"
grid = ""
step = rng / 4
for k in range(5):
    v = lo + k * step
    grid += (f'<line x1="{PAD}" y1="{py(v):.1f}" x2="{W-PAD}" y2="{py(v):.1f}" '
             f'stroke="#223246" stroke-width="1"/>'
             f'<text x="{W-PAD+4}" y="{py(v)+4:.1f}" fill="#8fa3b3" font-size="10">{v:+.0f}$</text>')
last_pos = eq[-1] >= 0
eq_color = "#4dd07a" if last_pos else "#ef5b5b"

# ---------- جدول روزها ----------
day_rows = ""
for x in days:
    cls = "pos" if x["pnl"] > 0 else ("neg" if x["pnl"] < 0 else "")
    btc = f'{x["btc_chg"]:+.2f}%' if x.get("btc_chg") is not None else "—"
    bcls = "pos" if (x.get("btc_chg") or 0) > 0 else "neg"
    day_rows += (f'<tr><td>{x["date"][5:]}</td><td>{x["issued"]}</td><td>{x["settled"]}</td>'
                 f'<td>{x["tp"]}✅/{x["sl"]}❌/{x["be"]}➖</td>'
                 f'<td class="{cls}">{x["pnl"]:+.2f}$</td>'
                 f'<td class="{cls}">{x["cum"]:+.2f}$</td>'
                 f'<td class="{bcls}">{btc}</td></tr>')

# ---------- جدول سناریوها ----------
sc_rows = ""
for sid in ["F1", "F2", "F3", "F4", "F5"]:
    s = sc.get(sid)
    if not s:
        sc_rows += (f'<tr><td class="sid">#{sid}</td><td>{sc_names[sid]}</td>'
                    f'<td colspan="7" style="color:#8fa3b3">بدون سیگنال در این ماه</td></tr>')
        continue
    wr = 100 * s["wins"] / s["settled"] if s["settled"] else 0
    gross = s["pnl"] + s["fees"]
    gcls = "pos" if gross >= 0 else "neg"
    ncls = "pos" if s["pnl"] >= 0 else "neg"
    sc_rows += (f'<tr><td class="sid">#{sid}</td><td>{sc_names[sid]}</td>'
                f'<td>{s["issued"]}</td><td>{s["tp"]}/{s["sl"]}/{s["be"]}/{s["cm"]}</td>'
                f'<td>{wr:.0f}%</td><td class="{gcls}">{gross:+.2f}$</td>'
                f'<td>{s["fees"]:.2f}$</td><td class="{ncls}"><b>{s["pnl"]:+.2f}$</b></td></tr>')

best = max(days, key=lambda x: x["pnl"])
worst = min(days, key=lambda x: x["pnl"])

page = f'''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PentaSignal v{d["version"]} — گزارش ۳۰ روزه {d["start"]} تا {d["end"]}</title>
<style>
  :root {{ --bg:#0e1621; --panel:#17212b; --accent:#2ea6ff; --green:#4dd07a; --red:#ef5b5b;
    --amber:#e8b34c; --text:#e9eef4; --dim:#8fa3b3; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:"Vazirmatn","Segoe UI",Tahoma,sans-serif; line-height:1.9; }}
  .wrap {{ max-width:900px; margin:0 auto; padding:18px 14px 60px; }}
  header.hero {{ background:linear-gradient(135deg,#17212b,#1b2a3d); border:1px solid #23364b;
    border-radius:18px; padding:22px; margin-bottom:16px; }}
  .hero-top {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
  .logo {{ width:54px; height:54px; border-radius:16px; display:flex; align-items:center; justify-content:center;
    background:linear-gradient(135deg,#2ea6ff,#874dff); font-size:26px; }}
  h1 {{ font-size:19px; }} .sub {{ color:var(--dim); font-size:13px; }}
  .ver {{ background:#23364b; color:var(--accent); border-radius:20px; padding:2px 12px; font-size:12px; font-weight:700; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(125px,1fr)); gap:10px; margin-top:16px; }}
  .card {{ background:var(--panel); border:1px solid #23364b; border-radius:14px; padding:10px 12px; text-align:center; }}
  .card .v {{ font-size:19px; font-weight:800; }} .card .k {{ font-size:11px; color:var(--dim); }}
  .pos {{ color:var(--green); }} .neg {{ color:var(--red); }} .amb {{ color:var(--amber); }}
  .panel {{ background:var(--panel); border:1px solid #23364b; border-radius:16px; padding:16px 18px; margin:14px 0; }}
  .panel h2 {{ font-size:15px; margin-bottom:10px; color:var(--accent); }}
  .panel h3 {{ font-size:13.5px; margin:12px 0 6px; color:var(--amber); }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  th,td {{ padding:6px 8px; border-bottom:1px solid #223246; text-align:center; }}
  th {{ color:var(--dim); font-weight:600; font-size:11.5px; }}
  td:first-child, th:first-child {{ text-align:right; }}
  td.sid {{ font-weight:800; color:var(--accent); }}
  ul {{ padding-inline-start:20px; }} li {{ margin:5px 0; }}
  .note {{ background:#1d2733; border-radius:12px; padding:10px 14px; font-size:12.5px; color:var(--dim); margin-top:10px; }}
  footer {{ margin-top:16px; color:var(--dim); font-size:11.5px; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">

<header class="hero">
  <div class="hero-top">
    <div class="logo">📈</div>
    <div>
      <h1>PentaSignal — گزارش شبیه‌سازی ۳۰ روز گذشته</h1>
      <div class="sub">از {d["start"]} تا {d["end"]} (تهران) · دیتای واقعی KuCoin کندل 30m · همان موتور ربات v{d["version"]}</div>
    </div>
    <span class="ver">v{d["version"]}</span>
  </div>
  <div class="cards">
    <div class="card"><div class="v">{t["signals"]}</div><div class="k">سیگنال صادرشده</div></div>
    <div class="card"><div class="v">{t["settled"]}</div><div class="k">تعیین‌تکلیف</div></div>
    <div class="card"><div class="v amb">{t["wr"]}%</div><div class="k">وین‌ریت</div></div>
    <div class="card"><div class="v neg">{t["pnl"]:+.2f}$</div><div class="k">PnL خالص (10$/معامله)</div></div>
    <div class="card"><div class="v neg">{t["maxdd"]:.2f}$</div><div class="k">بیشترین افت سرمایه</div></div>
    <div class="card"><div class="v">{t["fees"]:.2f}$</div><div class="k">کارمزد پرداختی</div></div>
    <div class="card"><div class="v pos">{t["days_positive"]}</div><div class="k">روز مثبت</div></div>
    <div class="card"><div class="v neg">{t["days_negative"]}</div><div class="k">روز منفی</div></div>
  </div>
</header>

<div class="panel">
  <h2>💵 منحنی سرمایه تجمعی (PnL روزانه، پوزیشن 10$)</h2>
  <svg viewBox="0 0 {W} {H}" style="width:100%; height:auto; direction:ltr;">
    {grid}
    <line x1="{PAD}" y1="{zero_y:.1f}" x2="{W-PAD}" y2="{zero_y:.1f}" stroke="#3a4a5c" stroke-dasharray="4 4"/>
    <polygon points="{area}" fill="{eq_color}" opacity="0.10"/>
    <polyline points="{pts}" fill="none" stroke="{eq_color}" stroke-width="2.5" stroke-linejoin="round"/>
    <circle cx="{px(eq.index(max(eq))):.1f}" cy="{py(max(eq)):.1f}" r="4" fill="#4dd07a"/>
    <circle cx="{px(eq.index(min(eq))):.1f}" cy="{py(min(eq)):.1f}" r="4" fill="#ef5b5b"/>
  </svg>
  <div class="sub">سقف: {max(eq):+.2f}$ ({days[eq.index(max(eq))]["date"]}) · کف: {min(eq):+.2f}$ ({days[eq.index(min(eq))]["date"]})</div>
</div>

<div class="panel">
  <h2>📊 عملکرد به تفکیک سناریو</h2>
  <table>
    <tr><th>سناریو</th><th>استراتژی</th><th>سیگنال</th><th>TP/SL/BE/CM</th><th>وین‌ریت</th><th>ناخالص</th><th>کارمزد</th><th>خالص</th></tr>
    {sc_rows}
  </table>
  <div class="note">💡 ناخالص = سود قبل از کارمزد. کل سیستم قبل از کارمزد <b class="pos">{t["pnl"] + t["fees"]:+.2f}$</b> بوده؛
  یعنی <b class="neg">کارمزد {t["fees"]:.2f}$ معامله‌های {t["signals"]}گانه</b> سود ناخالص را بلعیده و نتیجه را منفی کرده است.</div>
</div>

<div class="panel">
  <h2>🔎 پاسخ: چرا دیروز (و اکثر روزها) منفی شد؟</h2>
  <ul>
    <li><b>رژیم بازار:</b> بازار بعد از ریزش اواخر مرداد وارد <b>رنج کم‌دامنه</b> شد. هر ۵ سناریو ماهیت روندی دارند؛ در رنج، شکست‌ها برگشت می‌خورند و تریلینگ‌استاپ سریع فعال می‌شود.</li>
    <li><b>F3 بیش‌فعال بود:</b> دیروز ۱۲ از ۱۶ معامله F3 بود (ER حول آستانه 0.30 نوسان می‌کرد و مدام ورود جدید می‌گرفت) → خسارت زنجیره‌ای -0.89$.</li>
    <li><b>برچسب SL گمراه‌کننده است:</b> ۱۵ خروج «SL» دیروز در واقع <b>خروج تریلینگ‌استاپ</b> بود؛ ۳ موردش با سود بسته شد (مثلاً LTC لانگ +3.9٪). یعنی «همه منفی» نبود.</li>
    <li><b>کارمزد در روزهای پرمعامله سنگین است:</b> دیروز 16 معامله × 0.2٪ ≈ 0.32$ کارمزد = نصف ضرر خالص.</li>
    <li><b>مقایسه با روزهای روندی:</b> ۱۹–۲۲ آگوست که BTC روزانه +6٪ می‌رفت، همین سناریوها در ۴ روز <b class="pos">+15.1$</b> دادند. مشکل «انتخاب سهم» نیست؛ «رژیم بازار» است.</li>
  </ul>
  <h3>ریشه‌یابی عددی ماه</h3>
  <ul>
    <li><b>F3</b> با ۴۴۴ سیگنال (۶۶٪ کل) ناخالصش هم منفی است → هم overtrading دارد هم در رنج کیفیت ورودش پایین است؛ بزرگ‌ترین منبع ضرر.</li>
    <li><b>F1</b> ناخالص مثبت (+4.7$) ولی کارمزد 191 معامله آن را تقریباً خنثی کرده.</li>
    <li><b>F5</b> تنها سناریوی به‌طور واضح سودده (+8.05$ خالص) — استاپ سربه‌سر خودکار (۱۹ خروج BE) ضررها را قطع کرده.</li>
    <li>F2/F4 اصلاً فعال نشدند (هیچ روزی گیت افت ≥5٪ BTC برقرار نشد) → در ماه رنج/صعودی، محافظ کرش بی‌کار بود.</li>
  </ul>
</div>

<div class="panel">
  <h2>📅 روز‌به‌روز (۳۰ روز)</h2>
  <table>
    <tr><th>روز</th><th>سیگنال</th><th>تسویه</th><th>TP/SL/BE</th><th>PnL روز</th><th>تجمعی</th><th>BTC روز</th></tr>
    {day_rows}
  </table>
  <div class="note">⭐ بهترین روز: <b class="pos">{best["date"]} ({best["pnl"]:+.2f}$)</b> · 
  😞 بدترین روز: <b class="neg">{worst["date"]} ({worst["pnl"]:+.2f}$)</b> · 
  باز مانده پایان دوره: {t["still_open"]} پوزیشن</div>
</div>

<footer>
  PentaSignal v{d["version"]} · شبیه‌سازی با دیتای واقعی API عمومی KuCoin · کارمزد رفت‌وبرگشت 0.2٪ · پوزیشن 10$<br>
  ورود = بازِ کندل بعد از سیگنال (بدون آینده‌نگری) · اولویت استاپ در کندل دو‌جهته · نتایج گذشته تضمین آینده نیست
</footer>
</div>
</body>
</html>'''

out = "/home/z/my-project/download/PentaSignal_v2.1_month_report_2026-08-09_to_2026-09-07.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(page)
print(f"saved → {out} ({len(page)/1024:.0f} KB)")
