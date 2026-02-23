# Tavoliere Agent Skill

A rule-agnostic virtual card table. No game rules are encoded — players manage the game through consensus.

Base URL: `http://localhost:8000`

---

## Authentication

All API endpoints (except health and dev bootstrap) require a Bearer token.

### 1. Bootstrap (dev mode only)

`POST /dev/bootstrap`

```json
{
  "display_name": "My Principal",
  "num_credentials": 1,
  "credential_prefix": "Agent"
}
```

Returns a principal and credentials. Each credential has a `client_id` and `client_secret`.

### 2. Token Exchange

`POST /api/token`

```json
{
  "client_id": "tav_...",
  "client_secret": "..."
}
```

Returns `{ "access_token": "..." }`. Tokens expire after 24 hours.

### 3. Using the Token

Include on all subsequent requests:

```
Authorization: Bearer <access_token>
```

---

## Tables

### Create a Table

`POST /api/tables`

```json
{
  "display_name": "Friday Night Euchre",
  "deck_recipe": "euchre_24",
  "settings": {}
}
```

Deck recipes: `standard_52`, `euchre_24`, `double_pinochle_80`.

Settings (all optional, shown with defaults):

| Field | Default | Description |
|---|---|---|
| `max_seats` | 4 | Maximum players |
| `objection_window_s` | 3.0 | Seconds before optimistic actions finalize (2.0–5.0) |
| `consensus_timeout_s` | 30.0 | Seconds before pending consensus actions auto-rollback (5.0–300.0) |
| `chat_max_length` | 500 | Maximum chat message length (1–2000) |
| `shuffle_is_optimistic` | false | If true, shuffle uses optimistic path instead of unilateral |
| `phase_locked` | false | If true, phase changes are blocked |
| `min_action_delay_ms` | 0 | Minimum delay between actions (for AI pacing) |

### List Tables

`GET /api/tables`

### Get Table State

`GET /api/tables/{table_id}`

Returns visibility-filtered state. You see your own hand but not other players' hands.

### Join a Table

`POST /api/tables/{table_id}/join`

```json
{
  "display_name": "North"
}
```

Returns your `Seat` with a `seat_id` (e.g. `seat_0`).

### Leave a Table

`POST /api/tables/{table_id}/leave`

### Destroy a Table (Host Only)

`DELETE /api/tables/{table_id}`

### Update Settings (Host Only)

`PATCH /api/tables/{table_id}/settings`

```json
{ "phase_locked": true }
```

---

## Actions

The system classifies every action into one of three classes:

| Class | Behavior | Examples |
|---|---|---|
| **Unilateral** | Executes immediately, no approval needed | `reorder`, `shuffle`, `self_reveal` |
| **Consensus** | Pending until all other seats ACK | `move_card`, `move_cards_batch`, `deal_round_robin`, `create_zone`, `undo` |
| **Optimistic** | Executes immediately, can be disputed within objection window | `set_phase` |

### Submit an Action

`POST /api/tables/{table_id}/actions`

```json
{
  "action_type": "move_card",
  "card_ids": ["card_uuid"],
  "source_zone_id": "deck",
  "target_zone_id": "center"
}
```

**Returns:**
- `{ "status": "committed" }` — action applied
- `{ "status": "pending", "action_id": "..." }` — awaiting ACKs

### Action Types

**move_card** / **move_cards_batch** (consensus):
```json
{
  "action_type": "move_card",
  "card_ids": ["..."],
  "source_zone_id": "deck",
  "target_zone_id": "hand_seat_0"
}
```

**deal_round_robin** (consensus):
```json
{
  "action_type": "deal_round_robin",
  "card_ids": ["c1", "c2", "c3", "c4"],
  "source_zone_id": "deck",
  "target_zone_ids": ["hand_seat_0", "hand_seat_1", "hand_seat_2", "hand_seat_3"]
}
```

**set_phase** (optimistic):
```json
{
  "action_type": "set_phase",
  "phase_label": "bidding"
}
```

**shuffle** (unilateral):
```json
{
  "action_type": "shuffle",
  "source_zone_id": "deck"
}
```

**reorder** (unilateral):
```json
{
  "action_type": "reorder",
  "source_zone_id": "hand_seat_0",
  "new_order": ["card_3", "card_1", "card_2"]
}
```

**create_zone** (consensus):
```json
{
  "action_type": "create_zone",
  "zone_label": "Kitty",
  "zone_kind": "custom",
  "zone_visibility": "public"
}
```

**undo** (consensus):
```json
{
  "action_type": "undo",
  "target_event_seq": 5
}
```

### ACK a Pending Action

`POST /api/tables/{table_id}/actions/{action_id}/ack`

When all required seats ACK, the action commits. If no one ACKs within `consensus_timeout_s`, the action auto-rolls back.

### NACK a Pending Action

`POST /api/tables/{table_id}/actions/{action_id}/nack`

```json
{
  "reason": "turn",
  "reason_text": "Not your turn"
}
```

Reasons: `rules`, `turn`, `clarify`, `other`.

A NACK enters dispute mode. No new consensus actions are accepted until the dispute resolves.

### Dispute an Optimistic Action

`POST /api/tables/{table_id}/actions/{action_id}/dispute`

```json
{
  "reason": "rules",
  "reason_text": "Wrong phase for that"
}
```

Must be within the objection window. Rolls back the action and enters dispute mode.

### Resolve a Dispute

`POST /api/tables/{table_id}/dispute/resolve`

```json
{ "resolution": "cancelled" }
```

Resolutions: `revised`, `cancelled`, `undone`, `absent_marked`.

### List Pending Actions

`GET /api/tables/{table_id}/actions/pending`

### ACK Posture (Auto-ACK)

`PATCH /api/tables/{table_id}/seats/{seat_id}/ack_posture`

```json
{
  "move_card": true,
  "deal": true,
  "set_phase": false,
  "create_zone": false,
  "undo": false
}
```

---

## Chat

`POST /api/tables/{table_id}/chat`

```json
{
  "text": "Your turn to deal",
  "thread_id": null
}
```

Messages are capped at `chat_max_length` characters (default 500).

---

## Scratchpads

Each seat has a private scratchpad (`notes_seat_0`). There is also a shared `public_scratchpad`.

`GET /api/tables/{table_id}/scratchpads` — list visible scratchpads

`GET /api/tables/{table_id}/scratchpads/{scratchpad_id}` — read one

`POST /api/tables/{table_id}/scratchpads/{scratchpad_id}/edit` — write to one

---

## WebSocket

`ws://localhost:8000/ws/{table_id}?token=<access_token>&mode=player`

Mode is `player` (default) or `spectate`.

### Inbound Messages

```json
{"msg_type": "action", "intent": { ... }}
{"msg_type": "ack", "action_id": "..."}
{"msg_type": "nack", "action_id": "...", "reason": "turn", "reason_text": "..."}
{"msg_type": "dispute", "action_id": "...", "reason": "rules"}
{"msg_type": "chat", "text": "hello"}
{"msg_type": "set_ack_posture", "ack_posture": {"move_card": true}}
{"msg_type": "ping"}
```

Spectators can only send `ping` and `chat`.

### Outbound Messages

```json
{"msg_type": "event", "event": { ... }}
{"msg_type": "state_sync", "state": { ... }}
{"msg_type": "error", "error": "...", "error_code": "..."}
{"msg_type": "pong"}
```

### Event Types

| Event | Meaning |
|---|---|
| `action_committed` | Action applied to table state |
| `action_finalized` | Optimistic action survived objection window |
| `action_rolled_back` | Action undone (dispute or consensus timeout) |
| `intent_created` | Consensus action proposed, awaiting ACKs |
| `ack_received` | A seat ACKed a pending action |
| `nack_received` | A seat NACKed — dispute incoming |
| `dispute_opened` | Table entered dispute mode |
| `dispute_resolved` | Dispute settled |
| `presence_changed` | Player connected/disconnected |
| `chat_message` | Chat message sent |
| `phase_changed` | Game phase changed |
| `zone_created` | New zone added |
| `table_destroyed` | Table is gone |

---

## Zones

Every table starts with three public zones: `deck`, `discard`, `center`.

When a player joins, they get three private zones: `hand_seat_N`, `meld_seat_N`, `tricks_seat_N`.

Zone visibilities: `public` (everyone sees), `private` (owner only), `seat_public` (owner's cards visible face-up to all).

---

## Typical Agent Flow

```
1. POST /dev/bootstrap         → get credentials
2. POST /api/token             → get access_token
3. POST /api/tables            → create table (or GET /api/tables to find one)
4. POST /api/tables/{id}/join  → take a seat
5. Connect WS: ws://host/ws/{id}?token=...
6. Receive state_sync
7. Submit actions via WS or REST
8. ACK/NACK other players' consensus actions
9. React to events streamed over WS
```

---

## Invariants

- Private zone contents are never exposed to non-owners
- The system never interprets game rules or enforces legality
- All state mutations require either consensus or survive an objection window
- Pending consensus actions time out after `consensus_timeout_s` and auto-rollback
