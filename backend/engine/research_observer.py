"""Research observer — parallel instrumentation engine.

Attaches to TableState and enriches gameplay events into a separate
ResearchEventLog. Zero cost when research_mode is off (single `if` branch).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from backend.models.consent import AIParticipationMetadata, ConsentRecord, ConsentTier
from backend.models.event import Event, EventType
from backend.models.research import (
    ActionEnrichment,
    ChatEnrichment,
    IdentityRecord,
    ResearchConfig,
    ResearchEvent,
    ResearchSnapshot,
    RngProvenance,
    SeatMetadataSnapshot,
    VisibilityTransition,
    compute_table_config_hash,
)
from backend.models.table import Table
from backend.models.zone import ZoneVisibility


def compute_identity_hash(identity_id: str, salt: str) -> str:
    return hashlib.sha256(f"{identity_id}{salt}".encode()).hexdigest()


def generate_pseudonym(identity_hash: str) -> str:
    return f"P-{identity_hash[:8]}"


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


class ResearchObserver:
    """Parallel observer that enriches gameplay events for research."""

    def __init__(self, config: ResearchConfig):
        self.config = config
        self.research_log: list[ResearchEvent] = []
        self.identity_store: dict[str, IdentityRecord] = {}  # identity_hash -> record
        self.consent_store: dict[str, ConsentRecord] = {}  # identity_hash -> record
        self.snapshots: list[ResearchSnapshot] = []

        self._previous_event_id: str | None = None
        self._server_seq = 0
        self._action_created_ms: dict[str, int] = {}  # action_id -> timestamp_ms
        self._action_committed_ms: dict[str, int] = {}  # action_id -> timestamp_ms
        self._dispute_opened_ms: dict[str, int] = {}  # action_id -> timestamp_ms
        self._dispute_chat_counts: dict[str, int] = {}  # action_id -> chat count

    # ------------------------------------------------------------------
    # Identity management
    # ------------------------------------------------------------------

    def register_identity(
        self,
        identity_id: str,
        seat_id: str,
        seat_type: str,
        display_name: str,
        ai_metadata: AIParticipationMetadata | None = None,
    ) -> IdentityRecord:
        identity_hash = compute_identity_hash(identity_id, self.config.identity_salt)
        pseudonym_id = generate_pseudonym(identity_hash)

        record = IdentityRecord(
            identity_hash=identity_hash,
            session_id=self.config.session_id,
            seat_id=seat_id,
            seat_type=seat_type,
            pseudonym_id=pseudonym_id,
            ai_model_name=ai_metadata.ai_model_name if ai_metadata else None,
            ai_model_version=ai_metadata.ai_model_version if ai_metadata else None,
            ai_provider=ai_metadata.ai_provider if ai_metadata else None,
            client_type=ai_metadata.client_type if ai_metadata else None,
            client_version=ai_metadata.client_version if ai_metadata else None,
        )
        self.identity_store[identity_hash] = record
        return record

    def get_identity_hash_for_seat(self, seat_id: str) -> str | None:
        for record in self.identity_store.values():
            if record.seat_id == seat_id:
                return record.identity_hash
        return None

    def grant_longitudinal_linking(self, identity_hash: str) -> bool:
        """Grant longitudinal linking for a consented identity.

        Generates a stable longitudinal_link_id derived from the identity
        and a separate longitudinal salt. Only called when the participant
        has explicitly consented to LONGITUDINAL_LINKING.
        """
        record = self.identity_store.get(identity_hash)
        if not record:
            return False
        # Derive link_id from identity_hash + session-independent material
        # so the same person gets the same link_id across sessions with
        # the same identity_salt (researcher-controlled).
        link_id = hashlib.sha256(
            f"longitudinal:{identity_hash}".encode()
        ).hexdigest()[:16]
        record.longitudinal_link_id = f"L-{link_id}"
        record.longitudinal_link_consent = True
        return True

    def revoke_longitudinal_linking(self, identity_hash: str) -> bool:
        """Revoke longitudinal linking — scrub the link_id."""
        record = self.identity_store.get(identity_hash)
        if not record:
            return False
        record.longitudinal_link_id = None
        record.longitudinal_link_consent = False
        return True

    # ------------------------------------------------------------------
    # Core event handling
    # ------------------------------------------------------------------

    def on_event(self, event: Event, table: Table) -> ResearchEvent:
        """Called from TableState.append_event(). Enriches gameplay event."""
        self._server_seq += 1
        now_ms = _now_ms()
        event_id = str(uuid.uuid4())

        # Build seat snapshot for the acting seat
        seat_snapshot = None
        if event.seat_id:
            seat_snapshot = self._build_seat_snapshot(event.seat_id, table)

        # Build enrichments per event type
        action_enrichment = None
        chat_enrichment = None
        rng_provenance = None

        et = event.event_type

        if et == EventType.INTENT_CREATED:
            action_enrichment = self._enrich_intent_created(event, table, now_ms)
        elif et in (EventType.ACK_RECEIVED, EventType.NACK_RECEIVED):
            action_enrichment = self._enrich_ack(event, table, now_ms)
        elif et == EventType.ACTION_COMMITTED:
            action_enrichment, rng_provenance = self._enrich_action_committed(
                event, table, now_ms
            )
        elif et == EventType.ACTION_ROLLED_BACK:
            action_enrichment = self._enrich_action_basic(event)
        elif et == EventType.ACTION_FINALIZED:
            action_enrichment = self._enrich_action_basic(event)
        elif et == EventType.DISPUTE_OPENED:
            action_enrichment = self._enrich_dispute_opened(event, now_ms)
        elif et == EventType.DISPUTE_RESOLVED:
            action_enrichment = self._enrich_dispute_resolved(event, now_ms)
        elif et == EventType.CHAT_MESSAGE:
            chat_enrichment = self._enrich_chat(event, table)

        research_event = ResearchEvent(
            event_id=event_id,
            table_id=event.table_id,
            session_id=self.config.session_id,
            event_type=event.event_type.value,
            timestamp_utc_ms=now_ms,
            server_sequence_number=self._server_seq,
            phase_label=table.phase or "",
            previous_event_id=self._previous_event_id,
            gameplay_seq=event.seq,
            seat_snapshot=seat_snapshot,
            action_enrichment=action_enrichment,
            chat_enrichment=chat_enrichment,
            rng_provenance=rng_provenance,
        )

        self.research_log.append(research_event)
        self._previous_event_id = event_id

        # Auto-snapshot every N events
        if (
            self.config.snapshot_frequency_events > 0
            and self._server_seq % self.config.snapshot_frequency_events == 0
        ):
            self._take_research_snapshot(table)

        return research_event

    # ------------------------------------------------------------------
    # Enrichment builders
    # ------------------------------------------------------------------

    def _enrich_intent_created(
        self, event: Event, table: Table, now_ms: int
    ) -> ActionEnrichment:
        action_id = event.action_id or ""
        self._action_created_ms[action_id] = now_ms

        intent_data = event.data.get("intent", {})
        action_type = intent_data.get("action_type", "")
        action_class = event.data.get("action_class", "")
        card_ids = intent_data.get("card_ids", [])
        source_zone_id = intent_data.get("source_zone_id")
        target_zone_id = intent_data.get("target_zone_id")
        required_acks = event.data.get("required_acks", [])
        is_optimistic = action_class == "optimistic"

        visibility_transition = self._compute_visibility_transition(
            source_zone_id, target_zone_id, table
        )

        return ActionEnrichment(
            action_id=action_id,
            action_type=action_type,
            action_class=action_class,
            visibility_transition=visibility_transition,
            object_ids=card_ids,
            source_zone_id=source_zone_id,
            destination_zone_id=target_zone_id,
            is_optimistic=is_optimistic,
            required_ack_set=list(required_acks) if isinstance(required_acks, (list, set)) else [],
        )

    def _enrich_ack(
        self, event: Event, table: Table, now_ms: int
    ) -> ActionEnrichment:
        action_id = event.action_id or ""
        created_ms = self._action_created_ms.get(action_id)
        ack_latency_ms = (now_ms - created_ms) if created_ms is not None else None

        ack_type = "ack" if event.event_type == EventType.ACK_RECEIVED else "nack"

        # Capture ack posture at time of ack
        ack_posture_at_time = None
        if event.seat_id:
            seat = self._find_seat(event.seat_id, table)
            if seat:
                ack_posture_at_time = seat.ack_posture.model_dump()

        return ActionEnrichment(
            action_id=action_id,
            action_type=event.data.get("action_type", ""),
            action_class=event.data.get("action_class", "consensus"),
            ack_type=ack_type,
            ack_latency_ms=ack_latency_ms,
            ack_posture_at_time=ack_posture_at_time,
        )

    def _enrich_action_committed(
        self, event: Event, table: Table, now_ms: int
    ) -> tuple[ActionEnrichment, RngProvenance | None]:
        action_id = event.action_id or ""
        self._action_committed_ms[action_id] = now_ms

        intent_data = event.data.get("intent", {})
        action_type = intent_data.get("action_type", event.data.get("action_type", ""))
        action_class = event.data.get("action_class", "")
        card_ids = intent_data.get("card_ids", [])
        source_zone_id = intent_data.get("source_zone_id")
        target_zone_id = intent_data.get("target_zone_id")
        is_optimistic = action_class == "optimistic"

        visibility_transition = self._compute_visibility_transition(
            source_zone_id, target_zone_id, table
        )

        enrichment = ActionEnrichment(
            action_id=action_id,
            action_type=action_type,
            action_class=action_class,
            visibility_transition=visibility_transition,
            object_ids=card_ids,
            source_zone_id=source_zone_id,
            destination_zone_id=target_zone_id,
            is_optimistic=is_optimistic,
        )

        # RNG provenance for shuffle actions
        rng_prov = None
        if action_type == "shuffle":
            deck_zone = next(
                (z for z in table.zones if z.zone_id == "deck"), None
            )
            if deck_zone:
                rng_prov = RngProvenance(
                    rng_scheme=self.config.rng_scheme,
                    deck_order_after=list(deck_zone.card_ids),
                )

        return enrichment, rng_prov

    def _enrich_action_basic(self, event: Event) -> ActionEnrichment:
        """Basic enrichment for finalized / rolled_back events."""
        action_id = event.action_id or ""
        intent_data = event.data.get("intent", {})
        return ActionEnrichment(
            action_id=action_id,
            action_type=intent_data.get("action_type", event.data.get("action_type", "")),
            action_class=event.data.get("action_class", ""),
        )

    def _enrich_dispute_opened(
        self, event: Event, now_ms: int
    ) -> ActionEnrichment:
        action_id = event.action_id or ""
        self._dispute_opened_ms[action_id] = now_ms
        self._dispute_chat_counts[action_id] = 0

        # Dispute latency: time from action creation or commit
        created_ms = self._action_created_ms.get(action_id)
        committed_ms = self._action_committed_ms.get(action_id)
        ref_ms = committed_ms or created_ms
        dispute_latency_ms = (now_ms - ref_ms) if ref_ms is not None else None

        # For optimistic disputes, compute remaining window
        dispute_window_ms_remaining = None
        objection_deadline = event.data.get("objection_deadline")
        if objection_deadline:
            # objection_deadline is ISO string or epoch — handle both
            try:
                if isinstance(objection_deadline, (int, float)):
                    deadline_ms = int(objection_deadline * 1000)
                else:
                    dt = datetime.fromisoformat(str(objection_deadline))
                    deadline_ms = int(dt.timestamp() * 1000)
                dispute_window_ms_remaining = max(0, deadline_ms - now_ms)
            except (ValueError, TypeError):
                pass

        return ActionEnrichment(
            action_id=action_id,
            action_type=event.data.get("action_type", ""),
            action_class=event.data.get("action_class", ""),
            dispute_reason_tag=event.data.get("reason"),
            dispute_latency_ms=dispute_latency_ms,
            dispute_window_ms_remaining=dispute_window_ms_remaining,
        )

    def _enrich_dispute_resolved(
        self, event: Event, now_ms: int
    ) -> ActionEnrichment:
        action_id = event.action_id or event.data.get("action_id", "")
        opened_ms = self._dispute_opened_ms.get(action_id)
        resolution_latency_ms = (now_ms - opened_ms) if opened_ms is not None else None
        chat_count = self._dispute_chat_counts.get(action_id, 0)

        return ActionEnrichment(
            action_id=action_id,
            action_type=event.data.get("action_type", ""),
            action_class=event.data.get("action_class", ""),
            resolution_type=event.data.get("resolution"),
            resolution_latency_ms=resolution_latency_ms,
            chat_messages_during_resolution=chat_count,
        )

    def _enrich_chat(self, event: Event, table: Table) -> ChatEnrichment:
        message_id = event.data.get("message_id", "")
        sender_seat_id = event.seat_id or ""
        text = event.data.get("text", "")
        message_length_chars = len(text)

        # Check if dispute is active — link chat to disputed action
        in_response_to_action_id = None
        is_resolution_related = False
        if table.dispute_active and table.dispute_action_id:
            is_resolution_related = True
            in_response_to_action_id = table.dispute_action_id
            # Increment dispute chat counter
            if table.dispute_action_id in self._dispute_chat_counts:
                self._dispute_chat_counts[table.dispute_action_id] += 1

        return ChatEnrichment(
            chat_message_id=message_id,
            sender_seat_id=sender_seat_id,
            message_length_chars=message_length_chars,
            in_response_to_action_id=in_response_to_action_id,
            is_resolution_related=is_resolution_related,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_seat_snapshot(
        self, seat_id: str, table: Table
    ) -> SeatMetadataSnapshot | None:
        seat = self._find_seat(seat_id, table)
        if not seat:
            return None

        identity_hash = self.get_identity_hash_for_seat(seat_id)
        pseudonym_id = generate_pseudonym(identity_hash) if identity_hash else f"P-{seat_id}"

        return SeatMetadataSnapshot(
            seat_id=seat_id,
            seat_type=seat.player_kind.value,
            display_name=seat.display_name,
            pseudonym_id=pseudonym_id,
            presence_state=seat.presence.value,
            auto_ack_posture=seat.ack_posture.model_dump(),
        )

    def _find_seat(self, seat_id: str, table: Table):
        return next((s for s in table.seats if s.seat_id == seat_id), None)

    def _compute_visibility_transition(
        self,
        source_zone_id: str | None,
        target_zone_id: str | None,
        table: Table,
    ) -> VisibilityTransition:
        if not source_zone_id or not target_zone_id:
            return VisibilityTransition.NONE

        source_zone = next((z for z in table.zones if z.zone_id == source_zone_id), None)
        target_zone = next((z for z in table.zones if z.zone_id == target_zone_id), None)

        if not source_zone or not target_zone:
            return VisibilityTransition.NONE

        src_private = source_zone.visibility == ZoneVisibility.PRIVATE
        dst_private = target_zone.visibility == ZoneVisibility.PRIVATE

        if src_private and not dst_private:
            return VisibilityTransition.PRIVATE_TO_PUBLIC
        if not src_private and dst_private:
            return VisibilityTransition.PUBLIC_TO_PRIVATE
        if src_private and dst_private:
            return VisibilityTransition.PRIVATE_TO_PRIVATE
        return VisibilityTransition.NONE

    # ------------------------------------------------------------------
    # Research snapshots
    # ------------------------------------------------------------------

    def _take_research_snapshot(self, table: Table) -> ResearchSnapshot:
        from backend.engine.consensus import _pending_actions

        # Build seat auto-ack distribution
        seat_ack_dist: dict[str, list[str]] = {}
        for seat in table.seats:
            posture = seat.ack_posture.model_dump()
            enabled = [k for k, v in posture.items() if v]
            seat_ack_dist[seat.seat_id] = enabled

        pending_count = len(_pending_actions.get(table.table_id, {}))

        config_hash = compute_table_config_hash(
            settings_dump=table.settings.model_dump(),
            deck_recipe=table.deck_recipe.value if hasattr(table.deck_recipe, "value") else str(table.deck_recipe),
            max_seats=table.settings.max_seats,
            ai_min_action_delay_ms=self.config.ai_min_action_delay_ms,
            ai_latency_simulation_enabled=self.config.ai_latency_simulation_enabled,
        )

        snapshot = ResearchSnapshot(
            snapshot_id=str(uuid.uuid4()),
            session_id=self.config.session_id,
            server_sequence_number=self._server_seq,
            timestamp_utc_ms=_now_ms(),
            active_phase_label=table.phase or "",
            seat_auto_ack_distribution=seat_ack_dist,
            pending_actions_count=pending_count,
            dispute_active=table.dispute_active,
            table_config_hash=config_hash,
        )
        self.snapshots.append(snapshot)
        return snapshot

    # ------------------------------------------------------------------
    # Data deletion (A.10)
    # ------------------------------------------------------------------

    def delete_session_data(self) -> int:
        """Delete all research data for this session. Returns count deleted."""
        count = len(self.research_log) + len(self.snapshots) + len(self.identity_store)
        self.research_log.clear()
        self.snapshots.clear()
        self.identity_store.clear()
        self.consent_store.clear()
        self._previous_event_id = None
        self._server_seq = 0
        self._action_created_ms.clear()
        self._action_committed_ms.clear()
        self._dispute_opened_ms.clear()
        self._dispute_chat_counts.clear()
        return count

    def delete_identity_data(self, identity_hash: str) -> int:
        """Purge all data for a specific identity. Returns count deleted."""
        count = 0

        # Remove identity record
        if identity_hash in self.identity_store:
            record = self.identity_store.pop(identity_hash)
            count += 1
            seat_id = record.seat_id

            # Remove research events where this seat acted
            before = len(self.research_log)
            self.research_log = [
                e for e in self.research_log
                if not (e.seat_snapshot and e.seat_snapshot.seat_id == seat_id)
            ]
            count += before - len(self.research_log)

        # Remove consent record
        if identity_hash in self.consent_store:
            self.consent_store.pop(identity_hash)
            count += 1

        return count
