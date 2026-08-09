# PentaSignal

ربات سیگنال چندسناریویی کریپتو — مبتنی بر تحلیل تکنیکال چندتایم‌فریمی (KuCoin) با ارسال گزارش کامل به تلگرام.

## پنج سناریو

| کد | نام فارسی | نام انگلیسی | شخصیت | جهت | ریسک | RR |
|----|-----------|-------------|--------|------|------|-----|
| **S1** | شیر طلایی | Golden Lion | سخت‌گیر و باکیفیت | فقط LONG | LOW | 0.6 |
| **S2** | تیر نقره‌ای | Silver Arrow | متعادل و پایدار | فقط LONG | LOW | 0.6 |
| **S3** | الماس فیلسوف | Diamond Mind | خیلی انتخابی و کم‌سیگنال | فقط LONG | LOW | 0.6 |
| **B1** | موج تند | Fast Wave | سیگنال زیاد و فعال | LONG/SHORT | MEDIUM | 0.38 |
| **B2** | سپر فولادی | Steel Shield | تعادل تعداد و دقت | LONG/SHORT | MEDIUM | 0.32 |

### نمادها

- **هسته مشترک (۱۰ ارز):** BTC, ETH, BNB, SOL, XRP, XAUT, LTC, DOGE, SUI, NEAR
- هر سناریو حداقل **۱۵ نماد** دارد (هسته + اختصاصی)

## زمان‌بندی (همان پروژه قبلی)

| Workflow | Cron (UTC) | معادل تقریبی تهران |
|----------|------------|---------------------|
| سیگنال روزانه | `0,30 2-20 * * *` | هر ۳۰ دقیقه از ۶ صبح تا ۱۲ شب |
| مانیتور شبانه | `30 22 * * *` | حدود ۲ بامداد |

## ساختار پروژه

```
PentaSignal/
├── bot.py                 # اجرای اصلی — همه سناریوها
├── config.py              # نمادها + ۵ سناریو + ریسک
├── rules.py               # قوانین وزن‌دار + فیلتر سناریو
├── indicators.py
├── patterns.py
├── data_fetcher.py
├── signal_store.py        # CSV روزانه در signals/
├── monitor_nightly.py     # به‌روزرسانی TP/SL + گزارش شبانه
├── requirements.txt
├── .env.example
├── signals/               # دیتابیس CSV روزانه
└── .github/workflows/
    ├── signal-bot.yml
    └── nightly-monitor.yml
```

## راه‌اندازی

1. ریپو را فورک/کلون کنید (Public).
2. در GitHub → Settings → Secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Actions را Enable کنید.
4. برای تست دستی: Actions → PentaSignal → Run workflow.

## گزارش تلگرام

هر سیگنال شامل:

- نام سناریو + شخصیت
- نماد، جهت، سطح ریسک
- ورود / استاپ / تارگت
- وزن و تعداد قوانین پاس‌شده
- لیست قوانین پاس‌شده و ردشده
- زمان (تهران)

گزارش شبانه (monitor) همان منطق قبلی: به‌روزرسانی وضعیت CSV، محاسبه PnL، حذف فایل‌های قدیمی‌تر از ۱۰ روز، ارسال خلاصه به تلگرام.

## دیتابیس

- پوشه `signals/`
- فایل روزانه: `YYYY-MM-DD.csv`
- ستون‌ها: symbol, direction, risk_level, entry_price, stop_loss, take_profit, issued_at_tehran, status, hit_time_tehran, hit_price, broker_fee, final_pnl_usd, position_size_usd, return_pct, signal_source

## وابستگی‌ها

```
requests, numpy, pandas, python-dotenv, aiohttp, pytz
```
