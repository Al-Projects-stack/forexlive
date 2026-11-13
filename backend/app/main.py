import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.db.database import close_db, init_db
from app.models.schemas import ALLOWED_PAIRS
from app.services import candle_store
from app.routers import alerts, auth, health, trade_review, ws
from app.routers.ws import manager
from app.services import market_state
from app.services.consolidation import get_consolidation_zone
from app.services.key_levels import check_key_levels
from app.services import news_calendar
from app.services.news_calendar import get_imminent_high_impact_event
from app.services.smart_money import analyze_smart_money
from app.services.structure_alerts import StructureAlertTracker
from app.services.twelve_data import TwelveDataStream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

stream = TwelveDataStream()
structure_alerts = StructureAlertTracker()
limiter = Limiter(key_func=get_remote_address)


def _candle_to_dict(candle) -> dict:
    return {
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "timestamp": candle.timestamp.isoformat() if candle.timestamp else None,
    }


def build_candle_snapshot(pair: str) -> dict:
    """Initial state for a newly-connected client: full candle history plus the
    current consolidation and smart-money analysis, so the chart renders complete
    on load instead of accumulating one candle per minute."""
    candles = stream.aggregator.get_candles(pair)
    current_candle = stream.aggregator.get_current_candle(pair)
    history = [_candle_to_dict(c) for c in candles]
    if current_candle:
        history.append(_candle_to_dict(current_candle))

    consolidation_zone = get_consolidation_zone(candles)
    smart_money_zones = analyze_smart_money(candles)
    return {
        "candles": history,
        "consolidation_zone": {
            "active": consolidation_zone.active,
            "upper": consolidation_zone.upper,
            "lower": consolidation_zone.lower,
            "midpoint": consolidation_zone.midpoint,
        },
        "smart_money": smart_money_zones.model_dump(mode="json"),
    }


async def on_tick(pair: str, price: float, timestamp: datetime):
    """Called by TwelveDataStream on every tick. Builds WS message and broadcasts."""
    candles = stream.aggregator.get_candles(pair)
    current_candle = stream.aggregator.get_current_candle(pair)
    consolidation_zone = get_consolidation_zone(candles)
    smart_money_zones = analyze_smart_money(candles)

    # Check key levels
    previous_price = price  # fallback
    if len(candles) >= 1:
        previous_price = candles[-1].close

    triggered_levels = await check_key_levels(None, pair, price, previous_price)

    # Check for imminent news
    news_event = get_imminent_high_impact_event()

    candle_dict = None
    if current_candle:
        candle_dict = {
            "open": current_candle.open,
            "high": current_candle.high,
            "low": current_candle.low,
            "close": current_candle.close,
            "volume": current_candle.volume,
        }

    consolidation_dict = {
        "active": consolidation_zone.active,
        "upper": consolidation_zone.upper,
        "lower": consolidation_zone.lower,
        "midpoint": consolidation_zone.midpoint,
    }
    smart_money_dict = smart_money_zones.model_dump(mode="json")

    # Send a CANDLE_UPDATE message
    message = {
        "type": "CANDLE_UPDATE",
        "pair": pair,
        "timestamp": timestamp.isoformat(),
        "price": price,
        "candle": candle_dict,
        "consolidation_zone": consolidation_dict,
        "key_level_triggered": None,
        "news_warning": None,
        "smart_money": smart_money_dict,
    }
    await manager.broadcast(pair, message)

    # Send separate alert messages for each triggered key level
    for triggered in triggered_levels:
        alert_message = {
            "type": "KEY_LEVEL_ALERT",
            "pair": pair,
            "timestamp": timestamp.isoformat(),
            "price": price,
            "candle": candle_dict,
            "consolidation_zone": consolidation_dict,
            "key_level_triggered": {
                "level": triggered.level,
                "direction": triggered.direction,
            },
            "news_warning": None,
            "smart_money": smart_money_dict,
        }
        await manager.broadcast(pair, alert_message)

    for alert in structure_alerts.update(pair, smart_money_zones, price, timestamp):
        logger.info("Structure alert: %s", alert.message)
        await manager.broadcast(pair, {
            "type": "STRUCTURE_ALERT",
            "pair": pair,
            "timestamp": timestamp.isoformat(),
            "price": price,
            "candle": candle_dict,
            "consolidation_zone": consolidation_dict,
            "key_level_triggered": None,
            "news_warning": None,
            "smart_money": smart_money_dict,
            "structure_alert": alert.model_dump(),
        })

    # Send news warning broadcast to all pairs
    if news_event:
        news_message = {
            "type": "NEWS_WARNING",
            "pair": pair,
            "timestamp": timestamp.isoformat(),
            "price": price,
            "candle": candle_dict,
            "consolidation_zone": consolidation_dict,
            "key_level_triggered": None,
            "news_warning": {
                "event": news_event["name"],
                "minutes_away": news_event["minutes_away"],
                "impact": news_event["impact"],
            },
            "smart_money": smart_money_dict,
        }
        await manager.broadcast(pair, news_message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if await init_db():
        pruned = await candle_store.prune(older_than_days=30)
        for pair in ALLOWED_PAIRS:
            history = await candle_store.load_recent(pair, limit=100)
            if history:
                stream.aggregator.seed(pair, history)
                logger.info("Restored %d %s candles (last %s)", len(history), pair, history[-1].timestamp.isoformat())
        if pruned:
            logger.info("Pruned %d candles older than 30 days", pruned)
        stream.on_candle_closed(candle_store.save_candle)
    manager.snapshot_provider = build_candle_snapshot
    market_state.set_aggregator(stream.aggregator)
    stream.on_tick(on_tick)
    task = asyncio.create_task(stream.start())
    calendar_task = asyncio.create_task(news_calendar.run_refresher())
    logger.info("TwelveData stream started")
    yield
    await stream.stop()
    for t in (task, calendar_task):
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
    logger.info("TwelveData stream stopped")
    await close_db()


app = FastAPI(
    title="ForexLive API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws.router)
app.include_router(auth.router)
app.include_router(alerts.router)
app.include_router(trade_review.router)
app.include_router(health.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )
