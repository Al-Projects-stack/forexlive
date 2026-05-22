import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Optional

import websockets

from app.config import settings
from app.models.schemas import Candle, TickData

logger = logging.getLogger(__name__)

TWELVE_DATA_WS_BASE = "wss://ws.twelvedata.com/v1/quotes/price"

# Free plan supports 1 symbol — upgrade to stream all G30 pairs
PAIR_SYMBOLS = {
    "EUR/USD": "EUR/USD",
}


class CandleAggregator:
    """Aggregates tick data into 1-minute OHLC candles."""

    def __init__(self):
        self._candles: dict[str, list[Candle]] = defaultdict(list)
        self._current: dict[str, dict] = {}  # in-progress candle per pair

    def process_tick(self, pair: str, price: float, timestamp: datetime) -> Optional[Candle]:
        """Feed a tick. Returns a completed candle when the minute rolls over."""
        minute_key = timestamp.replace(second=0, microsecond=0)

        if pair not in self._current:
            self._current[pair] = {
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 1,
                "minute": minute_key,
            }
            return None

        current = self._current[pair]

        if minute_key > current["minute"]:
            # Minute rolled over — emit completed candle
            completed = Candle(
                open=current["open"],
                high=current["high"],
                low=current["low"],
                close=current["close"],
                volume=current["volume"],
                timestamp=current["minute"],
            )
            self._candles[pair].append(completed)
            # Keep last 100 candles per pair
            if len(self._candles[pair]) > 100:
                self._candles[pair] = self._candles[pair][-100:]

            # Start new candle
            self._current[pair] = {
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 1,
                "minute": minute_key,
            }
            return completed
        else:
            current["high"] = max(current["high"], price)
            current["low"] = min(current["low"], price)
            current["close"] = price
            current["volume"] += 1
            return None

    def get_current_candle(self, pair: str) -> Optional[Candle]:
        if pair not in self._current:
            return None
        c = self._current[pair]
        return Candle(
            open=c["open"],
            high=c["high"],
            low=c["low"],
            close=c["close"],
            volume=c["volume"],
            timestamp=c["minute"],
        )

    def get_candles(self, pair: str) -> list[Candle]:
        return list(self._candles[pair])

    def get_last_price(self, pair: str) -> Optional[float]:
        if pair in self._current:
            return self._current[pair]["close"]
        return None


class TwelveDataStream:
    """
    Connects to Twelve Data WebSocket.
    Receives tick data, aggregates into 1-minute OHLC candles.
    Calls on_tick callback for each tick received.
    """

    def __init__(self):
        self.aggregator = CandleAggregator()
        self._on_tick_callbacks: list[Callable] = []
        self._running = False
        self._ws: Optional[websockets.WebSocketClientProtocol] = None

    def on_tick(self, callback: Callable):
        self._on_tick_callbacks.append(callback)

    async def _notify(self, pair: str, price: float, timestamp: datetime):
        for cb in self._on_tick_callbacks:
            try:
                await cb(pair, price, timestamp)
            except Exception as e:
                logger.error(f"Tick callback error: {e}")

    async def start(self):
        self._running = True
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"TwelveData WS error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()

    async def _connect(self):
        url = f"{TWELVE_DATA_WS_BASE}?apikey={settings.twelve_data_api_key}"
        logger.info("Connecting to Twelve Data WebSocket...")
        async with websockets.connect(url) as ws:
            self._ws = ws
            logger.info("Connected to Twelve Data WebSocket")

            subscribe_msg = {
                "action": "subscribe",
                "params": {
                    "symbols": ",".join(PAIR_SYMBOLS.values()),
                },
            }
            await ws.send(json.dumps(subscribe_msg))

            async for raw in ws:
                if not self._running:
                    break
                try:
                    data = json.loads(raw)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Non-JSON message: {raw}")
                except Exception as e:
                    logger.error(f"Message handling error: {e}")

    async def _handle_message(self, data: dict):
        event = data.get("event")
        if event == "price":
            symbol = data.get("symbol", "")
            price_str = data.get("price")
            if not price_str:
                return
            price = float(price_str)
            timestamp = datetime.now(timezone.utc)
            # Map symbol back to our pair format
            pair = symbol  # Twelve Data uses the same format
            if pair not in PAIR_SYMBOLS:
                return
            self.aggregator.process_tick(pair, price, timestamp)
            await self._notify(pair, price, timestamp)
        elif event == "subscribe-status":
            logger.info(f"Subscription status: {data}")
        elif event == "heartbeat":
            pass
        else:
            logger.debug(f"Unhandled event: {data}")
