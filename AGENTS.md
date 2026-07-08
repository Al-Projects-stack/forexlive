# Agent Context — ForexLive

## Project Overview

Real-time forex trading dashboard (G30 pairs) — FastAPI backend + React frontend.

**Remote:** https://github.com/Al-Projects-stack/forexlive.git  
**Branch:** `master` — local is in sync with `origin/master`

## Architecture

- **Backend:** Python/FastAPI — Twelve Data WS stream → CandleAggregator → consolidation detection → key level checks → WebSocket broadcast
- **Frontend:** React 18 + TypeScript + Tailwind + lightweight-charts v4
- **Database:** PostgreSQL (SQLite in dev via .env override)
- **Infra:** Docker Compose, deployed on Render, GitHub Actions CI

## Features Added

### Desktop Push Notifications (`hooks/useDesktopNotifications.ts`)
Fires native OS notifications when the browser tab is not focused:
- **Key Level Alerts** — price touched a user-defined level
- **High-Impact News** — imminent news event
Requests permission once on first mount and caches the result in localStorage.

### Live Position P&L (`components/PositionPnL.tsx`)
- Add/remove positions per pair (Long/Short, entry price, quantity)
- Persists to localStorage
- Real-time floating P&L calculated against live `currentPrice`
- Color-coded (green for profit, red for loss) with a total P&L summary per pair
- Added to the Dashboard sidebar below the News Calendar

## New Files

| File | Purpose |
|---|---|
| `frontend/src/hooks/useDesktopNotifications.ts` | Native OS desktop notifications on alerts/news |
| `frontend/src/components/PositionPnL.tsx` | Live position tracking with P&L |
| `frontend/src/vite-env.d.ts` | Vite type reference |

## Observed Issues

1. **`.env` contains a live Twelve Data API key** — should be gitignored; currently tracked and pushed.
