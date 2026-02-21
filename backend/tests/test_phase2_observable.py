"""Tests for Phase 2: Observability features (persistence, history, spectator WS, chat channels)."""

import json
import shutil
from pathlib import Path

import pytest
from httpx import AsyncClient

from backend.engine.persistence import DATA_DIR, load_events, load_meta, list_persisted_tables, persist_table
from backend.engine.state import get_or_create_state, get_state
from backend.engine.table_manager import create_table, delete_table, get_table
from backend.models.event import Event, EventType
from backend.models.table import TableCreate
from backend.tests.conftest import auth_header


@pytest.fixture(autouse=True)
def clean_persistence():
    """Remove persisted event files between tests."""
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    yield
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)


# ---------------------------------------------------------------------------
# Event Persistence
# ---------------------------------------------------------------------------

class TestEventPersistence:
    def test_persist_and_load_events(self):
        table = create_table(TableCreate(display_name="P", deck_recipe="euchre_24"))
        state = get_or_create_state(table)
        state.append_event(event_type=EventType.TABLE_CREATED, data={"test": True})
        state.append_event(event_type=EventType.CHAT_MESSAGE, seat_id="seat_0", data={"text": "hi"})

        persist_table(table, state.event_log)

        loaded = load_events(table.table_id)
        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0].event_type == EventType.TABLE_CREATED
        assert loaded[1].data["text"] == "hi"

    def test_persist_and_load_meta(self):
        table = create_table(TableCreate(display_name="Meta Test", deck_recipe="standard_52"))
        state = get_or_create_state(table)
        persist_table(table, state.event_log)

        meta = load_meta(table.table_id)
        assert meta is not None
        assert meta["display_name"] == "Meta Test"
        assert meta["deck_recipe"] == "standard_52"
        assert "destroyed_at" in meta

    def test_list_persisted_tables(self):
        for i in range(3):
            t = create_table(TableCreate(display_name=f"T{i}", deck_recipe="euchre_24"))
            s = get_or_create_state(t)
            persist_table(t, s.event_log)

        results = list_persisted_tables()
        assert len(results) == 3

    def test_load_nonexistent(self):
        assert load_events("nonexistent") is None
        assert load_meta("nonexistent") is None


class TestDeleteTablePersistence:
    def test_delete_persists_events(self):
        table = create_table(TableCreate(display_name="Del", deck_recipe="euchre_24"))
        state = get_or_create_state(table)
        state.append_event(event_type=EventType.TABLE_CREATED, data={})
        tid = table.table_id

        result = delete_table(tid)
        assert result is True

        # Event log should be persisted with TABLE_DESTROYED
        events = load_events(tid)
        assert events is not None
        assert any(e.event_type == EventType.TABLE_DESTROYED for e in events)

    def test_delete_removes_state(self):
        table = create_table(TableCreate(display_name="D", deck_recipe="euchre_24"))
        get_or_create_state(table)
        tid = table.table_id

        delete_table(tid)
        assert get_state(tid) is None
        assert get_table(tid) is None


# ---------------------------------------------------------------------------
# TABLE_DESTROYED Event
# ---------------------------------------------------------------------------

class TestTableDestroyedEvent:
    def test_table_destroyed_in_enum(self):
        assert EventType.TABLE_DESTROYED.value == "table_destroyed"


# ---------------------------------------------------------------------------
# History Endpoints
# ---------------------------------------------------------------------------

class TestHistoryEndpoints:
    async def _create_and_join_and_destroy(self, client: AsyncClient, token: str) -> str:
        """Helper: create table, join, destroy, return table_id."""
        resp = await client.post(
            "/api/tables",
            json={"display_name": "History Test", "deck_recipe": "euchre_24"},
            headers=auth_header(token),
        )
        tid = resp.json()["table_id"]

        await client.post(
            f"/api/tables/{tid}/join",
            json={"display_name": "Player"},
            headers=auth_header(token),
        )

        await client.delete(f"/api/tables/{tid}", headers=auth_header(token))
        return tid

    async def test_games_list_empty(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.get("/api/games", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_games_list_after_destroy(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        tid = await self._create_and_join_and_destroy(client, token)

        resp = await client.get("/api/games", headers=auth_header(token))
        assert resp.status_code == 200
        games = resp.json()
        assert len(games) == 1
        assert games[0]["table_id"] == tid

    async def test_events_endpoint_persisted(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        tid = await self._create_and_join_and_destroy(client, token)

        resp = await client.get(f"/api/tables/{tid}/events", headers=auth_header(token))
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) > 0
        # Should contain TABLE_DESTROYED
        types = [e["event_type"] for e in events]
        assert "table_destroyed" in types

    async def test_events_endpoint_live(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Live", "deck_recipe": "euchre_24"},
            headers=auth_header(token),
        )
        tid = resp.json()["table_id"]

        resp = await client.get(f"/api/tables/{tid}/events", headers=auth_header(token))
        assert resp.status_code == 200

    async def test_events_not_found(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.get("/api/tables/nonexistent/events", headers=auth_header(token))
        assert resp.status_code == 404

    async def test_events_filter_by_seq(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        tid = await self._create_and_join_and_destroy(client, token)

        resp = await client.get(
            f"/api/tables/{tid}/events?from_seq=1&to_seq=2",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        events = resp.json()
        for e in events:
            assert 1 <= e["seq"] <= 2

    async def test_summary_endpoint(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        tid = await self._create_and_join_and_destroy(client, token)

        resp = await client.get(f"/api/tables/{tid}/summary", headers=auth_header(token))
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["table_id"] == tid
        assert "duration_s" in summary
        assert "total_actions" in summary
        assert "total_disputes" in summary
        assert "total_undos" in summary
        assert "total_events" in summary

    async def test_summary_not_found(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.get("/api/tables/nonexistent/summary", headers=auth_header(token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Chat Channel Field
# ---------------------------------------------------------------------------

class TestChatChannel:
    def test_chat_message_has_channel(self):
        from backend.models.chat import ChatMessage
        from datetime import datetime, timezone

        msg = ChatMessage(
            message_id="m1",
            seat_id="s1",
            identity_id="i1",
            text="hi",
            timestamp=datetime.now(timezone.utc),
        )
        assert msg.channel == "game"

        msg2 = ChatMessage(
            message_id="m2",
            seat_id="__spectator__",
            identity_id="i2",
            text="hello",
            channel="spectator",
            timestamp=datetime.now(timezone.utc),
        )
        assert msg2.channel == "spectator"

    def test_ws_inbound_has_channel(self):
        from backend.models.protocol import WSInbound

        msg = WSInbound(msg_type="chat", text="hi", channel="spectator")
        assert msg.channel == "spectator"

        msg2 = WSInbound(msg_type="chat", text="hi")
        assert msg2.channel is None


# ---------------------------------------------------------------------------
# Table List research_mode
# ---------------------------------------------------------------------------

class TestTableListResearchMode:
    async def test_table_list_includes_research_mode(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        await client.post(
            "/api/tables",
            json={"display_name": "Normal", "deck_recipe": "euchre_24"},
            headers=auth_header(token),
        )
        resp = await client.get("/api/tables", headers=auth_header(token))
        assert resp.status_code == 200
        tables = resp.json()
        assert len(tables) == 1
        assert "research_mode" in tables[0]
