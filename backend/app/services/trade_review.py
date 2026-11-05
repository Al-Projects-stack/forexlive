"""
AI Trade Review — after a position is closed, Claude critiques it against the
app's OWN live context: the consolidation state, smart-money structure, nearby
key levels the trader had set, and imminent high-impact news. That context is
assembled server-side from the same services that power the dashboard, so the
critique reasons about what the app actually saw, not generic advice.

Requires ANTHROPIC_API_KEY. If it's unset the feature degrades gracefully —
the router returns a clear "not configured" message instead of erroring.
"""
import logging
from typing import Optional

from app.config import settings
from app.models.schemas import TradeReviewRequest
from app.services import market_state
from app.services.consolidation import get_consolidation_zone
from app.services.key_levels import get_alerts
from app.services.news_calendar import get_upcoming_events
from app.services.smart_money import analyze_smart_money

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a disciplined forex trading coach reviewing a just-closed trade for a "
    "G30 price-action trader who works in SAST (UTC+2). You are given the trade and "
    "the live market context the platform recorded at the moment of exit: "
    "consolidation state, smart-money structure (order blocks, fair value gaps, "
    "liquidity sweeps, BOS/CHoCH), the trader's own key levels, and upcoming "
    "high-impact news.\n\n"
    "Write a tight review under 110 words: 1-2 specific observations that reference "
    "the provided context when it's relevant, then one concrete, actionable takeaway. "
    "Ground every point in the data given — never invent price action you weren't told "
    "about. No disclaimers, no 'as an AI', no hedging filler, no generic advice that "
    "would apply to any trade. You are not giving financial advice; you are reviewing "
    "execution and process."
)


def _digits(pair: str) -> int:
    return 3 if pair == "USD/JPY" else 5


def build_context(pair: str) -> dict:
    """Assemble the market context from the app's own live state at review time."""
    candles = market_state.get_candles(pair)
    zone = get_consolidation_zone(candles)
    smart_money = analyze_smart_money(candles)
    news = [e for e in get_upcoming_events(limit=10) if e["impact"] == "HIGH"][:3]
    return {
        "candles_available": len(candles),
        "consolidation": zone.model_dump(mode="json"),
        "smart_money": smart_money.model_dump(mode="json"),
        "upcoming_high_impact_news": news,
    }


async def _nearby_key_levels(pair: str, price: float) -> list[dict]:
    alerts = await get_alerts(None, pair=pair)
    out = []
    for a in alerts:
        distance_pct = abs(a["level"] - price) / price * 100 if price else None
        out.append({
            "level": a["level"],
            "direction": a["direction"],
            "distance_pct": round(distance_pct, 3) if distance_pct is not None else None,
        })
    # Closest levels first
    out.sort(key=lambda x: (x["distance_pct"] is None, x["distance_pct"] or 0))
    return out[:5]


def _format_prompt(trade: TradeReviewRequest, context: dict, key_levels: list[dict]) -> str:
    d = _digits(trade.pair)
    lines = [
        "## Trade",
        f"- Pair: {trade.pair}",
        f"- Direction: {trade.direction}",
        f"- Entry: {trade.entry_price:.{d}f}",
        f"- Exit: {trade.exit_price:.{d}f}",
        f"- Quantity: {trade.quantity:g}",
        f"- P&L: {trade.pnl:+.2f}",
    ]
    if trade.held_minutes is not None:
        lines.append(f"- Held: {trade.held_minutes} min")

    zone = context["consolidation"]
    lines.append("\n## Market context at exit")
    if zone.get("active"):
        lines.append(
            f"- Consolidation: ACTIVE, range {zone['lower']:.{d}f}–{zone['upper']:.{d}f} "
            f"(mid {zone['midpoint']:.{d}f})"
        )
    else:
        lines.append("- Consolidation: none (trending / no tight range)")

    sm = context["smart_money"]
    structure = sm.get("structure")
    if structure:
        lines.append(f"- Market structure: {structure['type']} {structure['direction']} @ {structure['level']:.{d}f}")
    sweep = sm.get("liquidity_sweep")
    if sweep:
        lines.append(f"- Liquidity sweep: {sweep['type']} @ {sweep['level']:.{d}f}")
    obs = sm.get("order_blocks") or []
    for ob in obs:
        lines.append(f"- Order block: {ob['type']} {ob['bottom']:.{d}f}–{ob['top']:.{d}f}")
    fvgs = sm.get("fair_value_gaps") or []
    for fvg in fvgs:
        lines.append(f"- Fair value gap: {fvg['type']} {fvg['bottom']:.{d}f}–{fvg['top']:.{d}f}")
    if not structure and not sweep and not obs and not fvgs:
        detail = "no smart-money signals" if context["candles_available"] else "no candle history for this pair yet"
        lines.append(f"- Smart money: {detail}")

    if key_levels:
        lines.append("- Your key levels (closest first):")
        for kl in key_levels:
            dist = f"{kl['distance_pct']}% away" if kl["distance_pct"] is not None else "distance n/a"
            lines.append(f"    - {kl['level']:.{d}f} ({kl['direction']}, {dist})")
    else:
        lines.append("- Key levels: none set")

    news = context["upcoming_high_impact_news"]
    if news:
        lines.append("- Upcoming HIGH-impact news:")
        for n in news:
            hrs = n["minutes_away"] // 60
            mins = n["minutes_away"] % 60
            lines.append(f"    - {n['name']} ({n['currency']}) in {hrs}h {mins}m")

    lines.append("\nReview this trade.")
    return "\n".join(lines)


def is_configured() -> bool:
    return bool(settings.anthropic_api_key)


async def generate_trade_review(trade: TradeReviewRequest) -> Optional[str]:
    """Return the review text, or None if the feature is not configured."""
    if not is_configured():
        return None

    from anthropic import AsyncAnthropic

    context = build_context(trade.pair)
    key_levels = await _nearby_key_levels(trade.pair, trade.exit_price)
    prompt = _format_prompt(trade, context, key_levels)

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model=settings.trade_review_model,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )

    if message.stop_reason == "refusal":
        logger.warning("Trade review refused: %s", getattr(message, "stop_details", None))
        return "The model declined to review this trade."

    return "".join(block.text for block in message.content if block.type == "text").strip()
