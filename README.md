# Tavoliere

[![PyPI](https://img.shields.io/pypi/v/tavoliere)](https://pypi.org/project/tavoliere)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/PStryder/Tavoliere)](LICENSE)

**Tavoliere** is a *rule-agnostic*, **consensus-based virtual card table**, designed as a proof-of-concept for mediated coordination between peers — human and AI — under ambiguous norms.

Tavoliere is not a game engine. It is a consensus mediation substrate disguised as a card table.

Unlike most digital card platforms, Tavoliere does **not encode game rules**.
Players **propose actions**, **acknowledge or dispute**, and **negotiate resolution through chat**.
This makes it not just a gameplay surface, but **an instrument for studying social coordination and norm formation** — the core questions behind the **SPQ-AN evaluation framework**.

---

## 🧠 Core Principles

- **Rule-Agnostic:** No legality checks, no referees, no enforcement.
- **Consensus Mediation:** Shared state changes require ACKs; disputes pause play.
- **Human and AI Peers:** All participants are equal first-class citizens.
- **Event-Driven API:** Real-time state sync via WebSockets.
- **Research-Ready:** Optional Research Mode logs structured consensus events.

---

## 🚦 How It Works

### Action Types

| Type | Flow | Example |
|------|------|---------|
| **Unilateral** | Immediate, non-disputable | Reorder your hand, shuffle the deck |
| **Consensus** | Intent → ACK from all seats → Commit | Move a card, deal round-robin |
| **Optimistic** | Commit immediately + objection window (3–5s) | Phase changes, auto-ACK'd moves |

### Visibility Boundaries

- **Public zones:** e.g., deck, discard, center — visible to all.
- **Private zones:** e.g., hand — visible only to the owner.
- **Seat-public zones:** e.g., melds, trick piles — visible to all, owned by a seat.

The system enforces visibility at the API layer.

---

## 👥 Dispute & Negotiation

Any seated player may:

- **NACK** a consensus intent
- **Dispute** an optimistic action within its objection window

Disputes pause the table — no new shared actions until resolved through negotiation (chat or revised intent).

---

## 📦 Architecture

```
backend/
  models/      # Pydantic API + domain models
  engine/      # State machine, consensus logic
  api/         # FastAPI REST + WebSocket
  auth/        # Auth (JWT)
  tests/       # pytest suite
```

- **State:** In-memory, ephemeral (no database)
- **Event Sourcing:** All mutations produce sequenced `Event` records
- **Snapshot + Rollback:** Optimistic actions can be rolled back
- **AUTO_ACK:** Promotes consensus to optimistic flow when all seats opt in
- **Rate Limiting:** Prevents grief (shuffle spam, flood, etc.)

---

## 📊 Research Mode (SPQ-AN)

Tables may be created with:

```json
{ "research_mode": true }
```

This enables:

- **ResearchObserver:** emits enriched event logs (ACK latencies, dispute timing, RNG provenance)
- **Identity anonymization:** SHA256 pseudonyms
- **Consent tiers:** research logging, chat storage, training use, publication, longitudinal linking, AI membership disclosure
- **Reproducibility:** machine-verifiable config hash
- **AI latency flags:** captures whether AI actions were temporally simulated

> **Ethical Boundary:** The Tavoliere research corpus shall not be used to covertly manipulate or psychologically steer participants without knowledge and consent — enforced in code as `RESEARCH_ETHICAL_BOUNDARY`.

---

## 🚀 Quick Start

```bash
# Install dependencies
uv sync --extra dev

# Run the server
uv run uvicorn backend.main:app --reload

# Run tests
uv run pytest
```

---

## 📡 API Overview

### Authentication

| Endpoint | Description |
|----------|-------------|
| `POST /dev/bootstrap` | Create a principal (dev only) |
| `POST /api/token` | Exchange credentials for JWT |

### Tables

| Endpoint | Description |
|----------|-------------|
| `POST /api/tables` | Create table (with optional `research_mode`) |
| `GET /api/tables` | List tables |
| `GET /api/tables/{id}` | Get seat-filtered state |
| `POST /api/tables/{id}/join` | Join seat |
| `PATCH /api/tables/{id}/settings` | Update table (host only) |
| `DELETE /api/tables/{id}` | Destroy table (host only) |

### Actions

| Endpoint | Description |
|----------|-------------|
| `POST /api/tables/{id}/actions` | Submit intent |
| `POST /api/tables/{id}/actions/{aid}/ack` | ACK intent |
| `POST /api/tables/{id}/actions/{aid}/nack` | NACK (initiate dispute) |
| `POST /api/tables/{id}/actions/{aid}/dispute` | Dispute optimistic action |
| `POST /api/tables/{id}/dispute/resolve` | Resolve dispute |
| `PATCH /api/tables/{id}/seats/{sid}/ack_posture` | Update AUTO_ACK |

### WebSocket

`WS /ws/{table_id}?token={jwt}`

Supports:

- Action intents
- ACK/NACK
- Dispute
- Chat
- ACK posture updates

### 📦 Research Endpoints (host only, `research_mode`)

| Endpoint | Description |
|----------|-------------|
| `GET …/research/config` | Session config |
| `GET …/research/events` | Filtered event export |
| `GET …/research/events/export` | NDJSON event export |
| `GET …/research/identities` | Identity pseudonyms |
| `DELETE …/research/session` | Delete research log |
| `DELETE …/research/identities/{hash}` | Purge identity data |

---

## 🧠 Key Design Decisions

- **Event-sourced state:** The event log is the source of truth.
- **Snapshot + rollback:** Enables optimistic actions and replay.
- **AUTO_ACK promotion:** Faster flow backstopped by objection windows.
- **Rate limits:** Prevent grief without interfering with play.
- **Ephemeral sessions:** Simple infra for v0.1.

---

## 🃏 Target Games (v0.1)

- 4-player Euchre (24-card deck)
- 4-player Double Pinochle (80-card deck)

No rules for either game are encoded.
Success means players can complete a game using only consensus primitives.

---

## 📌 Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI + Pydantic
- **Server:** uvicorn
- **Auth:** JWT
- **WebSocket:** Standard WebSockets
- **Tests:** pytest + pytest-asyncio

---

## 📫 Contributing

Contributions gratefully accepted.
Please open issues or pull requests targeting:

- feature enhancements
- API improvements
- research tooling
- documentation clarity
