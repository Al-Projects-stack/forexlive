# ForexLive



Real-time forex trading dashboard for currency pairs. Streams live tick data via WebSockets, detects consolidation zones automatically, fires instant browser alerts when price touches key levels, and shows upcoming high-impact news events with live countdowns.

Built by a trader who trades USD/JPY and understands consolidation setups — not a chart wrapper.

---

## Features

| Feature | Description |
|---|---|
| **Live Price Streaming** | WebSocket tick data for USD/JPY, EUR/USD, GBP/USD, USD/ZAR — no polling |
| **Consolidation Detector** | Flags when last 20 candles are ranging within 0.15% — draws shaded band on chart |
| **Key Level Alerts** | Set a price level → instant browser toast when price crosses it |
| **News Calendar** | Next 5 high-impact events with live countdown + red banner when event is live |
| **Session Indicator** | Tokyo / London / New York / Overlap in SAST — overlap highlighted (highest liquidity) |
| **Live Ticker** | Scrolling bid/ask bar for all 4 pairs, green/red on direction |

---

## WebSocket Architecture

```
Twelve Data WS  →  FastAPI TwelveDataStream  →  CandleAggregator  →  ConnectionManager  →  Browser
```

The backend maintains a single upstream WebSocket connection to Twelve Data. Every tick:

1. `TwelveDataStream` receives a price event and calls `CandleAggregator.process_tick()`
2. `CandleAggregator` maintains in-progress 1-minute OHLC candles, emitting completed candles when the minute rolls over
3. The `on_tick` callback in `main.py` runs consolidation detection and key level checks against the live database
4. `ConnectionManager.broadcast()` sends a typed JSON message to all clients subscribed to that pair

Clients reconnect automatically after 3 seconds on disconnect. The server never crashes on a dropped connection — dead connections are cleaned from the pool lazily on the next broadcast.

### Message schema

```json
{
  "type": "CANDLE_UPDATE | KEY_LEVEL_ALERT | NEWS_WARNING | CONNECTED | PING",
  "pair": "USD/JPY",
  "timestamp": "2026-05-17T10:30:00Z",
  "price": 154.91,
  "candle": { "open": 154.82, "high": 154.95, "low": 154.78, "close": 154.91, "volume": 1240 },
  "consolidation_zone": { "active": true, "upper": 155.10, "lower": 154.70, "midpoint": 154.90 },
  "key_level_triggered": { "level": 155.00, "direction": "ABOVE" },
  "news_warning": { "event": "US Non-Farm Payrolls", "minutes_away": 3, "impact": "HIGH" }
}
```

---

## Consolidation Detection

```python
def is_consolidating(candles: list[Candle], threshold: float = 0.0015) -> bool:
    recent = candles[-20:]
    range_pct = (max(c.high for c in recent) - min(c.low for c in recent)) / min(c.low for c in recent)
    return range_pct < threshold
```

Threshold of 0.15% is tuned for G30 behaviour. When consolidation is active, a shaded amber band is drawn between the upper and lower boundary of the zone.

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Twelve Data API key (free at [twelvedata.com](https://twelvedata.com))

### Run locally

```bash
git clone https://github.com/your-username/forexlive.git
cd forexlive

# Add your API key
echo "TWELVE_DATA_API_KEY=your_key_here" > .env

# Start everything
docker-compose up --build
```

Open [http://localhost:3000](http://localhost:3000).

Backend API docs at [http://localhost:8000/docs](http://localhost:8000/docs) (development only).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Tailwind CSS, TradingView Lightweight Charts v4 |
| Backend | Python 3.11, FastAPI, WebSockets, asyncio |
| Data | Twelve Data WebSocket API |
| Database | PostgreSQL 15 (key level alerts, persistence) |
| ORM | SQLAlchemy 2.0 async |
| Containers | Docker, Docker Compose |
| Deployment | Render |
| CI/CD | GitHub Actions |

---

## API Reference

```
GET  /health                        — Health check
GET  /api/v1/news                   — Next 5 high-impact events
GET  /api/v1/alerts?pair=USD/JPY   — List active key level alerts
POST /api/v1/alerts                 — Create alert { pair, level, direction }
DELETE /api/v1/alerts/{id}          — Remove alert

WS   /ws/{pair}                     — Real-time stream (e.g. /ws/USD%2FJPY)
```

---

## Project Structure

```
forexlive/
├── backend/
│   ├── app/
│   │   ├── main.py              — FastAPI app, lifespan, tick handler
│   │   ├── config.py            — Pydantic settings
│   │   ├── routers/
│   │   │   ├── ws.py            — WebSocket endpoint + ConnectionManager
│   │   │   ├── alerts.py        — REST CRUD for key level alerts
│   │   │   └── health.py        — Health + news endpoints
│   │   ├── services/
│   │   │   ├── twelve_data.py   — Twelve Data WS client + CandleAggregator
│   │   │   ├── consolidation.py — Consolidation zone detection
│   │   │   ├── key_levels.py    — Alert persistence + trigger logic
│   │   │   └── news_calendar.py — Upcoming high-impact events
│   │   ├── models/schemas.py    — Pydantic request/response models
│   │   └── db/                  — SQLAlchemy engine + ORM models
│   └── tests/                   — pytest test suite
├── frontend/
│   └── src/
│       ├── components/          — SessionIndicator, LiveTicker, PriceChart, etc.
│       ├── hooks/               — useWebSocket, useChartData
│       ├── pages/Dashboard.tsx  — Main layout
│       └── types/index.ts       — Shared TypeScript types
├── docker-compose.yml
└── .github/workflows/deploy.yml
```

---

## Deployment on Render

1. Push to GitHub
2. Create two Render services — one Web Service (backend), one Static Site or Web Service (frontend)
3. Set environment variables in Render dashboard:
   - `TWELVE_DATA_API_KEY`
   - `DATABASE_URL` (Render PostgreSQL connection string)
   - `FRONTEND_URL` (your frontend Render URL)
4. Add Render deploy hook URLs as GitHub secrets:
   - `RENDER_DEPLOY_HOOK_BACKEND`
   - `RENDER_DEPLOY_HOOK_FRONTEND`
5. Push to `main` — GitHub Actions runs tests then triggers Render deploys

---

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

Tests cover:
- Consolidation detection (tight range, wide range, boundary, minimum candle count)
- Key level trigger logic (ABOVE, BELOW, EITHER, no trigger)
- WebSocket ConnectionManager (connect, disconnect, broadcast, dead connection cleanup)
- REST API validation (invalid pair, invalid direction, missing alert)
- Health and news endpoints

---

*Built by Al Mujati — trader and developer.*
