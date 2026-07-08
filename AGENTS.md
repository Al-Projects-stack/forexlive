# Agent Context — ForexLive

## Project Overview

Real-time forex trading dashboard (G30 pairs) — FastAPI backend + React frontend.

**Remote:** https://github.com/Al-Projects-stack/forexlive.git  
**Branch:** `master` — local is up to date with `origin/master`

## Uncommitted Changes (local vs GitHub)

| File | Diff |
|---|---|
| `frontend/src/components/LiveTicker.tsx` | Removed unused `useRef` import |
| `frontend/src/components/PriceChart.tsx` | Migrated lightweight-charts from v3 to v4 API (`addCandlestickSeries`/`addLineSeries` instead of constructors; `LineStyle.Dashed` enum instead of magic number `2`; removed unused `useRef` import) |
| `frontend/src/pages/Landing.tsx` | Removed unused `useRef` import |
| `frontend/src/vite-env.d.ts` | New untracked file (Vite type reference) |

These changes are **not pushed** to GitHub.

## Architecture

- **Backend:** Python/FastAPI — Twelve Data WS stream → CandleAggregator → consolidation detection → key level checks → WebSocket broadcast
- **Frontend:** React 18 + TypeScript + Tailwind + lightweight-charts v4
- **Database:** PostgreSQL (SQLite in dev via .env override)
- **Infra:** Docker Compose, deployed on Render, GitHub Actions CI

## Observed Issues / Potential Improvements

1. **`.env` contains a live Twelve Data API key** — should be gitignored; currently tracked and pushed.
2. **No `AGENTS.md`** (just created) — this file for agent awareness.
3. **lightweight-charts v4 migration is incomplete** — `PriceChart.tsx` locally uses v4 API but GitHub has v3 API (inconsistent with `package.json` which declares `^4.1.3`).
