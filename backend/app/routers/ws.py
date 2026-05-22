import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from app.config import settings
from app.models.schemas import ALLOWED_PAIRS, ConsolidationZone

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages all active WebSocket connections from frontend clients."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {p: [] for p in ALLOWED_PAIRS}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, pair: str):
        await websocket.accept()
        async with self._lock:
            self.active_connections[pair].append(websocket)
        logger.info(f"Client connected for {pair}. Total: {self._total()}")

    async def disconnect(self, websocket: WebSocket, pair: str):
        async with self._lock:
            try:
                self.active_connections[pair].remove(websocket)
            except ValueError:
                pass
        logger.info(f"Client disconnected from {pair}. Total: {self._total()}")

    def _total(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())

    async def broadcast(self, pair: str, message: dict):
        dead = []
        for ws in list(self.active_connections.get(pair, [])):
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws, pair)

    async def broadcast_all(self, message: dict):
        for pair in ALLOWED_PAIRS:
            await self.broadcast(pair, message)


manager = ConnectionManager()


@router.websocket("/ws/{pair:path}")
async def websocket_endpoint(websocket: WebSocket, pair: str):
    # Normalise pair: the URL has slashes encoded, FastAPI passes raw
    pair = pair.replace("%2F", "/").upper()

    if pair not in ALLOWED_PAIRS:
        await websocket.close(code=4000, reason=f"Unsupported pair: {pair}")
        return

    if manager._total() >= settings.max_connections:
        await websocket.close(code=4001, reason="Server at max connections")
        return

    await manager.connect(websocket, pair)
    try:
        # Send initial connection ack
        await websocket.send_json({
            "type": "CONNECTED",
            "pair": pair,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Keep connection alive — data comes via broadcast from TwelveDataStream
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Ping/pong keepalive
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send server-side ping to keep connection alive
                try:
                    await websocket.send_json({"type": "PING"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for {pair}: {e}")
    finally:
        await manager.disconnect(websocket, pair)
