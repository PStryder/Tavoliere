"""Tests for research instrumentation layer (Appendix A)."""

import uuid

import pytest
from httpx import AsyncClient

from backend.engine.research_observer import (
    ResearchObserver,
    compute_identity_hash,
    generate_pseudonym,
)
from backend.engine.state import TableState, get_or_create_state
from backend.models.action import ActionClass, ActionType
from backend.models.consent import AIParticipationMetadata, ConsentTier
from backend.models.event import EventType
from backend.models.research import (
    RESEARCH_ETHICAL_BOUNDARY,
    ResearchConfig,
    ResearchEvent,
    VisibilityTransition,
    compute_table_config_hash,
)
from backend.models.seat import AckPosture, PlayerKind, Presence, Seat
from backend.models.table import Table, TableSettings
from backend.models.zone import Zone, ZoneKind, ZoneVisibility
from backend.tests.conftest import auth_header


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

def _make_research_config() -> ResearchConfig:
    return ResearchConfig(
        session_id=str(uuid.uuid4()),
        identity_salt="deadbeef" * 4,
    )


def _make_table(research_mode: bool = True) -> Table:
    from datetime import datetime, timezone

    return Table(
        table_id=str(uuid.uuid4()),
        display_name="Test Table",
        deck_recipe="standard_52",
        research_mode=research_mode,
        created_at=datetime.now(timezone.utc),
        zones=[
            Zone(zone_id="deck", kind=ZoneKind.DECK, visibility=ZoneVisibility.PUBLIC,
                 card_ids=["c1", "c2", "c3"]),
            Zone(zone_id="discard", kind=ZoneKind.DISCARD, visibility=ZoneVisibility.PUBLIC),
            Zone(zone_id="center", kind=ZoneKind.CENTER, visibility=ZoneVisibility.PUBLIC),
            Zone(zone_id="hand_seat_0", kind=ZoneKind.HAND, visibility=ZoneVisibility.PRIVATE,
                 owner_seat_id="seat_0", card_ids=["c4", "c5"]),
            Zone(zone_id="meld_seat_0", kind=ZoneKind.MELD, visibility=ZoneVisibility.SEAT_PUBLIC,
                 owner_seat_id="seat_0"),
        ],
        seats=[
            Seat(seat_id="seat_0", display_name="Alice", identity_id="id_alice",
                 player_kind=PlayerKind.HUMAN, presence=Presence.ACTIVE),
            Seat(seat_id="seat_1", display_name="BotBob", identity_id="id_bob",
                 player_kind=PlayerKind.AI, presence=Presence.ACTIVE),
        ],
    )


def _make_state_with_observer():
    table = _make_table()
    config = _make_research_config()
    observer = ResearchObserver(config)
    state = TableState(table)
    state.attach_research(observer)

    # Register identities
    observer.register_identity("id_alice", "seat_0", "human", "Alice")
    observer.register_identity(
        "id_bob", "seat_1", "ai", "BotBob",
        ai_metadata=AIParticipationMetadata(
            ai_model_name="gpt-4", ai_model_version="0613", ai_provider="openai",
        ),
    )
    return state, observer, table


# -----------------------------------------------------------------------
# Phase R1: Model validation tests
# -----------------------------------------------------------------------

class TestResearchModels:
    def test_research_config_defaults(self):
        config = _make_research_config()
        assert config.research_mode is True
        assert config.research_mode_version == "0.1.0"
        assert config.snapshot_frequency_events == 50
        assert config.rng_scheme == "server_authoritative"

    def test_visibility_transition_enum(self):
        assert VisibilityTransition.NONE.value == "none"
        assert VisibilityTransition.PRIVATE_TO_PUBLIC.value == "private_to_public"

    def test_consent_tier_enum(self):
        assert ConsentTier.RESEARCH_LOGGING.value == "research_logging"
        assert len(ConsentTier) == 7

    def test_table_research_mode_defaults(self):
        table = _make_table(research_mode=False)
        assert table.research_mode is False
        assert table.research_mode_version == "0.1.0"

    def test_ai_participation_metadata(self):
        meta = AIParticipationMetadata(
            ai_model_name="claude-3", ai_provider="anthropic",
        )
        assert meta.ai_model_name == "claude-3"
        assert meta.ai_disclosed_to_players is False


# -----------------------------------------------------------------------
# Phase R2: Observer unit tests
# -----------------------------------------------------------------------

class TestIdentity:
    def test_identity_hash_deterministic(self):
        h1 = compute_identity_hash("alice", "salt123")
        h2 = compute_identity_hash("alice", "salt123")
        assert h1 == h2

    def test_identity_hash_different_salt(self):
        h1 = compute_identity_hash("alice", "salt1")
        h2 = compute_identity_hash("alice", "salt2")
        assert h1 != h2

    def test_pseudonym_format(self):
        h = compute_identity_hash("alice", "salt")
        p = generate_pseudonym(h)
        assert p.startswith("P-")
        assert len(p) == 10  # "P-" + 8 hex chars

    def test_register_identity(self):
        _, observer, _ = _make_state_with_observer()
        assert len(observer.identity_store) == 2
        # Check Alice's record
        alice_hash = compute_identity_hash("id_alice", observer.config.identity_salt)
        record = observer.identity_store[alice_hash]
        assert record.seat_id == "seat_0"
        assert record.seat_type == "human"
        assert record.ai_model_name is None

    def test_register_ai_identity(self):
        _, observer, _ = _make_state_with_observer()
        bob_hash = compute_identity_hash("id_bob", observer.config.identity_salt)
        record = observer.identity_store[bob_hash]
        assert record.seat_type == "ai"
        assert record.ai_model_name == "gpt-4"
        assert record.ai_provider == "openai"


class TestObserverEvents:
    def test_zero_cost_when_off(self):
        """Research mode off = no observer, no overhead."""
        table = _make_table(research_mode=False)
        state = TableState(table)
        assert state._research_observer is None
        event = state.append_event(EventType.TABLE_CREATED)
        assert event.seq == 1
        # No research events

    def test_basic_event_enrichment(self):
        state, observer, table = _make_state_with_observer()
        event = state.append_event(EventType.TABLE_CREATED, seat_id="seat_0")
        assert len(observer.research_log) == 1
        re = observer.research_log[0]
        assert re.event_type == "table_created"
        assert re.gameplay_seq == event.seq
        assert re.session_id == observer.config.session_id
        assert re.phase_label == ""
        assert re.seat_snapshot is not None
        assert re.seat_snapshot.seat_id == "seat_0"

    def test_causality_chain(self):
        state, observer, _ = _make_state_with_observer()
        state.append_event(EventType.TABLE_CREATED)
        state.append_event(EventType.SEAT_JOINED, seat_id="seat_0")
        state.append_event(EventType.SEAT_JOINED, seat_id="seat_1")

        assert observer.research_log[0].previous_event_id is None
        assert observer.research_log[1].previous_event_id == observer.research_log[0].event_id
        assert observer.research_log[2].previous_event_id == observer.research_log[1].event_id

    def test_intent_created_enrichment(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(
            EventType.INTENT_CREATED,
            seat_id="seat_0",
            action_id="act_1",
            data={
                "intent": {
                    "action_type": "move_card",
                    "card_ids": ["c4"],
                    "source_zone_id": "hand_seat_0",
                    "target_zone_id": "center",
                },
                "action_class": "consensus",
                "required_acks": ["seat_1"],
            },
        )
        re = observer.research_log[0]
        ae = re.action_enrichment
        assert ae is not None
        assert ae.action_id == "act_1"
        assert ae.action_type == "move_card"
        assert ae.action_class == "consensus"
        assert ae.visibility_transition == VisibilityTransition.PRIVATE_TO_PUBLIC
        assert ae.object_ids == ["c4"]
        assert ae.source_zone_id == "hand_seat_0"
        assert ae.destination_zone_id == "center"
        assert ae.required_ack_set == ["seat_1"]

    def test_ack_latency(self):
        state, observer, table = _make_state_with_observer()
        # Create intent
        state.append_event(
            EventType.INTENT_CREATED, seat_id="seat_0", action_id="act_1",
            data={"intent": {"action_type": "move_card"}, "action_class": "consensus"},
        )
        # ACK
        state.append_event(
            EventType.ACK_RECEIVED, seat_id="seat_1", action_id="act_1",
            data={"action_type": "move_card", "action_class": "consensus"},
        )
        ack_event = observer.research_log[1]
        ae = ack_event.action_enrichment
        assert ae.ack_type == "ack"
        assert ae.ack_latency_ms is not None
        assert ae.ack_latency_ms >= 0
        assert ae.ack_posture_at_time is not None

    def test_nack_enrichment(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(
            EventType.INTENT_CREATED, seat_id="seat_0", action_id="act_1",
            data={"intent": {"action_type": "move_card"}, "action_class": "consensus"},
        )
        state.append_event(
            EventType.NACK_RECEIVED, seat_id="seat_1", action_id="act_1",
            data={"action_type": "move_card", "action_class": "consensus"},
        )
        nack_event = observer.research_log[1]
        assert nack_event.action_enrichment.ack_type == "nack"

    def test_action_committed_enrichment(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(
            EventType.ACTION_COMMITTED, seat_id="seat_0", action_id="act_1",
            data={
                "intent": {
                    "action_type": "move_card",
                    "card_ids": ["c4"],
                    "source_zone_id": "hand_seat_0",
                    "target_zone_id": "center",
                },
                "action_class": "consensus",
            },
        )
        re = observer.research_log[0]
        assert re.action_enrichment is not None
        assert re.action_enrichment.action_type == "move_card"
        assert re.rng_provenance is None  # Not a shuffle

    def test_shuffle_rng_provenance(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(
            EventType.ACTION_COMMITTED, seat_id="seat_0", action_id="act_1",
            data={
                "intent": {"action_type": "shuffle"},
                "action_class": "unilateral",
            },
        )
        re = observer.research_log[0]
        assert re.rng_provenance is not None
        assert re.rng_provenance.rng_scheme == "server_authoritative"
        assert re.rng_provenance.deck_order_after == ["c1", "c2", "c3"]

    def test_dispute_opened_enrichment(self):
        state, observer, table = _make_state_with_observer()
        # Create and commit an action first
        state.append_event(
            EventType.INTENT_CREATED, seat_id="seat_0", action_id="act_1",
            data={"intent": {"action_type": "move_card"}, "action_class": "consensus"},
        )
        state.append_event(
            EventType.DISPUTE_OPENED, seat_id="seat_1", action_id="act_1",
            data={"reason": "rules", "action_type": "move_card"},
        )
        re = observer.research_log[1]
        ae = re.action_enrichment
        assert ae.dispute_reason_tag == "rules"
        assert ae.dispute_latency_ms is not None
        assert ae.dispute_latency_ms >= 0

    def test_dispute_resolved_with_chat_count(self):
        state, observer, table = _make_state_with_observer()
        table.dispute_active = True
        table.dispute_action_id = "act_1"

        # Simulate dispute opened
        state.append_event(
            EventType.DISPUTE_OPENED, seat_id="seat_1", action_id="act_1",
            data={"reason": "rules"},
        )
        # Chat during dispute
        state.append_event(
            EventType.CHAT_MESSAGE, seat_id="seat_0",
            data={"message_id": "msg1", "text": "I disagree"},
        )
        state.append_event(
            EventType.CHAT_MESSAGE, seat_id="seat_1",
            data={"message_id": "msg2", "text": "Let me explain"},
        )
        # Resolve dispute
        table.dispute_active = False
        state.append_event(
            EventType.DISPUTE_RESOLVED, action_id="act_1",
            data={"resolution": "revised", "action_id": "act_1"},
        )

        resolved = observer.research_log[3]
        ae = resolved.action_enrichment
        assert ae.resolution_type == "revised"
        assert ae.chat_messages_during_resolution == 2

    def test_chat_enrichment_basic(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(
            EventType.CHAT_MESSAGE, seat_id="seat_0",
            data={"message_id": "msg1", "text": "Hello world"},
        )
        re = observer.research_log[0]
        ce = re.chat_enrichment
        assert ce is not None
        assert ce.chat_message_id == "msg1"
        assert ce.sender_seat_id == "seat_0"
        assert ce.message_length_chars == 11
        assert ce.is_resolution_related is False

    def test_chat_during_dispute_linked(self):
        state, observer, table = _make_state_with_observer()
        table.dispute_active = True
        table.dispute_action_id = "act_1"
        observer._dispute_chat_counts["act_1"] = 0

        state.append_event(
            EventType.CHAT_MESSAGE, seat_id="seat_0",
            data={"message_id": "msg1", "text": "About the dispute"},
        )
        re = observer.research_log[0]
        ce = re.chat_enrichment
        assert ce.is_resolution_related is True
        assert ce.in_response_to_action_id == "act_1"

    def test_seat_snapshot(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(EventType.PRESENCE_CHANGED, seat_id="seat_0")
        re = observer.research_log[0]
        ss = re.seat_snapshot
        assert ss is not None
        assert ss.seat_id == "seat_0"
        assert ss.seat_type == "human"
        assert ss.display_name == "Alice"
        assert ss.presence_state == "active"
        assert isinstance(ss.auto_ack_posture, dict)

    def test_no_seat_snapshot_when_no_seat_id(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(EventType.TABLE_CREATED)
        re = observer.research_log[0]
        assert re.seat_snapshot is None

    def test_action_finalized_enrichment(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(
            EventType.ACTION_FINALIZED, action_id="act_1",
            data={"action_type": "set_phase", "action_class": "optimistic"},
        )
        re = observer.research_log[0]
        assert re.action_enrichment is not None
        assert re.action_enrichment.action_type == "set_phase"

    def test_action_rolled_back_enrichment(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(
            EventType.ACTION_ROLLED_BACK, action_id="act_1",
            data={"intent": {"action_type": "set_phase"}, "action_class": "optimistic"},
        )
        re = observer.research_log[0]
        assert re.action_enrichment is not None
        assert re.action_enrichment.action_type == "set_phase"

    def test_phase_label_captured(self):
        state, observer, table = _make_state_with_observer()
        table.phase = "dealing"
        state.append_event(EventType.PHASE_CHANGED, seat_id="seat_0")
        re = observer.research_log[0]
        assert re.phase_label == "dealing"


class TestVisibilityTransition:
    def test_private_to_public(self):
        state, observer, table = _make_state_with_observer()
        vt = observer._compute_visibility_transition("hand_seat_0", "center", table)
        assert vt == VisibilityTransition.PRIVATE_TO_PUBLIC

    def test_public_to_private(self):
        state, observer, table = _make_state_with_observer()
        vt = observer._compute_visibility_transition("deck", "hand_seat_0", table)
        assert vt == VisibilityTransition.PUBLIC_TO_PRIVATE

    def test_public_to_public(self):
        state, observer, table = _make_state_with_observer()
        vt = observer._compute_visibility_transition("deck", "center", table)
        assert vt == VisibilityTransition.NONE

    def test_no_zones(self):
        state, observer, table = _make_state_with_observer()
        vt = observer._compute_visibility_transition(None, None, table)
        assert vt == VisibilityTransition.NONE

    def test_unknown_zone(self):
        state, observer, table = _make_state_with_observer()
        vt = observer._compute_visibility_transition("nonexistent", "center", table)
        assert vt == VisibilityTransition.NONE


class TestResearchSnapshots:
    def test_auto_snapshot(self):
        state, observer, table = _make_state_with_observer()
        observer.config.snapshot_frequency_events = 3

        for i in range(6):
            state.append_event(EventType.PHASE_CHANGED, seat_id="seat_0")

        assert len(observer.snapshots) == 2
        assert observer.snapshots[0].server_sequence_number == 3
        assert observer.snapshots[1].server_sequence_number == 6

    def test_snapshot_content(self):
        state, observer, table = _make_state_with_observer()
        observer.config.snapshot_frequency_events = 1
        table.phase = "playing"

        state.append_event(EventType.PHASE_CHANGED, seat_id="seat_0")

        snap = observer.snapshots[0]
        assert snap.active_phase_label == "playing"
        assert snap.session_id == observer.config.session_id
        assert "seat_0" in snap.seat_auto_ack_distribution
        assert snap.dispute_active is False

    def test_no_snapshot_when_frequency_zero(self):
        state, observer, table = _make_state_with_observer()
        observer.config.snapshot_frequency_events = 0
        for i in range(10):
            state.append_event(EventType.PHASE_CHANGED, seat_id="seat_0")
        assert len(observer.snapshots) == 0


class TestDataDeletion:
    def test_delete_session_data(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(EventType.TABLE_CREATED)
        state.append_event(EventType.SEAT_JOINED, seat_id="seat_0")

        assert len(observer.research_log) == 2
        assert len(observer.identity_store) == 2

        count = observer.delete_session_data()
        assert count > 0
        assert len(observer.research_log) == 0
        assert len(observer.identity_store) == 0
        assert len(observer.snapshots) == 0

    def test_delete_identity_data(self):
        state, observer, table = _make_state_with_observer()
        state.append_event(EventType.CHAT_MESSAGE, seat_id="seat_0",
                           data={"message_id": "m1", "text": "hi"})
        state.append_event(EventType.CHAT_MESSAGE, seat_id="seat_1",
                           data={"message_id": "m2", "text": "hey"})

        alice_hash = compute_identity_hash("id_alice", observer.config.identity_salt)
        count = observer.delete_identity_data(alice_hash)
        assert count >= 2  # identity record + events

        # Alice's events removed, Bob's remain
        assert all(
            e.seat_snapshot is None or e.seat_snapshot.seat_id != "seat_0"
            for e in observer.research_log
        )
        assert alice_hash not in observer.identity_store

    def test_delete_unknown_identity(self):
        _, observer, _ = _make_state_with_observer()
        count = observer.delete_identity_data("nonexistent_hash")
        assert count == 0


# -----------------------------------------------------------------------
# Longitudinal identity linking
# -----------------------------------------------------------------------

class TestLongitudinalLinking:
    def test_no_link_by_default(self):
        _, observer, _ = _make_state_with_observer()
        alice_hash = compute_identity_hash("id_alice", observer.config.identity_salt)
        record = observer.identity_store[alice_hash]
        assert record.longitudinal_link_id is None
        assert record.longitudinal_link_consent is False

    def test_grant_longitudinal_linking(self):
        _, observer, _ = _make_state_with_observer()
        alice_hash = compute_identity_hash("id_alice", observer.config.identity_salt)
        assert observer.grant_longitudinal_linking(alice_hash) is True
        record = observer.identity_store[alice_hash]
        assert record.longitudinal_link_consent is True
        assert record.longitudinal_link_id is not None
        assert record.longitudinal_link_id.startswith("L-")
        assert len(record.longitudinal_link_id) == 18  # "L-" + 16 hex chars

    def test_revoke_longitudinal_linking(self):
        _, observer, _ = _make_state_with_observer()
        alice_hash = compute_identity_hash("id_alice", observer.config.identity_salt)
        observer.grant_longitudinal_linking(alice_hash)
        assert observer.revoke_longitudinal_linking(alice_hash) is True
        record = observer.identity_store[alice_hash]
        assert record.longitudinal_link_id is None
        assert record.longitudinal_link_consent is False

    def test_link_id_deterministic(self):
        """Same identity_hash produces same link_id (reproducible across calls)."""
        _, observer, _ = _make_state_with_observer()
        alice_hash = compute_identity_hash("id_alice", observer.config.identity_salt)
        observer.grant_longitudinal_linking(alice_hash)
        link1 = observer.identity_store[alice_hash].longitudinal_link_id
        # Revoke and re-grant
        observer.revoke_longitudinal_linking(alice_hash)
        observer.grant_longitudinal_linking(alice_hash)
        link2 = observer.identity_store[alice_hash].longitudinal_link_id
        assert link1 == link2

    def test_different_identities_get_different_links(self):
        _, observer, _ = _make_state_with_observer()
        alice_hash = compute_identity_hash("id_alice", observer.config.identity_salt)
        bob_hash = compute_identity_hash("id_bob", observer.config.identity_salt)
        observer.grant_longitudinal_linking(alice_hash)
        observer.grant_longitudinal_linking(bob_hash)
        assert (observer.identity_store[alice_hash].longitudinal_link_id
                != observer.identity_store[bob_hash].longitudinal_link_id)

    def test_grant_unknown_identity_returns_false(self):
        _, observer, _ = _make_state_with_observer()
        assert observer.grant_longitudinal_linking("nonexistent") is False

    def test_sessions_not_linkable_without_consent(self):
        """Without longitudinal consent, no link_id exists."""
        _, observer, _ = _make_state_with_observer()
        for record in observer.identity_store.values():
            assert record.longitudinal_link_id is None


# -----------------------------------------------------------------------
# AI latency simulation metadata
# -----------------------------------------------------------------------

class TestAILatencySimulation:
    def test_config_defaults(self):
        config = _make_research_config()
        assert config.ai_min_action_delay_ms is None
        assert config.ai_latency_simulation_enabled is False

    def test_config_with_simulation(self):
        config = ResearchConfig(
            session_id="test",
            identity_salt="salt",
            ai_min_action_delay_ms=500,
            ai_latency_simulation_enabled=True,
        )
        assert config.ai_min_action_delay_ms == 500
        assert config.ai_latency_simulation_enabled is True


# -----------------------------------------------------------------------
# Table configuration hash
# -----------------------------------------------------------------------

class TestTableConfigHash:
    def test_hash_deterministic(self):
        settings = {"objection_window_s": 3.0, "shuffle_is_optimistic": False,
                     "min_action_delay_ms": 0, "phase_locked": False,
                     "dispute_cooldown_s": 3.0, "phase_change_cooldown_s": 10.0,
                     "shuffle_cooldown_s": 15.0, "intent_rate_max_count": 3,
                     "intent_rate_window_s": 5.0, "zone_create_cooldown_s": 30.0}
        h1 = compute_table_config_hash(settings, "standard_52", 4)
        h2 = compute_table_config_hash(settings, "standard_52", 4)
        assert h1 == h2

    def test_hash_changes_with_settings(self):
        settings_a = {"objection_window_s": 3.0, "shuffle_is_optimistic": False,
                       "min_action_delay_ms": 0, "phase_locked": False,
                       "dispute_cooldown_s": 3.0, "phase_change_cooldown_s": 10.0,
                       "shuffle_cooldown_s": 15.0, "intent_rate_max_count": 3,
                       "intent_rate_window_s": 5.0, "zone_create_cooldown_s": 30.0}
        settings_b = dict(settings_a)
        settings_b["objection_window_s"] = 5.0
        h1 = compute_table_config_hash(settings_a, "standard_52", 4)
        h2 = compute_table_config_hash(settings_b, "standard_52", 4)
        assert h1 != h2

    def test_hash_changes_with_deck_recipe(self):
        settings = {"objection_window_s": 3.0}
        h1 = compute_table_config_hash(settings, "standard_52", 4)
        h2 = compute_table_config_hash(settings, "euchre_24", 4)
        assert h1 != h2

    def test_hash_changes_with_ai_pacing(self):
        settings = {"objection_window_s": 3.0}
        h1 = compute_table_config_hash(settings, "standard_52", 4,
                                        ai_min_action_delay_ms=None,
                                        ai_latency_simulation_enabled=False)
        h2 = compute_table_config_hash(settings, "standard_52", 4,
                                        ai_min_action_delay_ms=500,
                                        ai_latency_simulation_enabled=True)
        assert h1 != h2

    def test_hash_is_hex(self):
        h = compute_table_config_hash({}, "standard_52", 4)
        assert len(h) == 64  # SHA256 hex digest
        int(h, 16)  # Should not raise

    def test_snapshot_includes_config_hash(self):
        state, observer, table = _make_state_with_observer()
        observer.config.snapshot_frequency_events = 1
        state.append_event(EventType.TABLE_CREATED)
        snap = observer.snapshots[0]
        assert snap.table_config_hash is not None
        assert len(snap.table_config_hash) == 64

    def test_config_hash_stored_at_creation(self):
        """ResearchConfig receives table_config_hash when created via table_manager."""
        config = ResearchConfig(
            session_id="test",
            identity_salt="salt",
            table_config_hash="ab" * 32,
        )
        assert config.table_config_hash == "ab" * 32


# -----------------------------------------------------------------------
# Ethical boundary
# -----------------------------------------------------------------------

class TestEthicalBoundary:
    def test_constant_exists(self):
        assert RESEARCH_ETHICAL_BOUNDARY is not None
        assert "manipulate" in RESEARCH_ETHICAL_BOUNDARY
        assert "consent" in RESEARCH_ETHICAL_BOUNDARY

    def test_constant_accessible_from_module(self):
        from backend.models.research import RESEARCH_ETHICAL_BOUNDARY as eb
        assert eb.startswith("The Tavoliere research corpus")


# -----------------------------------------------------------------------
# Phase R3: Integration through HTTP
# -----------------------------------------------------------------------

class TestResearchTableIntegration:
    @pytest.mark.anyio
    async def test_create_research_table(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={
                "display_name": "Research Game",
                "deck_recipe": "standard_52",
                "research_mode": True,
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["research_mode"] is True

    @pytest.mark.anyio
    async def test_create_normal_table_no_research(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={
                "display_name": "Normal Game",
                "deck_recipe": "standard_52",
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["research_mode"] is False

    @pytest.mark.anyio
    async def test_join_research_table_registers_identity(self, client: AsyncClient, bootstrapped):
        token0, token1 = bootstrapped["tokens"][0], bootstrapped["tokens"][1]

        # Create research table
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Research Game", "deck_recipe": "standard_52", "research_mode": True},
            headers=auth_header(token0),
        )
        table_id = resp.json()["table_id"]

        # Join as host
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Alice"},
            headers=auth_header(token0),
        )
        # Join as AI with metadata
        await client.post(
            f"/api/tables/{table_id}/join",
            json={
                "display_name": "BotBob",
                "ai_metadata": {
                    "ai_model_name": "gpt-4",
                    "ai_provider": "openai",
                },
            },
            headers=auth_header(token1),
        )

        # Verify identities registered via research config endpoint
        resp = await client.get(
            f"/api/tables/{table_id}/research/config",
            headers=auth_header(token0),
        )
        assert resp.status_code == 200
        config = resp.json()
        assert config["research_mode"] is True
        assert "session_id" in config

    @pytest.mark.anyio
    async def test_join_normal_table_with_ai_metadata_ignored(self, client: AsyncClient, bootstrapped):
        """AI metadata on non-research table is accepted but no observer runs."""
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Normal", "deck_recipe": "standard_52"},
            headers=auth_header(token),
        )
        table_id = resp.json()["table_id"]

        resp = await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Alice", "ai_metadata": {"ai_model_name": "test"}},
            headers=auth_header(token),
        )
        assert resp.status_code == 200


# -----------------------------------------------------------------------
# Phase R4: Research API + Consent endpoints
# -----------------------------------------------------------------------

class TestResearchAPI:
    async def _setup_research_table(self, client, bootstrapped):
        token0, token1 = bootstrapped["tokens"][0], bootstrapped["tokens"][1]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Research", "deck_recipe": "standard_52", "research_mode": True},
            headers=auth_header(token0),
        )
        table_id = resp.json()["table_id"]

        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Alice"},
            headers=auth_header(token0),
        )
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Bob"},
            headers=auth_header(token1),
        )
        return table_id, token0, token1

    @pytest.mark.anyio
    async def test_get_research_config(self, client: AsyncClient, bootstrapped):
        table_id, host_token, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.get(
            f"/api/tables/{table_id}/research/config",
            headers=auth_header(host_token),
        )
        assert resp.status_code == 200
        assert resp.json()["research_mode"] is True

    @pytest.mark.anyio
    async def test_non_host_cannot_access_research(self, client: AsyncClient, bootstrapped):
        table_id, _, non_host_token = await self._setup_research_table(client, bootstrapped)
        resp = await client.get(
            f"/api/tables/{table_id}/research/config",
            headers=auth_header(non_host_token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_research_events_empty(self, client: AsyncClient, bootstrapped):
        table_id, host_token, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.get(
            f"/api/tables/{table_id}/research/events",
            headers=auth_header(host_token),
        )
        assert resp.status_code == 200
        # Events exist from join operations
        assert isinstance(resp.json(), list)

    @pytest.mark.anyio
    async def test_research_events_filter_by_type(self, client: AsyncClient, bootstrapped):
        table_id, host_token, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.get(
            f"/api/tables/{table_id}/research/events",
            params={"event_type": "seat_joined"},
            headers=auth_header(host_token),
        )
        assert resp.status_code == 200
        events = resp.json()
        for e in events:
            assert e["event_type"] == "seat_joined"

    @pytest.mark.anyio
    async def test_research_events_ndjson_export(self, client: AsyncClient, bootstrapped):
        table_id, host_token, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.get(
            f"/api/tables/{table_id}/research/events/export",
            headers=auth_header(host_token),
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_identities_export(self, client: AsyncClient, bootstrapped):
        table_id, host_token, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.get(
            f"/api/tables/{table_id}/research/identities",
            headers=auth_header(host_token),
        )
        assert resp.status_code == 200
        identities = resp.json()
        assert len(identities) == 2
        # Verify identity fields
        for ident in identities:
            assert "identity_hash" in ident
            assert "pseudonym_id" in ident
            assert ident["pseudonym_id"].startswith("P-")

    @pytest.mark.anyio
    async def test_research_snapshots(self, client: AsyncClient, bootstrapped):
        table_id, host_token, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.get(
            f"/api/tables/{table_id}/research/snapshots",
            headers=auth_header(host_token),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.anyio
    async def test_delete_session(self, client: AsyncClient, bootstrapped):
        table_id, host_token, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.delete(
            f"/api/tables/{table_id}/research/session",
            headers=auth_header(host_token),
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] > 0

        # Verify empty after deletion
        resp = await client.get(
            f"/api/tables/{table_id}/research/events",
            headers=auth_header(host_token),
        )
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_delete_identity(self, client: AsyncClient, bootstrapped):
        table_id, host_token, _ = await self._setup_research_table(client, bootstrapped)

        # Get identities first
        resp = await client.get(
            f"/api/tables/{table_id}/research/identities",
            headers=auth_header(host_token),
        )
        identities = resp.json()
        target_hash = identities[0]["identity_hash"]

        resp = await client.delete(
            f"/api/tables/{table_id}/research/identities/{target_hash}",
            headers=auth_header(host_token),
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] >= 1

    @pytest.mark.anyio
    async def test_delete_unknown_identity_404(self, client: AsyncClient, bootstrapped):
        table_id, host_token, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.delete(
            f"/api/tables/{table_id}/research/identities/nonexistent",
            headers=auth_header(host_token),
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_non_research_table_rejects_research_api(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Normal", "deck_recipe": "standard_52"},
            headers=auth_header(token),
        )
        table_id = resp.json()["table_id"]
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Alice"},
            headers=auth_header(token),
        )

        resp = await client.get(
            f"/api/tables/{table_id}/research/config",
            headers=auth_header(token),
        )
        assert resp.status_code == 400


class TestConsentAPI:
    async def _setup_research_table(self, client, bootstrapped):
        token0, token1 = bootstrapped["tokens"][0], bootstrapped["tokens"][1]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Research", "deck_recipe": "standard_52", "research_mode": True},
            headers=auth_header(token0),
        )
        table_id = resp.json()["table_id"]
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Alice"},
            headers=auth_header(token0),
        )
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Bob"},
            headers=auth_header(token1),
        )
        return table_id, token0, token1

    @pytest.mark.anyio
    async def test_consent_requirements(self, client: AsyncClient, bootstrapped):
        table_id, token0, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.get(
            f"/api/tables/{table_id}/consent/requirements",
            headers=auth_header(token0),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "research_logging" in data["required"]
        assert len(data["optional"]) == 6

    @pytest.mark.anyio
    async def test_submit_consent(self, client: AsyncClient, bootstrapped):
        table_id, token0, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.post(
            f"/api/tables/{table_id}/consent",
            json={"tiers": {"research_logging": True, "chat_storage": True}},
            headers=auth_header(token0),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tiers"]["research_logging"] is True
        assert "identity_hash" in data

    @pytest.mark.anyio
    async def test_get_consent(self, client: AsyncClient, bootstrapped):
        table_id, token0, _ = await self._setup_research_table(client, bootstrapped)
        # Submit first
        await client.post(
            f"/api/tables/{table_id}/consent",
            json={"tiers": {"research_logging": True}},
            headers=auth_header(token0),
        )
        # Get
        resp = await client.get(
            f"/api/tables/{table_id}/consent",
            headers=auth_header(token0),
        )
        assert resp.status_code == 200
        assert resp.json()["tiers"]["research_logging"] is True

    @pytest.mark.anyio
    async def test_get_consent_not_found(self, client: AsyncClient, bootstrapped):
        table_id, token0, _ = await self._setup_research_table(client, bootstrapped)
        resp = await client.get(
            f"/api/tables/{table_id}/consent",
            headers=auth_header(token0),
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_revoke_consent(self, client: AsyncClient, bootstrapped):
        table_id, token0, _ = await self._setup_research_table(client, bootstrapped)
        await client.post(
            f"/api/tables/{table_id}/consent",
            json={"tiers": {"research_logging": True}},
            headers=auth_header(token0),
        )
        resp = await client.delete(
            f"/api/tables/{table_id}/consent",
            headers=auth_header(token0),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

    @pytest.mark.anyio
    async def test_unseated_cannot_submit_consent(self, client: AsyncClient, bootstrapped):
        token0, token2 = bootstrapped["tokens"][0], bootstrapped["tokens"][2]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Research", "deck_recipe": "standard_52", "research_mode": True},
            headers=auth_header(token0),
        )
        table_id = resp.json()["table_id"]
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Alice"},
            headers=auth_header(token0),
        )
        # token2 is not seated
        resp = await client.post(
            f"/api/tables/{table_id}/consent",
            json={"tiers": {"research_logging": True}},
            headers=auth_header(token2),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_non_research_table_rejects_consent(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Normal", "deck_recipe": "standard_52"},
            headers=auth_header(token),
        )
        table_id = resp.json()["table_id"]
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Alice"},
            headers=auth_header(token),
        )
        resp = await client.get(
            f"/api/tables/{table_id}/consent/requirements",
            headers=auth_header(token),
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_longitudinal_consent_grants_link_id(self, client: AsyncClient, bootstrapped):
        table_id, token0, _ = await self._setup_research_table(client, bootstrapped)
        # Submit consent with longitudinal linking
        await client.post(
            f"/api/tables/{table_id}/consent",
            json={"tiers": {"research_logging": True, "longitudinal_linking": True}},
            headers=auth_header(token0),
        )
        # Check identity now has link_id
        resp = await client.get(
            f"/api/tables/{table_id}/research/identities",
            headers=auth_header(token0),
        )
        identities = resp.json()
        consented = [i for i in identities if i["longitudinal_link_consent"]]
        assert len(consented) == 1
        assert consented[0]["longitudinal_link_id"] is not None
        assert consented[0]["longitudinal_link_id"].startswith("L-")

    @pytest.mark.anyio
    async def test_consent_without_longitudinal_no_link(self, client: AsyncClient, bootstrapped):
        table_id, token0, _ = await self._setup_research_table(client, bootstrapped)
        await client.post(
            f"/api/tables/{table_id}/consent",
            json={"tiers": {"research_logging": True}},
            headers=auth_header(token0),
        )
        resp = await client.get(
            f"/api/tables/{table_id}/research/identities",
            headers=auth_header(token0),
        )
        identities = resp.json()
        for ident in identities:
            if ident["longitudinal_link_consent"]:
                assert False, "No identity should have longitudinal consent"

    @pytest.mark.anyio
    async def test_revoke_consent_scrubs_link_id(self, client: AsyncClient, bootstrapped):
        table_id, token0, _ = await self._setup_research_table(client, bootstrapped)
        # Grant longitudinal
        await client.post(
            f"/api/tables/{table_id}/consent",
            json={"tiers": {"research_logging": True, "longitudinal_linking": True}},
            headers=auth_header(token0),
        )
        # Revoke
        await client.delete(
            f"/api/tables/{table_id}/consent",
            headers=auth_header(token0),
        )
        # Check link_id is gone
        resp = await client.get(
            f"/api/tables/{table_id}/research/identities",
            headers=auth_header(token0),
        )
        identities = resp.json()
        for ident in identities:
            assert ident["longitudinal_link_consent"] is False

    @pytest.mark.anyio
    async def test_research_config_includes_ai_latency_and_hash(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Research", "deck_recipe": "standard_52", "research_mode": True},
            headers=auth_header(token),
        )
        table_id = resp.json()["table_id"]
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Alice"},
            headers=auth_header(token),
        )
        resp = await client.get(
            f"/api/tables/{table_id}/research/config",
            headers=auth_header(token),
        )
        config = resp.json()
        assert "ai_latency_simulation_enabled" in config
        assert "ai_min_action_delay_ms" in config
        assert "table_config_hash" in config
        assert config["table_config_hash"] is not None
        assert len(config["table_config_hash"]) == 64
