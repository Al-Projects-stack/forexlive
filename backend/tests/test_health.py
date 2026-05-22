import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_health_endpoint():
    with patch("app.main.stream") as mock_stream:
        mock_stream.start = AsyncMock()
        mock_stream.stop = AsyncMock()
        mock_stream.on_tick = lambda cb: None

        with patch("app.main.init_db", new=AsyncMock()):
            from app.main import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_news_endpoint():
    with patch("app.main.stream") as mock_stream:
        mock_stream.start = AsyncMock()
        mock_stream.stop = AsyncMock()
        mock_stream.on_tick = lambda cb: None

        with patch("app.main.init_db", new=AsyncMock()):
            from app.main import app
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/news")

    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    assert len(events) <= 5
