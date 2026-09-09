## 3.1.3 — signal skip report in Action logs

- `detect_new` now prints a diagnostic report each tick:
  - issued count
  - skip counts: short history, no detector setup, open position, cooldown, invalid entry
  - up to 40 sample skip lines with symbol + scenario + reason
- Visible in GitHub Actions job logs for the signal workflow.

## 3.1.2 — signal issue reason on each row

- Each signal row stores a Persian `reason` explaining why it was issued (detector conditions).
- Reasons are scenario-specific (Donchian break, crash gate, pullback, rebound, capitulation metrics).
- Unified daily signal CSV remains the single source of truth.

## 3.1.1 — unified daily signal rows (no separate events)

- Removed separate `events` storage; everything lives on the signal row.
- Each daily `data/signals/YYYY-MM-DD.csv` row holds entry, status, exit, PnL, fees, BE time, Telegram ids, and notes.
- `append_event` now appends a short trail into `notes` and sets `be_armed_at_tehran` when relevant.
- Midnight-safe: open signals remain in their issue-day file and are still updated later.

## 3.1.0 — daily signal/event CSV storage

- Replaced monolithic `signals.csv` / `events.csv` with daily files:
  - `data/signals/YYYY-MM-DD.csv`
  - `data/events/YYYY-MM-DD.csv`
- Open signals stay in their issue-day file and are still found after midnight.
- `update_signal` locates the original day file (even across days).
- Rotation moves whole day files older than 90 days into `data/archive/signals|events/`.
- Workflows and `.gitignore` updated for the new layout.

## 3.0.1 — cleaner Telegram messages

- Redesigned all Telegram templates (signal / BE / settle).
- Separators changed to dashed lines.
- Hashtags reduced to `#SYMBOL` + `#scenario_name`.
- Scenario shown as `F3 · پول‌بک در روند`.
- Result messages use green/red markers based on PnL.
- Project name + version footer on every message.
- Fixed missing OHLCV settings (`OHLCV_RECENT_MINUTES`, `OHLCV_RETENTION_DAYS`, `OHLCV_BACKFILL_CHUNK_MINUTES`).
- Made git-auto-commit workflows resilient when some data files are missing.

## 3.0.0 — operational hardening

- Operational windows split into signal, night-settlement, and 02:00 nightly-report workflows (Tehran time).
- Added rolling 90-day 1m OHLCV archive under `data/ohlcv/`.
- Added initial 90-day OHLCV bootstrap workflow.
- Exit settlement uses closed 1m candles while preserving existing scenario parameters.
- Fixed signal persistence of `entry_candle_ts`.
- Nightly report is now explicit and no longer piggybacks on normal ticks.
- Telegram message presentation upgraded without changing strategy rules.
- CI now runs deterministic v3 tests without depending on live KuCoin availability.

# Changelog — PentaSignal

## [2.2.1] — 2026-09-08

### Added
- **ورک‌فلوهای عملیاتی GitHub Actions** (مثل نسخهٔ 1.x، این‌بار با نام درست):
  - `signal-bot.yml` → «PentaSignal Bot · 30m Signal & Settle» — تیک هر ۳۰ دقیقه از 06:30 تا 24:00 تهران؛ صدور سیگنال (07–20)، تسویه، تیک نیمه‌شب و کامیت CSV/استیت
  - `nightly-report.yml` → «PentaSignal Nightly · 24:00 Report & Rotation» — 00:05 تهران؛ تور ایمنیِ گزارش شبانه + چرخش ۹۰ روزه
- گارد ضدتکرار گزارش شبانه: کلید `last_nightly_date` در `state.json`؛ اگر تیک نیمه‌شب پرش/تأخیر خورد، اولین تیک قبل از ظهر (`NIGHTLY_CUTOFF_HOUR = 12`) گزارش را جبران می‌کند — هر روز فقط یک گزارش
- مانای وضعیت بین اجراهای Actions: `signals.csv` / `events.csv` / `state.json` / `reports/` / `archive/` از `.gitignore` خارج شدند (کش و لاگ همچنان نادیده)
- `concurrency group` مشترک (`pentasignal-live`) بین دو ورک‌فلوی عملیاتی — بدون ریسینگ روی CSV

### Changed
- نام ورک‌فلوی CI شفاف شد: «PentaSignal CI · Test Suite» + `paths-ignore` برای کامیت‌های دیتا؛ پیام کامیت‌های ربات `[skip ci]`
- هر دو ورک‌فلوی عملیاتی `workflow_dispatch` دارند (اجرای دستی بی‌خطر — گارد ضدتکرار فعال است)

### Removed
- نیاز به ورک‌فلوی `bootstrap-ohlcv` نسخهٔ 1.x از بین رفت — v2.2 در هر تیک مستقیم از API زندهٔ KuCoin می‌گیرد (بدون پارکت محلی)

## [2.2.0] — 2026-09-08

### Changed
- **بازطراحی کامل هر ۵ پروفایل** با جست‌وجوی شبکه‌ای روی ۹۱ روز دیتای واقعی (IS: Jul 10→Aug 8) و اعتبارسنجی OOS چندرژیمی (ژوئن، ماه گزارش‌شده، کرش فوریه):
  - F1: Donchian 16→32، SL 3.5→4.0×ATR، خروج TRAIL→BK (سربه‌سر خودکار بعد از +1R)
  - F2: گیت کرش 5%→8% (فقط کرش واقعی) + BK arm=1.5
  - F3: ER-swing whipsaw-ساز → پول‌بک لانگ در روند (شیب EMA50 ≥1.2% + لمس EMA21 + کندل برگشتی) + TRAIL پهن 5×ATR
  - F4: شکست → ریباند-شورتِ جدیدها (گیت dd BTC + افت ≥8% خود نماد + رد شدن EMA21) + BK
  - F5: آستانه حجم 1.8→1.5، SL 2.0→2.5×ATR (کاهش whipsaw) با حفظ BK
- یافتهٔ محوری: خروج BK در همهٔ سناریوها بر TRAIL/FIXED غلبهٔ قطعی و پلاتو داشت
- گیت‌های رژیم BTC و سقف ضرر روزانه تست شدند — اثر ناچیز؛ کنار گذاشته شدند (شفاف)

### Fixed
- ۴ اشکال در تست‌های انتها-به-انتها (bk_tp_rr KeyError، نمادهای مینی‌روز خارج از پول F1، ATR مصنوعی تنگ)

### Performance
- ۹۱ روز: **-81.6$ → +34.3$** | ماه گزارش‌شده: -6.0$ → **+44.0$** | تعداد سیگنال: 671 → 195 (کارمزد ماه: 13.4$ → 3.6$)

## [2.1.0] — 2026-09-08

### Added
- موتور ۵ سناریویی جدید F1–F5 (Donchian Breakout / Crash Short / ER Swing / New-Coin Short / Capitulation Long) با دیتکتورهای بدون آینده‌نگری
- **ریپلای تلگرام**: هر تعیین‌تکلیف (TP/SL/BE/CM) و هر جابجایی استاپ به سربه‌سر، به‌صورت reply روی خودِ پیام سیگنال ارسال می‌شود (reply_to_message_id در CSV ذخیره می‌شود)
- **پنجره زمانی تهران**: صدور سیگنال جدید فقط 07:00→20:00؛ از 20:00 تا 24:00 فقط تعیین تکلیف؛ گزارش کامل شبانه در 24:00
- **گزارش کامل شبانه**: آمار روز، تفکیک ۵ سناریو، بهترین/بدترین، پوزیشن‌های باز + نگهداری CSV
- **هشتگ استاندارد**: #سیگنال #تکلیف_شده #TP #SL #BE #مدیریت_ریسک #گزارش_شبانه #F1..#F5 #PentaSignal #KuCoin
- **خروج سربه‌سر خودکار (BK)** در F5: بعد از +1R استاپ به ورود+بافر کارمزد می‌رود
- **CSV غلتان 90 روزه**: signals.csv + events.csv + آرشیو خودکار + reports JSON
- شبیه‌ساز روز کامل (`simulate.py`) + مولد گزارش HTML چت‌مانند (`build_html_report.py`)
- سری تست ۶ بخشی (`tests/ps_v21_tests.py`) با دیتای ایزوله

### Changed
- ظاهر پیام‌های تلگرام به HTML تبدیل شد (حفظ ساختار قبلی: تیتر → هشتگ → مشخصات → ریپلای، با جداساز و ایموجی منظم)
- کارمزد از 0.1%×2 (مانیتور) به 0.2% رفت‌وبرگشت یکپارچه با بک‌تست پنتا
- پوزیشن پایه 10$ (قابل تغییر در settings)

### Fixed
- اولویت استاپ در کندل‌های دو‌جهته و پرشدن گپ در قیمت باز (مطابق معناشناسی بک‌تست)
- محاسبه r_multiple در موتور خروج

## [2.0.0]
- نسخه قبلی: سناریوهای S1–S3/B1–B2، مانیتور شبانه متنی، CSV روزانه

## [1.x]
- نسخه اصلی PentaSignal-main

## [2.2.0] — 2026-09-08 — بازنگری کامل ۵ پروفایل (داده‌محور)

### متدولوژی
- جست‌وجوی شبکه‌ای روی پنجره IS (Jul 10→Aug 8) با موتور درون‌حافظه‌ای سریع (scripts/ps_review.py)
- اعتبارسنجی Out-of-Sample: Aug 9→Sep 7 (دست‌نخورده) + ژوئن (quasi-OOS) + کرش واقعی فوریه 2026 (dd تا -20.3٪)

### تغییرات سناریوها
- **F1**: دونچیان 16→32، SL 3.5→4.0×ATR، خروج TRAIL→**BK** (arm 1R، CM 6d) — نتیجه ۹۱روزه: -0.4$→+12.7$
- **F2**: گیت افت 5→8٪ (فقط کرش واقعی؛ در کف‌های V شکل خاموش) + خروج FIXED→**BK** arm 1.5R، CM 9d
  - روی کرش فوریه: +12.6$ (dd -6.9$) — قبلاً با FIXED روی ژوئن -41$ می‌داد
- **F3**: بازطراحی کامل — از سوئینگ ER (بازنده ساختاری: -46.5$ در ۹۱ روز) به **پول‌بک لانگ** (شیب EMA50≥1.2٪ + لمس EMA21 + کلوز برگشتی) با تریل پهن 5×ATR → +9.6$
- **F4**: بازطراحی — از شکست-شورت به **ریباند-شورت** (بازگشت به EMA21 + کندل رد شدن در افت BTC) → +2.7$ (ژوئن) و +5.2$ (فوریه)
- **F5**: آستانه حجم 1.8→1.5 و SL 2.0→2.5×ATR → +9.3$ (قبلاً +9.4$ روی همین دیتا با پارامتر قدیمی)

### نتایج (پوزیشن 10$، کارمزد 0.2٪ RT)
- کل ۹۱ روز (Jun 8→Sep 7): **-81.6$ → +34.3$** | maxDD -87$ → **-16.7$**
- ماه گزارش‌شده (Aug 9→Sep 7): **-6.03$ → +43.96$** | سیگنال 671→195 (کارمزد 13.4→3.6$)
- شفاف: ژوئن/جولایِ بی‌روند هنوز جزئی منفی است (-4.6$ / -9.6$) — هزینه ذاتی سیستم‌های روندی؛ هیچ پارامتری بدون آسیب به سود آگوست آن را حذف نکرد

### Fixed
- محاسبه r_multiple · برچسب BK در پیام‌ها (بدون TP ثابت) · exit_param فقط arm
