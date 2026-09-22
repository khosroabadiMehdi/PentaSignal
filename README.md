# 📡 PentaSignal

**ربات سیگنال تلگرام کریپتو — ۵ سناریوی داده‌محور روی کندل 30m KuCoin**

![Version](https://img.shields.io/badge/version-3.5.5-2ea6ff)
![Python](https://img.shields.io/badge/python-3.10%2B-4dd07a)
![Exchange](https://img.shields.io/badge/exchange-KuCoin%20public%20API-e8b34c)
![License](https://img.shields.io/badge/license-MIT-8fa3b3)

> سیگنال می‌دهد، خودش تعیین‌تکلیف می‌کند و نتیجه را **ریپلایِ همان پیام سیگنال** اعلام می‌کند.  
> پارامترهای استراتژی با جست‌وجوی شبکه‌ای روی داده واقعی بهینه و Out-of-Sample اعتبارسنجی شده‌اند.

**نسخه جاری: `3.5.5`** (در `VERSION`، `pentasignal/settings.py` و نام ورک‌فلوهای Actions)

---

## ✨ امکانات کلیدی (v3.1)

| | |
|---|---|
| 🎯 **۵ پروفایل مستقل** | **F1 = Khosro Rule Book v1** · F2 بیمه کرش · F3 پول‌بک · F4 ریباند‌شورت · F5 کپیتولیشن |
| 🛡 **خروج BK / TRAIL** | سربه‌سر خودکار بعد از +armR · تریلینگ ATR · برچسب جدا `TRAIL_HIT` |
| 💬 **ریپلای تلگرام** | تعیین‌تکلیف و BE همیشه ریپلای همان پیام سیگنال |
| ⏰ **پنجره تهران** | ۰۷:۰۰–۲۰:۰۰ سیگنال+تسویه · ۲۰:۳۰–۰۱:۰۰ فقط تسویه · ۰۲:۰۰ گزارش شبانه |
| 🗃 **CSV روزانه یکپارچه** | `data/signals/YYYY-MM-DD.csv` — ورود، دلیل صدور، نتیجه، PnL، notes |
| 📈 **آرشیو ۱ دقیقه‌ای** | `data/ohlcv/` غلتان ۹۰ روزه برای تسویه دقیق |
| 📋 **گزارش رد سیگنال** | در لاگ Actions: چرا صادر نشد (داده کم / دیتکتور / کول‌داون / پوزیشن باز) |
| 🧪 **بدون آینده‌نگری** | ورود منطقی · اولویت استاپ · گپ روی open · کارمزد ۰.۲٪ |
| ⛔ **گارد پرتفویی W2** | مدار قطع روزانه −3R · سقف سراسری ۵ پوزیشن باز (از v3.3.0) |

---


### F1 — KhosroAiTrader Rule Book v1 + کشف ترند چندمنبعی **بدون AI** (از v3.5.0)

F1 دیگر دونچیان نیست. منطق رأی **بدون تغییر** از `KhosroAiTrader` آمده است و پیش از آن، کشف ترند چندمنبعی (کاملاً بدون هوش مصنوعی) universe هر تیک را می‌سازد:

- **① ترند چندمنبعی**: CoinGecko `/search/trending` (وزن ۰.۵) + برد KuCoin `allTickers` (بیشترین صعود ۰.۲ / نزول ۰.۱۵ / حجم ۰.۱۵) — فیلتر استیبل/لوریج‌توکن/جفت کم‌عمق؛ حضور در چند منبع = امتیاز ×۱.۰۸
- **② انتخاب**: top‑N کاندیداها (∩ استخر پنتا، سقف `F1_DISCOVERY_TOP_N`=8) ∪ **ارزهای اصلی (BTC/ETH/BNB/SOL/XRP همیشه)** ∪ تا `F1_TREND_EXTRA_N`=5 ترندِ صرف CG خارج از استخر که جفت واقعی `*-USDT` روی KuCoin داشته باشند (فقط F1 اسکن‌شان می‌کند)
- **③ چک و تولید سیگنال**: همین universe به موتور واقعی `RuleSignalEngine._evaluate_coin` خوسرو می‌رود — **هیچ فراخوان LLM، خواندن اخبار یا فیلتر AI در مسیر نیست**
- رأی وزن‌دار: ساختار EMA20/50/200 (±20) · قیمت/EMA20 (±10) · RSI (±15) · MACD (±15) · مومنتوم ۱۲ (±10) · حجم (±10) · depth/funding/LSR فقط اگر `F1_BINANCE_MD=1`
- آستانه‌ها: `min_confidence=45` · `min_score_gap=15` · `ATR stop ×1.5` · هدف **2R** · `cooldown=12h`
- داده اصلی: **کندل 1h کوکوین** (`fetch_1h_binance_style`)؛ فال‌بک: فشرده‌سازی 30m→1h با همان موتور
- لبه بایننس (depth/funding) اختیاری است: روی GitHub Actions به‌دلیل HTTP 451 به‌صورت پیش‌فرض **خاموش** (از v3.5.3) و روی سیستم محلی روشن — با `F1_BINANCE_MD=0/1` قابل تغییر؛ نبودش فقط وزن depth/funding را خنثی می‌کند
- **F2 تا F5 هیچ تغییری نکرده‌اند** — universe فقط F1 را فیلتر می‌کند

## 📦 تغییرات مهم نسبت به نسخه‌های قبلی

| نسخه | خلاصه |
|------|--------|
| **3.5.5** | رفع دو باگ: سقف ۵ پوزیشن حالا در حین اسکن هم اجرا می‌شود (تیک 15:30 روز 09-21 ده سیگنال یکجا صادر کرده بود) · گزارش شبانه پوزیشن‌های بسته‌شده بعد از نیمه‌شب را هم نشان می‌دهد و PnL/وین‌ریت کامل می‌شود |
| **3.5.4** | همگام‌سازی مستندات (README/.env.example/STRATEGY.md) با معماری بدون AI · حذف کد مرده · بسته ZIP تمیز |
| **3.5.3** | حذف اسپم HTTP 451 بایننس روی Actions (`F1_BINANCE_MD` خاموش روی Actions) · بدون retry روی 451/403 |
| **3.5.2** | ترندهای انحصاری CoinGecko خارج از استخر (تا ۵ نماد، فقط F1) |
| **3.5.1** | گزارش دلایل رد تفکیک‌شده هر سناریو در لاگ Actions |
| **3.5.0** | **حذف کامل AI از مسیر F1** · کشف ترند: CoinGecko + مومنتوم/حجم KuCoin · کندل 1h کوکوین اول |
| **3.4.0** | کشف ترند چندمنبعی + مشورت AI برای F1 (از 3.5.0 حذف شد) |
| **3.3.0** | گارد پرتفویی W2: مدار قطع روزانه −3R + سقف سراسری ۵ پوزیشن باز · به‌روزرسانی مستندات F1 |
| **3.2.2** | `TRAIL_HIT` به‌جای برچسب غلط SL · وین‌ریت گزارش شبانه بر اساس PnL واقعی · زمان خروج درست برای کندل ۱m |
| **3.1.3** | گزارش تشخیصی رد سیگنال در لاگ Actions |
| **3.1.2** | ستون `reason` (دلیل فارسی صدور) روی هر ردیف |
| **3.1.1** | حذف events جدا · همه چیز روی ردیف سیگنال |
| **3.1.0** | فایل‌های روزانه به‌جای یک `signals.csv` حجیم |
| **3.0.x** | زمان‌بندی عملیاتی · آرشیو OHLCV · سخت‌سازی Actions |

جزئیات: [CHANGELOG.md](CHANGELOG.md) · استراتژی: [docs/STRATEGY.md](docs/STRATEGY.md)

---

## 📊 اعتبارسنجی استراتژی (v2.2، پوزیشن ۱۰$، کارمزد ۰.۲٪)

| پنجره | رژیم | PnL | maxDD |
|---|---|---|---|
| Jun 8 → Jul 10 | کف‌های V شکل | −4.6$ | −8.3$ |
| Jul 10 → Aug 8 *(IS)* | رنج خاموش | −9.6$ | −10.6$ |
| **Aug 9 → Sep 7 (OOS)** | رنج + روند | **+48.7$** | −6.1$ |
| فوریه 2026 (کرش BTC −20٪) | سقوط | F2: +12.6$ | −6.9$ |
| **کل ۹۱ روز** | ترکیبی | **+34.3$** | −16.7$ |

---

## 🚀 راه‌اندازی سریع

```bash
git clone https://github.com/khosroabadiMehdi/PentaSignal.git
cd PentaSignal
pip install -r requirements.txt

cp .env.example .env   # TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID
```

`.env`:
```ini
TELEGRAM_BOT_TOKEN=123456:ABC-your-token
TELEGRAM_CHAT_ID=-1001234567890
DRY_RUN=1        # 1 = فقط لاگ / 0 = ارسال واقعی تلگرام
```

### اجرا

```bash
python run_bot.py --once          # یک تیک (مود از ساعت تهران)
python run_bot.py --once --signal # اجباری: سیگنال + تسویه
python run_bot.py --once --settle # اجباری: فقط تسویه
python run_bot.py --once --nightly# اجباری: گزارش شبانه

python bootstrap_ohlcv.py --days 90   # پر کردن اولیه آرشیو 1m
```

---

## 🤖 ورک‌فلوهای GitHub Actions (v3.5.5)

| ورک‌فلو | فایل | زمان تهران | نقش |
|---|---|---|---|
| **PentaSignal v3.5.5 · Signal 07–20** | `signal-bot.yml` | هر ۳۰ دقیقه ۰۷:۰۰→۲۰:۰۰ | کشف ترند چندمنبعی + سیگنال + تسویه + آرشیو ۱m |
| **PentaSignal v3.5.5 · Settle 20:30–01** | `settle-bot.yml` | هر ۳۰ دقیقه ۲۰:۳۰→۰۱:۰۰ | فقط تعیین‌تکلیف |
| **PentaSignal v3.5.5 · Nightly 02:00** | `nightly-report.yml` | ۰۲:۰۰ | گزارش شبانه + چرخش ۹۰ روزه |
| **PentaSignal v3.5.5 · Bootstrap OHLCV** | `bootstrap-ohlcv.yml` | دستی | پر کردن اولیه ۹۰ روز ۱m |

**سکرت‌ها:** `TELEGRAM_BOT_TOKEN` · `TELEGRAM_CHAT_ID` — همین دو کافی‌اند (بدون AI). `COINGECKO_API_KEY` اختیاری است فقط برای سقف نرخ بالاتر CoinGecko.

نکته‌ها:
- هر سه ورک‌فلوی زنده در `concurrency group: pentasignal-live` هستند (بدون تداخل روی `data/`).
- وضعیت با کامیت `data/` ماندگار می‌شود (`signals/`، `ohlcv/`، `state.json`، `reports/`).
- گزارش شبانه ضدتکرار دارد (`last_nightly_date` در `state.json`).
- کرون گیت‌هاب ممکن است چند دقیقه تأخیر داشته باشد.

### زمان‌بندی UTC (مرجع)

```text
Signal : 03:30–16:30 UTC  (cron: 30 3-16 + 0 4-16)
Settle : 17:00–21:30 UTC  (cron: 0,30 17-21)
Nightly: 22:30 UTC        (cron: 30 22)
```

---

## 🗂 ذخیره سیگنال (از v3.1)

```text
data/signals/2026-09-19.csv   ← یک فایل برای هر روز تهران
```

هر ردیف شامل:
- ورود / حد ضرر / وضعیت (`OPEN` · `TP_HIT` · `SL_HIT` · `BE_HIT` · **`TRAIL_HIT`** · `CM_CLOSED`)
- `reason` — دلیل فارسی صدور
- `pnl_usd` · `return_pct` · `fee_usd` · `r_multiple`
- `be_armed` / `be_armed_at_tehran`
- `telegram_message_id` / `settle_message_id`
- `notes` — رد وقایع (SIGNAL → BE_ARMED → SETTLE_…)

سیگنال‌های باز بعد از نیمه‌شب در فایل **روز صدور** می‌مانند و همان‌جا آپدیت می‌شوند.

---

## 📨 نمونه پیام (v3.1)

**سیگنال:**
```text
🟢 سیگنال لانگ
🏷 F3 · پول‌بک لانگ در روند
🪙 DOT/USDT  ·  30m
🗓 … تهران
---------------------
◈ ورود / حد ضرر / خروج / ریسک
---------------------
#DOT  #پول_بک_لانگ_در_روند
PentaSignal  ·  v3.5.5
```

**خروج تریل:**
```text
🟢 📉 خروج تریلینگ
… بازده و PnL …
```

---

## 🗂 ساختار پروژه

```text
PentaSignal/
├── run_bot.py            ← تیک زنده + کشف ترند چندمنبعی (بدون AI) برای F1
├── bootstrap_ohlcv.py
├── pentasignal/
│   ├── discovery.py      ← ترند چندمنبعی CoinGecko+KuCoin + انتخاب universe (بدون AI)
│   ├── scenarios.py      ← F1–F5 + reason (F1 = خوسرو + گیت universe)
│   ├── exit_engine.py    ← BK / TRAIL / TP / SL / CM
│   ├── engine.py         ← تیک + گارد W2 + گزارش کشف ترند و دلایل رد
│   ├── store.py          ← CSV روزانه
│   ├── messages.py       ← قالب تلگرام
│   ├── report.py         ← گزارش شبانه (وین‌ریت بر اساس PnL)
│   ├── ohlcv_store.py
│   └── …
├── data/
│   ├── signals/YYYY-MM-DD.csv
│   ├── discovery/latest.json  ← خروجی کشف ترند (کاندیدا/انتخاب)
│   ├── ohlcv/
│   ├── reports/
│   └── state.json
├── docs/STRATEGY.md
├── CHANGELOG.md
├── VERSION                 ← 3.5.5
└── .github/workflows/      ← نام‌ها با v3.5.5
```

---

## ⚙️ پیکربندی مهم

| کلید | پیش‌فرض | توضیح |
|---|---|---|
| `POSITION_SIZE_USD` | 10 | سایز پایه |
| `MAX_OPEN_TRADES` | 5 | سقف سراسری پوزیشن باز (گارد W2) |
| `MAX_DAILY_LOSS_R` | 3.0 | مدار قطع روزانه بعد از −3R ضرر تجمعی (گارد W2) |
| `PORTFOLIO_GUARDS` | 1 | 1 = گاردها روشن · 0 فقط برای شبیه‌سازی/پژوهش |
| `F1_DISCOVERY` | 1 | 1 = کشف ترند چندمنبعی **بدون AI** برای F1 روشن |
| `F1_MAIN_COINS` | BTC,ETH,BNB,SOL,XRP | ارزهای اصلی که همیشه به چک F1 می‌روند |
| `F1_DISCOVERY_TOP_N` | 8 | سقف انتخاب کاندیدا از داخل استخر |
| `F1_TREND_EXTRA_N` | 5 | سقف ترندهای صرف CG خارج از استخر (فقط F1) |
| `F1_DISCOVERY_TIMEOUT` | 8 | تایم‌اوت هر منبع کشف (ثانیه) |
| `F1_BINANCE_MD` | Actions:0 · محلی:1 | لبه depth/funding بایننس برای F1 (روی Actions خاموش — 451) |
| `FEE_RT` | 0.002 | کارمزد رفت‌وبرگشت |
| `NEW_SIGNAL_START/END_HOUR` | 7 / 20 | پنجره سیگنال (تهران) |
| `NIGHTLY_REPORT_HOUR` | 2 | گزارش شبانه |
| `CSV_KEEP_DAYS` | 90 | نگه‌داری فایل‌های روزانه |
| `OHLCV_RECENT_MINUTES` | 45 | دریافت زنده ۱m در هر تیک |
| `OHLCV_RETENTION_DAYS` | 90 | آرشیو بازار |

---

## ⚠️ سلب مسئولیت

این پروژه برای **آموزش و پژوهش** است و توصیه سرمایه‌گذاری نیست.  
نتایج بک‌تست یا اجرای زنده گذشته تضمین آینده نیستند.  
قبل از پول واقعی حداقل ۲ هفته با `DRY_RUN=1` کاغذی اجرا کنید.

## 📄 لایسنس

[MIT](LICENSE)
