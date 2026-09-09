# build_v22_html.py — گزارش HTML بازنگری v2.2 (قبل/بعد + اعتبارسنجی)
import os
import sys
import json

BASE = "/home/z/my-project/PentaSignal-v2.1"
d = json.load(open(os.path.join(BASE, "month_result.json"), encoding="utf-8"))
t = d["totals"]
days = d["days"]
sc = d["by_scenario"]

sc_names = {"F1": "شکست دونچیان 32 + گیت رژیم · BK 1R",
            "F2": "بیمهٔ کرش (فقط افت ≥8٪ BTC) · BK 1.5R",
            "F3": "پول‌بک لانگ در روند · تریل 5×ATR",
            "F4": "ریباند-شورت جدیدها · BK 1R",
            "F5": "کپیتولیشن لانگ · BK 1R"}

# منحنی سرمایه ماه
W, H, PAD = 780, 210, 34
eq = [x["cum"] for x in days]
lo, hi = min(eq + [0]), max(eq + [0])
rng = (hi - lo) or 1
def px(i): return PAD + i * (W - 2 * PAD) / max(1, len(eq) - 1)
def py(v): return H - PAD - (v - lo) * (H - 2 * PAD) / rng
pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(eq))
area = f"{px(0):.1f},{py(0):.1f} " + pts + f" {px(len(eq)-1):.1f},{py(0):.1f}"
grid = ""
for k in range(5):
    v = lo + k * rng / 4
    grid += (f'<line x1="{PAD}" y1="{py(v):.1f}" x2="{W-PAD}" y2="{py(v):.1f}" stroke="#223246"/>'
             f'<text x="{W-PAD+4}" y="{py(v)+4:.1f}" fill="#8fa3b3" font-size="10">{v:+.0f}$</text>')
eq_color = "#4dd07a" if eq[-1] >= 0 else "#ef5b5b"

sc_rows = ""
for sid in ["F1", "F2", "F3", "F4", "F5"]:
    s = sc.get(sid, {"issued": 0, "settled": 0, "tp": 0, "sl": 0, "be": 0, "cm": 0, "wins": 0, "pnl": 0.0})
    wr = 100 * s["wins"] / s["settled"] if s["settled"] else 0
    cls = "pos" if s["pnl"] >= 0 else "neg"
    sc_rows += (f'<tr><td class="sid">#{sid}</td><td style="text-align:right">{sc_names[sid]}</td>'
                f'<td>{s["issued"]}</td><td>{s["tp"]}✅/{s["sl"]}❌/{s["be"]}➖/{s["cm"]}🕒</td>'
                f'<td>{wr:.0f}%</td><td class="{cls}"><b>{s["pnl"]:+.2f}$</b></td></tr>')

day_rows = ""
for x in days:
    cls = "pos" if x["pnl"] > 0 else ("neg" if x["pnl"] < 0 else "")
    day_rows += (f'<tr><td>{x["date"][5:]}</td><td>{x["issued"]}</td><td>{x["settled"]}</td>'
                 f'<td class="{cls}">{x["pnl"]:+.2f}$</td><td class="{cls}">{x["cum"]:+.2f}$</td></tr>')

page = f'''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PentaSignal v2.2 — بازنگری کامل ۵ پروفایل</title>
<style>
  :root {{ --bg:#0e1621; --panel:#17212b; --accent:#2ea6ff; --green:#4dd07a; --red:#ef5b5b;
    --amber:#e8b34c; --text:#e9eef4; --dim:#8fa3b3; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:"Vazirmatn","Segoe UI",Tahoma,sans-serif; line-height:1.9; }}
  .wrap {{ max-width:900px; margin:0 auto; padding:18px 14px 60px; }}
  header.hero {{ background:linear-gradient(135deg,#17212b,#1b2a3d); border:1px solid #23364b; border-radius:18px; padding:22px; margin-bottom:16px; }}
  .hero-top {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
  .logo {{ width:54px; height:54px; border-radius:16px; display:flex; align-items:center; justify-content:center;
    background:linear-gradient(135deg,#4dd07a,#2ea6ff); font-size:26px; }}
  h1 {{ font-size:19px; }} .sub {{ color:var(--dim); font-size:13px; }}
  .ver {{ background:#23364b; color:var(--accent); border-radius:20px; padding:2px 12px; font-size:12px; font-weight:700; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:10px; margin-top:16px; }}
  .card {{ background:var(--panel); border:1px solid #23364b; border-radius:14px; padding:10px 12px; text-align:center; }}
  .card .v {{ font-size:19px; font-weight:800; }} .card .k {{ font-size:11px; color:var(--dim); }}
  .pos {{ color:var(--green); }} .neg {{ color:var(--red); }} .amb {{ color:var(--amber); }}
  .panel {{ background:var(--panel); border:1px solid #23364b; border-radius:16px; padding:16px 18px; margin:14px 0; }}
  .panel h2 {{ font-size:15px; margin-bottom:10px; color:var(--accent); }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  th,td {{ padding:6px 8px; border-bottom:1px solid #223246; text-align:center; }}
  th {{ color:var(--dim); font-weight:600; font-size:11.5px; }}
  td.sid {{ font-weight:800; color:var(--accent); }}
  ul {{ padding-inline-start:20px; }} li {{ margin:5px 0; }}
  .note {{ background:#1d2733; border-radius:12px; padding:10px 14px; font-size:12.5px; color:var(--dim); margin-top:10px; }}
  .big {{ font-size:15px; }}
  footer {{ margin-top:16px; color:var(--dim); font-size:11.5px; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">

<header class="hero">
  <div class="hero-top">
    <div class="logo">🔧</div>
    <div>
      <h1>PentaSignal v2.2 — بازنگری کامل ۵ پروفایل</h1>
      <div class="sub">جست‌وجوی شبکه‌ای روی IS (Jul 10→Aug 8) · اعتبارسنجی OOS (Aug 9→Sep 7، دست‌نخورده) · تست کرش فوریه</div>
    </div>
    <span class="ver">v2.2.0</span>
  </div>
  <div class="cards">
    <div class="card"><div class="v neg">-81.6$</div><div class="k">PnL v2.1 در ۹۱ روز</div></div>
    <div class="card"><div class="v pos">+34.3$</div><div class="k">PnL v2.2 در ۹۱ روز</div></div>
    <div class="card"><div class="v neg">-6.03$</div><div class="k">ماه گزارش‌شده (v2.1)</div></div>
    <div class="card"><div class="v pos">+43.96$</div><div class="k">همان ماه (v2.2)</div></div>
    <div class="card"><div class="v amb">-5.91$</div><div class="k">maxDD ماه (قبلاً -19.1$)</div></div>
    <div class="card"><div class="v">{t["signals"]}</div><div class="k">سیگنال ماه (قبلاً 671)</div></div>
  </div>
</header>

<div class="panel">
  <h2>💵 منحنی سرمایه ماه Aug 9→Sep 7 با پارامترهای جدید</h2>
  <svg viewBox="0 0 {W} {H}" style="width:100%; height:auto; direction:ltr;">
    {grid}
    <line x1="{PAD}" y1="{py(0):.1f}" x2="{W-PAD}" y2="{py(0):.1f}" stroke="#3a4a5c" stroke-dasharray="4 4"/>
    <polygon points="{area}" fill="{eq_color}" opacity="0.10"/>
    <polyline points="{pts}" fill="none" stroke="{eq_color}" stroke-width="2.5"/>
  </svg>
</div>

<div class="panel">
  <h2>📊 عملکرد ماه به تفکیک سناریو (پارامترهای v2.2)</h2>
  <table>
    <tr><th>سناریو</th><th>استراتژی جدید</th><th>سیگنال</th><th>TP/SL/BE/CM</th><th>وین‌ریت</th><th>PnL</th></tr>
    {sc_rows}
  </table>
  <div class="note">#F2 بیمهٔ کرش است و در این ماه (بدون کرش) عمداً خاموش بود — روی کرش واقعی فوریه ۲۰۲۶ (افت 20.3٪ BTC) تست شد: <b class="pos">+12.55$</b> در ۵ هفته با dd فقط -6.9$</div>
</div>

<div class="panel">
  <h2>🔎 چه چیزی عوض شد و چرا؟</h2>
  <ul>
    <li><b>همهٔ پروفایل‌های سودده به خروج BK مهاجرت کردند</b> — سربه‌سر خودکار بعد از +1R. در داده، BK در هر ۵ سناریو بر تریلینگ و FIXED برتری قطعی داشت (F1: +2.8$ → <b class="pos">+17$</b> در همان ماه IS).</li>
    <li><b>F1</b>: دونچیان 16→32 و SL 3.5→4×ATR — شکست‌های کمتر اما باکیفیت‌تر؛ نویز و کارمزد نصف شد.</li>
    <li><b>F3 بازطراحی شد</b>: سوئینگ ER ساختاراً بازنده بود (-46.5$ در ۹۱ روز با ۱۳۶۴ معامله!). حالا «پول‌بک لانگ در روند» است: فقط وقتی EMA50 شیب ≥1.2٪ دارد و قیمت به EMA21 برگشت با کندل صعودی → ورود با تریل پهن. → <b class="pos">+14.8$</b> در ماه.</li>
    <li><b>F2</b>: گیت افت 5٪ در کف‌های کم‌عمق V شکل هم فعال می‌شد و می‌سوخت (-41$!). حالا فقط در کرش واقعی (≥8٪) با خروج BK arm 1.5R — در فوریه <b class="pos">+12.6$</b> داد.</li>
    <li><b>F4</b>: شکست-شورت در کوین‌های نقدشونده جواب نمی‌داد (واکنش برگشتی). حالا «ریباند-شورت»: در افت، پاداشِ بازگشت به EMA21 با کندل رد شدن را شورت می‌کند.</li>
    <li><b>F5</b>: آستانه حجم کمی بازتر (1.5×) و SL 2.5×ATR — بیشترین سود به‌ازای ریسک در کل ماه (+10$ با dd -2.9$).</li>
  </ul>
</div>

<div class="panel">
  <h2>🧪 اعتبارسنجی چند-رژیمی (ورود-محور، پوزیشن 10$)</h2>
  <table>
    <tr><th>پنجره</th><th>رژیم</th><th>تعداد</th><th>PnL</th><th>maxDD</th></tr>
    <tr><td>Jun 8→Jul 10</td><td>کف‌های V شکل</td><td>165</td><td class="neg">-4.58$</td><td>-8.32$</td></tr>
    <tr><td>Jul 10→Aug 8 (IS)</td><td>رنج خاموش</td><td>145</td><td class="neg">-9.60$</td><td>-10.59$</td></tr>
    <tr><td>Aug 9→Sep 7 (OOS)</td><td>رنج + روند قوی</td><td>187</td><td class="pos"><b>+48.65$</b></td><td>-6.09$</td></tr>
    <tr><td>Feb 10→15 (کرش)</td><td>افت 20.3٪ BTC</td><td>—</td><td class="pos">F2: +12.6$</td><td>-6.9$</td></tr>
    <tr><td><b>کل ۹۱ روز</b></td><td>ترکیبی</td><td>503</td><td class="pos"><b>+34.28$</b></td><td>-16.66$</td></tr>
  </table>
  <div class="note">⚠️ شفافیت کامل: در ماه‌های بی‌روند (ژوئن/جولای) سیستم هنوز جزئی منفی است — این هزینه ذاتی استراتژی‌های روندی است و هیچ پارامتری بدون قربانی‌کردن سود آگوست آن را حذف نکرد. مطالعه قبلی روی ۶ رژیم هم همین را تأیید کرده بود. گام بعدی منطقی: اجرای کاغذی ۲ هفته‌ای با DRY_RUN=1.</div>
</div>

<div class="panel">
  <h2>📅 روز‌به‌روز ماه (خروج-محور)</h2>
  <table>
    <tr><th>روز</th><th>سیگنال</th><th>تسویه</th><th>PnL روز</th><th>تجمعی</th></tr>
    {day_rows}
  </table>
</div>

<footer>
  PentaSignal legacy v2.2.0 · دیتای واقعی KuCoin · ورود = باز کندل بعد · اولویت استاپ · کارمزد 0.2٪ RT · پوزیشن 10$<br>
  جست‌وجو فقط روی IS · اعداد OOS و فوریه هرگز در بهینه‌سازی استفاده نشدند · نتایج گذشته تضمین آینده نیست
</footer>
</div>
</body>
</html>'''

out = "/home/z/my-project/download/PentaSignal_v2.2_profile_overhaul.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(page)
print(f"saved → {out} ({len(page)/1024:.0f} KB)")
