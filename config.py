import os

# 🔑 تنظیمات تلگرام
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ⚖️ سطوح ریسک پایه (فقط برای آستانه‌های داخلی قوانین کندل/تأیید — در خروجی و سناریو نمایش داده نمی‌شود)
RISK_LEVELS = [
    {
        'key': 'LOW',
        'name': 'ریسک کم',
        'emoji': '🟢',
        'rules': {
            'trend_4h_emas': [21, 55, 200],
            'trend_1h_emas': [21, 55],
            'candle_15m_strength': 0.6,
            'candle_5m_strength': 0.6,
            'rsi_threshold_count': 5,
            'macd_threshold_count': 5,
            'entry_break_threshold': 0.0,
        }
    },
    {
        'key': 'MEDIUM',
        'name': 'ریسک میانی',
        'emoji': '🟡',
        'rules': {
            'trend_4h_emas': [21, 55],
            'trend_1h_emas': [21, 55],
            'candle_15m_strength': 0.48,
            'candle_5m_strength': 0.48,
            'rsi_threshold_count': 4,
            'macd_threshold_count': 4,
            'entry_break_threshold': 0.003,
        }
    },
    {
        'key': 'HIGH',
        'name': 'ریسک بالا',
        'emoji': '🔴',
        'rules': {
            'trend_4h_emas': [21],
            'trend_1h_emas': [21, 55],
            'candle_15m_strength': 0.35,
            'candle_5m_strength': 0.35,
            'rsi_threshold_count': 3,
            'macd_threshold_count': 3,
            'entry_break_threshold': 0.003,
        }
    }
]

# 📊 لیست کامل نمادها (اتحاد همه سناریوها)
SYMBOLS = [
    'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'SOL-USDT', 'XRP-USDT',
    'XAUT-USDT', 'LTC-USDT', 'DOGE-USDT', 'SUI-USDT', 'NEAR-USDT',
    'DOT-USDT', 'ADA-USDT', 'LINK-USDT', 'AVAX-USDT', 'ATOM-USDT',
    'FIL-USDT', 'INJ-USDT', 'SEI-USDT', 'TIA-USDT', 'POL-USDT',
    'OP-USDT',
]

RISK_PARAMS = {
    'atr_multiplier': 1.2,
    'rr_target': 2.0,
    'swing_lookback': 10,
    'rr_fallback': 2.0
}

RISK_FACTORS = {
    "LOW": {
        "ADX": 3, "CCI": 2, "SAR": 3, "Stoch": 2, "TF_Big": 4, "Patterns": 2, "RiskMgmt": 4,
        "Volume": 2, "Candles": 2, "EMA": 2, "Confirm": 3, "Pressure": 3
    },
    "MEDIUM": {
        "ADX": 2, "CCI": 3, "SAR": 2, "Stoch": 3, "TF_Big": 3, "Patterns": 3, "RiskMgmt": 3,
        "Volume": 2, "Candles": 2, "EMA": 2, "Confirm": 3, "Pressure": 3
    },
    "HIGH": {
        "ADX": 1, "CCI": 4, "SAR": 1, "Stoch": 4, "TF_Big": 1, "Patterns": 4, "RiskMgmt": 2,
        "Volume": 3, "Candles": 3, "EMA": 1, "Confirm": 2, "Pressure": 4
    }
}

INDICATOR_THRESHOLDS = {
    "adx_min": 22,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
}

ADVANCED_RISK_PARAMS = {
    "LOW": {"label": "conservative"},
    "MEDIUM": {"label": "balanced"},
    "HIGH": {"label": "aggressive"}
}

# ==================================================================================================================
# 5 SCENARIOS — PentaSignal (تنظیمات نهایی توافق‌شده)
# ==================================================================================================================
SHARED_SYMBOLS = [
    'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'SOL-USDT', 'XRP-USDT',
    'XAUT-USDT', 'LTC-USDT', 'DOGE-USDT', 'SUI-USDT', 'NEAR-USDT',
]

SCENARIOS = {
    "S1": {
        "id": "S1",
        "name_fa": "شیر طلایی",
        "name_en": "Golden Lion",
        "personality": "سخت‌گیر و باکیفیت — سیگنال کمتر، دقت بالاتر",
        "description": "سخت‌گیرانه‌ترین سناریو با آستانه وزن ۶۰٪ و حداقل ۱۱ قانون.",
        "rr": 1.2,
        "weight_threshold": 0.60,
        "min_passed_rules": 11,
        "cooldown_seconds": 6 * 3600,
        "symbols_list": SHARED_SYMBOLS + [
            'DOT-USDT', 'ADA-USDT', 'LINK-USDT', 'AVAX-USDT', 'ATOM-USDT',
        ],
        "direction_only": None,  # LONG و SHORT
        "atr_mult": 1.5,
        "rule_profile": "strict",  # آستانه‌های کندل/تأیید سخت‌تر
        "range_filter_mode": "AND",  # شل‌تر: فقط وقتی diff کم و ADX ضعیف
    },
    "S2": {
        "id": "S2",
        "name_fa": "تیر نقره‌ای",
        "name_en": "Silver Arrow",
        "personality": "متعادل و پایدار — تعادل تعداد و کیفیت",
        "description": "سناریوی متعادل با آستانه وزن ۵۰٪ و حداقل ۹ قانون.",
        "rr": 1.2,
        "weight_threshold": 0.50,
        "min_passed_rules": 9,
        "cooldown_seconds": 8 * 3600,
        "symbols_list": SHARED_SYMBOLS + [
            'LINK-USDT', 'DOT-USDT', 'FIL-USDT', 'INJ-USDT', 'SEI-USDT',
        ],
        "direction_only": None,
        "atr_mult": 1.5,
        "rule_profile": "strict",
        "range_filter_mode": "AND",
    },
    "S3": {
        "id": "S3",
        "name_fa": "الماس فیلسوف",
        "name_en": "Diamond Mind",
        "personality": "خیلی انتخابی و کم‌سیگنال — فقط بهترین فرصت‌ها",
        "description": "انتخابی‌ترین سناریو با آستانه وزن ۵۵٪ و حداقل ۷ قانون.",
        "rr": 1.2,
        "weight_threshold": 0.55,
        "min_passed_rules": 7,
        "cooldown_seconds": 6 * 3600,
        "symbols_list": SHARED_SYMBOLS + [
            'LINK-USDT', 'DOT-USDT', 'AVAX-USDT', 'INJ-USDT', 'TIA-USDT',
        ],
        "direction_only": None,
        "atr_mult": 1.5,
        "rule_profile": "strict",
        "range_filter_mode": "AND",
    },
    "B1": {
        "id": "B1",
        "name_fa": "موج تند",
        "name_en": "Fast Wave",
        "personality": "سیگنال زیاد و فعال — پوشش گسترده‌تر بازار",
        "description": "پرسیگنال با فیلتر قدرت بدنه ≥۰.۶۵ و ADX>۲۳. هر دو جهت.",
        "rr": 1.0,
        "weight_threshold": 0.45,
        "min_passed_rules": 8,
        "cooldown_seconds": 4 * 3600,
        "symbols_list": SHARED_SYMBOLS + [
            'DOT-USDT', 'ADA-USDT', 'POL-USDT', 'ATOM-USDT', 'FIL-USDT', 'OP-USDT',
        ],
        "direction_only": None,
        "atr_mult": 1.10,
        "rule_profile": "balanced",
        "range_filter_mode": "OR",
        "extra_filters": {
            "min_body_strength": 0.65,
            "min_adx": 23,
            "require_di_align": True,
        },
    },
    "B2": {
        "id": "B2",
        "name_fa": "سپر فولادی",
        "name_en": "Steel Shield",
        "personality": "تعادل تعداد و دقت — فیلتر کندل قوی و بسته شدن افراطی",
        "description": "قدرت بدنه ≥۰.۷۵ و بسته شدن در انتهای دامنه کندل. هر دو جهت.",
        "rr": 1.0,
        "weight_threshold": 0.45,
        "min_passed_rules": 8,
        "cooldown_seconds": 4 * 3600,
        "symbols_list": SHARED_SYMBOLS + [
            'DOT-USDT', 'ADA-USDT', 'LINK-USDT', 'FIL-USDT', 'AVAX-USDT', 'SEI-USDT',
        ],
        "direction_only": None,
        "atr_mult": 1.05,
        "rule_profile": "balanced",
        "range_filter_mode": "OR",
        "extra_filters": {
            "min_body_strength": 0.75,
            "min_adx": 20,
            "require_close_extreme": True,
            "close_long_min": 0.82,
            "close_short_max": 0.18,
            "require_di_align": True,
        },
    },
}

# ترتیب اجرا و گزارش شبانه
ACTIVE_SCENARIOS = ["S1", "S2", "S3", "B1", "B2"]

# نمایش نام سناریو برای کاربر (بدون کد S1 و ...)
def scenario_display_name(sc: dict) -> str:
    return f"{sc['name_fa']} ({sc['name_en']})"
