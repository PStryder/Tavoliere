"""Research instrumentation models (Appendix A).

These models define the parallel research event log, enrichment structures,
identity records, and configuration for SPQ-AN research mode.

Ethical Boundary:
    The Tavoliere research corpus shall not be used to develop systems
    intended to covertly manipulate, exploit, or psychologically steer
    human participants without their knowledge and consent.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Ethical boundary — machine-readable constant
# ---------------------------------------------------------------------------

RESEARCH_ETHICAL_BOUNDARY = (
    "The Tavoliere research corpus shall not be used to develop systems "
    "intended to covertly manipulate, exploit, or psychologically steer "
    "human participants without their knowledge and consent."
)


# ---------------------------------------------------------------------------
# A.3 — Visibility transition for action enrichment
# ---------------------------------------------------------------------------

class VisibilityTransition(str, Enum):
    NONE = "none"
    PRIVATE_TO_PUBLIC = "private_to_public"
    PUBLIC_TO_PRIVATE = "public_to_private"
    PRIVATE_TO_PRIVATE = "private_to_private"


# ---------------------------------------------------------------------------
# Research config (per-table when research_mode=True)
# ---------------------------------------------------------------------------

class ResearchConfig(BaseModel):
    research_mode: bool = True
    research_mode_version: str = "0.1.0"
    session_id: str  # UUID
    identity_salt: str  # random hex for SHA256 hashing
    snapshot_frequency_events: int = 50
    rng_scheme: Literal["server_authoritative"] = "server_authoritative"
    # AI latency simulation — whether AI timing was raw or artificially paced
    ai_min_action_delay_ms: int | None = None
    ai_latency_simulation_enabled: bool = False
    # Table configuration hash for reproducibility
    table_config_hash: str | None = None


# ---------------------------------------------------------------------------
# A.2.2 — Seat metadata snapshot (point-in-time)
# ---------------------------------------------------------------------------

class SeatMetadataSnapshot(BaseModel):
    seat_id: str
    seat_type: str  # "human" | "ai"
    display_name: str
    pseudonym_id: str
    presence_state: str
    auto_ack_posture: dict[str, bool]


# ---------------------------------------------------------------------------
# A.3 — Action enrichment
# ---------------------------------------------------------------------------

class ActionEnrichment(BaseModel):
    action_id: str
    action_type: str
    action_class: str
    visibility_transition: VisibilityTransition = VisibilityTransition.NONE
    object_ids: list[str] = []
    source_zone_id: str | None = None
    destination_zone_id: str | None = None
    is_optimistic: bool = False
    required_ack_set: list[str] = []
    # A.3.1 — ACK fields
    ack_type: str | None = None  # "ack" | "nack"
    ack_latency_ms: int | None = None
    ack_posture_at_time: dict[str, bool] | None = None
    # A.3.2 — Dispute fields
    dispute_reason_tag: str | None = None
    dispute_latency_ms: int | None = None
    dispute_window_ms_remaining: int | None = None
    # A.3.3 — Resolution fields
    resolution_type: str | None = None
    resolution_latency_ms: int | None = None
    chat_messages_during_resolution: int | None = None


# ---------------------------------------------------------------------------
# A.4 — Chat enrichment
# ---------------------------------------------------------------------------

class ChatEnrichment(BaseModel):
    chat_message_id: str
    sender_seat_id: str
    message_length_chars: int
    message_length_tokens: int | None = None
    in_response_to_action_id: str | None = None
    is_resolution_related: bool = False


# ---------------------------------------------------------------------------
# A.15.2 — RNG provenance
# ---------------------------------------------------------------------------

class RngProvenance(BaseModel):
    rng_scheme: str = "server_authoritative"
    rng_seed_id: str | None = None
    rng_seed_hash: str | None = None
    rng_seed_revealed: bool = False
    deck_order_after: list[str] = []  # card_ids post-shuffle


# ---------------------------------------------------------------------------
# A.2.1 — Canonical research event
# ---------------------------------------------------------------------------

class ResearchEvent(BaseModel):
    event_id: str  # UUID
    table_id: str
    session_id: str
    event_type: str
    timestamp_utc_ms: int  # epoch milliseconds
    server_sequence_number: int
    phase_label: str
    previous_event_id: str | None = None  # A.15 causality chain
    gameplay_seq: int  # back-reference to gameplay Event.seq
    seat_snapshot: SeatMetadataSnapshot | None = None
    action_enrichment: ActionEnrichment | None = None
    chat_enrichment: ChatEnrichment | None = None
    rng_provenance: RngProvenance | None = None


# ---------------------------------------------------------------------------
# A.5 — Research snapshot
# ---------------------------------------------------------------------------

class ResearchSnapshot(BaseModel):
    snapshot_id: str
    session_id: str
    server_sequence_number: int
    timestamp_utc_ms: int
    active_phase_label: str
    seat_auto_ack_distribution: dict[str, list[str]] = {}
    pending_actions_count: int = 0
    dispute_active: bool = False
    snapshot_hash: str | None = None
    table_config_hash: str | None = None


# ---------------------------------------------------------------------------
# A.2.3 — Identity record (stored separately from events)
# ---------------------------------------------------------------------------

class IdentityRecord(BaseModel):
    identity_hash: str  # SHA256(identity_id + salt)
    session_id: str
    seat_id: str
    seat_type: str  # "human" | "ai"
    ai_model_name: str | None = None
    ai_model_version: str | None = None
    ai_provider: str | None = None
    client_type: str | None = None
    client_version: str | None = None
    pseudonym_id: str
    # Longitudinal linking — only populated if participant consents
    longitudinal_link_id: str | None = None
    longitudinal_link_consent: bool = False


# ---------------------------------------------------------------------------
# Table configuration hash for reproducibility
# ---------------------------------------------------------------------------

def compute_table_config_hash(
    settings_dump: dict,
    deck_recipe: str,
    max_seats: int,
    ai_min_action_delay_ms: int | None = None,
    ai_latency_simulation_enabled: bool = False,
) -> str:
    """Compute a deterministic hash of table configuration.

    Includes: objection window, rate limits, AUTO_ACK defaults,
    shuffle policy, AI pacing, deck recipe, seat count.
    """
    canonical = {
        "deck_recipe": deck_recipe,
        "max_seats": max_seats,
        "objection_window_s": settings_dump.get("objection_window_s"),
        "shuffle_is_optimistic": settings_dump.get("shuffle_is_optimistic"),
        "min_action_delay_ms": settings_dump.get("min_action_delay_ms"),
        "phase_locked": settings_dump.get("phase_locked"),
        "dispute_cooldown_s": settings_dump.get("dispute_cooldown_s"),
        "phase_change_cooldown_s": settings_dump.get("phase_change_cooldown_s"),
        "shuffle_cooldown_s": settings_dump.get("shuffle_cooldown_s"),
        "intent_rate_max_count": settings_dump.get("intent_rate_max_count"),
        "intent_rate_window_s": settings_dump.get("intent_rate_window_s"),
        "zone_create_cooldown_s": settings_dump.get("zone_create_cooldown_s"),
        "ai_min_action_delay_ms": ai_min_action_delay_ms,
        "ai_latency_simulation_enabled": ai_latency_simulation_enabled,
    }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()
