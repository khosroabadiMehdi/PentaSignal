# discovery.py — کشف ترند چندمنبعی + مشورت AI برای F1 (از v3.4.0)
#
# معماری مورد انتظار F1 (تصمیم کاربر):
#   ① ترندها از چند منبع جمع می‌شود (CoinGecko trending + مومنتوم Binance + F&G)
#   ② تیتر اخبار خوانده می‌شود (RSS رایگان + CryptoPanic اختیاری با کلید)
#   ③ با AI مشورت می‌شود: یک فراخوان LLM با کانتکست فشرده →
#      «تاییدیه نمادها و جهت‌ها» (long/short/watch/avoid + اطمینان)
#   ④ AI تعدادی ارز انتخاب می‌کند → این انتخاب‌ها + ارزهای اصلی
#      به «قسمت چک و تولید سیگنال» (RuleSignalEngine) می‌روند
#   ⑤ حکم AI همزمان روی ctx.khosro_ai سوار می‌شود تا fusion داخل موتور
#      واقعی خوسرو فعال شود (+20 هم‌جهت، وتوی avoid)
#
# ایمنی:
#   • هیچ شکستی fatal نیست — در بدترین حالت universe=None یعنی اسکن کامل استخر (رفتار v3.3.0)
#   • بدون AI_API_KEY → فال‌بک «برترین‌های چندمنبعی + ارزهای اصلی» (رایگان، همیشه کار می‌کند)
#   • کش AI به مدت F1_AI_TTL_HOURS → حداکثر ~۶ فراخوان LLM در روز
#   • فقط نمادهای موجود در استخر KuCoin پنتا اجراپذیرند؛ نظر AI درباره بقیه
#     فقط در data/discovery/latest.json ثبت می‌شود (قابل مشاهده، غیرقابل اجرا)

from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from . import settings, scenarios

log_name = "ps.discovery"

_STABLE_RE = re.compile(r"USD|EUR|BRL|TRY$")
_LEVERAGED_RE = re.compile(r"(UP|DOWN|BULL|BEAR)$")

CG_BASE = "https://api.coingecko.com/api/v3"
BINANCE_BASE = "https://api.binance.com"
FNG_URL = "https://api.alternative.me/fng/"
CP_BASE = "https://cryptopanic.com/api/free/v1/posts"

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]


# ---------------------------------------------------------------------------
# بسته خروجی
# ---------------------------------------------------------------------------
@dataclass
class DiscoveryResult:
    """خروجی یک دور کشف ترند برای یک تیک سیگنال."""

    universe: set | None          # مجموعه نماد پایه مجاز برای F1 (مثل {"BTC","SOL"})؛ None = بدون فیلتر
    analysis: object | None       # AIAnalysis خوسرو (برای ctx.khosro_ai) یا None
    mode: str                     # ai | ai-cache | fallback | disabled
    info: dict = field(default_factory=dict)  # برای گزارش تشخیصی و ذخیره‌سازی


# ---------------------------------------------------------------------------
# ابزار شبکه سبک (timeout کوتاه، بدون retry سنگین — هیچ‌کدام fatal نیست)
# ---------------------------------------------------------------------------
def _get_json(url: str, params: dict | None = None, headers: dict | None = None,
              timeout: int | None = None):
    t = timeout or settings.F1_DISCOVERY_TIMEOUT
    r = requests.get(url, params=params, headers=headers, timeout=t)
    r.raise_for_status()
    return r.json()


def _session_headers() -> dict:
    h = {"User-Agent": "PentaSignal/3.4 (discovery)", "Accept": "*/*"}
    if os.getenv("COINGECKO_API_KEY", "").strip():
        h["x-cg-demo-api-key"] = os.getenv("COINGECKO_API_KEY", "").strip()
    return h


# ---------------------------------------------------------------------------
# ① منابع ترند — هر کدام مستقل و بی‌خطر
# ---------------------------------------------------------------------------
def fetch_binance_board() -> dict[str, dict]:
    """{base: {pair, price, change_pct, vol_usd}} برای جفت‌های USDT (فیلتر لوریج/استیبل)."""
    rows = _get_json(f"{BINANCE_BASE}/api/v3/ticker/24hr") or []
    best: dict[str, dict] = {}
    for row in rows:
        sym = row.get("symbol") or ""
        if not sym.endswith("USDT"):
            continue
        base = sym[:-4]
        if not base or _LEVERAGED_RE.search(base) or _STABLE_RE.search(base):
            continue
        try:
            rec = {
                "pair": sym,
                "price": float(row.get("lastPrice") or 0.0),
                "change_pct": float(row.get("priceChangePercent") or 0.0),
                "vol_usd": float(row.get("quoteVolume") or 0.0),
            }
        except (TypeError, ValueError):
            continue
        if rec["vol_usd"] < 1_000_000:      # جفت‌های خیلی نازک حذف
            continue
        prev = best.get(base)
        if prev is None or rec["vol_usd"] > prev["vol_usd"]:
            best[base] = rec
    return best


def fetch_cg_trending() -> list[dict]:
    """بورد CoinGecko: [{symbol, name, rank}]"""
    data = _get_json(f"{CG_BASE}/search/trending", headers=_session_headers()) or {}
    out = []
    for pos, item in enumerate((data.get("coins") or []), start=1):
        info = item.get("item") or {}
        if not info.get("symbol"):
            continue
        out.append({
            "symbol": str(info["symbol"]).upper(),
            "name": info.get("name") or str(info["symbol"]),
            "rank": pos,
        })
    return out[:15]


def fetch_fear_greed() -> int | None:
    try:
        data = _get_json(FNG_URL, params={"limit": 1}) or {}
        return int((data.get("data") or [{}])[0].get("value"))
    except Exception:
        return None


def fetch_cg_global() -> dict:
    try:
        data = (_get_json(f"{CG_BASE}/global", headers=_session_headers()) or {}).get("data") or {}
        return {
            "btc_dominance": (data.get("market_cap_percentage") or {}).get("btc"),
            "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd"),
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# ② اخبار — RSS رایگان + CryptoPanic اختیاری
# ---------------------------------------------------------------------------
def fetch_news_headlines(limit: int | None = None) -> list[str]:
    n = limit or settings.F1_NEWS_MAX
    if not settings.F1_NEWS_ENABLED:
        return []
    heads: list[str] = []

    key = os.getenv("CRYPTOPANIC_API_KEY", "").strip()
    if key:
        try:
            data = _get_json(CP_BASE, params={"auth_token": key, "public": "true"},
                             timeout=settings.F1_DISCOVERY_TIMEOUT) or {}
            for post in (data.get("results") or [])[:n]:
                t = str(post.get("title") or "").strip()
                if t:
                    heads.append(t[:160])
        except Exception:
            pass

    if len(heads) < n:
        for url in RSS_FEEDS:
            if len(heads) >= n:
                break
            try:
                r = requests.get(url, timeout=settings.F1_DISCOVERY_TIMEOUT,
                                 headers={"User-Agent": "PentaSignal/3.4"})
                r.raise_for_status()
                root = ET.fromstring(r.content)
                titles = [el.text.strip() for el in root.findall(".//item/title") if el.text]
                for t in titles:
                    if len(heads) >= n:
                        break
                    heads.append(t[:160])
            except Exception:
                continue
    return heads[:n]


# ---------------------------------------------------------------------------
# امتیاز چندمنبعی کاندیداها (پایه فال‌بک + ترتیب پرامپت AI)
# ---------------------------------------------------------------------------
def build_candidates(board: dict, trending: list[dict]) -> list[dict]:
    """اجتماع کاندیداهای چند منبع + امتیاز حضور چندمنبعی.

    فلسفه: کوینی که همزمان در چند منبع ظاهر شود مهم‌تر از کوینی است که
    فقط در یک منبع داغ است (همان قاعده پرامپت AI خوسرو).
    خروجی: [{symbol, name, pair, stats, components, score, sources}] مرتب نزولی
    """
    cand: dict[str, dict] = {}

    def _put(base: str, comp: str, weight_rank: float, name: str = ""):
        # دفاع دوم: لوریج‌توکن/استیبل هرگز وارد کاندیدا نمی‌شوند
        if _LEVERAGED_RE.search(base) or _STABLE_RE.search(base):
            return
        c = cand.setdefault(base, {
            "symbol": base, "name": name or base, "pair": (board.get(base) or {}).get("pair"),
            "stats": {}, "components": {}, "sources": [], "score": 0.0,
        })
        c["components"][comp] = round(max(weight_rank, 0.0), 4)
        if comp not in c["sources"]:
            c["sources"].append(comp)
        md = board.get(base)
        if md:
            c["stats"] = {
                "price_usd": md["price"],
                "change_24h_pct": md["change_pct"],
                "volume_24h_usd": md["vol_usd"],
            }
            c["pair"] = md["pair"]

    # ۱) مومنتوم Binance: 10 صعودی + 10 نزولی + 10 پرحجم
    with_stats = [(b, m) for b, m in board.items() if m.get("vol_usd", 0) > 0]
    gainers = sorted(with_stats, key=lambda x: x[1]["change_pct"], reverse=True)[:10]
    losers = sorted(with_stats, key=lambda x: x[1]["change_pct"])[:10]
    heavy = sorted(with_stats, key=lambda x: x[1]["vol_usd"], reverse=True)[:10]
    for i, (b, _m) in enumerate(gainers, 1):
        _put(b, "binance_gainer", 1.0 - (i - 1) / 10.0)
    for i, (b, _m) in enumerate(losers, 1):
        _put(b, "binance_loser", 1.0 - (i - 1) / 10.0)
    for i, (b, _m) in enumerate(heavy, 1):
        _put(b, "binance_volume", 1.0 - (i - 1) / 10.0)

    # ۲) بورد ترند CoinGecko (15 نفر اول)
    for item in trending:
        i = item["rank"]
        _put(item["symbol"], "coingecko_trending", max(0.0, 1.0 - (i - 1) / 15.0),
             name=item.get("name") or "")

    # امتیاز نهایی: وزن منبع + جایزه حضور چندمنبعی
    W = {"coingecko_trending": 0.40, "binance_gainer": 0.22,
         "binance_loser": 0.18, "binance_volume": 0.20}
    for c in cand.values():
        comps = c["components"]
        base_score = sum(W.get(k, 0.1) * v for k, v in comps.items())
        multi = min(1.0, (len(c["sources"]) - 1) / 3.0)
        c["score"] = round(100.0 * (base_score + 0.10 * multi), 2)
        c["sources"] = sorted(c["sources"])
    return sorted(cand.values(), key=lambda c: c["score"], reverse=True)


# ---------------------------------------------------------------------------
# ③ مشورت AI — یک فراخوان LLM (کش TTL-دار)
# ---------------------------------------------------------------------------
def _discovery_dir() -> str:
    d = os.path.join(settings.DATA_DIR, "discovery")
    os.makedirs(d, exist_ok=True)
    return d


def _latest_path() -> str:
    return os.path.join(_discovery_dir(), "latest.json")


def _load_cached_ai(ttl_h: float):
    """AIAnalysis ذخیره‌شده اگر تازه باشد (کش رایگان)."""
    try:
        with open(_latest_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        ai = data.get("ai") or {}
        if not ai.get("verdicts") or not ai.get("created_at_ts"):
            return None
        age_h = (time.time() - float(ai["created_at_ts"])) / 3600.0
        if age_h > max(0.0, ttl_h):
            return None
        from khosro_ai_trader.models import AIAnalysis, CoinVerdict
        return AIAnalysis(
            model=str(ai.get("model") or "cached"),
            run_at_utc=str(ai.get("run_at_utc") or ""),
            market_summary=str(ai.get("market_summary") or ""),
            sentiment=str(ai.get("sentiment") or "mixed"),
            sentiment_confidence=int(ai.get("sentiment_confidence") or 50),
            verdicts=[CoinVerdict(**v) for v in ai["verdicts"]],
        )
    except Exception:
        return None


def _consult_ai(candidates: list[dict]):
    """یک فراخوان AIAnalyst خوسرو روی کاندیداهای چندمنبعی + اخبار. None = ناموفط/خاموش."""
    from khosro_ai_trader.ai.analyst import AIAnalyst
    from khosro_ai_trader.models import MarketStats, TrendingCoin, TrendingSnapshot

    cfg = scenarios._f1_cfg()
    analyst = AIAnalyst(cfg)
    if not analyst.available:
        return None, {"ai_skipped": "no_key_or_disabled"}

    coins = []
    for c in candidates[: cfg.ai.max_candidates]:
        st = c.get("stats") or {}
        coins.append(TrendingCoin(
            symbol=c["symbol"], name=c.get("name") or c["symbol"],
            binance_pair=c.get("pair"),
            stats=MarketStats(
                price_usd=st.get("price_usd"),
                change_24h_pct=st.get("change_24h_pct"),
                volume_24h_usd=st.get("volume_24h_usd"),
            ),
            components=dict(c.get("components") or {}),
            score=float(c.get("score") or 0.0),
            sources=list(c.get("sources") or []),
        ))

    now = datetime.now(ZoneInfo("Asia/Tehran"))
    snap = TrendingSnapshot(
        run_at_utc=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        run_at_tehran=now.strftime("%Y-%m-%d %H:%M"),
        duration_seconds=0.0,
        coins=coins,
    )

    macro = {"fear_greed": fetch_fear_greed(), **fetch_cg_global()}
    news = fetch_news_headlines()
    analysis = analyst.analyze(snap, macro=macro, news_headlines=news)
    return analysis, {"news_count": len(news), "macro": macro}


# ---------------------------------------------------------------------------
# ④ انتخاب: تاییدیه‌های AI + ارزهای اصلی → universe قابل اجرا
# ---------------------------------------------------------------------------
def select_universe(candidates: list[dict], analysis, mains: set) -> tuple[set, list[dict], str]:
    """خروجی: (universe، ردیف‌های انتخاب برای گزارش، حالت)"""
    pool_bases = {s.split("-")[0].upper() for s in scenarios.UNION_SYMBOLS}
    mains = {m.upper() for m in mains} & pool_bases

    if analysis is not None and analysis.verdicts:
        approved = [
            v for v in analysis.verdicts
            if v.direction in ("long", "short") and v.confidence >= settings.F1_AI_SELECT_MIN_CONF
        ]
        approved.sort(key=lambda v: v.confidence, reverse=True)
        rows = [{
            "symbol": v.symbol, "direction": v.direction, "confidence": v.confidence,
            "trend": v.trend, "reason": "؛ ".join(v.reasons[:2]),
            "risk_note": v.risk_note,
            "tradeable": v.symbol.upper() in pool_bases,
            "selected": False,
        } for v in approved]

        picked: set = set()
        for sym in [r["symbol"].upper() for r in rows]:
            if len(picked - mains) >= settings.F1_DISCOVERY_TOP_N:
                break
            if sym in pool_bases:
                picked.add(sym)
        for r in rows:
            r["selected"] = r["symbol"].upper() in picked
        universe = picked | mains
        return universe, rows, "ai"

    # فال‌بک بدون AI: برترین‌های چندمنبعی داخل استخر + ارزهای اصلی
    fb = [c for c in candidates if c["symbol"] in pool_bases]
    picked = {c["symbol"] for c in fb[: settings.F1_DISCOVERY_TOP_N]}
    rows = [{
        "symbol": c["symbol"], "direction": None, "confidence": None,
        "trend": None, "reason": "فال‌بک چندمنبعی score=" + str(c.get("score")),
        "risk_note": "", "tradeable": True,
        "selected": c["symbol"] in picked,
    } for c in fb[: settings.F1_DISCOVERY_TOP_N + 5]]
    return picked | mains, rows, "fallback"


# ---------------------------------------------------------------------------
# ⑤ اجرای یک دور کامل — همیشه بی‌خطر
# ---------------------------------------------------------------------------
def run() -> DiscoveryResult:
    t0 = time.time()
    res = DiscoveryResult(universe=None, analysis=None, mode="disabled")
    info: dict = {
        "run_at_tehran": datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d %H:%M:%S"),
        "sources_ok": [], "sources_failed": {}, "candidates_top": [],
        "selected": {}, "ai": {}, "elapsed_ms": 0,
    }
    res.info = info
    if not settings.F1_DISCOVERY:
        res.mode = "disabled"
        return res

    board, trending = {}, []
    try:
        board = fetch_binance_board()
        info["sources_ok"].append("binance")
    except Exception as exc:
        info["sources_failed"]["binance"] = str(exc)[:120]
    try:
        trending = fetch_cg_trending()
        info["sources_ok"].append("coingecko")
    except Exception as exc:
        info["sources_failed"]["coingecko"] = str(exc)[:120]

    candidates = build_candidates(board, trending)
    info["candidates_top"] = [{
        "symbol": c["symbol"], "score": c["score"], "sources": c["sources"],
        "change_24h_pct": (c.get("stats") or {}).get("change_24h_pct"),
    } for c in candidates[:15]]

    mains = set(settings.F1_MAIN_COINS)
    analysis = _load_cached_ai(settings.F1_AI_TTL_HOURS)
    ai_meta = {}
    if analysis is not None:
        res.mode = "ai-cache"
        ai_meta = {"model": analysis.model, "sentiment": analysis.sentiment,
                   "sentiment_confidence": analysis.sentiment_confidence, "cached": True}
    else:
        try:
            analysis, ai_meta = _consult_ai(candidates)
            res.mode = "ai" if analysis is not None else "fallback"
        except Exception as exc:
            analysis, res.mode = None, "fallback"
            ai_meta = {"error": str(exc)[:160]}
    res.analysis = analysis

    if analysis is not None:
        from dataclasses import asdict as _asdict
        ai_meta.update({
            "model": analysis.model,
            "market_summary": analysis.market_summary[:200],
            "sentiment": analysis.sentiment,
            "sentiment_confidence": analysis.sentiment_confidence,
            "verdict_count": len(analysis.verdicts),
            "verdicts": [_asdict(v) for v in analysis.verdicts],
            "created_at_ts": time.time(),
        })

    universe, sel_rows, mode = select_universe(candidates, analysis, mains)
    res.mode = mode if mode != "ai" else res.mode
    res.universe = universe

    info["selected"] = {
        "mode": res.mode, "universe": sorted(universe),
        "main_coins": sorted(mains),
        "rows": sel_rows,
    }
    info["ai"] = ai_meta
    info["elapsed_ms"] = int((time.time() - t0) * 1000)

    _persist(info)
    _log_summary(info)
    return res


def _persist(info: dict):
    """latest.json + history.jsonl (نگه‌داری غلتان 96 ردیف = 48 ساعت)."""
    try:
        d = _discovery_dir()
        with open(os.path.join(d, "latest.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        hist = os.path.join(d, "history.jsonl")
        with open(hist, "a", encoding="utf-8") as f:
            f.write(json.dumps(info, ensure_ascii=False) + "\n")
        # کوتاه‌سازی تاریخچه
        try:
            with open(hist, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > 96:
                with open(hist, "w", encoding="utf-8") as f:
                    f.writelines(lines[-96:])
        except Exception:
            pass
    except Exception:
        pass


def _log_summary(info: dict):
    import logging
    sel = info.get("selected") or {}
    ai = info.get("ai") or {}
    logging.getLogger(log_name).info(
        "F1 DISCOVERY [%s] sources=%s news=%s ai=%s sentiment=%s | universe(%d)=%s",
        sel.get("mode"), ",".join(info.get("sources_ok") or []) or "-",
        ai.get("news_count", "-"), ai.get("model") or "off",
        ai.get("sentiment") or "-",
        len(sel.get("universe") or []), ",".join(sorted(sel.get("universe") or [])),
    )


# ---------------------------------------------------------------------------
# سیم‌کشی به MarketContext — از run_bot در مود سیگنال صدا زده می‌شود
# ---------------------------------------------------------------------------
def apply(ctx) -> DiscoveryResult | None:
    """کشف ترند را اجرا و روی ctx سوار می‌کند. هر خطایی → None (بدون فیلتر)."""
    if not settings.F1_DISCOVERY:
        return None
    try:
        res = run()
    except Exception as exc:
        import logging
        logging.getLogger(log_name).error("discovery failed — F1 unfiltered: %s", exc)
        return None
    ctx.f1_universe = res.universe
    ctx.khosro_ai = res.analysis
    ctx.discovery_info = res.info
    return res
