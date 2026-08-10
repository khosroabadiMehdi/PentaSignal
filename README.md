# PentaSignal

ربات سیگنال چندسناریویی کریپتو — تحلیل تکنیکال چندتایم‌فریمی روی KuCoin با ارسال سیگنال و گزارش شبانه به تلگرام.

---

## پنج سناریو

| نام فارسی | نام انگلیسی | شخصیت | جهت | RR | آستانه وزن | حداقل قانون | کول‌داون |
|-----------|-------------|--------|------|-----|------------|-------------|----------|
| **شیر طلایی** | Golden Lion | سخت‌گیر و باکیفیت | LONG / SHORT | **1.2** | 60% | 11 | 6 ساعت |
| **تیر نقره‌ای** | Silver Arrow | متعادل و پایدار | LONG / SHORT | **1.2** | 50% | 9 | 8 ساعت |
| **الماس فیلسوف** | Diamond Mind | خیلی انتخابی و کم‌سیگنال | LONG / SHORT | **1.2** | 55% | 7 | 6 ساعت |
| **موج تند** | Fast Wave | سیگنال زیاد و فعال | LONG / SHORT | **1.0** | 45% | 8 | 4 ساعت |
| **سپر فولادی** | Steel Shield | تعادل تعداد و دقت | LONG / SHORT | **1.0** | 45% | 8 | 4 ساعت |

### فیلترهای اضافه

- **موج تند:** قدرت بدنه ≥ 0.65 — ADX > 23 — هم‌راستایی DI
- **سپر فولادی:** قدرت بدنه ≥ 0.75 — بسته شدن افراطی کندل — ADX > 20 — هم‌راستایی DI
- **سه سناریوی اول:** فیلتر range ترکیبی با منطق **AND** (فقط وقتی فاصله EMA کم **و** ADX ضعیف → رد)

> سطح ریسک (LOW/MEDIUM/HIGH) از منطق سناریو حذف شده؛ هر سناریو فقط تنظیمات خودش را دارد.

### نمادها

- **هسته مشترک (۱۰ ارز):** BTC, ETH, BNB, SOL, XRP, XAUT, LTC, DOGE, SUI, NEAR  
- هر سناریو حداقل **۱۵ نماد** (هسته + اختصاصی مثل LINK, ATOM, FIL, INJ, SEI, TIA, …)

---

## زمان‌بندی

| Workflow | Cron (UTC) | معادل تقریبی تهران |
|----------|------------|---------------------|
| سیگنال | `0,30 2-20 * * *` | هر ۳۰ دقیقه از ۶ صبح تا ۱۲ شب |
| مانیتور شبانه | `30 22 * * *` | حدود ۲ بامداد |

---

## ساختار پروژه

```
PentaSignal/
├── bot.py                 # حلقه اصلی — همه سناریوها
├── config.py              # نمادها + ۵ سناریو
├── rules.py               # قوانین وزن‌دار + تولید سیگنال
├── indicators.py
├── patterns.py
├── data_fetcher.py
├── signal_store.py        # CSV روزانه در signals/
├── monitor_nightly.py     # TP/SL + گزارش ۶ پیام شبانه
├── requirements.txt
├── .env.example
├── signals/
└── .github/workflows/
    ├── signal-bot.yml
    └── nightly-monitor.yml
```

---

## راه‌اندازی

1. ریپو را Public بسازید و کد را آپلود کنید.
2. GitHub → **Settings → Secrets and variables → Actions**:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. **Settings → Actions → General → Workflow permissions**  
   → **Read and write permissions** را فعال کنید (برای commit فایل CSV).
4. Actions را Enable کنید.
5. تست دستی: Actions → **PentaSignal** → Run workflow.

---

## پیام سیگنال تلگرام

هر سیگنال شامل:

- نام سناریو (بدون کد داخلی) + شخصیت  
- نماد و جهت  
- ورود / استاپ / تارگت  
- وزن و تعداد قوانین پاس‌شده  
- لیست قوانین پاس‌شده و ردشده  
- زمان تهران  

چند سناریو می‌توانند هم‌زمان روی یک نماد سیگنال بدهند؛ هر کدام با نام خودش ذخیره و ارسال می‌شود.

---

## گزارش شبانه (۶ پیام)

1. **کلیات:** تعداد سیگنال، TP / SL / CLOSED_MANUAL / باز، وین‌ریت، PnL تقریبی  
2–6. **به تفکیک هر سناریو:** آمار + لیست کامل سیگنال‌ها  

- مانیتور **امروز + دو روز قبل** را بررسی می‌کند  
- **CLOSED_MANUAL** فقط اگر از صدور بیش از **۲ روز** گذشته و هنوز TP/SL نخورده باشد  
- حتی اگر سیگنال جدیدی نباشد، گزارش ارسال می‌شود  
- PnL با فرض پوزیشن **۱۰ دلار** و کارمزد **۰.۲٪**

---

## دیتابیس CSV

- پوشه `signals/` — فایل روزانه `YYYY-MM-DD.csv`
- ستون‌های اصلی:

```
symbol, direction, scenario_id, scenario_name,
entry_price, stop_loss, take_profit,
issued_at_tehran, status, hit_time_tehran, hit_price,
broker_fee, final_pnl_usd, position_size_usd, return_pct,
signal_source
```

---

## وابستگی‌ها

```
requests
numpy
pandas
python-dotenv
aiohttp
pytz
```

نصب:

```bash
pip install -r requirements.txt
```

---

## نکات

- داده از **KuCoin public API** گرفته می‌شود (نیاز به کلید API نیست).
- وین‌ریت ظاهری به‌تنهایی معیار سود نیست؛ با RR و کارمزد با هم تفسیر شود.
- برای چند روز اول لاگ‌ها و CSV را بررسی کنید تا رفتار واقعی سناریوها مشخص شود.
