# Tavoliere

## What This Is
A rule-agnostic virtual card table. No game rules encoded — players manage the game.
POC for a consensus mediation system.

## Stack
- Backend: Python 3.11+, FastAPI, Pydantic, uvicorn
- Frontend: React + Vite + Tailwind
- State: In-memory only (ephemeral sessions)
- Package manager: `uv`

## Running
```bash
uv sync --extra dev
uv run uvicorn backend.main:app --reload
uv run pytest
```

## Key Invariants
- Private state never exposed to non-owners
- UI and API expose identical per-seat information
- No rule enforcement — the system never interprets legality
- All commits require appropriate ACK (consensus) or survive objection window (optimistic)

## Architecture
- `backend/models/` — Pydantic models (canonical schema)
- `backend/engine/` — State machine, action processing, visibility
- `backend/api/` — REST endpoints + WebSocket
- `backend/auth/` — Principal/credential auth, JWT tokens
