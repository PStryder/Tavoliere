# Tavoliere

A rule-agnostic virtual card table. No game rules encoded — players negotiate, agree, and manage the game themselves. Proof-of-concept for a **consensus mediation system** where human and AI participants coordinate under ambiguous norms.

## Why

Most digital card games hard-code rules. Tavoliere inverts this: the system provides a neutral surface with cards, zones, and visibility boundaries, but never interprets legality. Players propose actions, acknowledge or dispute them, and resolve disagreements through chat. This makes it an instrument for studying how groups form and enforce norms without external authority — the core question behind **SPQ-AN** (Social Participation Quality under Ambiguous Norms).

## How It Works

### Three Action Types

| Type | Flow | Example |
|------|------|---------|
| **Unilateral** | Immediate, non-disputable | Reorder your hand, shuffle the deck |
| **Consensus** | Intent &rarr; ACK from all seats &rarr; Commit | Move a card, deal round-robin |
| **Optimistic** | Commit immediately + objection window (3-5s) | Change phase, auto-ACK'd moves |

### Visibility Boundaries

- **Public zones** (deck, discard, center) — visible to all
- **Private zones** (hand) — only the owner sees contents
- **Seat-public zones** (melds, tricks) — visible to all, owned by a seat

The system enforces visibility at the API layer. Private card contents never leave the server for non-owners.

### Dispute Resolution

Any seated player can NACK a consensus action or dispute an optimistic action within its objection window. Disputes pause the table — no new actions until resolved. Resolution happens through chat negotiation, not system adjudication.

## Architecture

```
backend/
  models/      Pydantic models — the canonical schema
  engine/      State machine, action classification, consensus, visibility
  api/         REST endpoints + WebSocket (event-driven)
  auth/        Principal/credential auth, JWT tokens
  tests/       pytest suite
```

All state is in-memory and ephemeral. No database — sessions exist for the duration of the server process.

### Key Design Decisions

- **Event-sourced state**: Every mutation produces an `Event` with monotonic sequence number. The event log is the source of truth.
- **Snapshot + rollback**: Snapshots are taken before mutations. Optimistic actions that get disputed roll back to the pre-commit snapshot.
- **AUTO_ACK promotion**: When all seats enable auto-acknowledge for an action type, consensus actions are promoted to optimistic (faster flow, still disputable).
- **Rate limiting**: Per-seat, per-action-type cooldowns prevent grief (shuffle spam, phase change floods, action flooding).

## Research Mode

Tables can be created with `research_mode: true` to enable a parallel instrumentation layer for SPQ-AN studies. This adds:

- **ResearchObserver** — attaches to `TableState`, enriches gameplay events into a separate write-only log with action enrichments, visibility transitions, ACK/dispute latencies, RNG provenance, and chat metadata
- **Identity anonymization** — SHA256 hashing with per-session salt, pseudonym generation (`P-{hash[:8]}`)
- **Consent management** — 7 tiered opt-ins (research logging, chat storage, training use, publication, publication excerpts, longitudinal linking, AI disclosure acknowledgment)
- **Longitudinal linking** — cross-session identity linking only when explicitly consented; scrubbed on revocation
- **Table configuration hash** — SHA256 of all settings (objection window, rate limits, shuffle policy, AI pacing, deck recipe, seat count) for machine-verifiable reproducibility
- **AI latency simulation flags** — records whether AI timing was raw or artificially paced, since timing distribution is a behavioral signature that affects SPQ-AN metrics

Zero overhead when research mode is off — a single `if None` branch per event.

### Ethical Boundary

> The Tavoliere research corpus shall not be used to develop systems intended to covertly manipulate, exploit, or psychologically steer human participants without their knowledge and consent.

This is enforced as a machine-readable constant (`RESEARCH_ETHICAL_BOUNDARY`) in `backend/models/research.py`.

## Quick Start

```bash
# Install dependencies
uv sync --extra dev

# Run the server
uv run uvicorn backend.main:app --reload

# Run tests (146 passing)
uv run pytest
```

## API Overview

### Authentication

| Endpoint | Description |
|----------|-------------|
| `POST /dev/bootstrap` | Create a principal with N credentials (dev only) |
| `POST /api/token` | Exchange client_id/secret for JWT |

### Tables

| Endpoint | Description |
|----------|-------------|
| `POST /api/tables` | Create table (with optional `research_mode`) |
| `GET /api/tables` | List tables (summary) |
| `GET /api/tables/{id}` | Get visibility-filtered table state |
| `POST /api/tables/{id}/join` | Join a seat (with optional `ai_metadata`) |
| `POST /api/tables/{id}/leave` | Leave seat |
| `PATCH /api/tables/{id}/settings` | Update settings (host only) |
| `DELETE /api/tables/{id}` | Destroy table (host only) |

### Actions

| Endpoint | Description |
|----------|-------------|
| `POST /api/tables/{id}/actions` | Submit action intent |
| `POST /api/tables/{id}/actions/{aid}/ack` | ACK a consensus action |
| `POST /api/tables/{id}/actions/{aid}/nack` | NACK (triggers dispute) |
| `POST /api/tables/{id}/actions/{aid}/dispute` | Dispute optimistic action |
| `POST /api/tables/{id}/dispute/resolve` | Resolve active dispute |
| `PATCH /api/tables/{id}/seats/{sid}/ack_posture` | Update AUTO_ACK posture |

### WebSocket

`WS /ws/{table_id}?token={jwt}` — per-seat event stream. Supports action submission, ACK/NACK, dispute, chat, and ACK posture updates as inbound messages.

### Research (host only, research tables)

| Endpoint | Description |
|----------|-------------|
| `GET .../research/config` | Research session configuration |
| `GET .../research/events` | Export events (JSON, filterable) |
| `GET .../research/events/export` | Full NDJSON export |
| `GET .../research/identities` | Export identity records |
| `GET .../research/snapshots` | Export research snapshots |
| `DELETE .../research/session` | Delete all session research data |
| `DELETE .../research/identities/{hash}` | Purge identity data |

### Consent (seated players, research tables)

| Endpoint | Description |
|----------|-------------|
| `GET .../consent/requirements` | Required/optional consent tiers |
| `POST .../consent` | Submit consent |
| `GET .../consent` | Get own consent status |
| `DELETE .../consent` | Revoke consent |

## Stack

- **Runtime**: Python 3.11+
- **Framework**: FastAPI + Pydantic v2
- **Server**: uvicorn
- **Auth**: JWT (python-jose + bcrypt)
- **WebSocket**: websockets
- **Tests**: pytest + pytest-asyncio + httpx
- **Package manager**: uv

## Target Games (v0.1 validation)

- 4-player Euchre (standard 24-card deck)
- 4-player Double Pinochle (80-card deck)

No rules for either game are encoded. Success means players can complete a full game using only the consensus mediation primitives.
