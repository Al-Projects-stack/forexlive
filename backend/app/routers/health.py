from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/api/v1/news")
async def get_news():
    from app.services.news_calendar import get_upcoming_events
    return get_upcoming_events(limit=5)
