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
    "F1": POOL_OLD,  # Khosro rule book: هر نماد نقدشونده با داده کافی
    "F2": POOL_OLD,
    "F3": POOL3A + POOL2,
    "F4": POOL45,
    "F5": POOL45,
}

# ---------- پارامتر نهایی v2.2 ----------
SCENARIOS = {
    "F1": {
        "id": "F1",
        "name_fa": "KhosroAiTrader Rule Book v1 (کامل)",
        "name_en": "KhosroAiTrader Rule Book v1",
        "desc_fa": (
            "پکیج کامل KhosroAiTrader: RuleSignalEngine + MarketDataHub + RiskEngine + config.yaml "
            "بدون بازنویسی منطق؛ کندل 1h بایننس و لبه depth/funding/OI/LSR"
        ),
        "direction": "BOTH",
        "exit_mode": "FIXED",
        "tp_atr": 3.0,              # 2R وقتی SL = 1.5×ATR
        "sl_atr": 1.5,              # config signals.atr_sl_multiplier
        "cm_candles": 144,          # ~72h روی 30m ≈ max_age_hours خوسرو
        "cooldown_h": 12,           # signals.cooldown_hours
        "min_confidence": 45,       # signals.min_confidence
        "min_score_gap": 15,        # signals.min_score_gap
        "min_atr_pct": 0.3,         # percent of price
        "max_atr_pct": 8.0,
        "trend_gate": False,        # tested off in Khosro config
        "vol_surge_min": 1.15,
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
    """داده بازار برای یک تیک: کندل‌های 30m هر نماد + کندل‌های 4h BTC.

    فیلدهای کشف ترند (از v3.4.0 — فقط در مسیر زنده توسط discovery.apply پر می‌شوند؛
    در شبیه‌ساز/بک‌تست None می‌مانند یعنی F1 بدون فیلتر روی کل استخر اسکن می‌شود):
      f1_universe    — مجموعه نمادهای پایه مجاز برای F1 (انتخاب AI + ارزهای اصلی)
      khosro_ai      — AIAnalysis خوسرو → داخل detect_F1 به snapshot می‌چسبد (fusion)
      discovery_info — خلاصه کشف ترند برای گزارش تشخیصی Actions
    """

    def __init__(self, candles30: dict, btc_4h=None, candles1m=None):
        self.candles30 = candles30
        self.btc_4h = btc_4h or []
        self.candles1m = candles1m or {}
        self.f1_universe = None
        self.khosro_ai = None
        self.discovery_info = None
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
def _base_signal(sc, symbol, direction, i, entry, sl, atr_val, extra=None, reason=""):
    sig = {
        "scenario_id": sc["id"],
        "symbol": symbol,
        "direction": direction,
        "candle_index": i,
        "entry_hint": entry,
        "stop_loss": sl,
        "atr": atr_val,
        "reason": reason or sc.get("desc_fa", sc.get("name_fa", sc["id"])),
    }
    if sc["exit_mode"] == "FIXED":
        tp_dist = sc["tp_atr"] * atr_val
        # LONG هدف بالای ورود؛ SHORT هدف پایین ورود
        sig["take_profit"] = entry + tp_dist if direction == "LONG" else entry - tp_dist
    if extra:
        sig.update(extra)
    return sig



def _f1_rows_from_kucoin(candles, i):
    """30m KuCoin → ردیف خام 1h سبک بایننس برای تغذیه RuleSignalEngine."""
    src = candles[: i + 1]
    if len(src) < 2:
        return []
    bars = []
    start = len(src) % 2
    for j in range(start, len(src), 2):
        chunk = src[j:j + 2]
        if len(chunk) == 1:
            bars.append(chunk[0])
            continue
        a, b = chunk[0], chunk[1]
        bars.append({
            "t": a.get("t", 0),
            "o": a["o"], "h": max(a["h"], b["h"]), "l": min(a["l"], b["l"]),
            "c": b["c"], "v": float(a.get("v") or 0) + float(b.get("v") or 0),
        })
    rows = []
    for c in bars:
        t0 = int(c.get("t") or 0)
        ms = t0 if t0 > 10_000_000_000 else t0 * 1000
        o, h, l, cl, v = c["o"], c["h"], c["l"], c["c"], c.get("v") or 0
        rows.append([ms, str(o), str(h), str(l), str(cl), str(v), ms + 3_599_999,
                     "0", 0, "0", "0", "0"])
    return rows



def _f1_rows_from_kucoin(candles, i):
    """30m → ردیف 1h خام برای تغذیه RuleSignalEngine (پشتیبان)."""
    src = candles[: i + 1]
    if len(src) < 2:
        return []
    bars = []
    start_i = len(src) % 2
    for j in range(start_i, len(src), 2):
        chunk = src[j:j + 2]
        if len(chunk) == 1:
            bars.append(chunk[0])
            continue
        a, b = chunk[0], chunk[1]
        bars.append({
            "t": a.get("t", 0),
            "o": a["o"], "h": max(a["h"], b["h"]), "l": min(a["l"], b["l"]),
            "c": b["c"], "v": float(a.get("v") or 0) + float(b.get("v") or 0),
        })
    rows = []
    for c in bars:
        t0 = int(c.get("t") or 0)
        ms = t0 if t0 > 10_000_000_000 else t0 * 1000
        o, h, l, cl, v = c["o"], c["h"], c["l"], c["c"], c.get("v") or 0
        rows.append([ms, str(o), str(h), str(l), str(cl), str(v), ms + 3_599_999,
                     "0", 0, "0", "0", "0"])
    return rows


def detect_F1(candles, i, ctx: MarketContext, symbol):
    """F1 = Rule Book خوسرو + داده ترجیحاً KuCoin 1h (بدون AI).

    اولویت کندل:
      1) KuCoin type=1hour
      2) فشرده‌سازی 30m همان candles
    لبه depth/funding بایننس فقط در صورت موفقیت (روی Actions اغلب 451 است).
    """
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo

    from khosro_ai_trader.models import TrendingSnapshot
    from khosro_ai_trader.risk.engine import RiskEngine
    from khosro_ai_trader.signals.engine import RuleSignalEngine
    from khosro_ai_trader.sources.market_data import MarketDataHub

    from . import kucoin as kc

    sc = SCENARIOS["F1"]
    base = symbol.split("-")[0].upper()
    pair = f"{base}USDT"
    kc_symbol = f"{base}-USDT"

    cfg = _f1_cfg()
    hub = _f1_hub(cfg)
    engine = _f1_engine(cfg, hub)

    # لبه بازار — اختیاری؛ خطا نادیده
    try:
        md_data = hub.enrich_coins([{"symbol": base, "pair": pair}])
    except Exception:
        md_data = {}

    # --- کندل 1h: اول KuCoin ---
    rows = []
    try:
        rows = kc.fetch_1h_binance_style(kc_symbol, limit=cfg.signals.kline_limit, use_cache=True)
    except Exception:
        rows = []
    if not rows or len(rows) < 220:
        # پشتیبان: fold 30m
        rows = _f1_rows_from_kucoin(candles, i)
    if not rows or len(rows) < 220:
        return None
    engine._klines_cache[pair] = rows

    now = datetime.now(timezone.utc)
    tehran = now.astimezone(ZoneInfo("Asia/Tehran"))
    snap = TrendingSnapshot(
        run_at_utc=now.strftime("%Y-%m-%d %H:%M UTC"),
        run_at_tehran=tehran.strftime("%Y-%m-%d %H:%M"),
        duration_seconds=0.0,
    )
    # AI حذف شده — fusion خاموش
    snap.ai = None

    try:
        raw = engine._evaluate_coin(base, pair, snap, md_data)
    except Exception:
        return None
    if raw is None:
        return None

    risk = RiskEngine(cfg)
    reject = risk._validate(raw)
    if reject:
        return None
    risk._size(raw)

    entry = float(raw.entry)
    sl = float(raw.stop_loss)
    atr_val = float((raw.meta or {}).get("atr") or abs(entry - sl) / max(cfg.signals.atr_sl_multiplier, 1e-9))
    direction = "LONG" if raw.direction == "long" else "SHORT"
    tps = list(raw.take_profits or [])
    tp = float(tps[1]) if len(tps) > 1 else (float(tps[0]) if tps else None)
    reasons = list(raw.reasons or [])
    conf = raw.confidence
    reason = (
        f"Khosro rule-book v1 | {direction} conf={conf} | "
        + "؛ ".join(reasons[:5])
    )
    extra = {
        "take_profit": tp,
        "take_profits": tps,
        "f1_confidence": conf,
        "khosro_meta": dict(raw.meta or {}),
        "khosro_rr": raw.rr,
        "khosro_r_value": raw.r_value,
        "position_size_usd_khosro": raw.position_size_usd,
        "notional_usd_khosro": raw.notional_usd,
    }
    return _base_signal(sc, symbol, direction, i, entry, sl, atr_val, extra=extra, reason=reason)



_F1_CFG = None
_F1_HUB = None
_F1_ENGINE = None


def _f1_cfg():
    global _F1_CFG
    if _F1_CFG is None:
        from pathlib import Path
        from khosro_ai_trader.config import load_config
        # config کنار ریشه پروژه PentaSignal
        root = Path(__file__).resolve().parents[1]
        _F1_CFG = load_config(root / "config" / "config.yaml")
    return _F1_CFG


def _f1_hub(cfg):
    global _F1_HUB
    if _F1_HUB is None:
        from khosro_ai_trader.sources.market_data import MarketDataHub
        _F1_HUB = MarketDataHub(cfg)
    return _F1_HUB


def _f1_engine(cfg, hub):
    global _F1_ENGINE
    if _F1_ENGINE is None:
        from khosro_ai_trader.signals.engine import RuleSignalEngine
        _F1_ENGINE = RuleSignalEngine(cfg, hub)
    return _F1_ENGINE


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
    btc_dd = round(ctx.btc_drawdown_96h() * 100, 1)
    reason = (
        f"افت BTC از سقف 96 کندلی = {btc_dd}% (≥{sc['dd_gate']*100:.0f}%)؛ "
        f"کلوز زیر EMA50 و زیر کف {sc['break_lookback']} کندل"
    )
    return _base_signal(sc, symbol, "SHORT", i, entry, sl, atr_val,
                        extra={"btc_dd": btc_dd}, reason=reason)


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
    slope = (e50 / e50_past - 1.0) * 100 if e50_past else 0.0
    reason = (
        f"روند صعودی: شیب EMA50 در {sc['slope_lb']} کندل = {slope:.2f}% (≥{sc['slope_min']*100:.1f}%)؛ "
        f"لمس EMA21 و کلوز صعودی بالای آن"
    )
    return _base_signal(sc, symbol, "LONG", i, entry, sl, atr_val, reason=reason)


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
    coin_dd = (1.0 - px / hi72) * 100
    btc_dd = ctx.btc_drawdown_96h() * 100
    reason = (
        f"افت BTC={btc_dd:.1f}% (≥{sc['dd_gate']*100:.1f}%) و افت نماد={coin_dd:.1f}% (≥{sc['coin_dd']*100:.0f}%)؛ "
        f"بازگشت به EMA21 و کندل رد شدن نزولی"
    )
    return _base_signal(sc, symbol, "SHORT", i, entry, sl, atr_val, reason=reason)


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
    vx = round(c["v"] / avg_v, 1) if avg_v else 0
    reason = (
        f"حجم {vx}× میانگین20 (≥{sc['vol_x']}×)؛ دامنه {rng/atr_val:.1f}×ATR (≥{sc['range_x']}×)؛ "
        f"کلوز در {close_pos*100:.0f}% پایینی دامنه و زیر EMA50"
    )
    return _base_signal(sc, symbol, "LONG", i, entry, sl, atr_val,
                        extra={"vol_x": vx}, reason=reason)


DETECTORS = {
    "F1": detect_F1,
    "F2": detect_F2,
    "F3": detect_F3,
    "F4": detect_F4,
    "F5": detect_F5,
}


def run_detectors(candles, i, ctx: MarketContext, symbol):
    out = []
    base = symbol.split("-")[0].upper()
    for sid in ACTIVE_SCENARIOS:
        if symbol not in SCENARIO_SYMBOLS[sid]:
            continue
        # گشت کشف ترند F1 (از v3.4.0): خارج از «انتخاب AI + ارزهای اصلی» اسکن نشو.
        # فقط F1 فیلتر می‌شود؛ F2–F5 روی کل استخر خودشان باقی می‌مانند.
        if sid == "F1" and getattr(ctx, "f1_universe", None) is not None \
                and base not in ctx.f1_universe:
            continue
        try:
            sig = DETECTORS[sid](candles, i, ctx, symbol)
        except Exception:
            sig = None
        if sig:
            out.append(sig)
    return out
