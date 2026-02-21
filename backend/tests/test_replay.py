"""Tests for CLI replay tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.cli.replay import ReplayState, load_events
from backend.models.research import (
    ActionEnrichment,
    ChatEnrichment,
    ResearchEvent,
    SeatMetadataSnapshot,
)
from backend.models.schema_version import RESEARCH_EVENT_SCHEMA_VERSION


def _make_event(
    event_type: str = "table_created",
    gameplay_seq: int = 1,
    phase_label: str = "",
    seat_snapshot: SeatMetadataSnapshot | None = None,
    action_enrichment: ActionEnrichment | None = None,
    chat_enrichment: ChatEnrichment | None = None,
    **overrides,
) -> ResearchEvent:
    defaults = dict(
        schema_version=RESEARCH_EVENT_SCHEMA_VERSION,
        event_id="evt-001",
        table_id="table-001",
        session_id="sess-001",
        event_type=event_type,
        timestamp_utc_ms=1700000000000,
        server_sequence_number=gameplay_seq,
        phase_label=phase_label,
        gameplay_seq=gameplay_seq,
        seat_snapshot=seat_snapshot,
        action_enrichment=action_enrichment,
        chat_enrichment=chat_enrichment,
    )
    defaults.update(overrides)
    return ResearchEvent(**defaults)


def _seat_snap(seat_id: str = "seat_0", pseudonym: str = "P-abcd1234") -> SeatMetadataSnapshot:
    return SeatMetadataSnapshot(
        seat_id=seat_id,
        seat_type="human",
        display_name="Alice",
        pseudonym_id=pseudonym,
        presence_state="active",
        auto_ack_posture={"move_card": False},
    )


# -------------------------------------------------------------------
# ReplayState unit tests
# -------------------------------------------------------------------


class TestReplayState:
    def test_phase_change(self):
        state = ReplayState()
        event = _make_event(event_type="phase_changed", phase_label="bidding")
        desc = state.apply(event)
        assert state.phase == "bidding"
        assert "bidding" in desc

    def test_action_committed_tracked(self):
        state = ReplayState()
        ae = ActionEnrichment(
            action_id="act-001", action_type="move_card", action_class="consensus"
        )
        event = _make_event(
            event_type="action_committed",
            action_enrichment=ae,
            seat_snapshot=_seat_snap(),
        )
        desc = state.apply(event)
        assert "act-001" in state.committed_actions
        assert "COMMIT" in desc
        assert "move_card" in desc

    def test_rollback_tracked(self):
        state = ReplayState()
        ae = ActionEnrichment(
            action_id="act-002", action_type="set_phase", action_class="optimistic"
        )
        event = _make_event(
            event_type="action_rolled_back",
            action_enrichment=ae,
            seat_snapshot=_seat_snap(),
        )
        desc = state.apply(event)
        assert "act-002" in state.rolled_back_actions
        assert "ROLLBACK" in desc

    def test_dispute_lifecycle(self):
        state = ReplayState()
        # Open dispute
        ae_open = ActionEnrichment(
            action_id="act-003", action_type="move_card", action_class="consensus",
            dispute_reason_tag="rules",
        )
        state.apply(_make_event(
            event_type="dispute_opened",
            action_enrichment=ae_open,
            seat_snapshot=_seat_snap(),
        ))
        assert state.dispute_active is True

        # Resolve dispute
        ae_resolve = ActionEnrichment(
            action_id="act-003", action_type="move_card", action_class="consensus",
            resolution_type="cancel_intent",
            chat_messages_during_resolution=2,
        )
        desc = state.apply(_make_event(
            event_type="dispute_resolved",
            action_enrichment=ae_resolve,
        ))
        assert state.dispute_active is False
        assert "cancel_intent" in desc

    def test_chat_during_dispute_tagged(self):
        state = ReplayState()
        ce = ChatEnrichment(
            chat_message_id="msg-001",
            sender_seat_id="seat_0",
            message_length_chars=42,
            is_resolution_related=True,
        )
        desc = state.apply(_make_event(
            event_type="chat_message",
            chat_enrichment=ce,
            seat_snapshot=_seat_snap(),
        ))
        assert "42 chars" in desc
        assert "during dispute" in desc

    def test_seat_pseudonyms_tracked(self):
        state = ReplayState()
        state.apply(_make_event(
            event_type="seat_joined",
            seat_snapshot=_seat_snap("seat_0", "P-aaa11111"),
        ))
        state.apply(_make_event(
            event_type="seat_joined",
            seat_snapshot=_seat_snap("seat_1", "P-bbb22222"),
        ))
        assert state.seat_pseudonyms["seat_0"] == "P-aaa11111"
        assert state.seat_pseudonyms["seat_1"] == "P-bbb22222"

    def test_summary_counts(self):
        state = ReplayState()
        ae = ActionEnrichment(action_id="a1", action_type="x", action_class="c")
        state.apply(_make_event(event_type="action_committed", action_enrichment=ae))
        state.apply(_make_event(event_type="action_committed", action_enrichment=ae))
        ae2 = ActionEnrichment(action_id="a2", action_type="x", action_class="c")
        state.apply(_make_event(event_type="action_rolled_back", action_enrichment=ae2))
        summary = state.summary()
        assert "Total events: 3" in summary
        assert "Actions committed: 2" in summary
        assert "Actions rolled back: 1" in summary

    def test_event_type_counts(self):
        state = ReplayState()
        state.apply(_make_event(event_type="table_created"))
        state.apply(_make_event(event_type="seat_joined", seat_snapshot=_seat_snap()))
        state.apply(_make_event(event_type="seat_joined", seat_snapshot=_seat_snap()))
        assert state.event_type_counts["table_created"] == 1
        assert state.event_type_counts["seat_joined"] == 2


# -------------------------------------------------------------------
# load_events tests
# -------------------------------------------------------------------


class TestLoadEvents:
    def test_load_valid_ndjson(self, tmp_path: Path):
        event = _make_event()
        ndjson_path = tmp_path / "test.ndjson"
        ndjson_path.write_text(event.model_dump_json() + "\n", encoding="utf-8")
        events = load_events(ndjson_path)
        assert len(events) == 1
        assert events[0].event_id == "evt-001"

    def test_load_multiple_events(self, tmp_path: Path):
        lines = []
        for i in range(5):
            e = _make_event(event_id=f"evt-{i}", gameplay_seq=i + 1, server_sequence_number=i + 1)
            lines.append(e.model_dump_json())
        ndjson_path = tmp_path / "multi.ndjson"
        ndjson_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        events = load_events(ndjson_path)
        assert len(events) == 5

    def test_skip_invalid_lines(self, tmp_path: Path, capsys):
        event = _make_event()
        ndjson_path = tmp_path / "mixed.ndjson"
        ndjson_path.write_text(
            "this is not json\n" + event.model_dump_json() + "\n",
            encoding="utf-8",
        )
        events = load_events(ndjson_path)
        assert len(events) == 1
        captured = capsys.readouterr()
        assert "WARNING: skipping line 1" in captured.err

    def test_empty_file(self, tmp_path: Path):
        ndjson_path = tmp_path / "empty.ndjson"
        ndjson_path.write_text("", encoding="utf-8")
        events = load_events(ndjson_path)
        assert len(events) == 0

    def test_blank_lines_skipped(self, tmp_path: Path):
        event = _make_event()
        ndjson_path = tmp_path / "blanks.ndjson"
        ndjson_path.write_text(
            "\n\n" + event.model_dump_json() + "\n\n",
            encoding="utf-8",
        )
        events = load_events(ndjson_path)
        assert len(events) == 1
