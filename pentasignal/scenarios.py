# scenarios.py — پنج سناریوی PentaSignal v2.2 (بازنگری کامل داده‌محور)
#
# بازنگری 2026-09-08: جست‌وجوی شبکه‌ای روی Jun–Aug (IS) + اعتبارسنجی Aug (OOS) + کرش فوریه
# تغییرات کلیدی نسبت به v2.1:
#  • همه پروفایل‌های سودده به خروج BK (سربه‌سر خودکار بعد از +armR) مهاجرت کردند —
#    در تحلیل داده، BK در هر ۵ سناریو بر تریلینگ/FIXED برتری معنادار داشت
#  • F1: دونچیان 16→32 و SL 3.5→4.0 (شکست‌های باکیفیت‌تر)
#  • F3: از سوئینگ ER (بازنده: -46$ در ۳ ماه) به پول‌بک لانگ در روند بازطراحی شد
#  • F2: گیت 5%→8% (فقط کرش واقعی؛ در کف‌های V شکلِ کم‌عمق خاموش) + خروج BK arm 1.5
#  • F4: از شکست-شورت (بازنده) به ریباند-شورت بازطراحی شد
#  • F5: آستانه حجم 1.8→1.5 (سیگنال بیشتر با حفظ لبه)
#
# ⚠️ اعداد از بک‌تست ۹۱ روزه با کارمزد 0.2٪ هستند؛ تضمین آینده نیستند.

from . import indicators as ind

# ---------- پول‌های نماد ----------
POOL1 = ["BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT"]
POOL2 = ["XAUT-USDT", "LTC-USDT", "DOGE-USDT", "SUI-USDT", "NEAR-USDT"]
POOL3A = ["DOT-USDT", "ADA-USDT", "LINK-USDT", "AVAX-USDT", "ATOM-USDT", "FIL-USDT",
          "INJ-USDT", "SEI-USDT", "TIA-USDT", "POL-USDT", "OP-USDT"]
POOL45 = ["SUI-USDT", "SEI-USDT", "TIA-USDT", "OP-USDT", "INJ-USDT", "POL-USDT"]

POOL_OLD = POOL1 + POOL2 + POOL3A
UNION_SYMBOLS = sorted(set(POOL_OLD))

SCENARIO_SYMBOLS = {
    "F1": POOL1 + POOL2,
    "F2": POOL_OLD,
    "F3": POOL3A + POOL2,
    "F4": POOL45,
    "F5": POOL45,
}

# ---------- پارامتر نهایی v2.2 ----------
SCENARIOS = {
    "F1": {
        "id": "F1",
        "name_fa": "شکست دونچیان ۳۲ + گیت رژیم",
        "name_en": "Donchian-32 Breakout",
        "desc_fa": "شکست کانال ۳۲ کندلی فقط در رژیم صعودی BTC؛ بعد از +1R استاپ به سربه‌سر می‌رود و تا ۶ روز رید می‌کند",
        "direction": "LONG",
        "exit_mode": "BK",
        "bk_arm_r": 1.0,            # +1R → استاپ = ورود + بافر کارمزد
        "sl_atr": 4.0,
        "cm_candles": 288,          # 6 روز
        "cooldown_h": 6,
        "donchian": 32,
        "min_atr_pct": 0.0015,
    },
    "F2": {
        "id": "F2",
        "name_fa": "بیمهٔ کرش (شورت شکست)",
        "name_en": "Crash Insurance Short",
        "desc_fa": "فقط در کرش واقعی (افت ≥8٪ BTC از سقف 96 کندلی) شورتِ شکست ۸ کندلی با استاپ سربه‌سر خودکار",
        "direction": "SHORT",
        "exit_mode": "BK",
        "bk_arm_r": 1.5,
        "sl_atr": 3.5,
        "cm_candles": 432,          # 9 روز
        "cooldown_h": 24,
        "dd_gate": 0.08,
        "break_lookback": 8,
    },
    "F3": {
        "id": "F3",
        "name_fa": "پول‌بک لانگ در روند",
        "name_en": "Trend Pullback Long",
        "desc_fa": "در روند صعودی (شیب EMA50 ≥1.2٪ در ۲۴ کندل)، بازگشت به EMA21 با کندل برگشتی = ورود؛ تریلینگ پهن 5×ATR",
        "direction": "LONG",
        "exit_mode": "TRAIL",
        "trail_atr": 5.0,
        "sl_atr": 2.5,
        "cm_candles": 432,
        "cooldown_h": 24,
        "slope_lb": 24,
        "slope_min": 0.012,
        "touch_atr": 0.2,
    },
    "F4": {
        "id": "F4",
        "name_fa": "ریباند-شورت جدیدها",
        "name_en": "New-Coin Rebound Short",
        "desc_fa": "در افت BTC و افت ≥8٪ خود نماد، پاداشِ بازگشت به EMA21 با کندل رد شدن = شورت؛ استاپ سربه‌سر خودکار",
        "direction": "SHORT",
        "exit_mode": "BK",
        "bk_arm_r": 1.0,
        "sl_atr": 2.5,
        "cm_candles": 288,
        "cooldown_h": 8,
        "dd_gate": 0.035,
        "coin_dd": 0.08,
        "touch_atr": 0.2,
    },
    "F5": {
        "id": "F5",
        "name_fa": "کپیتولیشن لانگ",
        "name_en": "Capitulation Long",
        "desc_fa": "کف‌گیری حجم‌محور در پنیک جدیدها (حجم ≥1.5×، دامنه ≥1.8×ATR، کلوز نزدیک کف)؛ بعد از +1R سربه‌سر",
        "direction": "LONG",
        "exit_mode": "BK",
        "bk_arm_r": 1.0,
        "sl_atr": 2.5,
        "cm_candles": 144,
        "cooldown_h": 24,
        "vol_x": 1.5,
        "range_x": 1.8,
        "close_pos_max": 0.35,
    },
}

ACTIVE_SCENARIOS = ["F1", "F2", "F3", "F4", "F5"]

SYMBOL_TAG = {s: s.split("-")[0] for s in UNION_SYMBOLS}


def scenario_desc(sid: str) -> str:
    sc = SCENARIOS[sid]
    return f"{sc['name_fa']} ({sc['name_en']})"


class MarketContext:
    """داده بازار برای یک تیک: کندل‌های 30m هر نماد + کندل‌های 4h BTC."""

    def __init__(self, candles30: dict, btc_4h=None, candles1m=None):
        self.candles30 = candles30
        self.btc_4h = btc_4h or []
        self.candles1m = candles1m or {}
        self._btc_regime = None
        self._btc_dd = None

    def btc_regime_bull(self) -> bool:
        if self._btc_regime is None:
            closes = [c["c"] for c in self.btc_4h]
            e21 = ind.ema(closes, 21)
            e50 = ind.ema(closes, 50)
            self._btc_regime = (e21 is not None and e50 is not None and e21 > e50)
        return self._btc_regime

    def btc_drawdown_96h(self, i_btc=None) -> float:
        if self._btc_dd is None:
            btc = self.candles30.get("BTC-USDT") or []
            if len(btc) < 96:
                self._btc_dd = 0.0
            else:
                hi = max(c["h"] for c in btc[-96:])
                last = btc[-1]["c"]
                self._btc_dd = max(0.0, 1.0 - last / hi) if hi > 0 else 0.0
        return self._btc_dd


# ---------- دیتکتورها (بدون آینده‌نگری؛ فقط داده تا کندل i) ----------
def _base_signal(sc, symbol, direction, i, entry, sl, atr_val, extra=None):
    sig = {
        "scenario_id": sc["id"],
        "symbol": symbol,
        "direction": direction,
        "candle_index": i,
        "entry_hint": entry,
        "stop_loss": sl,
        "atr": atr_val,
    }
    if sc["exit_mode"] == "FIXED":
        tp_dist = sc["tp_atr"] * atr_val
        sig["take_profit"] = entry - tp_dist if direction == "LONG" else entry + tp_dist
    if extra:
        sig.update(extra)
    return sig


def detect_F1(candles, i, ctx: MarketContext, symbol):
    sc = SCENARIOS["F1"]
    if sc["direction"] != "LONG":
        return None
    if not ctx.btc_regime_bull():
        return None
    if i < sc["donchian"] + 60:
        return None
    a = ind.atr_series(candles, 14)
    atr_val = a[i]
    if not atr_val:
        return None
    px = candles[i]["c"]
    if atr_val / px < sc["min_atr_pct"]:
        return None
    if px <= ind.highest(candles, i, sc["donchian"]):
        return None
    entry = px
    sl = entry - sc["sl_atr"] * atr_val
    return _base_signal(sc, symbol, "LONG", i, entry, sl, atr_val,
                        extra={"donchian_hi": ind.highest(candles, i, sc["donchian"])})


def detect_F2(candles, i, ctx: MarketContext, symbol):
    sc = SCENARIOS["F2"]
    if ctx.btc_drawdown_96h() < sc["dd_gate"]:
        return None
    if i < 80:
        return None
    closes = [c["c"] for c in candles[:i + 1]]
    e50 = ind.ema(closes, 50)
    a = ind.atr_series(candles, 14)
    atr_val = a[i]
    if not e50 or not atr_val:
        return None
    px = candles[i]["c"]
    if px >= e50:
        return None
    if px >= ind.lowest(candles, i, sc["break_lookback"]):
        return None
    entry = px
    sl = entry + sc["sl_atr"] * atr_val
    return _base_signal(sc, symbol, "SHORT", i, entry, sl, atr_val,
                        extra={"btc_dd": round(ctx.btc_drawdown_96h() * 100, 1)})


def detect_F3(candles, i, ctx: MarketContext, symbol):
    """پول‌بک لانگ: روند صعودی + لمس EMA21 + کندل برگشتی"""
    sc = SCENARIOS["F3"]
    if i < 80 + sc["slope_lb"]:
        return None
    closes = [c["c"] for c in candles[:i + 1]]
    e21 = ind.ema(closes, 21)
    e50 = ind.ema(closes, 50)
    a = ind.atr_series(candles, 14)
    atr_val = a[i]
    if not e21 or not e50 or not atr_val:
        return None
    e50_past = ind.ema(closes[:i + 1 - sc["slope_lb"]], 50)
    if not e50_past:
        return None
    px = candles[i]["c"]
    # گیت روند: شیب EMA50 و قیمت بالای آن
    if e50 < e50_past * (1 + sc["slope_min"]):
        return None
    if px <= e50:
        return None
    # پول‌بک: لمس EMA21 + کلوز صعودی بالای EMA21
    if candles[i]["l"] > e21 + sc["touch_atr"] * atr_val:
        return None
    if px <= e21 or px <= candles[i]["o"]:
        return None
    entry = px
    sl = entry - sc["sl_atr"] * atr_val
    return _base_signal(sc, symbol, "LONG", i, entry, sl, atr_val)


def detect_F4(candles, i, ctx: MarketContext, symbol):
    """ریباند-شورت: افت BTC + افت خود نماد + بازگشت به EMA21 + کندل رد شدن"""
    sc = SCENARIOS["F4"]
    if ctx.btc_drawdown_96h() < sc["dd_gate"]:
        return None
    if i < 120:
        return None
    closes = [c["c"] for c in candles[:i + 1]]
    e21 = ind.ema(closes, 21)
    e50 = ind.ema(closes, 50)
    a = ind.atr_series(candles, 14)
    atr_val = a[i]
    if not e21 or not e50 or not atr_val:
        return None
    px = candles[i]["c"]
    hi72 = max(c["h"] for c in candles[i - 71:i + 1])
    if (1.0 - px / hi72) < sc["coin_dd"]:
        return None
    if px >= e50:
        return None
    if candles[i]["h"] < e21 - sc["touch_atr"] * atr_val:
        return None
    if px >= candles[i]["o"] or px >= e21:
        return None
    entry = px
    sl = entry + sc["sl_atr"] * atr_val
    return _base_signal(sc, symbol, "SHORT", i, entry, sl, atr_val)


def detect_F5(candles, i, ctx: MarketContext, symbol):
    sc = SCENARIOS["F5"]
    if i < 80:
        return None
    a = ind.atr_series(candles, 14)
    atr_val = a[i]
    if not atr_val:
        return None
    c = candles[i]
    avg_v = ind.avg_volume(candles, i, 20)
    if avg_v <= 0 or c["v"] < sc["vol_x"] * avg_v:
        return None
    rng = c["h"] - c["l"]
    if rng < sc["range_x"] * atr_val:
        return None
    close_pos = (c["c"] - c["l"]) / rng if rng > 0 else 1.0
    if close_pos > sc["close_pos_max"]:
        return None
    closes = [x["c"] for x in candles[:i + 1]]
    e50 = ind.ema(closes, 50)
    if not e50 or c["c"] >= e50:
        return None
    entry = c["c"]
    sl = entry - sc["sl_atr"] * atr_val
    return _base_signal(sc, symbol, "LONG", i, entry, sl, atr_val,
                        extra={"vol_x": round(c["v"] / avg_v, 1)})


DETECTORS = {
    "F1": detect_F1,
    "F2": detect_F2,
    "F3": detect_F3,
    "F4": detect_F4,
    "F5": detect_F5,
}


def run_detectors(candles, i, ctx: MarketContext, symbol):
    out = []
    for sid in ACTIVE_SCENARIOS:
        if symbol not in SCENARIO_SYMBOLS[sid]:
            continue
        try:
            sig = DETECTORS[sid](candles, i, ctx, symbol)
        except Exception:
            sig = None
        if sig:
            out.append(sig)
    return out
