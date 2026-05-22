import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.key_levels import check_key_levels
from app.db.models import KeyLevelAlert


def make_db_alert(id_: int, level: float, direction: str) -> KeyLevelAlert:
    alert = KeyLevelAlert()
    alert.id = id_
    alert.pair = "USD/JPY"
    alert.level = level
    alert.direction = direction
    alert.active = True
    alert.triggered = False
    return alert


@pytest.mark.asyncio
async def test_key_level_above_triggered():
    db = AsyncMock()
    alert = make_db_alert(1, 155.00, "ABOVE")

    # Mock get_alerts to return our alert
    from app.services import key_levels as kl
    original = kl.get_alerts

    async def mock_get_alerts(db, pair=None):
        return [alert]

    kl.get_alerts = mock_get_alerts
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    triggered = await check_key_levels(db, "USD/JPY", current_price=155.05, previous_price=154.99)
    assert len(triggered) == 1
    assert triggered[0].level == 155.00
    assert triggered[0].direction == "ABOVE"

    kl.get_alerts = original


@pytest.mark.asyncio
async def test_key_level_below_triggered():
    from app.services import key_levels as kl
    db = AsyncMock()
    alert = make_db_alert(2, 154.00, "BELOW")

    async def mock_get_alerts(db, pair=None):
        return [alert]

    original = kl.get_alerts
    kl.get_alerts = mock_get_alerts
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    triggered = await check_key_levels(db, "USD/JPY", current_price=153.99, previous_price=154.01)
    assert len(triggered) == 1
    assert triggered[0].direction == "BELOW"

    kl.get_alerts = original


@pytest.mark.asyncio
async def test_key_level_not_triggered():
    from app.services import key_levels as kl
    db = AsyncMock()
    alert = make_db_alert(3, 155.00, "ABOVE")

    async def mock_get_alerts(db, pair=None):
        return [alert]

    original = kl.get_alerts
    kl.get_alerts = mock_get_alerts

    triggered = await check_key_levels(db, "USD/JPY", current_price=154.50, previous_price=154.40)
    assert len(triggered) == 0

    kl.get_alerts = original


@pytest.mark.asyncio
async def test_key_level_either_direction():
    from app.services import key_levels as kl
    db = AsyncMock()
    alert = make_db_alert(4, 155.00, "EITHER")

    async def mock_get_alerts(db, pair=None):
        return [alert]

    original = kl.get_alerts
    kl.get_alerts = mock_get_alerts
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    # Price crosses down through the level
    triggered = await check_key_levels(db, "USD/JPY", current_price=154.99, previous_price=155.01)
    assert len(triggered) == 1

    kl.get_alerts = original
