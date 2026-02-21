"""SPQ-AN metric computation engine.

Computes per-seat behavioural metrics from persisted research events:
  CE  — Commitment Efficiency
  RC  — Resolution Capability
  NS  — Norm Sensitivity
  CA  — Communicative Agency
  SSC — Social–Strategic Conduct
"""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Metric models
# ---------------------------------------------------------------------------


class CEMetrics(BaseModel):
    """Commitment Efficiency — how promptly a seat acknowledges actions."""

    mean_ack_latency_ms: float | None = None
    dispute_density: float = 0.0  # disputes_opened / actions_involving_seat
    rollback_rate: float = 0.0  # rollbacks / committed_actions


class RCMetrics(BaseModel):
    """Resolution Capability — how effectively disputes are resolved."""

    mean_resolution_latency_ms: float | None = None
    mean_chat_per_dispute: float = 0.0
    resolution_distribution: dict[str, int] = {}  # resolution_type → count


class NSMetrics(BaseModel):
    """Norm Sensitivity — adaptation to auto-ack postures and phase labels."""

    auto_ack_adoption_rate: float = 0.0  # fraction of snapshots with any auto-ack
    auto_ack_churn: float = 0.0  # posture changes / snapshots
    phase_label_diversity: int = 0  # unique phase labels observed


class CAMetrics(BaseModel):
    """Communicative Agency — chat behaviour during gameplay."""

    mean_message_length_chars: float = 0.0
    resolution_related_chat_ratio: float = 0.0
    messages_per_dispute: float = 0.0


class SSCMetrics(BaseModel):
    """Social-Strategic Conduct — dispute initiation and involvement patterns."""

    dispute_initiation_rate: float = 0.0  # disputes_opened_by_seat / total_disputes
    dispute_involvement_rate: float = 0.0  # disputes_on_seat_actions / total_disputes
    dispute_clustering_score: float = 0.0  # clustered disputes (within 10 events)


class SeatSPQAN(BaseModel):
    """Full SPQ-AN profile for a single seat."""

    seat_id: str
    pseudonym_id: str
    seat_type: str
    ce: CEMetrics
    rc: RCMetrics
    ns: NSMetrics
    ca: CAMetrics
    ssc: SSCMetrics


class SessionSPQAN(BaseModel):
    """SPQ-AN results for an entire session."""

    session_id: str
    table_id: str
    seats: list[SeatSPQAN]
    event_count: int
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_mean(values: list[float | int]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _safe_div(num: float, den: float) -> float:
    return num / den if den > 0 else 0.0


# ---------------------------------------------------------------------------
# Per-seat computation
# ---------------------------------------------------------------------------


def compute_ce_for_seat(
    seat_id: str,
    events: list[dict],
) -> CEMetrics:
    """CE — from ack latencies, dispute counts, rollback counts."""
    ack_latencies: list[int] = []
    disputes_involving = 0
    rollbacks = 0
    actions_involving = 0

    # Collect action_ids proposed by this seat
    proposed_actions: set[str] = set()
    for ev in events:
        ss = ev.get("seat_snapshot")
        ae = ev.get("action_enrichment")
        if not ae:
            continue
        action_id = ae.get("action_id", "")
        et = ev.get("event_type", "")

        if et == "intent_created" and ss and ss.get("seat_id") == seat_id:
            proposed_actions.add(action_id)

    for ev in events:
        ae = ev.get("action_enrichment")
        ss = ev.get("seat_snapshot")
        if not ae:
            continue
        action_id = ae.get("action_id", "")
        et = ev.get("event_type", "")

        # Ack latency — when this seat acks
        if et in ("ack_received", "nack_received") and ss and ss.get("seat_id") == seat_id:
            lat = ae.get("ack_latency_ms")
            if lat is not None:
                ack_latencies.append(lat)

        # Disputes on actions proposed by this seat
        if et == "dispute_opened" and action_id in proposed_actions:
            disputes_involving += 1

        # Rollbacks on actions proposed by this seat
        if et == "action_rolled_back" and action_id in proposed_actions:
            rollbacks += 1

        # Committed actions by this seat
        if et == "action_committed" and action_id in proposed_actions:
            actions_involving += 1

    return CEMetrics(
        mean_ack_latency_ms=_safe_mean(ack_latencies),
        dispute_density=_safe_div(disputes_involving, max(actions_involving, len(proposed_actions))),
        rollback_rate=_safe_div(rollbacks, actions_involving),
    )


def compute_rc_for_seat(
    seat_id: str,
    events: list[dict],
) -> RCMetrics:
    """RC — resolution latencies, chat per dispute, resolution type distribution."""
    resolution_latencies: list[int] = []
    chat_per_dispute: list[int] = []
    resolution_dist: dict[str, int] = {}

    # We attribute a dispute resolution to the seat that opened it
    disputes_opened_by_seat: set[str] = set()

    for ev in events:
        ae = ev.get("action_enrichment")
        ss = ev.get("seat_snapshot")
        et = ev.get("event_type", "")
        if not ae:
            continue
        action_id = ae.get("action_id", "")

        if et == "dispute_opened" and ss and ss.get("seat_id") == seat_id:
            disputes_opened_by_seat.add(action_id)

        if et == "dispute_resolved" and action_id in disputes_opened_by_seat:
            lat = ae.get("resolution_latency_ms")
            if lat is not None:
                resolution_latencies.append(lat)
            chat_count = ae.get("chat_messages_during_resolution", 0)
            chat_per_dispute.append(chat_count or 0)
            res_type = ae.get("resolution_type", "unknown") or "unknown"
            resolution_dist[res_type] = resolution_dist.get(res_type, 0) + 1

    return RCMetrics(
        mean_resolution_latency_ms=_safe_mean(resolution_latencies),
        mean_chat_per_dispute=_safe_mean(chat_per_dispute) or 0.0,
        resolution_distribution=resolution_dist,
    )


def compute_ns_for_seat(
    seat_id: str,
    events: list[dict],
    snapshots: list[dict],
) -> NSMetrics:
    """NS — auto-ack adoption, churn, phase label diversity."""
    # Auto-ack from snapshots
    seat_postures: list[dict[str, bool]] = []
    for snap in snapshots:
        dist = snap.get("seat_auto_ack_distribution", {})
        enabled = dist.get(seat_id, [])
        # Convert list of enabled keys to dict
        posture = {k: True for k in enabled}
        seat_postures.append(posture)

    # Also collect postures from seat_snapshot in ack events
    for ev in events:
        ss = ev.get("seat_snapshot")
        if ss and ss.get("seat_id") == seat_id:
            posture = ss.get("auto_ack_posture")
            if posture:
                seat_postures.append(posture)

    adoption_count = sum(1 for p in seat_postures if any(p.values())) if seat_postures else 0
    adoption_rate = _safe_div(adoption_count, len(seat_postures)) if seat_postures else 0.0

    # Churn: count posture changes between consecutive snapshots
    churn = 0
    for i in range(1, len(seat_postures)):
        if seat_postures[i] != seat_postures[i - 1]:
            churn += 1
    churn_rate = _safe_div(churn, len(seat_postures)) if seat_postures else 0.0

    # Phase label diversity
    phase_labels: set[str] = set()
    for ev in events:
        pl = ev.get("phase_label", "")
        if pl:
            phase_labels.add(pl)

    return NSMetrics(
        auto_ack_adoption_rate=adoption_rate,
        auto_ack_churn=churn_rate,
        phase_label_diversity=len(phase_labels),
    )


def compute_ca_for_seat(
    seat_id: str,
    events: list[dict],
) -> CAMetrics:
    """CA — message lengths, resolution-related chat ratio, messages per dispute."""
    message_lengths: list[int] = []
    resolution_related = 0
    total_messages = 0
    total_disputes = 0

    for ev in events:
        et = ev.get("event_type", "")
        ce = ev.get("chat_enrichment")
        ss = ev.get("seat_snapshot")

        if et == "chat_message" and ce and ce.get("sender_seat_id") == seat_id:
            total_messages += 1
            message_lengths.append(ce.get("message_length_chars", 0))
            if ce.get("is_resolution_related"):
                resolution_related += 1

        if et == "dispute_opened":
            total_disputes += 1

    return CAMetrics(
        mean_message_length_chars=_safe_mean(message_lengths) or 0.0,
        resolution_related_chat_ratio=_safe_div(resolution_related, total_messages),
        messages_per_dispute=_safe_div(total_messages, total_disputes),
    )


def compute_ssc_for_seat(
    seat_id: str,
    events: list[dict],
) -> SSCMetrics:
    """SSC — dispute initiation, involvement, and clustering."""
    total_disputes = 0
    disputes_initiated = 0
    disputes_on_own_actions = 0

    # Build proposer map: action_id -> seat_id from INTENT_CREATED
    proposer_map: dict[str, str] = {}
    for ev in events:
        ae = ev.get("action_enrichment")
        ss = ev.get("seat_snapshot")
        et = ev.get("event_type", "")
        if et == "intent_created" and ae and ss:
            proposer_map[ae.get("action_id", "")] = ss.get("seat_id", "")

    # Track dispute event indices for clustering
    dispute_indices: list[int] = []

    for idx, ev in enumerate(events):
        ae = ev.get("action_enrichment")
        ss = ev.get("seat_snapshot")
        et = ev.get("event_type", "")

        if et == "dispute_opened":
            total_disputes += 1
            action_id = ae.get("action_id", "") if ae else ""

            # Initiated by this seat
            if ss and ss.get("seat_id") == seat_id:
                disputes_initiated += 1
                dispute_indices.append(idx)

            # On actions proposed by this seat
            if proposer_map.get(action_id) == seat_id:
                disputes_on_own_actions += 1

    # Clustering score: fraction of disputes within 10 events of another dispute by same seat
    clustered = 0
    for i in range(1, len(dispute_indices)):
        if dispute_indices[i] - dispute_indices[i - 1] <= 10:
            clustered += 1
    clustering_score = _safe_div(clustered, len(dispute_indices)) if dispute_indices else 0.0

    return SSCMetrics(
        dispute_initiation_rate=_safe_div(disputes_initiated, total_disputes),
        dispute_involvement_rate=_safe_div(disputes_on_own_actions, total_disputes),
        dispute_clustering_score=clustering_score,
    )


# ---------------------------------------------------------------------------
# Session-level computation
# ---------------------------------------------------------------------------


def compute_session_spqan(
    research_events: list[dict],
    identities: dict[str, dict],
    snapshots: list[dict],
) -> SessionSPQAN:
    """Compute SPQ-AN for all seats in a research session.

    Args:
        research_events: List of research event dicts (from NDJSON).
        identities: Dict of identity_hash -> IdentityRecord dict.
        snapshots: List of ResearchSnapshot dicts.
    """
    # Determine session_id and table_id from first event
    session_id = ""
    table_id = ""
    if research_events:
        session_id = research_events[0].get("session_id", "")
        table_id = research_events[0].get("table_id", "")

    # Duration
    duration_ms = 0
    if len(research_events) >= 2:
        first_ts = research_events[0].get("timestamp_utc_ms", 0)
        last_ts = research_events[-1].get("timestamp_utc_ms", 0)
        duration_ms = last_ts - first_ts

    # Build seat list from identities
    seats: list[SeatSPQAN] = []
    for _hash, identity in identities.items():
        sid = identity.get("seat_id", "")
        pseudonym = identity.get("pseudonym_id", "")
        seat_type = identity.get("seat_type", "human")

        seats.append(
            SeatSPQAN(
                seat_id=sid,
                pseudonym_id=pseudonym,
                seat_type=seat_type,
                ce=compute_ce_for_seat(sid, research_events),
                rc=compute_rc_for_seat(sid, research_events),
                ns=compute_ns_for_seat(sid, research_events, snapshots),
                ca=compute_ca_for_seat(sid, research_events),
                ssc=compute_ssc_for_seat(sid, research_events),
            )
        )

    return SessionSPQAN(
        session_id=session_id,
        table_id=table_id,
        seats=seats,
        event_count=len(research_events),
        duration_ms=duration_ms,
    )
