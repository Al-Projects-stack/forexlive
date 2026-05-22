import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone


def make_mock_alert(id_: int = 1, pair: str = "USD/JPY", level: float = 155.00, direction: str = "ABOVE"):
    alert = MagicMock()
    alert.id = id_
    alert.pair = pair
    alert.level = level
    alert.direction = direction
    alert.active = True
    alert.created_at = datetime.now(timezone.utc)
    return alert


@pytest.mark.asyncio
async def test_create_alert_valid():
    mock_alert = make_mock_alert()

    with patch("app.routers.alerts.create_alert", new=AsyncMock(return_value=mock_alert)):
        with patch("app.main.init_db", new=AsyncMock()):
            with patch("app.main.stream") as mock_stream:
                mock_stream.start = AsyncMock()
                mock_stream.stop = AsyncMock()
                mock_stream.on_tick = lambda cb: None

                from app.main import app
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.post(
                        "/api/v1/alerts",
                        json={"pair": "USD/JPY", "level": 155.00, "direction": "ABOVE"},
                    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_alert_invalid_pair():
    with patch("app.main.init_db", new=AsyncMock()):
        with patch("app.main.stream") as mock_stream:
            mock_stream.start = AsyncMock()
            mock_stream.stop = AsyncMock()
            mock_stream.on_tick = lambda cb: None

            from app.main import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/alerts",
                    json={"pair": "BTC/USD", "level": 50000, "direction": "ABOVE"},
                )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_alert_invalid_direction():
    with patch("app.main.init_db", new=AsyncMock()):
        with patch("app.main.stream") as mock_stream:
            mock_stream.start = AsyncMock()
            mock_stream.stop = AsyncMock()
            mock_stream.on_tick = lambda cb: None

            from app.main import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/alerts",
                    json={"pair": "USD/JPY", "level": 155.00, "direction": "SIDEWAYS"},
                )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_alert_not_found():
    with patch("app.routers.alerts.delete_alert", new=AsyncMock(return_value=False)):
        with patch("app.main.init_db", new=AsyncMock()):
            with patch("app.main.stream") as mock_stream:
                mock_stream.start = AsyncMock()
                mock_stream.stop = AsyncMock()
                mock_stream.on_tick = lambda cb: None

                from app.main import app
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    response = await client.delete("/api/v1/alerts/999")

    assert response.status_code == 404
