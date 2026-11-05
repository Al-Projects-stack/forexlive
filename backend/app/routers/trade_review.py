import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.models.schemas import TradeReviewRequest, TradeReviewResponse
from app.services.trade_review import generate_trade_review, is_configured

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/v1/trade-review", tags=["trade-review"])


@router.get("/status")
async def status():
    return {"configured": is_configured()}


@router.post("", response_model=TradeReviewResponse)
@limiter.limit("10/minute")
async def create_trade_review(request: Request, body: TradeReviewRequest):
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail="AI trade review is not configured. Set ANTHROPIC_API_KEY on the server to enable it.",
        )
    try:
        review = await generate_trade_review(body)
    except Exception as e:
        logger.error(f"Trade review failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Could not generate a review right now. Please try again.")

    if review is None:
        raise HTTPException(status_code=503, detail="AI trade review is not configured.")

    return TradeReviewResponse(review=review, model=settings.trade_review_model)
