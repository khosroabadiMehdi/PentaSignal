# build_html_report.py — ساخت فایل HTML تحویلی از خروجی شبیه‌سازی
#
#   python build_html_report.py [sim_result.json] [out.html]
#
# خروجی: شبیه‌ساز چت تلگرام (تم تاریک، RTL) شامل همه پیام‌هایی که ربات در
# روز گذشته (07:00→24:00) می‌فرستاد + گزارش نهایی شبانه + کارت آمار.

import os
import re
import sys
import json
import html as html_mod

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

SIM = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "sim_result.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/z/my-project/download/PentaSignal_v2.1_simulation_2026-09-07.html"

d = json.load(open(SIM, encoding="utf-8"))
msgs = d["messages"]
stats = d["stats"]


def tg_to_html(text: str) -> str:
    """تبدیل HTML تلگرام (فقط b/code که خودمان تولید کرده‌ایم) به HTML صفحه"""
    s = html_mod.escape(text)
    s = s.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    s = s.replace("&lt;code&gt;", '<code class="mono">').replace("&lt;/code&gt;", "</code>")
    return s


KIND_STYLE = {
    "SIGNAL": ("🎯", "signal"),
    "BE_ARMED": ("🛡", "be"),
    "SETTLE": ("🔒", "settle"),
    "REPORT": ("🌙", "report"),
}
BY_ID = {m["message_id"]: m for m in msgs}


def quote_snippet(mid):
    m = BY_ID.get(str(mid))
    if not m:
        return None
    lines = [l for l in m["text"].split("\n") if l.strip()]
    # خط سناریو/نماد از پیام مبدأ (تگ‌های تلگرام حذف می‌شوند)
    strip = lambda s: re.sub(r"</?(b|code)[^>]*>", "", s)
    pick = [strip(l) for l in lines if ("سناریو:" in l or "نماد:" in l)][:1]
    return (lines[0], pick[0] if pick else "")


def bubble(m):
    icon, cls = KIND_STYLE.get(m["kind"], ("💬", "signal"))
    t = m["ts_tehran"][11:16]
    if m["kind"] == "SETTLE":
        status_line = "تکلیف سیگنال"
        if "#TP" in m["text"]:
            status_line, icon = "بستن در سود ✅", "🎯"
        elif "#SL" in m["text"]:
            status_line, icon = "بستن در ضرر ❌", "🛑"
        elif "#BE" in m["text"]:
            status_line, icon = "خروج سربه‌سر ➖", "⚖️"
        else:
            status_line, icon = "بستن زمانی 🕒", "🕒"
    body = tg_to_html(m["text"])
    reply_html = ""
    if m["reply_to"]:
        q = quote_snippet(m["reply_to"])
        if q:
            reply_html = (f'<a class="reply-quote" href="#msg-{m["reply_to"]}">'
                          f'<span class="rq-line"></span>'
                          f'<span class="rq-body"><span class="rq-title">↩ در پاسخ به سیگنال</span>'
                          f'<span class="rq-text">{html_mod.escape((q[1] or q[0])[:80])}</span></span></a>')
    return f'''
<div class="msg {cls}" id="msg-{m["message_id"]}">
  <div class="avatar">{icon}</div>
  <div class="bubble">
    <div class="meta"><span class="botname">PentaSignal</span><span class="badge">v{d["version"]}</span><span class="time">{t}</span></div>
    {reply_html}
    <div class="text">{body}</div>
  </div>
</div>'''


def divider(label, sub="", icon="⏰"):
    return f'''<div class="divider"><span class="d-icon">{icon}</span>
<div><div class="d-label">{label}</div><div class="d-sub">{sub}</div></div></div>'''


# ---------- ساخت تایم‌لاین ----------
timeline = []
divider_added_20 = False
divider_added_24 = False
prev_tick_hour = None
for m in msgs:
    hh = int(m["ts_tehran"][11:13])
    mm = int(m["ts_tehran"][14:16])
    # دیوایدر بازه تعیین تکلیف: اولین پیام بعد از 20:00
    if not divider_added_20 and (hh > 20 or (hh == 20 and mm >= 0)):
        if m["kind"] in ("SETTLE", "BE_ARMED") or (hh >= 20 and m["kind"] != "SIGNAL"):
            timeline.append(divider("🔒 حالت تعیین تکلیف — از 20:00 تا 24:00",
                                    "سیگنال جدید صادر نمی‌شود؛ فقط نتایج به‌صورت ریپلای اعلام می‌شوند", "🔒"))
            divider_added_20 = True
    if not divider_added_24 and m["kind"] == "REPORT":
        timeline.append(divider("🌙 اجرای شبانه ساعت 24:00",
                                "تسویه آخرین کندل روز + گزارش کامل روز گذشته + نگهداری CSV ۹۰ روزه", "🌙"))
        divider_added_24 = True
    timeline.append(bubble(m))

# ---------- کارت آمار ----------
wr = 0.0
closed = stats["tp"] + stats["sl"] + stats["be"] + stats["cm"]
if closed:
    wr = 100.0 * stats["tp"] / closed

sc_rows = {}
for r in d["issued_rows"]:
    s = sc_rows.setdefault(r["scenario_id"], [0, 0])
    s[0] += 1
for r in d["settled_rows"]:
    s = sc_rows.setdefault(r["scenario_id"], [0, 0])
    s[1] += 1
sc_names = {"F1": "شکست دونچیان + گیت رژیم", "F2": "کرش-شورت با گیت افت",
            "F3": "سوئینگ کافمن ER", "F4": "شورت مومنتوم جدیدها", "F5": "کپیتولیشن لانگ"}
sc_html = ""
for sid in ["F1", "F2", "F3", "F4", "F5"]:
    issued_n, settled_n = sc_rows.get(sid, [0, 0])
    sc_html += (f'<tr><td class="sid">#{sid}</td><td>{sc_names[sid]}</td>'
                f'<td>{issued_n}</td><td>{settled_n}</td></tr>')

open_html = ""
for r in d["still_open_rows"]:
    open_html += (f'<span class="chip">#{r["scenario_id"]} {r["symbol"].replace("-", "/")} '
                  f'{r["direction"]} @ {float(r["entry_price"]):.6g}</span> ')

pnl_cls = "pos" if stats["pnl_total"] >= 0 else "neg"

page = f'''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PentaSignal v{d["version"]} — شبیه‌سازی {d["date"]}</title>
<style>
  :root {{
    --bg:#0e1621; --panel:#17212b; --bubble:#182533; --bubble2:#1e2c3a;
    --accent:#2ea6ff; --green:#4dd07a; --red:#ef5b5b; --amber:#e8b34c;
    --text:#e9eef4; --dim:#8fa3b3; --mono:'Courier New',monospace;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text);
    font-family:"Vazirmatn","Segoe UI",Tahoma,sans-serif; line-height:1.9; }}
  .wrap {{ max-width:860px; margin:0 auto; padding:18px 14px 60px; }}
  header.hero {{ background:linear-gradient(135deg,#17212b,#1b2a3d); border:1px solid #23364b;
    border-radius:18px; padding:22px 22px 16px; margin-bottom:16px; }}
  .hero-top {{ display:flex; flex-wrap:wrap; align-items:center; gap:10px; }}
  .logo {{ width:54px; height:54px; border-radius:16px; display:flex; align-items:center; justify-content:center;
    background:linear-gradient(135deg,#2ea6ff,#874dff); font-size:26px; }}
  h1 {{ font-size:20px; }}
  .sub {{ color:var(--dim); font-size:13px; }}
  .ver {{ background:#23364b; color:var(--accent); border-radius:20px; padding:2px 12px; font-size:12px; font-weight:700; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:10px; margin-top:16px; }}
  .card {{ background:var(--panel); border:1px solid #23364b; border-radius:14px; padding:10px 12px; text-align:center; }}
  .card .v {{ font-size:20px; font-weight:800; }}
  .card .k {{ font-size:11px; color:var(--dim); }}
  .pos {{ color:var(--green); }} .neg {{ color:var(--red); }}
  .windows {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; font-size:12px; }}
  .win {{ border-radius:12px; padding:6px 12px; background:var(--panel); border:1px solid #23364b; color:var(--dim); }}
  .win b {{ color:var(--text); }}
  .panel {{ background:var(--panel); border:1px solid #23364b; border-radius:16px; padding:16px 18px; margin:14px 0; }}
  .panel h2 {{ font-size:15px; margin-bottom:10px; color:var(--accent); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th,td {{ padding:7px 8px; border-bottom:1px solid #223246; text-align:right; }}
  th {{ color:var(--dim); font-weight:600; font-size:12px; }}
  td.sid {{ font-weight:800; color:var(--accent); }}
  .chip {{ display:inline-block; background:var(--bubble2); border:1px solid #2a3f55; border-radius:10px;
     padding:3px 10px; margin:3px 2px; font-size:12px; }}
  /* ---------- chat ---------- */
  .chat {{ background:#0b131c; border:1px solid #1d2d3f; border-radius:18px; padding:18px 12px;
     background-image:radial-gradient(#12202e 1px, transparent 1px); background-size:22px 22px; }}
  .date-divider {{ text-align:center; margin:6px 0 14px; }}
  .date-divider span {{ background:#1c2733; color:var(--dim); border-radius:14px; padding:4px 16px; font-size:12px; }}
  .msg {{ display:flex; gap:8px; margin:10px 0; align-items:flex-start; }}
  .avatar {{ flex:0 0 40px; width:40px; height:40px; border-radius:50%; display:flex; align-items:center;
     justify-content:center; font-size:18px; background:linear-gradient(135deg,#22486b,#3a2a5e); border:1px solid #2c4a68; }}
  .bubble {{ background:var(--bubble); border-radius:14px 14px 14px 4px; padding:10px 14px 8px;
     max-width:640px; box-shadow:0 1px 2px rgba(0,0,0,.35); }}
  .meta {{ display:flex; align-items:center; gap:8px; margin-bottom:4px; }}
  .botname {{ color:#6ab3f3; font-weight:700; font-size:13px; }}
  .badge {{ background:#1c3a57; color:#7cc0ff; font-size:10px; border-radius:8px; padding:0 7px; }}
  .time {{ color:var(--dim); font-size:10px; margin-inline-start:auto; }}
  .text {{ font-size:13.5px; white-space:pre-wrap; }}
  .text b {{ color:#fff; }}
  code.mono {{ direction:ltr; unicode-bidi:embed; display:inline-block; background:#0d1b29; color:#9fd0ff;
     border-radius:6px; padding:0 7px; font-family:var(--mono); font-size:12.5px; }}
  .msg.settle .bubble {{ background:#251c1e; border:1px solid #4a2a2d; }}
  .msg.settle .text b {{ color:#ffb4b4; }}
  .msg.be .bubble {{ background:#242418; border:1px solid #4a442a; }}
  .msg.report .bubble {{ background:#16232e; border:1px solid #27506f; max-width:700px; }}
  .reply-quote {{ display:flex; gap:8px; background:#0d1b29; border-radius:8px; padding:5px 9px; margin:2px 0 7px;
     text-decoration:none; }}
  .rq-line {{ width:3px; border-radius:2px; background:var(--accent); flex:0 0 3px; }}
  .rq-body {{ display:flex; flex-direction:column; }}
  .rq-title {{ color:#6ab3f3; font-size:11px; font-weight:700; }}
  .rq-text {{ color:var(--dim); font-size:11.5px; }}
  .divider {{ display:flex; align-items:center; gap:10px; justify-content:center; margin:16px 0; }}
  .d-icon {{ width:38px; height:38px; border-radius:50%; background:#20242b; display:flex; align-items:center;
     justify-content:center; font-size:17px; border:1px solid #333c49; }}
  .d-label {{ font-size:13px; font-weight:700; color:#ffd28a; text-align:center; }}
  .d-sub {{ font-size:11px; color:var(--dim); text-align:center; }}
  .hashtags .chip {{ color:#69d2a8; border-color:#22503c; }}
  footer {{ margin-top:18px; color:var(--dim); font-size:11.5px; text-align:center; }}
  footer b {{ color:var(--text); }}
</style>
</head>
<body>
<div class="wrap">

<header class="hero">
  <div class="hero-top">
    <div class="logo">📡</div>
    <div>
      <h1>PentaSignal — شبیه‌سازی روز کاری ربات</h1>
      <div class="sub">دوشنبه <b>{d["date"]}</b> · پنجره 07:00 → 24:00 تهران · دیتای واقعی KuCoin (کندل 30m)</div>
    </div>
    <span class="ver">v{d["version"]}</span>
  </div>
  <div class="cards">
    <div class="card"><div class="v">{stats["issued"]}</div><div class="k">سیگنال جدید</div></div>
    <div class="card"><div class="v">{len(msgs)}</div><div class="k">پیام تلگرام</div></div>
    <div class="card"><div class="v">{closed}</div><div class="k">تعیین‌تکلیف</div></div>
    <div class="card"><div class="v">{stats["tp"]}✅ {stats["sl"]}❌ {stats["be"]}➖</div><div class="k">TP / SL / BE</div></div>
    <div class="card"><div class="v">{wr:.1f}%</div><div class="k">وین‌ریت روز</div></div>
    <div class="card"><div class="v {pnl_cls}">{stats["pnl_total"]:+.2f}$</div><div class="k">PnL خالص · پوزیشن 10$</div></div>
  </div>
  <div class="windows">
    <span class="win">🟢 07:00–20:00: صدور سیگنال جدید</span>
    <span class="win">🔒 20:00–24:00: فقط تعیین تکلیف (ریپلای)</span>
    <span class="win">🌙 24:00: گزارش کامل شبانه</span>
    <span class="win">#هشتگ در همه پیام‌ها</span>
  </div>
</header>

<div class="panel">
  <h2>📊 عملکرد به تفکیک سناریو (این روز)</h2>
  <table>
    <tr><th>سناریو</th><th>استراتژی</th><th>سیگنال صادرشده</th><th>تعیین‌تکلیف‌شده</th></tr>
    {sc_html}
  </table>
</div>

{('<div class="panel"><h2>📂 پوزیشن‌های بازِ منتقل‌شده به فردا</h2>' + open_html + '</div>') if open_html.strip() else ''}

<div class="chat" id="chat">
  <div class="date-divider"><span>دوشنبه 2026-09-07</span></div>
  {"".join(timeline)}
  <div class="date-divider"><span>امروز · 2026-09-08 00:00</span></div>
</div>

<div class="panel hashtags">
  <h2>#️⃣ طرح هشتگ پیام‌ها</h2>
  <span class="chip">#سیگنال</span><span class="chip">#تکلیف_شده</span><span class="chip">#TP</span>
  <span class="chip">#SL</span><span class="chip">#BE</span><span class="chip">#مدیریت_ریسک</span>
  <span class="chip">#گزارش_شبانه</span><span class="chip">#F1 … #F5</span><span class="chip">#PentaSignal</span>
  <span class="chip">#KuCoin</span>
</div>

<footer>
  ساخته‌شده با <b>PentaSignal v{d["version"]}</b> · داده واقعی API عمومی KuCoin · کارمزد رفت‌وبرگشت 0.2٪ · پوزیشن پایه 10$<br>
  ورود هر سیگنال = بازِ کندل بعد از کندل سیگنال (بدون آینده‌نگری) · تعیین تکلیف با اولویت استاپ در کندل‌های دو‌جهته
</footer>
</div>
</body>
</html>'''

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(page)
print(f"HTML saved → {OUT}  ({len(page)/1024:.1f} KB)")
