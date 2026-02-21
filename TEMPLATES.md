# Tavoliere Template Definitions

**Version:** v0.1 – Rule-Agnostic Card Surface

---

## 1. Card Template

### 1.1 Purpose

Defines the minimal structure of a portable card object. Contains no intrinsic gameplay logic.

### 1.2 Schema

```
Card {
  card_id: UUID,
  template_id: string,
  suit: string,
  rank: string,
  face_state: "face_up" | "face_down",
  owner_seat_id: string | null,
  current_zone_id: string,
  created_at: timestamp,
  metadata: object
}
```

### 1.3 Field Semantics

| Field | Description |
|-------|-------------|
| card_id | Globally unique identifier. Immutable. |
| template_id | Identifies originating card template (e.g., "standard_52"). |
| suit | Arbitrary string. No ordering implied. |
| rank | Arbitrary string. No ordering implied. |
| face_state | Visibility control only. |
| owner_seat_id | Seat currently holding card (if applicable). |
| current_zone_id | Container location reference. |
| metadata | Free-form extension field (never interpreted by engine). |

### 1.4 Explicit Non-Features

The Card Template does not encode:

- Numeric value
- Rank ordering
- Trump logic
- Legality constraints
- Scoring weight

All interpretation is external and social.

---

## 2. Deck Template

### 2.1 Purpose

Defines a structured collection of Card objects.

### 2.2 Schema

```
Deck {
  deck_id: UUID,
  template_id: string,
  card_ids: [UUID],
  shuffle_state: {
    shuffled_by: string | null,
    shuffled_at: timestamp | null,
    seed: string | null
  },
  metadata: object
}
```

### 2.3 Allowed Actions

All actions must use Tavoliere primitives.

- propose_shuffle
- propose_deal
- move_card
- reveal_card
- conceal_card

None enforce correctness of count or distribution.

### 2.4 Determinism Requirement

If shuffle is logged with seed: replay must reproduce card order exactly.

If no seed: replay must reproduce recorded post-shuffle order.

---

## 3. Zone Template

### 3.1 Purpose

Defines a container for objects. Zones are neutral surfaces.

### 3.2 Schema

```
Zone {
  zone_id: UUID,
  zone_type: "private" | "public" | "shared_control",
  seat_visibility: [seat_id],
  capacity: integer | null,
  ordering: "stacked" | "ordered" | "unordered",
  metadata: object
}
```

### 3.3 Zone Types

**private** — Visible only to designated seat(s).

**public** — Visible to all seats.

**shared_control** — Visible to all, but write access may require consensus.

### 3.4 Engine Guarantees

Engine enforces:

- Visibility constraints
- Container membership
- Event ordering

Engine does NOT enforce:

- Legal card count
- Card identity restrictions
- Move legality

---

## 4. Table Template (4-Seat Cutthroat Layout)

### 4.1 Purpose

Defines structural zones for a 4-player free-for-all card table.

### 4.2 Required Zones

For each seat:

```
SeatZone {
  hand_zone_id
  trick_pile_zone_id
  private_scratchpad_zone_id (optional)
}
```

Shared zones:

```
SharedZones {
  deck_zone_id
  trick_play_zone_id
  discard_zone_id (optional)
  public_scratchpad_zone_id (optional)
}
```

### 4.3 Example Layout Definition

```
TableTemplate {
  table_id: UUID,
  seat_count: 4,
  zones: {
    seat_A_hand,
    seat_B_hand,
    seat_C_hand,
    seat_D_hand,
    seat_A_tricks,
    seat_B_tricks,
    seat_C_tricks,
    seat_D_tricks,
    trick_play_zone,
    deck_zone,
    discard_zone,
    public_scratchpad,
    seat_A_notes,
    seat_B_notes,
    seat_C_notes,
    seat_D_notes
  }
}
```

### 4.4 Turn Model

Turn tracking is structural only:

```
TurnState {
  active_seat_id: string,
  phase_label: string,
  metadata: object
}
```

No enforcement of turn compliance is performed by engine. Violations must be socially disputed.

---

## 5. Scratchpad Template

### 5.1 Purpose

Provides structured text surface for social memory externalization.

### 5.2 Schema

```
Scratchpad {
  scratchpad_id: UUID,
  visibility: "public" | "private",
  owner_seat_id: string | null,
  content: string,
  last_modified_by: string,
  last_modified_at: timestamp
}
```

### 5.3 Allowed Actions

- propose_edit
- append
- clear
- replace

All edits are event-logged.

### 5.4 Research-Relevant Logging

Each edit event must include:

```json
{
  "seat_id": "...",
  "previous_content_hash": "...",
  "new_content_hash": "...",
  "timestamp": "..."
}
```

This enables:

- Memory reliance analysis
- Note-taking frequency correlation
- Dispute resolution acceleration tracking

---

## 6. Action Primitive Requirements

All template interactions must use:

- Unilateral actions (private changes)
- Consensus actions (ACK required)
- Optimistic actions (commit, reversible)
- Dispute events (NACK)
- Rollback events

Templates must never bypass the primitive model.

---

## 7. Explicit Non-Enforcement Clause

The following must never be encoded in any template:

- Game legality
- Follow-suit rules
- Trick ranking
- Bid validation
- Score calculation
- Card counting enforcement
- Phase compliance enforcement

Templates provide surface only. Participants provide meaning.

---

## 8. Replay Integrity Requirements

For deterministic replay:

- All card moves must reference card_id
- All zone transitions must be ordered
- All scratchpad edits must be serialized
- All proposal/ACK/NACK events must include timestamps

Replay must reconstruct:

- Visible table state
- Hidden seat state
- Negotiation trace
- Scratchpad content

without requiring external interpretation.

---

## 9. Extensibility Constraints

Future templates may extend:

- Multiple decks
- Non-card tokens
- Multi-zone layering
- Timed windows

But must not introduce rule evaluation logic.

---

## 10. Design Principle Summary

Tavoliere Templates:

- Model furniture
- Enforce visibility
- Enforce event order
- Log negotiation

They do not:

- Interpret meaning
- Judge legality
- Enforce correctness

All game reality emerges socially.