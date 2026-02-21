"""Tests for Phase 4: Researchable (research persistence, SPQ-AN, DataExplorer API)."""

import json
import shutil
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from backend.auth.service import create_principal, create_token
from backend.engine.persistence import (
    DATA_DIR,
    list_persisted_tables,
    load_research_events,
    load_research_meta,
    persist_research_data,
    persist_table,
)
from backend.engine.research_observer import ResearchObserver
from backend.engine.spqan import (
    CEMetrics,
    RCMetrics,
    NSMetrics,
    CAMetrics,
    SSCMetrics,
    SeatSPQAN,
    SessionSPQAN,
    compute_ce_for_seat,
    compute_rc_for_seat,
    compute_ns_for_seat,
    compute_ca_for_seat,
    compute_ssc_for_seat,
    compute_session_spqan,
)
from backend.engine.state import TableState
from backend.models.consent import AIParticipationMetadata
from backend.models.event import EventType
from backend.models.research import ResearchConfig
from backend.models.seat import AckPosture, PlayerKind, Presence, Seat
from backend.models.table import Table
from backend.models.zone import Zone, ZoneKind, ZoneVisibility
from backend.tests.conftest import auth_header


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_persistence():
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    yield
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)


def _make_config() -> ResearchConfig:
    return ResearchConfig(
        session_id=str(uuid.uuid4()),
        identity_salt="deadbeef" * 4,
    )


def _make_table() -> Table:
    return Table(
        table_id=str(uuid.uuid4()),
        display_name="Research Table",
        deck_recipe="standard_52",
        research_mode=True,
        created_at=datetime.now(timezone.utc),
        zones=[
            Zone(zone_id="deck", kind=ZoneKind.DECK, visibility=ZoneVisibility.PUBLIC,
                 card_ids=["c1", "c2", "c3"]),
            Zone(zone_id="discard", kind=ZoneKind.DISCARD, visibility=ZoneVisibility.PUBLIC),
            Zone(zone_id="center", kind=ZoneKind.CENTER, visibility=ZoneVisibility.PUBLIC),
            Zone(zone_id="hand_seat_0", kind=ZoneKind.HAND, visibility=ZoneVisibility.PRIVATE,
                 owner_seat_id="seat_0"),
        ],
        seats=[
            Seat(seat_id="seat_0", display_name="Alice", identity_id="id_alice",
                 player_kind=PlayerKind.HUMAN, presence=Presence.ACTIVE),
            Seat(seat_id="seat_1", display_name="BotBob", identity_id="id_bob",
                 player_kind=PlayerKind.AI, presence=Presence.ACTIVE),
        ],
    )


def _make_observer_with_events():
    """Create a state with observer and generate some research events."""
    table = _make_table()
    config = _make_config()
    observer = ResearchObserver(config)
    state = TableState(table)
    state.attach_research(observer)

    observer.register_identity("id_alice", "seat_0", "human", "Alice")
    observer.register_identity(
        "id_bob", "seat_1", "ai", "BotBob",
        ai_metadata=AIParticipationMetadata(
            ai_model_name="gpt-4", ai_model_version="0613", ai_provider="openai",
        ),
    )

    # Generate gameplay events
    state.append_event(event_type=EventType.INTENT_CREATED, seat_id="seat_0",
                       action_id="act1",
                       data={"intent": {"action_type": "move_card", "card_ids": ["c1"],
                                        "source_zone_id": "hand_seat_0", "target_zone_id": "center"},
                             "action_class": "consensus", "required_acks": ["seat_1"]})
    state.append_event(event_type=EventType.ACK_RECEIVED, seat_id="seat_1",
                       action_id="act1", data={"action_type": "move_card", "action_class": "consensus"})
    state.append_event(event_type=EventType.ACTION_COMMITTED, seat_id="seat_0",
                       action_id="act1",
                       data={"intent": {"action_type": "move_card", "card_ids": ["c1"],
                                        "source_zone_id": "hand_seat_0", "target_zone_id": "center"},
                             "action_class": "consensus"})
    state.append_event(event_type=EventType.CHAT_MESSAGE, seat_id="seat_0",
                       data={"message_id": "msg1", "text": "Nice move!"})
    state.append_event(event_type=EventType.DISPUTE_OPENED, seat_id="seat_1",
                       action_id="act1",
                       data={"reason": "wrong_card", "action_type": "move_card", "action_class": "consensus"})
    state.append_event(event_type=EventType.CHAT_MESSAGE, seat_id="seat_1",
                       data={"message_id": "msg2", "text": "I disagree with that"})
    state.append_event(event_type=EventType.DISPUTE_RESOLVED, seat_id="seat_1",
                       action_id="act1",
                       data={"resolution": "revised", "action_type": "move_card", "action_class": "consensus"})

    return state, observer, table


def _human_token(principal) -> str:
    resp = create_token(principal.identity_id, None, PlayerKind.HUMAN)
    return resp.access_token


# ---------------------------------------------------------------------------
# Research Persistence
# ---------------------------------------------------------------------------


class TestResearchPersistence:
    def test_persist_and_load_research_data(self):
        state, observer, table = _make_observer_with_events()

        # Persist
        path = persist_research_data(table.table_id, observer)
        assert path is not None
        assert path.exists()

        # Load events
        events = load_research_events(table.table_id)
        assert events is not None
        assert len(events) == len(observer.research_log)
        assert events[0]["event_type"] == "intent_created"

        # Load meta
        meta = load_research_meta(table.table_id)
        assert meta is not None
        assert meta["session_id"] == observer.config.session_id
        assert "seat_0" in [v["seat_id"] for v in meta["identities"].values()]
        assert meta["event_count"] == len(observer.research_log)

    def test_persist_empty_observer_returns_none(self):
        config = _make_config()
        observer = ResearchObserver(config)
        result = persist_research_data("fake_id", observer)
        assert result is None

    def test_persist_non_observer_returns_none(self):
        result = persist_research_data("fake_id", "not_an_observer")
        assert result is None

    def test_list_persisted_tables_includes_research_flag(self):
        state, observer, table = _make_observer_with_events()

        # Persist both game and research data
        persist_table(table, state.event_log)
        persist_research_data(table.table_id, observer)

        tables = list_persisted_tables()
        assert len(tables) == 1
        assert tables[0]["has_research_data"] is True

    def test_list_persisted_tables_without_research(self):
        table = _make_table()
        state = TableState(table)
        state.append_event(event_type=EventType.TABLE_CREATED, data={})
        persist_table(table, state.event_log)

        tables = list_persisted_tables()
        assert len(tables) == 1
        assert tables[0]["has_research_data"] is False


# ---------------------------------------------------------------------------
# SPQ-AN Unit Tests
# ---------------------------------------------------------------------------


class TestSPQANModels:
    def test_ce_metrics_defaults(self):
        m = CEMetrics()
        assert m.mean_ack_latency_ms is None
        assert m.dispute_density == 0.0
        assert m.rollback_rate == 0.0

    def test_session_spqan_model(self):
        s = SessionSPQAN(
            session_id="sid", table_id="tid", seats=[], event_count=0, duration_ms=0,
        )
        assert s.session_id == "sid"
        assert s.seats == []


class TestSPQANComputation:
    def test_compute_ce_for_seat(self):
        _, observer, _ = _make_observer_with_events()
        events = [e.model_dump(mode="json") for e in observer.research_log]
        ce = compute_ce_for_seat("seat_0", events)
        # seat_0 proposed act1, which got committed and disputed
        assert ce.dispute_density > 0.0
        assert isinstance(ce.mean_ack_latency_ms, (float, int, type(None)))

    def test_compute_rc_for_seat(self):
        _, observer, _ = _make_observer_with_events()
        events = [e.model_dump(mode="json") for e in observer.research_log]
        rc = compute_rc_for_seat("seat_1", events)
        # seat_1 opened and resolved a dispute
        assert "revised" in rc.resolution_distribution

    def test_compute_ns_for_seat(self):
        _, observer, _ = _make_observer_with_events()
        events = [e.model_dump(mode="json") for e in observer.research_log]
        ns = compute_ns_for_seat("seat_0", events, [])
        assert isinstance(ns.phase_label_diversity, int)

    def test_compute_ca_for_seat(self):
        _, observer, _ = _make_observer_with_events()
        events = [e.model_dump(mode="json") for e in observer.research_log]
        ca = compute_ca_for_seat("seat_0", events)
        # seat_0 sent one chat message "Nice move!"
        assert ca.mean_message_length_chars > 0

    def test_compute_ssc_for_seat(self):
        _, observer, _ = _make_observer_with_events()
        events = [e.model_dump(mode="json") for e in observer.research_log]
        ssc = compute_ssc_for_seat("seat_1", events)
        # seat_1 initiated one dispute
        assert ssc.dispute_initiation_rate > 0.0

    def test_compute_session_spqan(self):
        state, observer, table = _make_observer_with_events()
        events = [e.model_dump(mode="json") for e in observer.research_log]
        identities = {k: v.model_dump(mode="json") for k, v in observer.identity_store.items()}
        spqan = compute_session_spqan(events, identities, [])
        assert len(spqan.seats) == 2
        assert spqan.event_count == len(events)
        assert spqan.duration_ms >= 0

    def test_empty_events_returns_empty_spqan(self):
        spqan = compute_session_spqan([], {}, [])
        assert spqan.seats == []
        assert spqan.event_count == 0


# ---------------------------------------------------------------------------
# Research Sessions API
# ---------------------------------------------------------------------------


class TestResearchSessionsAPI:
    async def _setup_persisted_research(self):
        """Create and persist a research table with events."""
        state, observer, table = _make_observer_with_events()
        state.append_event(event_type=EventType.TABLE_DESTROYED, data={"reason": "test"})
        persist_table(table, state.event_log)
        persist_research_data(table.table_id, observer)
        return table.table_id

    @pytest.mark.anyio
    async def test_list_research_sessions(self, client: AsyncClient):
        p = create_principal("Admin")
        token = _human_token(p)
        table_id = await self._setup_persisted_research()

        resp = await client.get("/api/research/sessions", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["table_id"] == table_id
        assert data[0]["has_research_data"] is True

    @pytest.mark.anyio
    async def test_list_sessions_filter_deck_recipe(self, client: AsyncClient):
        p = create_principal("Admin")
        token = _human_token(p)
        await self._setup_persisted_research()

        resp = await client.get(
            "/api/research/sessions?deck_recipe=nonexistent",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_compute_metrics_endpoint(self, client: AsyncClient):
        p = create_principal("Admin")
        token = _human_token(p)
        table_id = await self._setup_persisted_research()

        resp = await client.post(
            "/api/research/metrics/compute",
            headers=auth_header(token),
            json={"table_ids": [table_id]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["table_id"] == table_id
        assert len(data[0]["seats"]) == 2

    @pytest.mark.anyio
    async def test_compute_metrics_with_family_filter(self, client: AsyncClient):
        p = create_principal("Admin")
        token = _human_token(p)
        table_id = await self._setup_persisted_research()

        resp = await client.post(
            "/api/research/metrics/compute",
            headers=auth_header(token),
            json={"table_ids": [table_id], "families": ["ce"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        seat = data[0]["seats"][0]
        assert seat["ce"] is not None
        assert seat["rc"] is None

    @pytest.mark.anyio
    async def test_get_research_events_endpoint(self, client: AsyncClient):
        p = create_principal("Admin")
        token = _human_token(p)
        table_id = await self._setup_persisted_research()

        resp = await client.get(
            f"/api/research/sessions/{table_id}/events",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) > 0
        assert events[0]["event_type"] == "intent_created"

    @pytest.mark.anyio
    async def test_get_research_events_with_filter(self, client: AsyncClient):
        p = create_principal("Admin")
        token = _human_token(p)
        table_id = await self._setup_persisted_research()

        resp = await client.get(
            f"/api/research/sessions/{table_id}/events?event_type=CHAT_MESSAGE",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        events = resp.json()
        assert all(e["event_type"] == "chat_message" for e in events)

    @pytest.mark.anyio
    async def test_get_research_events_not_found(self, client: AsyncClient):
        p = create_principal("Admin")
        token = _human_token(p)

        resp = await client.get(
            "/api/research/sessions/nonexistent/events",
            headers=auth_header(token),
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_export_research_events(self, client: AsyncClient):
        p = create_principal("Admin")
        token = _human_token(p)
        table_id = await self._setup_persisted_research()

        resp = await client.get(
            f"/api/research/sessions/{table_id}/events/export",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert "ndjson" in resp.headers.get("content-type", "")
        lines = resp.text.strip().split("\n")
        assert len(lines) > 0
        first = json.loads(lines[0])
        assert "event_id" in first


# ---------------------------------------------------------------------------
# Backend Enhancements
# ---------------------------------------------------------------------------


class TestBackendEnhancements:
    @pytest.mark.anyio
    async def test_summary_includes_spqan_for_research(self, client: AsyncClient):
        p = create_principal("Admin")
        token = _human_token(p)

        state, observer, table = _make_observer_with_events()
        state.append_event(event_type=EventType.TABLE_DESTROYED, data={"reason": "test"})
        persist_table(table, state.event_log)
        persist_research_data(table.table_id, observer)

        resp = await client.get(
            f"/api/tables/{table.table_id}/summary",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["research_mode"] is True
        assert "spqan" in data
        assert len(data["spqan"]["seats"]) == 2

    @pytest.mark.anyio
    async def test_research_health_includes_consent_distribution(self, client: AsyncClient):
        p = create_principal("Admin")
        token = _human_token(p)

        resp = await client.get("/api/admin/research/health", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "consent_distribution" in data


# ---------------------------------------------------------------------------
# Table Manager Integration
# ---------------------------------------------------------------------------


class TestTableManagerResearchPersistence:
    @pytest.mark.anyio
    async def test_delete_table_persists_research(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]

        # Create research-mode table
        resp = await client.post(
            "/api/tables",
            json={"display_name": "ResTest", "deck_recipe": "standard_52", "research_mode": True},
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        table_id = resp.json()["table_id"]

        # Join
        resp = await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "TestPlayer"},
            headers=auth_header(token),
        )
        assert resp.status_code == 200

        # Destroy
        resp = await client.delete(
            f"/api/tables/{table_id}",
            headers=auth_header(token),
        )
        assert resp.status_code == 204

        # Check persistence
        tables = list_persisted_tables()
        research_table = next((t for t in tables if t["table_id"] == table_id), None)
        assert research_table is not None
        assert research_table["has_research_data"] is True

        # Verify research files exist
        events = load_research_events(table_id)
        assert events is not None
        meta = load_research_meta(table_id)
        assert meta is not None
