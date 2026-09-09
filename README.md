# 📡 PentaSignal

**ربات سیگنال تلگرام کریپتو — ۵ سناریوی داده‌محور روی کندل 30m KuCoin**

![Version](https://img.shields.io/badge/version-3.0.0-2ea6ff)
![Python](https://img.shields.io/badge/python-3.10%2B-4dd07a)
![Exchange](https://img.shields.io/badge/exchange-KuCoin%20public%20API-e8b34c)
![Tests](https://img.shields.io/badge/tests-59%2F59%20pass-4dd07a)
![License](https://img.shields.io/badge/license-MIT-8fa3b3)

> سیگنال می‌دهد، خودش تعیین‌تکلیف می‌کند و نتیجه را **ریپلایِ همان پیام سیگنال** اعلام می‌کند.
> پارامترها با جست‌وجوی شبکه‌ای روی داده واقعی بهینه و به‌صورت Out-of-Sample اعتبارسنجی شده‌اند.

---

## ✨ امکانات کلیدی (v2.2)

| | |
|---|---|
| 🎯 **۵ پروفایل مستقل** | شکست روند، بیمهٔ کرش، پول‌بک، ریباند-شورت، کپیتولیشن — هرکدام با دیتکتور و مدیریت خروج مخصوص |
| 🛡 **استاپ سربه‌سر خودکار (BK)** | بعد از +1R استاپ به ورود+بافر کارمزد می‌رود؛ قهرمان بک‌تست در هر ۵ سناریو |
| 💬 **ریپلای تلگرام** | تعیین تکلیف (TP/SL/BE/CM) و جابجایی استاپ، همیشه ریپلایِ خودِ پیام سیگنال |
| ⏰ **پنجره زمانی تهران** | سیگنال جدید فقط 07:00→20:00 · 20:00→24:00 فقط تعیین تکلیف · 24:00 گزارش کامل شبانه |
| #️⃣ **هشتگ استاندارد** | `#سیگنال` `#تکلیف_شده` `#TP` `#SL` `#BE` `#گزارش_شبانه` `#F1..#F5` `#PentaSignal` |
| 🗃 **CSV غلتان ۹۰ روزه** | `signals.csv` + `events.csv` + آرشیو خودکار + اسنپ‌شات JSON گزارش شبانه |
| 🎨 **پیام‌های HTML زیبا** | جداساز، ایموجی منظم، قیمت مونو‌اسپیس، رنگ‌بندی وضعیت |
| 🧪 **بدون آینده‌نگری** | ورود = بازِ کندل بعد · اولویت استاپ در کندل دو‌جهته · گپ در قیمت باز · کارمزد 0.2٪ در همه اعداد |

## 📊 نتیجه اعتبارسنجی v2.2 (پوزیشن 10$، کارمزد 0.2٪)

| پنجره | رژیم بازار | PnL | maxDD |
|---|---|---|---|
| Jun 8 → Jul 10 | کف‌های V شکل | -4.6$ | -8.3$ |
| Jul 10 → Aug 8 *(IS بهینه‌سازی)* | رنج خاموش | -9.6$ | -10.6$ |
| **Aug 9 → Sep 7 (خارج از نمونه)** | رنج + روند | **+48.7$** | **-6.1$** |
| فوریه 2026 (کرش، BTC -20٪) | سقوط | F2: +12.6$ | -6.9$ |
| **کل ۹۱ روز** | ترکیبی | **+34.3$** | -16.7$ |

نسخه قبلی روی همین ۹۱ روز **-81.6$** بود. جزئیات کامل و صادقانه: [docs/STRATEGY.md](docs/STRATEGY.md)

## 🚀 راه‌اندازی سریع

```bash
git clone https://github.com/<you>/PentaSignal.git
cd PentaSignal
pip install -r requirements.txt

cp .env.example .env       # توکن ربات و chat_id را پر کنید
```

`.env`:
```ini
TELEGRAM_BOT_TOKEN=123456:ABC-your-token
TELEGRAM_CHAT_ID=-1001234567890
DRY_RUN=1        # 1 = شبیه‌سازی ارسال (پیش‌فرض امن)
```

### اجرا

```bash
python run_bot.py            # لوپ زنده (هر بسته‌شدن کندل 30m یک تیک)
python run_bot.py --once     # فقط یک تیک

# شبیه‌سازی یک روز کامل با دیتای واقعی + گزارش HTML چت‌مانند
python simulate.py --date 2026-09-07
python build_html_report.py

# شبیه‌سازی ۳۰ روز + گزارش بازنگری
python simulate_month.py --start 2026-08-09 --end 2026-09-07
python build_v22_html.py

# تست ۶ بخشی (پیکربندی/API واقعی/دیتکتورها/موتور خروج/CSV/انتها-به-انتها)
python tests/ps_v21_tests.py
```

## 🤖 ورک‌فلوهای GitHub Actions (اجرای بدون‌سرور)

ربات مثل نسخهٔ اصلی روی GitHub Actions اجرا می‌شود — بدون سرور، بدون downtime.
سه ورک‌فلو با نام‌های شفاف:

| ورک‌فلو | فایل | زمان‌بندی (تهران) | نقش |
|---|---|---|---|
| **PentaSignal Bot · 30m Signal & Settle** | `signal-bot.yml` | هر ۳۰ دقیقه، 06:30 → 24:00 | صدور سیگنال (07–20) · تسویه · تیک نیمه‌شب (گزارش) · کامیت CSV |
| **PentaSignal Nightly · 24:00 Report & Rotation** | `nightly-report.yml` | 00:05 روزانه | تور ایمنی گزارش شبانه — اگر تیک نیمه‌شب پرش شد جبران می‌کند (ضدتکرار) |
| **PentaSignal CI · Test Suite** | `ci.yml` | هر push | سری تست ۶ پاسه با API عمومی KuCoin |

**پیش‌نیاز:** در `Settings → Secrets and variables → Actions` دو سکرت بسازید:
`TELEGRAM_BOT_TOKEN` و `TELEGRAM_CHAT_ID` (همان مقادیر `.env`).

نکته‌ها:
- موتور خودش پنجره‌های تهران را کنترل می‌کند؛ زمان‌بندی UTC با اختلاف 3:30 ساعت در YAML کامنت شده است.
- وضعیت بین اجراها با **کامیت CSV/استیت** می‌ماند (`data/signals.csv`، `data/events.csv`، `data/state.json`، گزارش‌ها و آرشیو)؛ لاگ و کش کامیت نمی‌شوند.
- هر دو ورک‌فلوی عملیاتی در `concurrency group` مشترک‌اند تا هرگز هم‌زمان روی CSV ننویسند.
- گزارش شبانه گارد ضدتکرار دارد (کلید `last_nightly_date`)؛ اجرای دستی (`workflow_dispatch`) هم بی‌خطر است.
- برخلاف نسخهٔ 1.x، ورک‌فلوی `bootstrap-ohlcv` لازم نیست — v2.2 هر تیک را مستقیم از API زنده KuCoin می‌گیرد.

## 📨 نمونه پیام‌ها

**سیگنال جدید:**
```
🎯 سیگنال جدید · PentaSignal v3.0

#F1 #LONG #BTC
━━━━━━━━━━━━━━━━━━━━
🏷 سناریو: F1 · شکست دونچیان ۳۲ + گیت رژیم
🪙 نماد: BTC/USDT · تایم‌فریم 30m
📅 شنبه 2026-09-07 · 🕐 14:30 تهران

🟢 جهت: لانگ
💰 ورود: 43,250.0
🛑 حد ضرر: 41,230.0 (-4.67%)
🎯 مدیریت خروج: سربه‌سر خودکار — پس از +1R ...
⚖️ ریسک 1R: 4.67% ≈ 0.47$ از پوزیشن 10$

📎 نتیجه به‌صورت ریپلای همین پیام اعلام می‌شود.
#سیگنال #F1 #LONG #BTC #PentaSignal #KuCoin
```

**تعیین تکلیف (ریپلای همان پیام):**
```
✅ تکلیف سیگنال مشخص شد — حد سود فعال شد
↩️ سیگنال F1 · BTC/USDT · LONG
📈 بازده: +6.2% | 💵 PnL خالص: +0.62$
#تکلیف_شده #TP #F1 #LONG #BTC #PentaSignal
```

## 🗂 ساختار

```
PentaSignal/
├── run_bot.py               ← اجرای زنده
├── simulate.py              ← شبیه‌سازی یک روز (07:00→24:00) با دیتای واقعی
├── simulate_month.py        ← شبیه‌سازی چندروزه
├── build_html_report.py     ← گزارش HTML چت‌مانند روزانه
├── build_month_html.py / build_v22_html.py
├── pentasignal/             ← پکیج اصلی
│   ├── scenarios.py         ← F1–F5: پول‌ها، پارامترها، دیتکتورها
│   ├── exit_engine.py       ← FIXED/TRAIL/BK/CM + گپ + کارمزد
│   ├── engine.py            ← تیک هر کندل: تسویه → سیگنال → گزارش
│   ├── store.py             ← CSV + چرخش ۹۰ روزه
│   ├── telegram.py          ← ارسال + ریپلای
│   ├── messages.py          ← قالب‌های زیبا + هشتگ
│   ├── report.py            ← گزارش کامل شبانه
│   └── kucoin.py · indicators.py · utils.py · state.py · settings.py
├── tests/ps_v21_tests.py    ← ۶ بخش تست (۵۹ چک)
├── research/                ← هارنس بک‌تست و جست‌وجوی شبکه‌ای
├── results/                 ← اسنپ‌شات نتایج رسمی
├── docs/STRATEGY.md         ← مشخصات کامل استراتژی + اعداد اعتبارسنجی
└── .github/workflows/       ← signal-bot.yml · nightly-report.yml · ci.yml
```

## ⚙️ پیکربندی

همه در `pentasignal/settings.py` و `pentasignal/scenarios.py`:

| کلید | پیش‌فرض | توضیح |
|---|---|---|
| `POSITION_SIZE_USD` | 10 | پوزیشن پایه هر سیگنال |
| `FEE_RT` | 0.002 | کارمزد رفت‌وبرگشت |
| `NEW_SIGNAL_START/END_HOUR` | 7 / 20 | پنجره صدور سیگنال جدید (تهران) |
| `CSV_KEEP_DAYS` | 90 | نگهداری غلتان |
| `SCENARIOS` | v2.2 | پارامترهای هر سناریو (قابل تنظیم) |

## ⚠️ سلب مسئولیت

این پروژه برای **آموزش و پژوهش** است و توصیه سرمایه‌گذاری نیست. نتایج بک‌تست
تضمین آینده نیستند؛ در ماه‌های بی‌روند سیستم جزئی منفی می‌شود (شفاف در
[docs/STRATEGY.md](docs/STRATEGY.md)). قبل از هر سرمایه واقعی، حداقل ۲ هفته با
`DRY_RUN=1` اجرای کاغذی بگیرید و مسئولیت معاملات با خود شماست.

## 📄 لایسنس

[MIT](LICENSE)


## PentaSignal v3 — Operational Schedule

- **07:00–20:00 Tehran:** every 30 minutes; settle previous open signals and issue new signals.
- **20:00–01:00 Tehran:** every 30 minutes; settle open signals only, no new signals.
- **02:00 Tehran:** nightly report only.
- Signal management remains in `data/signals.csv` and `data/events.csv`.
- Rolling 90-day 1-minute market data for all project symbols is stored under `data/ohlcv/` as compressed daily JSONL files.
- Each operational tick refreshes the 1-minute market archive; open positions are resolved from the stored 1-minute history.
- `bootstrap_ohlcv.py` and the manual GitHub Action `PentaSignal · Bootstrap 90d OHLCV` can populate the initial 90-day archive.

> Strategy parameters and scenario rules are unchanged in v3. Only execution scheduling, data persistence, validation, and presentation were upgraded.
