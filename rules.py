import logging
import aiohttp
import asyncio
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from datetime import datetime
from zoneinfo import ZoneInfo

from config import (
    RISK_LEVELS, RISK_PARAMS, RISK_FACTORS,
    INDICATOR_THRESHOLDS, ADVANCED_RISK_PARAMS,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SYMBOLS,
    SCENARIOS, ACTIVE_SCENARIOS
)
from indicators import (
    calculate_adx, calculate_cci, calculate_sar, 
    calculate_stochastic, calculate_ema, 
    calculate_swing_low, calculate_swing_high, calculate_atr
)
from patterns import ema_rejection, resistance_test, pullback, double_top_bottom
from signal_store import append_signal_row, tehran_time_str
from f6_filter import is_f6_blocked

logger = logging.getLogger(__name__)


# ==================================================================================================================
#                                              SENARIO CONFIGURATIONS
# ==================================================================================================================
# 
#  3 senario ba Win Rate 70%+ bar asas backtest 35 roozeh (2026-07-05 ta 2026-08-09)
#  Hame senario-ha: LOW risk, LONG only, RR=0.6 (TP = 60% faseleh SL)
#  RR=0.6 yani TP naziiktar az SL ast -> asan-tar hit mishavad -> WR balatar
#
#  PnL hesab: Position $10, Fee 0.1% har taraf (total 0.2% = $0.02)
#  Max hold: 48 candle 30m = 24 saat
#
# ==================================================================================================================

# SCENARIOS are defined in config.py (S1..S3 + B1 + B2)
# Import: from config import SCENARIOS, ACTIVE_SCENARIOS

# ===== Cooldown tracker: {scenario_id: {symbol: last_signal_timestamp}} =====
_last_signal_times: Dict[str, Dict[str, float]] = {
    "S1": {},
    "S2": {},
    "S3": {},
    "B1": {},
    "B2": {},
}


def reset_cooldowns():
    """
    Pak kardan hame cooldown-ha - masalan har rooz nobat-e avval ya reset manual.
    """
    for key in _last_signal_times:
        _last_signal_times[key] = {}


def get_scenario(scenario_id: str) -> Optional[dict]:
    """
    Daryaft etelaat-e senario ba ID ("S1", "S2", "S3").
    Agar ID motabar nabashad, None bargardandeh mishavad.
    """
    return SCENARIOS.get(scenario_id)


def list_scenarios() -> List[dict]:
    """
    لیست تمام سناریوها با خلاصه اطلاعات.
    """
    result = []
    for sid, sc in SCENARIOS.items():
        n_sym = len(sc["symbols_list"]) if sc.get("symbols_list") else 0
        result.append({
            "id": sid,
            "name": f"{sc['name_fa']} ({sc['name_en']})",
            "personality": sc.get("personality", ""),
            "symbols_count": n_sym,
            "rr": sc["rr"],
            "weight_threshold": sc["weight_threshold"],
            "min_rules": sc["min_passed_rules"],
            "cooldown_h": sc["cooldown_seconds"] // 3600,
            "direction_only": sc.get("direction_only"),
        })
    return result


@dataclass
class RuleResult:
    name: str
    passed: bool
    detail: str

    def __str__(self):
        status = "\u2705" if self.passed else "\u274c"
        return f"{status} {self.name}: {self.detail}"


# ========== ERSAL TELEGRAM ==========
async def send_to_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("\u26a0\ufe0f tanzimat-e telegram naqes ast")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=20) as resp:
                if resp.status == 200:
                    logger.info("\u2705 payam be telegram ersal shod")
                else:
                    logger.warning(f"\u26a0\ufe0f khata dar ersal-e telegram: {resp.status}")
        except Exception as e:
            logger.error(f"\u274c khata dar ersal be telegram: {e}")


# ===== GHAVANIN PAYEH =====
def rule_body_strength(open_15m, close_15m, high_15m, low_15m, risk_rules) -> RuleResult:
    bs = abs(close_15m - open_15m) / max(high_15m - low_15m, 1e-6)
    th = risk_rules.get("candle_15m_strength", 0.5)
    
    # Agar ghoodat-e kandel khayli bala bood (> 0.8), ehtemal-e payan-e harakat
    if bs > 0.8:
        ok = False
        detail = f"BS15={bs:.3f} [khayli bala - ehtemal-e payan-e harakat]"
    else:
        ok = bs >= th
        detail = f"BS15={bs:.3f} [>= {th}]"
    return RuleResult("ghoodat-e kandel 15m", ok, detail)


def rule_body_strength_5m(open_5m, close_5m, high_5m, low_5m, risk_rules) -> RuleResult:
    bs = abs(close_5m - open_5m) / max(high_5m - low_5m, 1e-6)
    th = risk_rules.get("candle_5m_strength", 0.5)
    
    # Agar ghoodat-e kandel 5m khayli bala bood (> 0.8)
    if bs > 0.8:
        ok = False
        detail = f"BS5={bs:.3f} [khayli bala - ehtemal-e payan-e harakat]"
    else:
        ok = bs >= th
        detail = f"BS5={bs:.3f} [>= {th}]"
    return RuleResult("ghoodat-e kandel 5m", ok, detail)


def rule_trend_1h(ema21_1h, ema50_1h, direction) -> RuleResult:
    if ema21_1h is None or ema50_1h is None:
        return RuleResult("rawand EMA 1h", False, "dade mojud nist")
    ok = (ema21_1h > ema50_1h) if direction == "LONG" else (ema21_1h < ema50_1h)
    return RuleResult("rawand EMA 1h", ok, f"EMA21={ema21_1h:.2f}, EMA50={ema50_1h:.2f}")


def rule_trend_4h(ema21_4h, ema50_4h, ema200_4h, direction) -> RuleResult:
    if ema21_4h is None or ema50_4h is None or ema200_4h is None:
        return RuleResult("rawand EMA 4h", False, "dade mojud nist")
    if direction == "LONG":
        ok = (ema21_4h > ema50_4h and ema50_4h > ema200_4h)
    else:
        ok = (ema21_4h < ema50_4h and ema50_4h < ema200_4h)
    return RuleResult("rawand EMA 4h", ok, f"EMA21={ema21_4h:.2f}, EMA50={ema50_4h:.2f}, EMA200={ema200_4h:.2f}")


def rule_rsi(rsi_30m, direction, risk_level) -> RuleResult:
    if rsi_30m is None:
        return RuleResult("RSI 30m", False, "dade mojud nist")
    
    if direction == "LONG":
        if rsi_30m > 75:
            ok = False
            detail = f"RSI={rsi_30m:.2f} [eshba-e kharid - risk-e bargasht]"
        elif risk_level == "LOW":
            ok = 50 <= rsi_30m <= 65
        elif risk_level == "MEDIUM":
            ok = 45 <= rsi_30m <= 70
        else:
            ok = 40 <= rsi_30m <= 75
        return RuleResult("RSI 30m", ok, f"RSI={rsi_30m:.2f}")
    
    else:  # SHORT
        # RSI baraye SHORT hade-aqal 35
        if rsi_30m < 35:
            ok = False
            detail = f"RSI={rsi_30m:.2f} [khayli payin - risk-e bargasht]"
        elif rsi_30m > 70:
            ok = False
            detail = f"RSI={rsi_30m:.2f} [khayli bala - risk-e edameh-ye so'ud]"
        elif risk_level == "LOW":
            ok = 35 <= rsi_30m <= 48
        elif risk_level == "MEDIUM":
            ok = 35 <= rsi_30m <= 50
        else:
            ok = 35 <= rsi_30m <= 55
        return RuleResult("RSI 30m", ok, f"RSI={rsi_30m:.2f}")


def rule_macd(macd_hist, direction, risk_level) -> RuleResult:
    if macd_hist is None:
        return RuleResult("MACD 30m", False, "dade mojud nist")
    
    if isinstance(macd_hist, list):
        macd_hist = macd_hist[-1] if macd_hist else 0.0
    
    # MACD baraye LONG MEDIUM roo-e 0.001
    if direction == "LONG":
        if risk_level == "LOW":
            ok = macd_hist > 0.002
        elif risk_level == "MEDIUM":
            ok = macd_hist > 0.001  # az 0.002 be 0.001 kahesh
        else:
            ok = macd_hist > 0.0005
    else:
        if risk_level == "LOW":
            ok = macd_hist < -0.002
        elif risk_level == "MEDIUM":
            ok = macd_hist < -0.0015
        else:
            ok = macd_hist < -0.001
    return RuleResult("MACD 30m", ok, f"MACD_hist={macd_hist:.4f}")


# ===== MARHALEH 2: VORUD-E HOSHMAND POOLBACK =====
def rule_smart_pullback_entry(price_30m, ema21_30m, rsi_30m, open_15m, close_15m, high_15m, low_15m, direction) -> RuleResult:
    if price_30m is None or ema21_30m is None or rsi_30m is None:
        return RuleResult("vorud-e hoshmand poolback", False, "dade mojud nist")
    
    if direction == "LONG":
        pullback_ok = price_30m < ema21_30m * 0.998
        rsi_ok = 45 <= rsi_30m <= 60
        bs = abs(close_15m - open_15m) / max(high_15m - low_15m, 1e-8)
        # Mahdudeh ghoodat-e kandel 0.40 ta 0.85
        candle_strong = 0.40 <= bs <= 0.85
        ok = pullback_ok and rsi_ok and candle_strong
        detail = f"ghimat={price_30m:.4f} EMA={ema21_30m:.4f} RSI={rsi_30m:.1f} BS15={bs:.3f}"
    else:
        pullback_ok = price_30m > ema21_30m * 1.002
        rsi_ok = 35 <= rsi_30m <= 50
        bs = abs(open_15m - close_15m) / max(high_15m - low_15m, 1e-8)
        candle_strong = 0.40 <= bs <= 0.85
        ok = pullback_ok and rsi_ok and candle_strong
        detail = f"ghimat={price_30m:.4f} EMA={ema21_30m:.4f} RSI={rsi_30m:.1f} BS15={bs:.3f}"
    return RuleResult("vorud-e hoshmand poolback", ok, detail)


# ===== MARHALEH 3: MOMENTUM-E JADID =====
def rule_cci_momentum(candles, direction) -> RuleResult:
    cci = calculate_cci(candles)
    if cci is None:
        return RuleResult("CCI momentum", False, "dade mojud nist")
    
    if direction == "LONG":
        if cci > 100:
            ok = False
            detail = f"CCI={cci:.2f} [eshba-e kharid]"
        else:
            ok = cci > -20
            detail = f"CCI={cci:.2f}"
    else:
        if cci < -100:
            ok = False
            detail = f"CCI={cci:.2f} [eshba-e foroosh]"
        else:
            ok = cci < 20
            detail = f"CCI={cci:.2f}"
    return RuleResult("CCI obruz az 0", ok, detail)


def rule_stochastic_momentum(candles, direction) -> RuleResult:
    k, d = calculate_stochastic(candles)
    if k is None or d is None:
        return RuleResult("Stochastic cross", False, "dade mojud nist")
    
    if direction == "LONG":
        if k > 80:
            ok = False
            detail = f"K={k:.2f} [eshba-e kharid]"
        else:
            ok = (k > d) and (k < 70) and (k > 20)
            detail = f"K={k:.2f} D={d:.2f}"
    else:
        if k < 20:
            ok = False
            detail = f"K={k:.2f} [eshba-e foroosh]"
        else:
            ok = (k < d) and (k > 25) and (k < 80)
            detail = f"K={k:.2f} D={d:.2f}"
    return RuleResult("Stochastic cross", ok, detail)


# ===== GHAVANIN MARHALEH 1 =====
def rule_adx(candles: list, direction: str) -> RuleResult:
    adx, di_plus, di_minus = calculate_adx(candles)
    if adx is None:
        return RuleResult("ADX", False, "dade ADX mojud nist")
    
    # ADX baraye LONG roo-e 22
    if direction == "LONG":
        ok = adx > 22 and (di_plus > di_minus)
        threshold = 22
    else:
        ok = adx > 22 and (di_minus > di_plus)
        threshold = 22
    detail = f"ADX={adx:.2f} [>{threshold}], DI+={di_plus:.2f}, DI-={di_minus:.2f}"
    return RuleResult("ADX", ok, detail)


def rule_sar(candles: list, direction: str) -> RuleResult:
    sar = calculate_sar(candles)
    if sar is None:
        return RuleResult("SAR", False, "dade SAR mojud nist")
    last_close = candles[-1]['c']
    ok = (last_close > sar) if direction == "LONG" else (last_close < sar)
    return RuleResult("SAR", ok, f"SAR={sar:.4f}, gimat={last_close:.4f}")


def rule_range_filter(ema21_30m: float, ema50_30m: float, price_30m: float) -> RuleResult:
    if ema21_30m is None or ema50_30m is None or price_30m is None or price_30m == 0:
        return RuleResult("filter-e ranj", False, "dade mojud nist")
    diff = abs(ema21_30m - ema50_30m) / price_30m
    ok = diff > 0.005
    return RuleResult("filter-e ranj", ok, f"faseleh EMA={diff:.4f} [>0.005]")


# ===== GHANUN-E JADID: FILTER-E RANJ-E TARKIBI (NESKHEH S8 - OR) =====
def rule_combined_range_filter(diff: float, adx: float, direction: str, mode: str = "OR") -> RuleResult:
    """
    mode=OR  (سخت): اگر diff<0.003 یا ADX<22 → رد
    mode=AND (شل‌تر برای S1/S2/S3): فقط اگر diff<0.003 و ADX<22 → رد
    """
    if mode == "AND":
        bad = (diff < 0.003 and adx < 22)
    else:
        bad = (diff < 0.003 or adx < 22)
    ok = not bad
    detail = f"diff={diff:.4f}, ADX={adx:.2f}, mode={mode} -> {'OK' if ok else 'RAD'}"
    return RuleResult("filter-e ranj-e tarkibi", ok, detail)


# ===== GHAVANIN-E OLOGHU =====
def rule_ema_rejection(prices_series_30m: list, ema21_30m: float) -> RuleResult:
    if not prices_series_30m or ema21_30m is None:
        return RuleResult("rad EMA", False, "dade mojud nist")
    rejected = ema_rejection(prices_series_30m, ema21_30m)
    return RuleResult("rad EMA", rejected, "rad EMA tashkhis dadeh shod" if rejected else "bedun rad")


def rule_resistance_test(prices_series_30m: list, ema50_30m: float) -> RuleResult:
    if not prices_series_30m or ema50_30m is None:
        return RuleResult("test-e moqavemat", False, "dade mojud nist")
    tested = resistance_test(prices_series_30m, ema50_30m)
    return RuleResult("test-e moqavemat", tested, "test-e moqavemat taeed shod" if tested else "bedun test")


def rule_pullback(prices_series_30m: list, direction: str) -> RuleResult:
    if not prices_series_30m:
        return RuleResult("poolback", False, "dade mojud nist")
    pb = pullback(prices_series_30m, direction)
    return RuleResult("poolback", pb, "poolback tashkhis dadeh shod" if pb else "bedun poolback")


def rule_double_top_bottom(prices_series_30m: list) -> RuleResult:
    if not prices_series_30m:
        return RuleResult("Double Top/Bottom", False, "dade mojud nist")
    pattern = double_top_bottom(prices_series_30m)
    ok = pattern is not None
    return RuleResult("Double Top/Bottom", ok, f"ologhu={pattern}" if ok else "bedun ologhu")


# ===== NAGHESHEH VAZN-E GHAVANIN =====
RULE_GROUP_MAP = {
    "ghoodat-e kandel 15m": "Candles",
    "ghoodat-e kandel 5m": "Candles",
    "rawand EMA 1h": "EMA",
    "rawand EMA 4h": "TF_Big",
    "RSI 30m": "Confirm",
    "MACD 30m": "Confirm",
    "vorud-e hoshmand poolback": "Confirm",
    "ADX": "ADX",
    "CCI obruz az 0": "CCI",
    "SAR": "SAR",
    "Stochastic cross": "Stoch",
    "rad EMA": "Patterns",
    "test-e moqavemat": "Patterns",
    "poolback": "Patterns",
    "Double Top/Bottom": "Patterns",
    "filter-e ranj": "RiskMgmt",
    "filter-e ranj-e tarkibi": "RiskMgmt",
}


def evaluate_rules(
    symbol: str, direction: str, risk: str, risk_rules: dict,
    price_30m: float,
    open_15m: float, close_15m: float, high_15m: float, low_15m: float,
    open_5m: float, close_5m: float, high_5m: float, low_5m: float,
    open_1m: float, close_1m: float, high_1m: float, low_1m: float,
    ema21_30m: float, ema50_30m: float, ema8_30m: float,
    ema21_1h: float, ema50_1h: float,
    ema21_4h: float, ema50_4h: float, ema200_4h: float,
    macd_hist_30m: float, rsi_30m: float,
    vol_spike_factor: float, divergence_detected: bool,
    candles: list, prices_series_30m: list, closes_by_tf: dict,
    adx_value: float,
    range_filter_mode: str = "OR",
) -> Tuple[List[RuleResult], float, float]:

    # Mohasebeh faseleh EMA baraye filter-e tarkibi
    diff = abs(ema21_30m - ema50_30m) / price_30m if price_30m and price_30m != 0 else 0

    rule_results = [
        rule_body_strength(open_15m, close_15m, high_15m, low_15m, risk_rules),
        rule_body_strength_5m(open_5m, close_5m, high_5m, low_5m, risk_rules),
        rule_trend_1h(ema21_1h, ema50_1h, direction),
        rule_trend_4h(ema21_4h, ema50_4h, ema200_4h, direction),
        rule_rsi(rsi_30m, direction, risk),
        rule_macd(macd_hist_30m, direction, risk),
        rule_smart_pullback_entry(price_30m, ema21_30m, rsi_30m, open_15m, close_15m, high_15m, low_15m, direction),
        rule_adx(candles, direction),
        rule_cci_momentum(candles, direction),
        rule_sar(candles, direction),
        rule_stochastic_momentum(candles, direction),
        rule_ema_rejection(prices_series_30m, ema21_30m),
        rule_resistance_test(prices_series_30m, ema50_30m),
        rule_pullback(prices_series_30m, direction),
        rule_double_top_bottom(prices_series_30m),
        rule_range_filter(ema21_30m, ema50_30m, price_30m),
        rule_combined_range_filter(diff, adx_value, direction, mode=range_filter_mode),
    ]

    weights = RISK_FACTORS.get(risk, {})
    passed_weight = sum(weights.get(RULE_GROUP_MAP.get(r.name, "Other"), 0) for r in rule_results if r.passed)
    total_weight = sum(weights.get(RULE_GROUP_MAP.get(r.name, "Other"), 0) for r in rule_results)

    return rule_results, passed_weight, total_weight


# ==================================================================================================================
#                                         TOLID-E SIGNAL - NESKHEH ASLI (BA SENARIO)
# ==================================================================================================================
async def generate_signal(
    symbol: str,
    direction: str,
    prefer_risk: str,
    price_30m: float,
    open_15m: float, close_15m: float, high_15m: float, low_15m: float,
    open_5m: float, close_5m: float, high_5m: float, low_5m: float,
    open_1m: float, close_1m: float, high_1m: float, low_1m: float,
    ema21_30m: float, ema50_30m: float, ema8_30m: float,
    ema21_1h: float, ema50_1h: float,
    ema21_4h: float, ema50_4h: float, ema200_4h: float,
    macd_line_30m: float, hist_30m: float,
    rsi_30m: float,
    atr_val_30m: float,
    curr_vol: float,
    avg_vol_30m: float,
    divergence_detected: bool,
    candles: list,
    prices_series_30m: list,
    closes_by_tf: dict,
    scenario_id: Optional[str] = None
) -> Optional[dict]:
    """
    Tolid-e signal ba poshtibani az 3 senario-e baha-tar az 70% win rate.
    
    Agar scenario_id=None ya None bashad, raftare asli ghabli (bedun senario) ejra mishavad.
    Agar scenario_id yek az "S1", "S2", "S3" bashad, ghavanin-e senaro etefaq mioftad.
    
    Hame senario-ha:
      - Faghat direction LONG
      - Faghat risk level LOW
      - RR sabt-e 0.6 (TP = 60% faseleh az entry be SL)
      - Agah-e vazn-e khas baraye har senario
      - Tadad-e kamtar-e ghanoon-e pass-shodeh baraye har senario
      - Cooldown bein signal-ha baraye har symbol
      - Filter-e symbol-haye mozam baraye S2 va S3
    """
    time_str = tehran_time_str()

    # ===== AGHAB-NDAZI SENARIO =====
    scenario = None
    if scenario_id and scenario_id in SCENARIOS:
        scenario = SCENARIOS[scenario_id]
    
    # ===== FILTER-E JHAT (FAGHAT LONG) =====
    if scenario and scenario["direction_only"] and direction != scenario["direction_only"]:
        logger.info(f"Senario {scenario_id}: rad shod - jhat {direction} != {scenario['direction_only']}")
        return None
    
    
    # ===== FILTER-E SYMBOL =====
    if scenario and scenario["symbols_list"] is not None:
        if symbol not in scenario["symbols_list"]:
            return None  # Bedun log - signal-haye symbol-haye gheire-mojaz nadarim
    
    # ===== FILTER-E COOLDOWN =====
    if scenario:
        sc_cooldown = scenario["cooldown_seconds"]
        sc_id = scenario["id"]
        if sc_id not in _last_signal_times:
            _last_signal_times[sc_id] = {}
        last_ts = _last_signal_times[sc_id].get(symbol, 0)
        now_ts = time.time()
        if now_ts - last_ts < sc_cooldown:
            remaining = sc_cooldown - (now_ts - last_ts)
            logger.info(
                f"Senario {scenario_id} | {symbol}: cooldown - {remaining/3600:.1f}s baghi mandeh"
            )
            return None

    # ===== F6: قفل جهت بعد از ۲ استاپ هم‌جهت در همان روز =====
    # جلوی کلاستر ضرر (مثل روز ۲۲) را می‌گیرد؛ در بک‌تست WR≈۷۶٪ با حفظ رشد
    f6_blocked, f6_sl = is_f6_blocked(direction)
    if f6_blocked:
        logger.info(
            f"F6 block | {symbol} {direction}: {f6_sl} STOP_HIT هم‌جهت امروز "
            f"(سقف={2}) — سیگنال جدید در این جهت صادر نمی‌شود"
        )
        return None

    # ===== MOHASEBEH ADX =====
    adx, _, _ = calculate_adx(candles)
    if adx is None:
        adx = 0

    
    # ===== EXTRA FILTERS (B1 / B2) =====
    if scenario and scenario.get("extra_filters"):
        ef = scenario["extra_filters"]
        # body strength from 15m candle
        bs15 = abs(close_15m - open_15m) / max(high_15m - low_15m, 1e-8)
        adx_tmp, di_p, di_m = calculate_adx(candles)
        if adx_tmp is None:
            adx_tmp = 0.0
        if ef.get("min_body_strength") and bs15 < ef["min_body_strength"]:
            logger.info(f"Senario {scenario_id}: رد - body={bs15:.3f} < {ef['min_body_strength']}")
            return None
        if ef.get("min_adx") and adx_tmp < ef["min_adx"]:
            logger.info(f"Senario {scenario_id}: رد - ADX={adx_tmp:.1f} < {ef['min_adx']}")
            return None
        if ef.get("require_di_align"):
            if direction == "LONG" and not (di_p > di_m):
                logger.info(f"Senario {scenario_id}: رد - DI نه همسو برای LONG")
                return None
            if direction == "SHORT" and not (di_m > di_p):
                logger.info(f"Senario {scenario_id}: رد - DI نه همسو برای SHORT")
                return None
        if ef.get("require_close_extreme"):
            rng = max(high_15m - low_15m, 1e-12)
            close_pos = (close_15m - low_15m) / rng
            if direction == "LONG" and close_pos < ef.get("close_long_min", 0.82):
                logger.info(f"Senario {scenario_id}: رد - close_pos={close_pos:.2f} برای LONG")
                return None
            if direction == "SHORT" and close_pos > ef.get("close_short_max", 0.18):
                logger.info(f"Senario {scenario_id}: رد - close_pos={close_pos:.2f} برای SHORT")
                return None

    # پروفایل قوانین از سناریو (بدون نمایش سطح ریسک)
    if scenario:
        profile = scenario.get("rule_profile", "strict")
        internal_risk = "LOW" if profile == "strict" else "MEDIUM"
        range_mode = scenario.get("range_filter_mode", "OR")
    else:
        internal_risk = prefer_risk or "MEDIUM"
        range_mode = "OR"
    risk_rules = next((r["rules"] for r in RISK_LEVELS if r["key"] == internal_risk), RISK_LEVELS[1]["rules"])
    rule_results, passed_weight, total_weight = evaluate_rules(
        symbol=symbol,
        direction=direction,
        risk=internal_risk,
        risk_rules=risk_rules,
        price_30m=price_30m,
        open_15m=open_15m, close_15m=close_15m, high_15m=high_15m, low_15m=low_15m,
        open_5m=open_5m, close_5m=close_5m, high_5m=high_5m, low_5m=low_5m,
        open_1m=open_1m, close_1m=close_1m, high_1m=high_1m, low_1m=low_1m,
        ema21_30m=ema21_30m, ema50_30m=ema50_30m, ema8_30m=ema8_30m,
        ema21_1h=ema21_1h, ema50_1h=ema50_1h,
        ema21_4h=ema21_4h, ema50_4h=ema50_4h, ema200_4h=ema200_4h,
        macd_hist_30m=hist_30m,
        rsi_30m=rsi_30m,
        vol_spike_factor=1.0,
        divergence_detected=divergence_detected,
        candles=candles,
        prices_series_30m=prices_series_30m,
        closes_by_tf=closes_by_tf,
        adx_value=adx,
        range_filter_mode=range_mode,
    )

    strength_ratio = passed_weight / total_weight if total_weight > 0 else 0
    passed_rules_count = sum(1 for r in rule_results if r.passed)
    total_rules = len(rule_results)

    # ===== TAEIN-E SL/TP =====
    if scenario:
        # ===== SCENARIO MODE =====
        rr_target = scenario["rr"]
        atr_mult = scenario.get("atr_mult", 1.5)
    else:
        # ===== MODE ASLI (BEDUN SENARIO): RR dinamik bar asas strength_ratio =====
        if direction == "LONG":
            if strength_ratio >= 0.65:
                atr_mult, rr_target = 1.5, 2.5
            elif strength_ratio >= 0.45:
                atr_mult, rr_target = 1.8, 2.0
            else:
                atr_mult, rr_target = 2.0, 1.5
        else:
            if strength_ratio >= 0.65:
                atr_mult, rr_target = 2.0, 2.5
            elif strength_ratio >= 0.45:
                atr_mult, rr_target = 2.5, 2.0
            else:
                atr_mult, rr_target = 3.0, 1.5

    if direction == "LONG":
        swing_low = calculate_swing_low(candles)
        buffer = 0.001 * price_30m
        stop_loss = swing_low - buffer if swing_low is not None else price_30m - atr_val_30m * atr_mult
        take_profit = price_30m + (price_30m - stop_loss) * rr_target
    else:
        swing_high = calculate_swing_high(candles)
        buffer = 0.003 * price_30m
        stop_loss = swing_high + buffer if swing_high is not None else price_30m + atr_val_30m * atr_mult
        take_profit = price_30m - (stop_loss - price_30m) * rr_target

    # سطح ریسک حذف شده — فقط سناریو
    final_risk = ""

    # ===== TAEIN-E VOZUD-E SIGNAL =====
    if scenario:
        # Senario mode: az vazn-e senaro estefadeh kon
        sc_wt = scenario["weight_threshold"]
        sc_mr = scenario["min_passed_rules"]
        status = "SIGNAL" if (passed_weight >= total_weight * sc_wt and passed_rules_count >= sc_mr) else "NO_SIGNAL"
    else:
        # Mode asli: aastaneh 0.50
        status = "SIGNAL" if passed_weight >= total_weight * 0.50 else "NO_SIGNAL"

    passed_list = [str(r) for r in rule_results if r.passed]
    failed_list = [str(r) for r in rule_results if not r.passed]
    failed_rules_count = len(failed_list)

    # ===== LOGGING =====
    log_prefix = f"[Senario {scenario_id}]" if scenario else "[Default]"
    logger.info("=" * 80)
    logger.info(f"{log_prefix} signal {symbol} | jhat={direction} | risk={final_risk}")
    logger.info(f"ghavanin-e pass-shodeh: vazn={passed_weight}/{total_weight} | tedad={passed_rules_count}/{total_rules}")
    if scenario:
        logger.info(f"senario: WT>={scenario['weight_threshold']*100:.0f}% | MinRules>={scenario['min_passed_rules']} | RR={scenario['rr']}")
    logger.info("hame ghavanin barresi-shodeh:")
    logger.info("\n".join([str(r) for r in rule_results]))
    logger.info("-" * 60)
    logger.info("ghavanin-e pass-shodeh:")
    logger.info("\n".join(passed_list) if passed_list else "hich-kodom")
    logger.info("ghavanin rad-shodeh:")
    logger.info("\n".join(failed_list) if failed_list else "hich-kodom")
    logger.info(f"vozhud-e nahayi: {status}")
    logger.info(f"SL: {stop_loss:.4f} | TP: {take_profit:.4f}")
    logger.info("=" * 80)

    signal_dict = {
        "symbol": symbol,
        "direction": direction,
        "risk": "",
        "status": status,
        "strength": passed_weight / total_weight if status == "SIGNAL" else None,
        "price": price_30m,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "time": time_str,
        "signal_source": ";".join([str(r) for r in rule_results]),
        "details": [str(r) for r in rule_results],
        "passed_weight": passed_weight,
        "total_weight": total_weight,
        "passed_rules_count": passed_rules_count,
        "total_rules": total_rules,
    }
    
    # Ezafeh kardan etelaat-e senaro
    if scenario:
        signal_dict["scenario_id"] = scenario_id
        signal_dict["scenario_name"] = f"{scenario['name_fa']} ({scenario['name_en']})"
        signal_dict["scenario_rr"] = scenario["rr"]

    if status == "SIGNAL":
        # ===== UPDATE COOLDOWN =====
        if scenario:
            sc_id = scenario["id"]
            if sc_id not in _last_signal_times:
                _last_signal_times[sc_id] = {}
            _last_signal_times[sc_id][symbol] = time.time()

        sc_name = ""
        sc_id_val = ""
        if scenario:
            sc_id_val = scenario.get("id", scenario_id or "")
            sc_name = f"{scenario['name_fa']} ({scenario['name_en']})"

        append_signal_row(
            symbol=symbol,
            direction=direction,
            entry_price=price_30m,
            stop_loss=stop_loss,
            take_profit=take_profit,
            issued_at_tehran=time_str,
            signal_source=";".join([str(r) for r in rule_results]),
            scenario_id=sc_id_val,
            scenario_name=sc_name,
            position_size_usd=10.0,
        )

        dir_icon = "🟢" if direction == "LONG" else "🔴"

        sc_header = ""
        if scenario:
            personality = scenario.get("personality", "")
            sc_header = (
                f"──────────────────\n"
                f"🏆 سناریو {scenario['name_fa']} ({scenario['name_en']})\n"
                f"🎭 شخصیت: {personality}\n"
                f"🎯 RR={scenario['rr']} | آستانه وزن≥{scenario['weight_threshold']*100:.0f}% | "
                f"حداقل قانون≥{scenario['min_passed_rules']} | "
                f"کول‌داون={scenario['cooldown_seconds']//3600}س\n"
                f"──────────────────\n"
            )

        msg = (
            f"{sc_header}"
            f"───────────\n"
            f"📊 سیگنال {symbol}\n"
            f"جهت: {dir_icon} {direction}\n"
            f"ورود: {price_30m:.4f}\n"
            f"استاپ: {stop_loss:.4f}\n"
            f"تارگت: {take_profit:.4f}\n"
            f"زمان: {time_str}\n"
            f"───────────\n"
            f"📋 قوانین پاس‌شده: وزن={passed_weight}/{total_weight} | تعداد={passed_rules_count}/{total_rules}\n"
            + "\n".join([f"✅ {r.name} → {r.detail}" for r in rule_results if r.passed]) + "\n"
            f"❌ قوانین ردشده ({failed_rules_count}):\n"
            + "\n".join([f"❌ {r.name} → {r.detail}" for r in rule_results if not r.passed])
        )
        await send_to_telegram(msg)


    return signal_dict


# ==================================================================================================================
#                                         TOLID-E SIGNAL - BAA SENARIO (NAAME RAHA-TAR)
# ==================================================================================================================
async def generate_signal_scenario(
    scenario_id: str,
    symbol: str,
    direction: str,
    price_30m: float,
    open_15m: float, close_15m: float, high_15m: float, low_15m: float,
    open_5m: float, close_5m: float, high_5m: float, low_5m: float,
    open_1m: float, close_1m: float, high_1m: float, low_1m: float,
    ema21_30m: float, ema50_30m: float, ema8_30m: float,
    ema21_1h: float, ema50_1h: float,
    ema21_4h: float, ema50_4h: float, ema200_4h: float,
    macd_line_30m: float, hist_30m: float,
    rsi_30m: float,
    atr_val_30m: float,
    curr_vol: float,
    avg_vol_30m: float,
    divergence_detected: bool,
    candles: list,
    prices_series_30m: list,
    closes_by_tf: dict,
) -> Optional[dict]:
    """
    Naame-e rahat-tar baraye tolid-e signal ba senaro.
    Faghat scenario_id ra begirad va baaqi parametr-ha ra be generate_signal pass bedehad.
    
    Senaro automatic risk=LOW ra estefadeh mikonad.
    
    Masaalan:
        result = await generate_signal_scenario(
            scenario_id="S2",  # Silver Arrow
            symbol="SOL-USDT",
            direction="LONG",
            ...
        )
    """
    from config import SCENARIOS
    sc = SCENARIOS.get(scenario_id, {})
    prefer = sc.get("risk_level", "LOW")
    return await generate_signal(
        symbol=symbol,
        direction=direction,
        prefer_risk=prefer,
        price_30m=price_30m,
        open_15m=open_15m, close_15m=close_15m, high_15m=high_15m, low_15m=low_15m,
        open_5m=open_5m, close_5m=close_5m, high_5m=high_5m, low_5m=low_5m,
        open_1m=open_1m, close_1m=close_1m, high_1m=high_1m, low_1m=low_1m,
        ema21_30m=ema21_30m, ema50_30m=ema50_30m, ema8_30m=ema8_30m,
        ema21_1h=ema21_1h, ema50_1h=ema50_1h,
        ema21_4h=ema21_4h, ema50_4h=ema50_4h, ema200_4h=ema200_4h,
        macd_line_30m=macd_line_30m, hist_30m=hist_30m,
        rsi_30m=rsi_30m,
        atr_val_30m=atr_val_30m,
        curr_vol=curr_vol,
        avg_vol_30m=avg_vol_30m,
        divergence_detected=divergence_detected,
        candles=candles,
        prices_series_30m=prices_series_30m,
        closes_by_tf=closes_by_tf,
        scenario_id=scenario_id
    )
