# ps_review.py — بازنگری کامل ۵ پروفایل: بک‌تست سریع درون‌حافظه‌ای + جست‌وجوی شبکه‌ای
#
#   python ps_review.py fetch [start end]     → گرم‌کردن کش (پیش‌فرض 2026-05-07→2026-09-08)
#   python ps_review.py baseline              → پارامترهای فعلی روی 60 روز + تفکیک IS/OOS
#   python ps_review.py search F1|F2|F3|F4|F5 → جست‌وجوی شبکه‌ای یک سناریو روی پنجره IS
#   python ps_review.py combine '<json>'      → ارزیابی ترکیب انتخابی روی کل دوره + OOS
#
# پنجره‌ها (تهران):
#   IS  (بهینه‌سازی): 2026-07-10 → 2026-08-08   (30 روز — فقط این را می‌بینیم)
#   OOS (اعتبارسنجی): 2026-08-09 → 2026-09-07   (30 روز — همان ماه منفی قبلی، دست‌نخورده)
#
# معیار انتخاب (پیش‌ثبت‌شده): معامله ≥15 | maxDD≤12$ | بیشترین سود خالص
# قانون ثابت: سیگنال فقط 07:00–19:30 تهران · ورود = باز کندل بعد · کارمزد 0.2٪ RT

import os
import sys
import json
import time
import bisect
import itertools
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# مسیر ریشه ریپو (این فایل در research/ است)
V21 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = V21
sys.path.insert(0, V21)
os.environ["PS_DATA_DIR"] = os.path.join(V21, "data_review")

from pentasignal import kucoin  # noqa: E402
from pentasignal import indicators as ind  # noqa: E402

TEHRAN = ZoneInfo("Asia/Tehran")
FEE = 0.002
POS = 10.0

POOL1 = ["BTC-USDT", "ETH-USDT", "BNB-USDT", "SOL-USDT", "XRP-USDT"]
POOL2 = ["XAUT-USDT", "LTC-USDT", "DOGE-USDT", "SUI-USDT", "NEAR-USDT"]
POOL3A = ["DOT-USDT", "ADA-USDT", "LINK-USDT", "AVAX-USDT", "ATOM-USDT", "FIL-USDT",
          "INJ-USDT", "SEI-USDT", "TIA-USDT", "POL-USDT", "OP-USDT"]
POOL45 = ["SUI-USDT", "SEI-USDT", "TIA-USDT", "OP-USDT", "INJ-USDT", "POL-USDT"]
POOL_OLD = POOL1 + POOL2 + POOL3A
UNION = sorted(set(POOL_OLD))
POOL = {"F1": POOL1 + POOL2, "F2": POOL_OLD, "F3": POOL3A + POOL2,
        "F4": POOL45, "F5": POOL45}

IS_START, IS_END = "2026-07-10", "2026-08-08"
OOS_END = "2026-09-07"

D = {}      # symbol → SymData
BTC4 = None
BTC30 = None


class S:
    """داده پیش‌محاسبه‌شده یک نماد"""
    def __init__(self, candles):
        self.candles = candles
        self.t = [c["t"] for c in candles]
        self.o = [c["o"] for c in candles]
        self.h = [c["h"] for c in candles]
        self.l = [c["l"] for c in candles]
        self.c = [c["c"] for c in candles]
        self.v = [c["v"] for c in candles]
        self.atr = ind.atr_series(candles, 14)
        self.e21 = ind.ema_series(self.c, 21)
        self.e50 = ind.ema_series(self.c, 50)
        self.er10 = [0.0] * len(candles)
        for i in range(len(candles)):
            if i >= 10:
                net = abs(self.c[i] - self.c[i - 10])
                path = sum(abs(self.c[j] - self.c[j - 1]) for j in range(i - 9, i + 1))
                self.er10[i] = net / path if path > 0 else 0.0
        # میانگین حجم 20 کندل قبل
        self.avgv = [0.0] * len(candles)
        run = 0.0
        for i, v in enumerate(self.v):
            run += v
            if i >= 20:
                run -= self.v[i - 20]
            self.avgv[i] = run / min(i + 1, 20)


def hh_tehran(close_ts: int) -> int:
    return datetime.fromtimestamp(close_ts, TEHRAN).hour


def date_tehran(close_ts: int) -> str:
    return datetime.fromtimestamp(close_ts, TEHRAN).strftime("%Y-%m-%d")


class BtcCtx:
    def __init__(self, btc30: S, btc4h):
        self.b30 = btc30
        self.t4 = [c["t"] for c in btc4h]
        c4 = [c["c"] for c in btc4h]
        self.e21_4 = ind.ema_series(c4, 21)
        self.e50_4 = ind.ema_series(c4, 50)
        self.e200_30 = ind.ema_series(btc30.c, 200)
        self.atr_30 = btc30.atr
        self._dd_cache = {}

    def gate_ok(self, close_ts: int, gate: str) -> bool:
        """گیت رژیم برای ورودهای لانگ: روند/نوسان کافی BTC"""
        k = bisect.bisect_left(self.b30.t, close_ts) - 1
        if k < 200 or not self.e200_30[k] or not self.atr_30[k]:
            return False
        px = self.b30.c[k]
        atrp = self.atr_30[k] / px
        above = px > self.e200_30[k]
        if gate == "atr":
            return atrp >= 0.0022
        if gate == "ema":
            return above
        if gate == "both":
            return atrp >= 0.0022 and above
        if gate == "atr15":
            return atrp >= 0.0015
        return True

    def regime_bull(self, close_ts: int) -> bool:
        j = bisect.bisect_left(self.t4, close_ts - 4 * 3600 + 1) - 1
        if j < 50:
            return False
        e21, e50 = self.e21_4[j], self.e50_4[j]
        return bool(e21 and e50 and e21 > e50)

    def dd96(self, close_ts: int) -> float:
        """افت BTC از سقف 96 کندل 30m (تا کندل بسته‌شده در close_ts)"""
        if close_ts in self._dd_cache:
            return self._dd_cache[close_ts]
        k = bisect.bisect_left(self.b30.t, close_ts)   # t < close_ts
        seg = self.b30.h[max(0, k - 96):k]
        dd = 0.0
        if seg:
            hi = max(seg)
            last = self.b30.c[k - 1]
            dd = max(0.0, 1.0 - last / hi) if hi > 0 else 0.0
        self._dd_cache[close_ts] = dd
        return dd


def load_data(start_ts: int, end_ts: int):
    global D, BTC4, BTC30
    lb = start_ts - 32 * 86400
    D.clear()
    for sym in UNION:
        cs = kucoin.chunked_candles(sym, "30min", lb, end_ts, chunk_days=25)
        D[sym] = S(cs)
        time.sleep(0.05)
    btc4h = kucoin.chunked_candles("BTC-USDT", "4hour", lb, end_ts, chunk_days=30)
    BTC4 = btc4h
    BTC30 = D["BTC-USDT"]
    print(f"loaded {len(D)} symbols, bars={len(next(iter(D.values())).t)}")


def ts_tehran(date_str: str, hour=0) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=TEHRAN, hour=hour)
    return int(dt.timestamp())


# ================= دیتکتورها (سریع، روی آرایه‌های پیش‌محاسبه) =================
def raw_signals_F1(sym: S, p, ctx: BtcCtx, first_i, last_i):
    """p: donchian, min_atr_pct, buf_atr (بافر شکست)"""
    out = []
    D16 = p["donchian"]
    for i in range(max(first_i, D16 + 60), last_i):
        close_ts = sym.t[i] + 1800
        if not (7 <= hh_tehran(close_ts) < 20):
            continue
        if not ctx.regime_bull(close_ts):
            continue
        g = p.get("gate")
        if g and not ctx.gate_ok(close_ts, g):
            continue
        a = sym.atr[i]
        if not a or a / sym.c[i] < p["min_atr_pct"]:
            continue
        hi = max(sym.h[i - D16:i])
        px = sym.c[i]
        if px > hi + p.get("buf_atr", 0.0) * a:
            out.append((i, px, a))
    return out


def raw_signals_F3_pullback(sym: S, p, ctx: BtcCtx, first_i, last_i):
    """F3 بازطراحی: پول‌بک به EMA21 در روند — گیت: EMA50 شیب صعودی + قیمت بالای EMA50
    ورود: کندل برگشتی که low به EMA21 رسیده و close بالای EMA21 بسته شد"""
    out = []
    lb = p.get("slope_lb", 24)
    for i in range(max(first_i, 60 + lb), last_i):
        close_ts = sym.t[i] + 1800
        if not (7 <= hh_tehran(close_ts) < 20):
            continue
        g = p.get("gate")
        if g and not ctx.gate_ok(close_ts, g):
            continue
        a = sym.atr[i]
        e21, e50 = sym.e21[i], sym.e50[i]
        if not a or not e21 or not e50:
            continue
        px = sym.c[i]
        # روند صعودی
        if p.get("side", "both") in ("long", "both"):
            e50_past = sym.e50[i - lb]
            if e50_past and e50 > e50_past * (1 + p.get("slope_min", 0.004)) and px > e50:
                # پول‌بک: کندل فعلی به EMA21 رسیده (low ≤ e21+0.2atr) و close بالای e21
                if sym.l[i] <= e21 + 0.2 * a and px > e21 and px > sym.o[i]:
                    out.append((i, px, a, "LONG"))
        if p.get("side", "both") in ("short", "both"):
            e50_past = sym.e50[i - lb]
            if e50_past and e50 < e50_past * (1 - p.get("slope_min", 0.004)) and px < e50:
                if sym.h[i] >= e21 - 0.2 * a and px < e21 and px < sym.o[i]:
                    out.append((i, px, a, "SHORT"))
    return out


def raw_signals_F3_er(sym: S, p, ctx: BtcCtx, first_i, last_i):
    """F3 کلاسیک ER (برای مقایسه)"""
    out = []
    for i in range(max(first_i, 80), last_i):
        close_ts = sym.t[i] + 1800
        if not (7 <= hh_tehran(close_ts) < 20):
            continue
        g = p.get("gate")
        if g and not ctx.gate_ok(close_ts, g):
            continue
        er = sym.er10[i]
        if er < p["er_th"]:
            continue
        a = sym.atr[i]
        e50 = sym.e50[i]
        if not a or not e50:
            continue
        px = sym.c[i]
        lbk = p["break_lookback"]
        if px > e50 and px > max(sym.h[i - lbk:i]):
            out.append((i, px, a, "LONG"))
        elif px < e50 and px < min(sym.l[i - lbk:i]):
            out.append((i, px, a, "SHORT"))
    return out


def raw_signals_F2b(sym: S, p, ctx: BtcCtx, first_i, last_i):
    """F2 بازطراحی: ریباند-شورت — در افت BTC، بازگشت به EMA21 + کندل رد شدن"""
    out = []
    for i in range(max(first_i, 80), last_i):
        close_ts = sym.t[i] + 1800
        if not (7 <= hh_tehran(close_ts) < 20):
            continue
        if ctx.dd96(close_ts) < p["dd_gate"]:
            continue
        a = sym.atr[i]
        e21 = sym.e21[i]
        e50 = sym.e50[i]
        if not a or not e21 or not e50:
            continue
        px = sym.c[i]
        if px >= e50:
            continue                      # هنوز زیر EMA50 (نزول)
        if sym.h[i] < e21 - 0.2 * a:
            continue                      # بازگشت به مقاومت نرسیده
        if px >= sym.o[i] or px >= e21:
            continue                      # کندل نزولی + بسته‌شدن زیر EMA21
        out.append((i, px, a))
    return out


def raw_signals_F4b(sym: S, p, ctx: BtcCtx, first_i, last_i):
    """F4 بازطراحی: ریباند-شورت کوین‌های جدید با شرط افت خود نماد"""
    out = []
    for i in range(max(first_i, 120), last_i):
        close_ts = sym.t[i] + 1800
        if not (7 <= hh_tehran(close_ts) < 20):
            continue
        if ctx.dd96(close_ts) < p["dd_gate"]:
            continue
        a = sym.atr[i]
        e21 = sym.e21[i]
        e50 = sym.e50[i]
        if not a or not e21 or not e50:
            continue
        px = sym.c[i]
        hi72 = max(sym.h[max(0, i - 71):i + 1])
        if (1.0 - px / hi72) < p["coin_dd"]:
            continue
        if px >= e50:
            continue
        if sym.h[i] < e21 - 0.2 * a:
            continue
        if px >= sym.o[i] or px >= e21:
            continue
        out.append((i, px, a))
    return out


def raw_signals_F5(sym: S, p, ctx: BtcCtx, first_i, last_i):
    out = []
    for i in range(max(first_i, 80), last_i):
        close_ts = sym.t[i] + 1800
        if not (7 <= hh_tehran(close_ts) < 20):
            continue
        g = p.get("gate")
        if g and not ctx.gate_ok(close_ts, g):
            continue
        a = sym.atr[i]
        if not a:
            continue
        rng = sym.h[i] - sym.l[i]
        if sym.v[i] < p["vol_x"] * sym.avgv[i] or rng < p["range_x"] * a:
            continue
        cp = (sym.c[i] - sym.l[i]) / rng if rng > 0 else 1.0
        if cp > p["close_pos_max"]:
            continue
        if sym.c[i] >= sym.e50[i]:
            continue
        out.append((i, sym.c[i], a))
    return out


def raw_signals_F2(sym: S, p, ctx: BtcCtx, first_i, last_i):
    out = []
    for i in range(max(first_i, 80), last_i):
        close_ts = sym.t[i] + 1800
        if not (7 <= hh_tehran(close_ts) < 20):
            continue
        if ctx.dd96(close_ts) < p["dd_gate"]:
            continue
        a = sym.atr[i]
        e50 = sym.e50[i]
        if not a or not e50:
            continue
        px = sym.c[i]
        lbk = p["break_lookback"]
        if px < e50 and px < min(sym.l[i - lbk:i]):
            out.append((i, px, a))
    return out


def raw_signals_F4(sym: S, p, ctx: BtcCtx, first_i, last_i):
    out = []
    for i in range(max(first_i, 120), last_i):
        close_ts = sym.t[i] + 1800
        if not (7 <= hh_tehran(close_ts) < 20):
            continue
        if ctx.dd96(close_ts) < p["dd_gate"]:
            continue
        a = sym.atr[i]
        e21 = sym.e21[i]
        if not a or not e21:
            continue
        px = sym.c[i]
        lbk = p["break_lookback"]
        hi72 = max(sym.h[max(0, i - 71):i + 1])
        if (1.0 - px / hi72) < p["coin_dd"]:
            continue
        if px < e21 and px < min(sym.l[i - lbk:i]):
            out.append((i, px, a))
    return out


# ================= موتور خروج (همان معناشناسی exit_engine) =================
def resolve(Sym, ei, entry, direction, sl, tp, mode, trail_atr, atr_e, cm, bk_arm=1.0):
    t = Sym.t; o = Sym.o; h = Sym.h; l = Sym.l; c = Sym.c
    n = len(t)
    long = direction == "LONG"
    R = abs(entry - sl) or 1e-12
    stop = sl
    be = entry * (1 + FEE) if long else entry * (1 - FEE)
    armed = False
    best = entry
    end = min(n, ei + cm)
    for i in range(ei, end):
        hi_ = h[i]; lo_ = l[i]; op = o[i]
        if (long and op <= stop) or ((not long) and op >= stop):
            return i, (be if (armed and stop == be) else stop)
        if (long and lo_ <= stop) or ((not long) and hi_ >= stop):
            return i, (be if (armed and stop == be) else stop)
        if tp is not None and ((long and hi_ >= tp) or ((not long) and lo_ <= tp)):
            return i, tp
        if mode == "TRAIL" and trail_atr and atr_e:
            best = max(best, hi_) if long else min(best, lo_)
            ts = (best - trail_atr * atr_e) if long else (best + trail_atr * atr_e)
            if long and ts > stop:
                stop = ts
            elif (not long) and ts < stop:
                stop = ts
        if mode == "BK" and not armed:
            arm = entry + bk_arm * R if long else entry - bk_arm * R
            if (long and hi_ >= arm) or ((not long) and lo_ <= arm):
                armed = True
                stop = be
    i = end - 1
    return i, c[i]   # CM


def run_scenario(sid, det_params, exit_params, cooldown_h, pool, first_ts, last_ts,
                 f3_mode="er", collect_trades=False):
    """تولید سیگنال خام → ادغام زمانی با dedupe/کول‌داون → رزولوشن"""
    gen = {"F1": raw_signals_F1, "F2": raw_signals_F2,
           "F3": raw_signals_F3_pullback if f3_mode == "pullback" else raw_signals_F3_er,
           "F4": raw_signals_F4, "F5": raw_signals_F5}[sid]
    if sid == "F2" and f3_mode == "rebound":
        gen = raw_signals_F2b
    if sid == "F4" and f3_mode == "rebound":
        gen = raw_signals_F4b
    raw = []
    for sym_name in pool:
        Sym = D[sym_name]
        first_i = bisect.bisect_left(Sym.t, first_ts - 1800)
        last_i = len(Sym.t) - 1   # ورود به کندل i+1 لازم است
        sigs = gen(Sym, det_params, BTCCTX, first_i, last_i)
        for s in sigs:
            i, px, a = s[0], s[1], s[2]
            direction = s[3] if len(s) > 3 else ("LONG" if sid in ("F1", "F5") else "SHORT")
            entry = Sym.o[i + 1]
            raw.append((Sym.t[i + 1], sid, sym_name, i, entry, a, direction))
    raw.sort(key=lambda x: x[0])
    cool_until = {}
    open_until = {}
    trades = []
    for entry_ts, sid_, sym_name, i, entry, a, direction in raw:
        key = (sid_, sym_name)
        if entry_ts < open_until.get(key, 0) or entry_ts < cool_until.get(key, 0):
            continue
        long = direction == "LONG"
        sl = entry - det_params["sl_atr"] * a if long else entry + det_params["sl_atr"] * a
        tp = None
        mode = exit_params["mode"]
        if mode == "FIXED":
            tp = entry - exit_params["tp_atr"] * a if long else entry + exit_params["tp_atr"] * a
        xi, exit_px = resolve(D[sym_name], i + 1, entry, direction, sl, tp, mode,
                              exit_params.get("trail_atr"), a,
                              exit_params["cm"], exit_params.get("bk_arm", 1.0))
        exit_ts = D[sym_name].t[xi] + 1800
        ret = (exit_px - entry) / entry if long else (entry - exit_px) / entry
        net = POS * ret - POS * FEE
        cool_until[key] = entry_ts + cooldown_h * 3600
        open_until[key] = exit_ts
        trades.append({"sid": sid_, "sym": sym_name, "entry_ts": entry_ts,
                       "exit_ts": exit_ts, "net": net, "ret": ret * 100,
                       "direction": direction,
                       "reason": exit_reason_of(mode, exit_px, sl, tp, be_entry(entry, long), exit_ts - entry_ts >= exit_params["cm"] * 1800)})
    return trades


def be_entry(entry, long):
    return entry * (1 + FEE) if long else entry * (1 - FEE)


def exit_reason_of(mode, exit_px, sl, tp, be, is_cm):
    if is_cm:
        return "CM"
    if tp is not None and abs(exit_px - tp) < 1e-12:
        return "TP"
    if abs(exit_px - be) < 1e-12:
        return "BE"
    return "SL"


def metrics(trades, start_ts=None, end_ts=None):
    if start_ts:
        trades = [x for x in trades if start_ts <= x["exit_ts"] < end_ts]
    if not trades:
        return {"n": 0, "net": 0.0, "fees": 0.0, "wr": 0.0, "maxdd": 0.0,
                "wins": 0, "days_pos": 0, "days_neg": 0}
    ts = sorted(trades, key=lambda x: x["exit_ts"])
    cum = 0.0
    peak = 0.0
    dd = 0.0
    day = {}
    for x in ts:
        cum += x["net"]
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
        d = date_tehran(x["exit_ts"])
        day[d] = day.get(d, 0.0) + x["net"]
    wins = sum(1 for x in trades if x["net"] > 0)
    return {"n": len(trades), "net": round(cum, 3),
            "fees": round(len(trades) * POS * FEE, 3),
            "wr": round(100.0 * wins / len(trades), 1), "maxdd": round(dd, 2),
            "wins": wins,
            "days_pos": sum(1 for v in day.values() if v > 0),
            "days_neg": sum(1 for v in day.values() if v < 0)}


BTCCTX = None

CURRENT = {  # پارامتر فعلی v2.1 (خط پایه)
    "F1": {"det": {"donchian": 16, "min_atr_pct": 0.0015, "buf_atr": 0.0, "sl_atr": 3.5},
           "exit": {"mode": "TRAIL", "trail_atr": 2.0, "cm": 192}, "cool": 6},
    "F2": {"det": {"dd_gate": 0.05, "break_lookback": 8, "sl_atr": 2.5},
           "exit": {"mode": "FIXED", "tp_atr": 3.0, "cm": 144}, "cool": 8},
    "F3": {"det": {"er_th": 0.30, "break_lookback": 12, "sl_atr": 3.0},
           "exit": {"mode": "TRAIL", "trail_atr": 2.5, "cm": 288}, "cool": 12},
    "F4": {"det": {"dd_gate": 0.05, "coin_dd": 0.08, "break_lookback": 6, "sl_atr": 2.0},
           "exit": {"mode": "TRAIL", "trail_atr": 3.5, "cm": 144}, "cool": 8},
    "F5": {"det": {"vol_x": 1.8, "range_x": 1.8, "close_pos_max": 0.35, "sl_atr": 2.0},
           "exit": {"mode": "BK", "bk_arm": 1.0, "cm": 144}, "cool": 8},
}


def split_metrics(trades):
    is_s, is_e = ts_tehran(IS_START), ts_tehran(IS_END)
    oos_e = ts_tehran(OOS_END) + 86400
    m_all = metrics([x for x in trades if x["entry_ts"] >= is_s])
    m_is = metrics([x for x in trades if is_s <= x["entry_ts"] < is_e])
    m_oos = metrics([x for x in trades if is_e <= x["entry_ts"] < oos_e])
    return m_all, m_is, m_oos


def show(tag, trades, verbose=False):
    m_all, m_is, m_oos = split_metrics(trades)
    print(f"{tag:<46} ALL n={m_all['n']:>3} net={m_all['net']:+8.2f}$ dd={m_all['maxdd']:>7.2f} "
          f"wr={m_all['wr']:>5.1f}% | IS n={m_is['n']:>3} {m_is['net']:+7.2f}$ | "
          f"OOS n={m_oos['n']:>3} {m_oos['net']:+7.2f}$")
    return m_all


# ================= فرمان‌ها =================
def cmd_fetch():
    a = sys.argv[2] if len(sys.argv) > 2 else "2026-05-07"
    b = sys.argv[3] if len(sys.argv) > 3 else "2026-09-08"
    t0 = time.time()
    load_data(ts_tehran(a), ts_tehran(b) + 86400)
    print(f"fetch done in {time.time()-t0:.0f}s")


def cmd_baseline():
    global BTCCTX
    BTCCTX = BtcCtx(BTC30, BTC4)
    start = ts_tehran("2026-06-08")
    end = ts_tehran(OOS_END) + 86400
    all_trades = []
    for sid in ["F1", "F2", "F3", "F4", "F5"]:
        c = CURRENT[sid]
        tr = run_scenario(sid, c["det"], c["exit"], c["cool"], POOL[sid], start, end)
        all_trades += tr
        show(f"baseline #{sid}", tr)
    show("baseline PORTFOLIO", all_trades)


def cmd_search():
    global BTCCTX
    BTCCTX = BtcCtx(BTC30, BTC4)
    sid = sys.argv[2]
    is_s, is_e = ts_tehran(IS_START), ts_tehran(IS_END)
    start = is_s - 10 * 86400  # کمی قبل برای گرم‌شدن اندیکاتورها
    grid = GRIDS[sid]
    results = []
    for det, exitp, cool in itertools.product(*grid):
        tr = run_scenario(sid, det, exitp, cool, POOL[sid], start, is_e,
                          f3_mode=det.get("_mode", "er"))
        m = metrics([x for x in tr if x["entry_ts"] >= is_s])
        if m["n"] >= MIN_N.get(sid, 12):
            results.append((m["net"], m, det, exitp, cool, len(tr)))
    results.sort(key=lambda r: -r[0])
    print(f"== search {sid}: {len(results)} configs with n>=12 (IS {IS_START}→{IS_END}) ==")
    for net, m, det, exitp, cool, ntotal in results[:12]:
        print(f"  net={m['net']:+8.2f}$ n={m['n']:>3} dd={m['maxdd']:>7.2f} wr={m['wr']:>5.1f}% | "
              f"det={json.dumps({k: v for k, v in det.items() if not k.startswith('_')})} "
              f"exit={json.dumps(exitp)} cool={cool}h")
    # ذخیره برای combine
    out_dir = os.path.join(V21, "research")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"search_{sid}.json"), "w", encoding="utf-8") as f:
        json.dump([{"net": n, "m": m, "det": {k: v for k, v in d.items() if not k.startswith('_')},
                    "exit": e, "cool": c, "n_total": nt} for n, m, d, e, c, nt in results[:40]],
                  f, ensure_ascii=False, indent=1)


MIN_N = {"F1": 12, "F3": 12, "F5": 12, "F2": 8, "F4": 8}

GRIDS = {
    "F1": [
        [dict(donchian=16, min_atr_pct=0.0015, buf_atr=0.0, sl_atr=3.5),
         dict(donchian=24, min_atr_pct=0.0015, buf_atr=0.0, sl_atr=3.5),
         dict(donchian=32, min_atr_pct=0.0015, buf_atr=0.0, sl_atr=4.0),
         dict(donchian=24, min_atr_pct=0.0025, buf_atr=0.25, sl_atr=4.0)],
        [dict(mode="TRAIL", trail_atr=2.0, cm=192), dict(mode="TRAIL", trail_atr=3.0, cm=288),
         dict(mode="TRAIL", trail_atr=4.0, cm=288), dict(mode="BK", bk_arm=1.0, cm=288),
         dict(mode="FIXED", tp_atr=6.0, cm=288)],
        [6, 12, 24],
    ],
    "F3": [
        [dict(_mode="er", er_th=0.30, break_lookback=12, sl_atr=3.0),
         dict(_mode="er", er_th=0.42, break_lookback=12, sl_atr=3.5),
         dict(_mode="er", er_th=0.50, break_lookback=16, sl_atr=3.5),
         dict(_mode="pullback", side="both", slope_min=0.004, sl_atr=2.5),
         dict(_mode="pullback", side="long", slope_min=0.008, sl_atr=2.5)],
        [dict(mode="TRAIL", trail_atr=2.5, cm=288), dict(mode="TRAIL", trail_atr=3.5, cm=288),
         dict(mode="TRAIL", trail_atr=5.0, cm=432), dict(mode="BK", bk_arm=1.0, cm=288),
         dict(mode="BK", bk_arm=1.0, cm=432), dict(mode="FIXED", tp_atr=4.0, cm=288)],
        [12, 24, 48],
    ],
    "F5": [
        [dict(vol_x=1.8, range_x=1.8, close_pos_max=0.35, sl_atr=2.0),
         dict(vol_x=1.5, range_x=1.6, close_pos_max=0.40, sl_atr=2.0),
         dict(vol_x=1.5, range_x=1.8, close_pos_max=0.35, sl_atr=2.5),
         dict(vol_x=2.2, range_x=2.0, close_pos_max=0.30, sl_atr=2.0)],
        [dict(mode="BK", bk_arm=1.0, cm=144), dict(mode="BK", bk_arm=1.0, cm=192),
         dict(mode="BK", bk_arm=1.2, cm=192), dict(mode="FIXED", tp_atr=4.0, cm=192)],
        [8, 12, 24],
    ],
    "F2": [
        [dict(dd_gate=0.05, break_lookback=8, sl_atr=2.5),
         dict(dd_gate=0.035, break_lookback=8, sl_atr=2.5),
         dict(dd_gate=0.035, break_lookback=12, sl_atr=3.0)],
        [dict(mode="FIXED", tp_atr=3.0, cm=144), dict(mode="FIXED", tp_atr=4.5, cm=288),
         dict(mode="TRAIL", trail_atr=3.5, cm=288)],
        [8, 24],
    ],
    "F4": [
        [dict(dd_gate=0.05, coin_dd=0.08, break_lookback=6, sl_atr=2.0),
         dict(dd_gate=0.035, coin_dd=0.10, break_lookback=8, sl_atr=2.0),
         dict(dd_gate=0.035, coin_dd=0.08, break_lookback=8, sl_atr=2.5)],
        [dict(mode="TRAIL", trail_atr=3.5, cm=144), dict(mode="TRAIL", trail_atr=5.0, cm=288),
         dict(mode="FIXED", tp_atr=4.0, cm=288)],
        [8, 24],
    ],
}


def cmd_combine():
    global BTCCTX
    BTCCTX = BtcCtx(BTC30, BTC4)
    cfg = json.loads(sys.argv[2])
    start = ts_tehran("2026-06-08")
    end = ts_tehran(OOS_END) + 86400
    all_tr = []
    for sid, c in cfg.items():
        tr = run_scenario(sid, c["det"], c["exit"], c["cool"], POOL[sid], start, end,
                          f3_mode=c["det"].get("_mode", "er"))
        all_tr += tr
        show(f"  #{sid}", tr)
    show("COMBINE", all_tr)


def cmd_gates():
    """آزمایش گیت‌های رژیم روی کاندیدهای نهایی (ورود-محور)"""
    global BTCCTX
    BTCCTX = BtcCtx(BTC30, BTC4)
    F1D = {"donchian": 32, "min_atr_pct": 0.0015, "buf_atr": 0.0, "sl_atr": 4.0}
    F1E = {"mode": "BK", "bk_arm": 1.0, "cm": 288}
    f3_er = lambda g: ({"_mode": "er", "er_th": 0.42, "break_lookback": 12, "sl_atr": 3.5, "gate": g},
                       {"mode": "BK", "bk_arm": 1.0, "cm": 288}, 48)
    f3_pb = lambda g: ({"_mode": "pullback", "side": "long", "slope_min": 0.008, "sl_atr": 2.5, "gate": g},
                       {"mode": "TRAIL", "trail_atr": 5.0, "cm": 432}, 24)
    F5D = {"vol_x": 1.5, "range_x": 1.8, "close_pos_max": 0.35, "sl_atr": 2.5}
    F5E = {"mode": "BK", "bk_arm": 1.0, "cm": 144}
    start = ts_tehran("2026-06-08")
    end = ts_tehran(OOS_END) + 86400
    for gname in [None, "atr15", "atr", "ema", "both"]:
        trs = []
        trs += run_scenario("F1", {**F1D, "gate": gname}, F1E, 6, POOL["F1"], start, end)
        det, ex, cool = f3_er(gname)
        trs += run_scenario("F3", det, ex, cool, POOL["F3"], start, end, f3_mode="er")
        trs += run_scenario("F5", {**F5D, "gate": gname}, F5E, 24, POOL["F5"], start, end)
        m_all, m_is, m_oos = split_metrics(trs)
        print(f"gate={str(gname):<6} ALL n={m_all['n']:>3} {m_all['net']:+8.2f}$ dd={m_all['maxdd']:>7.2f} | "
              f"IS {m_is['net']:+7.2f}$ (n={m_is['n']}) | OOS {m_oos['net']:+8.2f}$ (n={m_oos['n']})")


def run_portfolio(cfg, first_ts, end_ts, daily_limit=None):
    """ترکیب سناریوها با dedupe مستقل + اختیاری: توقف ورود جدید بعد از ضرر روزانه"""
    raw = []
    for sid, c in cfg.items():
        gen = {"F1": raw_signals_F1, "F2": raw_signals_F2,
               "F3": raw_signals_F3_pullback if c["det"].get("_mode") == "pullback" else raw_signals_F3_er,
               "F4": raw_signals_F4, "F5": raw_signals_F5}[sid]
        if sid == "F2" and c["det"].get("_mode") == "rebound":
            gen = raw_signals_F2b
        if sid == "F4" and c["det"].get("_mode") == "rebound":
            gen = raw_signals_F4b
        for sym_name in POOL[sid]:
            Sym = D[sym_name]
            first_i = bisect.bisect_left(Sym.t, first_ts - 1800)
            sigs = gen(Sym, c["det"], BTCCTX, first_i, len(Sym.t) - 1)
            for s in sigs:
                i, px, a = s[0], s[1], s[2]
                direction = s[3] if len(s) > 3 else ("LONG" if sid in ("F1", "F5") else "SHORT")
                raw.append((Sym.t[i + 1], sid, sym_name, i, Sym.o[i + 1], a, direction))
    raw.sort(key=lambda x: x[0])
    exits = []   # (exit_ts, net) مرتب برای محاسبه ضرر روز
    ei = 0
    day_realized = {}
    cool_until, open_until = {}, {}
    trades = []
    for entry_ts, sid_, sym_name, i, entry, a, direction in raw:
        day = date_tehran(entry_ts)
        # به‌روزرسانی سود تحقق‌یافته روز از معاملات بسته‌شده قبل از این ورود
        while ei < len(exits) and exits[ei][0] <= entry_ts:
            ets, net = exits[ei]
            day_realized[date_tehran(ets)] = day_realized.get(date_tehran(ets), 0.0) + net
            ei += 1
        if daily_limit is not None and day_realized.get(day, 0.0) <= -daily_limit:
            continue
        key = (sid_, sym_name)
        if entry_ts < open_until.get(key, 0) or entry_ts < cool_until.get(key, 0):
            continue
        det, exitp, _cool = c_det_exit(cfg, sid_)
        long = direction == "LONG"
        sl = entry - det["sl_atr"] * a if long else entry + det["sl_atr"] * a
        tp = None
        if exitp["mode"] == "FIXED":
            tp = entry - exitp["tp_atr"] * a if long else entry + exitp["tp_atr"] * a
        xi, exit_px = resolve(D[sym_name], i + 1, entry, direction, sl, tp, exitp["mode"],
                              exitp.get("trail_atr"), a, exitp["cm"], exitp.get("bk_arm", 1.0))
        exit_ts = D[sym_name].t[xi] + 1800
        ret = (exit_px - entry) / entry if long else (entry - exit_px) / entry
        net = POS * ret - POS * FEE
        cool_until[key] = entry_ts + c_det_exit(cfg, sid_)[2] * 3600
        open_until[key] = exit_ts
        exits.append((exit_ts, net))
        exits.sort(key=lambda x: x[0])
        trades.append({"sid": sid_, "sym": sym_name, "entry_ts": entry_ts, "exit_ts": exit_ts,
                       "net": net, "ret": ret * 100, "direction": direction})
    return trades


_CFG_CACHE = {}


def c_det_exit(cfg, sid):
    if sid not in _CFG_CACHE:
        c = cfg[sid]
        _CFG_CACHE[sid] = (c["det"], c["exit"], c["cool"])
    return _CFG_CACHE[sid]


def cmd_portfolio():
    global BTCCTX
    BTCCTX = BtcCtx(BTC30, BTC4)
    F1 = {"det": {"donchian": 32, "min_atr_pct": 0.0015, "buf_atr": 0.0, "sl_atr": 4.0},
          "exit": {"mode": "BK", "bk_arm": 1.0, "cm": 288}, "cool": 6}
    F3ER = {"det": {"_mode": "er", "er_th": 0.42, "break_lookback": 12, "sl_atr": 3.5},
            "exit": {"mode": "BK", "bk_arm": 1.0, "cm": 288}, "cool": 48}
    F3PB = {"det": {"_mode": "pullback", "side": "long", "slope_min": 0.008, "sl_atr": 2.5},
            "exit": {"mode": "TRAIL", "trail_atr": 5.0, "cm": 432}, "cool": 24}
    F5 = {"det": {"vol_x": 1.5, "range_x": 1.8, "close_pos_max": 0.35, "sl_atr": 2.5},
          "exit": {"mode": "BK", "bk_arm": 1.0, "cm": 144}, "cool": 24}
    for f3name, F3 in (("F3=ER", F3ER), ("F3=PB", F3PB)):
        for L in (None, 2.0, 3.0, 4.0):
            _CFG_CACHE.clear()
            cfg = {"F1": F1, "F3": F3, "F5": F5}
            trs = run_portfolio(cfg, ts_tehran("2026-06-08"), None, daily_limit=L)
            m_all, m_is, m_oos = split_metrics(trs)
            print(f"[{f3name}] limit={str(L):<5} ALL n={m_all['n']:>3} {m_all['net']:+8.2f}$ "
                  f"dd={m_all['maxdd']:>7.2f} wr={m_all['wr']:>5.1f}% | "
                  f"IS {m_is['net']:+7.2f}$ (n={m_is['n']}) | OOS {m_oos['net']:+8.2f}$ (n={m_oos['n']})")


def cmd_daytable():
    global BTCCTX
    BTCCTX = BtcCtx(BTC30, BTC4)
    cfg = json.loads(sys.argv[2])
    start = ts_tehran("2026-06-08")
    end = ts_tehran(OOS_END) + 86400
    all_tr = []
    for sid, c in cfg.items():
        all_tr += run_scenario(sid, c["det"], c["exit"], c["cool"], POOL[sid], start, end,
                               f3_mode=c["det"].get("_mode", "er"))
    day = {}
    for x in all_tr:
        d = date_tehran(x["exit_ts"])
        day[d] = day.get(d, 0.0) + x["net"]
    cum = 0.0
    for d in sorted(day):
        cum += day[d]
        print(f"{d} {day[d]:+7.2f}$ cum={cum:+8.2f}$")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    if cmd == "fetch":
        cmd_fetch()
    else:
        # لود از کش دیسکی (کلیدهای کش همان fetch است → بدون شبکه)
        load_data(ts_tehran("2026-05-07"), ts_tehran("2026-09-08") + 86400)
        if cmd == "baseline":
            cmd_baseline()
        elif cmd == "search":
            cmd_search()
        elif cmd == "combine":
            cmd_combine()
        elif cmd == "gates":
            cmd_gates()
        elif cmd == "portfolio":
            cmd_portfolio()
        elif cmd == "daytable":
            cmd_daytable()
        else:
            print("unknown cmd")
