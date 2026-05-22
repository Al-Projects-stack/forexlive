import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from starlette.websockets import WebSocketState
from app.routers.ws import ConnectionManager


@pytest.mark.asyncio
async def test_connection_manager_connect():
    manager = ConnectionManager()
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED
    await manager.connect(mock_ws, "USD/JPY")
    assert mock_ws in manager.active_connections["USD/JPY"]
    mock_ws.accept.assert_called_once()


@pytest.mark.asyncio
async def test_connection_manager_disconnect():
    manager = ConnectionManager()
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED
    await manager.connect(mock_ws, "USD/JPY")
    await manager.disconnect(mock_ws, "USD/JPY")
    assert mock_ws not in manager.active_connections["USD/JPY"]


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    manager = ConnectionManager()
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED
    await manager.connect(mock_ws, "EUR/USD")

    msg = {"type": "CANDLE_UPDATE", "pair": "EUR/USD"}
    await manager.broadcast("EUR/USD", msg)
    mock_ws.send_json.assert_called_once_with(msg)


@pytest.mark.asyncio
async def test_connection_manager_handles_dead_connection():
    manager = ConnectionManager()
    mock_ws = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED
    mock_ws.send_json.side_effect = Exception("Connection closed")
    await manager.connect(mock_ws, "GBP/USD")

    # Should not raise, should remove dead connection
    await manager.broadcast("GBP/USD", {"type": "test"})
    assert mock_ws not in manager.active_connections["GBP/USD"]


@pytest.mark.asyncio
async def test_connection_manager_rejects_unknown_pair():
    manager = ConnectionManager()
    # Total connections from unknown pair should not be in active_connections
    assert "FAKE/PAIR" not in manager.active_connections
