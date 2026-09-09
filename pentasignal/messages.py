# messages.py — قالب پیام‌های فاخر Telegram برای PentaSignal v3
#
# ساختار پیام سیگنال مثل v2.0 (تیتر → هشتگ → مشخصات → نتیجه) اما با:
#  • بلوک‌بندی با خطوط جداکننده و ایموجی منظم
#  • هشتگ استاندارد: #سیگنال #F1 #LONG #BTC #PentaSignal #KuCoin
#  • اعلام صریح ریپلای برای تعیین تکلیف
#  • پیام‌های تعیین تکلیف به‌صورت ریپلای روی پیام سیگنال ارسال می‌شوند

from . import settings
from .utils import fmt_price, fa_weekday, duration_fa
from .exit_engine import STATUS_TP, STATUS_SL, STATUS_BE, STATUS_CM

VERSION = settings.VERSION
BRAND = "PentaSignal"

# ---------- هشتگ‌ها ----------
def hashtags_signal(sig) -> str:
    sym = sig["symbol"].split("-")[0]
    return f"#سیگنال #{sig['scenario_id']} #{sig['direction']} #{sym} #PentaSignal #KuCoin"


def hashtags_settle(sig, status: str) -> str:
    sym = sig["symbol"].split("-")[0]
    tag = {STATUS_TP: "#TP", STATUS_SL: "#SL", STATUS_BE: "#BE", STATUS_CM: "#بسته_زمانی"}[status]
    return f"#تکلیف_شده {tag} #{sig['scenario_id']} #{sig['direction']} #{sym} #PentaSignal"


def hashtags_report() -> str:
    return "#گزارش_شبانه #PentaSignal #KuCoin"


def hashtags_be(sig) -> str:
    sym = sig["symbol"].split("-")[0]
    return f"#مدیریت_ریسک #BE #{sig['scenario_id']} #{sym} #PentaSignal"


# ---------- کمکی‌ها ----------
def _risk_pct(entry, sl, direction) -> float:
    if direction == "LONG":
        return (entry - sl) / entry * 100.0
    return (sl - entry) / entry * 100.0


def _tp_label(sig) -> str:
    if sig.get("take_profit"):
        return f"<code>{fmt_price(sig['take_profit'])}</code>"
    mode = sig.get("exit_mode")
    if mode == "TRAIL":
        return f"تریلینگ {sig.get('exit_param')}×ATR (دینامیک)"
    if mode == "BK":
        arm = "1"
        ep = str(sig.get("exit_param") or "")
        if "arm=" in ep:
            arm = ep.split("arm=")[1].split(";")[0]
        try:
            cm_days = float(sig.get("cm_candles", 288)) / 48.0
            cm_label = f"{cm_days:g} روز"
        except Exception:
            cm_label = "طبق سناریو"
        return (f"سربه‌سر خودکار پس از +{arm}R  ·  بدون TP ثابت  ·  سقف نگهداری {cm_label}")
    return "—"


def _scenario_line(sig) -> str:
    from .scenarios import SCENARIOS
    sc = SCENARIOS[sig["scenario_id"]]
    return f"{sig['scenario_id']} · {sc['name_fa']}"


def _date_line(candle_close_tehran: str) -> str:
    from .utils import parse_tehran
    d = parse_tehran(candle_close_tehran)
    if not d:
        return candle_close_tehran
    return f"{fa_weekday(d)} {d.strftime('%Y-%m-%d')}"


# ---------- پیام سیگنال جدید ----------
def format_signal(sig) -> str:
    sym = sig["symbol"].replace("-", "/")
    entry = float(sig["entry_price"])
    sl = float(sig["stop_loss"])
    risk = _risk_pct(entry, sl, sig["direction"])
    is_long = sig["direction"] == "LONG"
    arrow = "🟢" if is_long else "🔴"
    dir_fa = "لانگ" if is_long else "شورت"
    risk_usd = settings.POSITION_SIZE_USD * risk / 100.0
    tp_html = _tp_label(sig)
    lines = [
        f"✦ <b>{BRAND}</b>  ·  <b>v{VERSION}</b>",
        f"{arrow} <b>سیگنال {dir_fa.upper()}</b>  |  <b>#{sig['scenario_id']}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🪙 <b>{sym}</b>   ·   30m",
        f"🏷 <b>{_scenario_line(sig)}</b>",
        f"🗓 {_date_line(sig['candle_close_tehran'])}  ·  {sig['candle_close_tehran'][11:16]} تهران",
        "",
        f"◈ ورود      <code>{fmt_price(entry)}</code>",
        f"◈ حد ضرر    <code>{fmt_price(sl)}</code>  <i>({-risk:+.2f}%)</i>",
        f"◈ خروج      {tp_html}",
        "",
        f"⚖️ ریسک هر معامله: <b>{risk:.2f}%</b>  ≈  <b>{risk_usd:.2f}$</b>",
        f"💼 سایز مبنا: <b>{settings.POSITION_SIZE_USD:.0f}$</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "↩️ <i>تعیین تکلیف و تغییر وضعیت، در ریپلای همین پیام اعلام می‌شود.</i>",
        hashtags_signal(sig),
    ]
    return "\n".join(lines)


# ---------- پیام جابجایی استاپ به سربه‌سر (ریپلای) ----------
def format_be_armed(sig) -> str:
    lines = [
        "🛡 <b>حد ضرر به سربه‌سر منتقل شد</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"↩️ سیگنال <b>{_scenario_line(sig)}</b> · {sig['symbol'].replace('-', '/')} · {sig['direction']}",
        f"• قیمت به +{sig.get('bk_arm_r', 1)}R رسید؛ استاپ: <code>{fmt_price(sig.get('be_price'))}</code>",
        "• از این لحظه ریسک این معامله ≈ صفر است.",
        hashtags_be(sig),
    ]
    return "\n".join(lines)


# ---------- پیام تعیین تکلیف (ریپلای) ----------
_SETTLE_HEAD = {
    STATUS_TP: ("✅", "حد سود فعال شد", "سود کامل برداشت شد"),
    STATUS_SL: ("❌", "حد ضرر فعال شد", "معامله با ضرر بسته شد"),
    STATUS_BE: ("➖", "خروج سربه‌سر", "پس از جابجایی استاپ، بدون سود/ضرر بسته شد"),
    STATUS_CM: ("🕒", "بستن زمانی پوزیشن", "پس از پایان مهلت نگهداری، با قیمت بازار بسته شد"),
}


def format_settle(sig, status: str, exit_price: float, pnl_usd: float,
                  ret_pct: float, held_minutes: int) -> str:
    emoji, title, sub = _SETTLE_HEAD[status]
    dur = duration_fa(held_minutes)
    pnl_html = f"<b>{pnl_usd:+.2f}$</b>"
    ret_html = f"<b>{ret_pct:+.2f}%</b>"
    lines = [
        f"✦ <b>{BRAND}</b>  ·  {emoji} <b>{title}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"↩️ <b>{_scenario_line(sig)}</b>  ·  {sig['symbol'].replace('-', '/')}  ·  {sig['direction']}",
        "",
        f"◈ ورود   <code>{fmt_price(sig['entry_price'])}</code>",
        f"◈ خروج   <code>{fmt_price(exit_price)}</code>",
        f"📈 بازده  {ret_html}   ·   💵 PnL خالص  {pnl_html}",
        f"⏱ مدت نگهداری  <b>{dur}</b>",
        f"💬 {sub}",
        "━━━━━━━━━━━━━━━━━━━━",
        hashtags_settle(sig, status),
    ]
    return "\n".join(lines)
