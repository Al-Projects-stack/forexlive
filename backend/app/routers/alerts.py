from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.database import get_db
from app.models.schemas import AlertRequest
from app.services.key_levels import create_alert, get_alerts, delete_alert

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.post("", status_code=201)
@limiter.limit("20/minute")
async def create_key_level_alert(
    request: Request,
    body: AlertRequest,
    db=Depends(get_db),
):
    alert = await create_alert(db, body)
    return alert


@router.get("")
async def list_alerts(
    pair: str | None = None,
    db=Depends(get_db),
):
    return await get_alerts(db, pair=pair)


@router.delete("/{alert_id}", status_code=204)
async def remove_alert(alert_id: int, db=Depends(get_db)):
    deleted = await delete_alert(db, alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found")
