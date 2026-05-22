from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from app.db.database import Base


def _now():
    return datetime.now(timezone.utc)


class KeyLevelAlert(Base):
    __tablename__ = "key_level_alerts"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String(20), nullable=False, index=True)
    level = Column(Float, nullable=False)
    direction = Column(String(10), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    triggered = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_now)
    triggered_at = Column(DateTime, nullable=True)
