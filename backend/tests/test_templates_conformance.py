"""TEMPLATES.md conformance tests.

Validates: card enrichment, zone enrichment, shuffle determinism,
TurnState, scratchpad system, ShuffleState, and rollback integrity.
"""

import hashlib
import random
from datetime import datetime, timezone

import pytest

from backend.engine.deck import create_deck
from backend.engine.scratchpad import apply_scratchpad_edit
from backend.engine.state import TableState
from backend.engine.table_manager import create_table, join_table
from backend.engine.action_engine import execute_unilateral
from backend.engine.optimistic import execute_optimistic
from backend.engine.scratchpad import MAX_SCRATCHPAD_CONTENT
from backend.engine.table_manager import leave_table
from backend.models.action import ActionIntent, ActionType
from backend.models.card import Card, DeckRecipe
from backend.models.event import EventType
from backend.models.schema_version import EVENT_SCHEMA_VERSION
from backend.models.scratchpad import (
    Scratchpad,
    ScratchpadAction,
    ScratchpadEdit,
    ScratchpadVisibility,
)
from backend.models.seat import PlayerKind, Presence, Seat
from backend.models.table import ShuffleState, Table, TableCreate, TurnState
from backend.models.zone import Zone, ZoneKind, ZoneOrdering, ZoneVisibility
from backend.engine.visibility import filter_table_for_seat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_table(recipe: str = "euchre_24", research: bool = False) -> Table:
    req = TableCreate(
        display_name="Test",
        deck_recipe=DeckRecipe(recipe),
        research_mode=research,
    )
    return create_table(req)


def _join(table: Table, name: str, index: int) -> Seat:
    seat = join_table(
        table.table_id,
        identity_id=f"id_{index}",
        display_name=name,
    )
    assert seat is not None
    return seat


def _make_state(table: Table) -> TableState:
    from backend.engine.state import get_or_create_state
    return get_or_create_state(table)


# ===================================================================
# 1. Card Model Enrichment
# ===================================================================

class TestCardEnrichment:
    def test_new_fields_populated_at_creation(self):
        cards = create_deck(DeckRecipe.STANDARD_52)
        assert len(cards) == 52
        for card in cards:
            assert card.template_id == "standard_52"
            assert card.created_at is not None
            assert isinstance(card.created_at, datetime)
            assert card.metadata == {}

    def test_defaults_work_for_bare_card(self):
        card = Card(unique_id="test", rank="A", suit="hearts")
        assert card.template_id == ""
        assert card.created_at is None
        assert card.metadata == {}
        assert card.face_up is False

    def test_euchre_template_id(self):
        cards = create_deck(DeckRecipe.EUCHRE_24)
        assert len(cards) == 24
        assert all(c.template_id == "euchre_24" for c in cards)

    def test_pinochle_template_id(self):
        cards = create_deck(DeckRecipe.DOUBLE_PINOCHLE_80)
        assert len(cards) == 80
        assert all(c.template_id == "double_pinochle_80" for c in cards)

    def test_metadata_is_freeform(self):
        card = Card(
            unique_id="test",
            rank="A",
            suit="hearts",
            metadata={"custom_key": "value", "count": 42},
        )
        assert card.metadata["custom_key"] == "value"
        assert card.metadata["count"] == 42


# ===================================================================
# 2. Zone Model Enrichment
# ===================================================================

class TestZoneEnrichment:
    def test_new_enum_values_exist(self):
        assert ZoneVisibility.SHARED_CONTROL.value == "shared_control"
        assert ZoneKind.TRICK_PLAY.value == "trick_play"
        assert ZoneKind.SCRATCHPAD.value == "scratchpad"

    def test_zone_ordering_enum(self):
        assert ZoneOrdering.STACKED.value == "stacked"
        assert ZoneOrdering.ORDERED.value == "ordered"
        assert ZoneOrdering.UNORDERED.value == "unordered"

    def test_zone_new_fields_defaults(self):
        zone = Zone(zone_id="z1", kind=ZoneKind.HAND, visibility=ZoneVisibility.PRIVATE)
        assert zone.capacity is None
        assert zone.ordering == ZoneOrdering.ORDERED
        assert zone.seat_visibility == []
        assert zone.metadata == {}

    def test_zone_capacity(self):
        zone = Zone(
            zone_id="z1",
            kind=ZoneKind.HAND,
            visibility=ZoneVisibility.PRIVATE,
            capacity=5,
        )
        assert zone.capacity == 5

    def test_shared_control_visibility(self):
        table = _create_test_table()
        seat_a = _join(table, "A", 0)
        seat_b = _join(table, "B", 1)

        shared_zone = Zone(
            zone_id="shared",
            kind=ZoneKind.CENTER,
            visibility=ZoneVisibility.SHARED_CONTROL,
            card_ids=[],
        )
        table.zones.append(shared_zone)

        view_a = filter_table_for_seat(table, seat_a.seat_id)
        view_b = filter_table_for_seat(table, seat_b.seat_id)

        # Both can see the shared zone contents
        shared_a = next(z for z in view_a["zones"] if z["zone_id"] == "shared")
        shared_b = next(z for z in view_b["zones"] if z["zone_id"] == "shared")
        assert "card_count" not in shared_a  # full visibility
        assert "card_count" not in shared_b

    def test_seat_visibility_narrowing(self):
        table = _create_test_table()
        seat_a = _join(table, "A", 0)
        seat_b = _join(table, "B", 1)
        seat_c = _join(table, "C", 2)

        # Create a public zone visible only to seat_a and seat_b
        restricted = Zone(
            zone_id="restricted",
            kind=ZoneKind.CUSTOM,
            visibility=ZoneVisibility.PUBLIC,
            card_ids=list(table.cards.keys())[:3],
            seat_visibility=[seat_a.seat_id, seat_b.seat_id],
        )
        table.zones.append(restricted)

        view_a = filter_table_for_seat(table, seat_a.seat_id)
        view_c = filter_table_for_seat(table, seat_c.seat_id)

        zone_a = next(z for z in view_a["zones"] if z["zone_id"] == "restricted")
        zone_c = next(z for z in view_c["zones"] if z["zone_id"] == "restricted")

        # A can see contents, C cannot
        assert len(zone_a["card_ids"]) == 3
        assert zone_c["card_ids"] == []
        assert zone_c["card_count"] == 3

    def test_backward_compat_center_zone(self):
        """Existing CENTER kind still works."""
        table = _create_test_table()
        center = next(z for z in table.zones if z.zone_id == "center")
        assert center.kind == ZoneKind.CENTER


# ===================================================================
# 3. Shuffle Determinism
# ===================================================================

class TestShuffleDeterminism:
    def test_same_seed_same_order(self):
        """Given the same seed, shuffling produces the same order."""
        ids = [f"card_{i}" for i in range(52)]

        seed = "test_seed_abc123"
        a = list(ids)
        random.Random(seed).shuffle(a)

        b = list(ids)
        random.Random(seed).shuffle(b)

        assert a == b

    def test_shuffle_stores_seed_hash_in_event(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        intent = ActionIntent(action_type=ActionType.SHUFFLE)
        result = execute_unilateral(intent, seat, state)
        assert result.status == "committed"

        # Find the ACTION_COMMITTED event
        committed = [e for e in state.event_log if e.event_type == EventType.ACTION_COMMITTED]
        assert len(committed) >= 1
        event = committed[-1]
        # Only the hash is in event data, not the raw seed or full deck order
        assert "shuffle_seed_hash" in event.data
        assert "shuffle_seed" not in event.data
        assert "deck_order_after" not in event.data
        # Verify hash matches the seed on shuffle_state
        expected_hash = hashlib.sha256(table.shuffle_state.seed.encode()).hexdigest()
        assert event.data["shuffle_seed_hash"] == expected_hash

    def test_shuffle_state_populated(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        intent = ActionIntent(action_type=ActionType.SHUFFLE)
        execute_unilateral(intent, seat, state)

        ss = table.shuffle_state
        assert ss.shuffled_by == seat.seat_id
        assert ss.shuffled_at is not None
        assert ss.seed is not None
        assert len(ss.seed) == 32

    def test_shuffle_state_survives_rollback(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        # Shuffle
        intent = ActionIntent(action_type=ActionType.SHUFFLE)
        execute_unilateral(intent, seat, state)
        seed_before = table.shuffle_state.seed

        # Take snapshot, modify, rollback
        seq = state.take_snapshot()
        table.shuffle_state = ShuffleState()  # clear it
        assert table.shuffle_state.seed is None

        state.rollback_to(seq)
        assert table.shuffle_state.seed == seed_before

    def test_rng_provenance_populated_in_research_mode(self):
        table = _create_test_table(research=True)
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        intent = ActionIntent(action_type=ActionType.SHUFFLE)
        execute_unilateral(intent, seat, state)

        observer = state._research_observer
        assert observer is not None

        # Find shuffle research event
        shuffle_events = [
            e for e in observer.research_log
            if e.rng_provenance is not None
        ]
        assert len(shuffle_events) >= 1
        rng = shuffle_events[-1].rng_provenance
        assert rng.rng_seed_id is not None
        assert rng.rng_seed_hash is not None
        assert rng.rng_seed_hash == hashlib.sha256(rng.rng_seed_id.encode()).hexdigest()
        assert len(rng.deck_order_after) > 0


# ===================================================================
# 4. TurnState
# ===================================================================

class TestTurnState:
    def test_turn_state_defaults(self):
        table = _create_test_table()
        assert table.turn_state.active_seat_id is None
        assert table.turn_state.phase_label == ""
        assert table.turn_state.metadata == {}

    def test_phase_sync_via_optimistic(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        _join(table, "Player2", 1)
        state = _make_state(table)

        # SET_PHASE is optimistic
        intent = ActionIntent(action_type=ActionType.SET_PHASE, phase_label="bidding")
        execute_optimistic(intent, seat, state)

        assert table.phase == "bidding"
        assert table.turn_state.phase_label == "bidding"

    def test_turn_state_rollback(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        table.turn_state.phase_label = "playing"
        table.turn_state.active_seat_id = seat.seat_id

        seq = state.take_snapshot()

        table.turn_state.phase_label = "scoring"
        table.turn_state.active_seat_id = None

        state.rollback_to(seq)
        assert table.turn_state.phase_label == "playing"
        assert table.turn_state.active_seat_id == seat.seat_id


# ===================================================================
# 5. Scratchpad System
# ===================================================================

class TestScratchpad:
    def test_table_creates_public_scratchpad(self):
        table = _create_test_table()
        assert "public_scratchpad" in table.scratchpads
        sp = table.scratchpads["public_scratchpad"]
        assert sp.visibility == ScratchpadVisibility.PUBLIC
        assert sp.content == ""

    def test_join_creates_private_scratchpad(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        sp_id = f"notes_{seat.seat_id}"
        assert sp_id in table.scratchpads
        sp = table.scratchpads[sp_id]
        assert sp.visibility == ScratchpadVisibility.PRIVATE
        assert sp.owner_seat_id == seat.seat_id

    def test_scratchpad_append(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        edit = ScratchpadEdit(
            scratchpad_id="public_scratchpad",
            action=ScratchpadAction.APPEND,
            content="hello",
        )
        apply_scratchpad_edit(edit, seat.seat_id, state)
        assert table.scratchpads["public_scratchpad"].content == "hello"

        edit2 = ScratchpadEdit(
            scratchpad_id="public_scratchpad",
            action=ScratchpadAction.APPEND,
            content=" world",
        )
        apply_scratchpad_edit(edit2, seat.seat_id, state)
        assert table.scratchpads["public_scratchpad"].content == "hello world"

    def test_scratchpad_replace(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        edit = ScratchpadEdit(
            scratchpad_id="public_scratchpad",
            action=ScratchpadAction.REPLACE,
            content="new content",
        )
        apply_scratchpad_edit(edit, seat.seat_id, state)
        assert table.scratchpads["public_scratchpad"].content == "new content"

    def test_scratchpad_clear(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        table.scratchpads["public_scratchpad"].content = "existing"
        edit = ScratchpadEdit(
            scratchpad_id="public_scratchpad",
            action=ScratchpadAction.CLEAR,
        )
        apply_scratchpad_edit(edit, seat.seat_id, state)
        assert table.scratchpads["public_scratchpad"].content == ""

    def test_private_scratchpad_access_control(self):
        table = _create_test_table()
        seat_a = _join(table, "A", 0)
        seat_b = _join(table, "B", 1)
        state = _make_state(table)

        sp_id = f"notes_{seat_a.seat_id}"

        # Owner can edit
        edit = ScratchpadEdit(
            scratchpad_id=sp_id,
            action=ScratchpadAction.REPLACE,
            content="my notes",
        )
        apply_scratchpad_edit(edit, seat_a.seat_id, state)
        assert table.scratchpads[sp_id].content == "my notes"

        # Non-owner cannot edit
        edit2 = ScratchpadEdit(
            scratchpad_id=sp_id,
            action=ScratchpadAction.REPLACE,
            content="hacked",
        )
        with pytest.raises(ValueError, match="Cannot edit"):
            apply_scratchpad_edit(edit2, seat_b.seat_id, state)

    def test_scratchpad_content_hashing(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        edit = ScratchpadEdit(
            scratchpad_id="public_scratchpad",
            action=ScratchpadAction.REPLACE,
            content="test content",
        )
        event_data = apply_scratchpad_edit(edit, seat.seat_id, state)

        assert "content_hash_before" in event_data
        assert "content_hash_after" in event_data
        assert event_data["content_hash_before"] == hashlib.sha256(b"").hexdigest()
        assert event_data["content_hash_after"] == hashlib.sha256(b"test content").hexdigest()

    def test_scratchpad_event_emission(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        edit = ScratchpadEdit(
            scratchpad_id="public_scratchpad",
            action=ScratchpadAction.APPEND,
            content="data",
        )
        apply_scratchpad_edit(edit, seat.seat_id, state)

        sp_events = [e for e in state.event_log if e.event_type == EventType.SCRATCHPAD_EDITED]
        assert len(sp_events) == 1
        assert sp_events[0].data["scratchpad_id"] == "public_scratchpad"
        assert sp_events[0].data["action"] == "append"

    def test_scratchpad_visibility_filtering(self):
        table = _create_test_table()
        seat_a = _join(table, "A", 0)
        seat_b = _join(table, "B", 1)

        view_a = filter_table_for_seat(table, seat_a.seat_id)
        view_b = filter_table_for_seat(table, seat_b.seat_id)

        # A can see public + own private, not B's private
        assert "public_scratchpad" in view_a.get("scratchpads", {})
        assert f"notes_{seat_a.seat_id}" in view_a.get("scratchpads", {})
        assert f"notes_{seat_b.seat_id}" not in view_a.get("scratchpads", {})

        # B can see public + own private, not A's private
        assert "public_scratchpad" in view_b.get("scratchpads", {})
        assert f"notes_{seat_b.seat_id}" in view_b.get("scratchpads", {})
        assert f"notes_{seat_a.seat_id}" not in view_b.get("scratchpads", {})

    def test_scratchpad_not_found(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        edit = ScratchpadEdit(
            scratchpad_id="nonexistent",
            action=ScratchpadAction.REPLACE,
            content="x",
        )
        with pytest.raises(ValueError, match="not found"):
            apply_scratchpad_edit(edit, seat.seat_id, state)

    def test_scratchpad_survives_rollback(self):
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        table.scratchpads["public_scratchpad"].content = "before"
        seq = state.take_snapshot()

        table.scratchpads["public_scratchpad"].content = "after"
        state.rollback_to(seq)

        assert table.scratchpads["public_scratchpad"].content == "before"


# ===================================================================
# 6. Schema Version
# ===================================================================

class TestSchemaVersion:
    def test_event_schema_bumped(self):
        assert EVENT_SCHEMA_VERSION == "1.1.0"


# ===================================================================
# 7. Table Model Integration
# ===================================================================

class TestTableModelIntegration:
    def test_table_has_new_fields(self):
        table = _create_test_table()
        assert isinstance(table.shuffle_state, ShuffleState)
        assert isinstance(table.turn_state, TurnState)
        assert isinstance(table.scratchpads, dict)

    def test_table_serialization_roundtrip(self):
        """Ensure Table can serialize and deserialize with new fields."""
        table = _create_test_table()
        seat = _join(table, "Player", 0)

        table.shuffle_state = ShuffleState(
            shuffled_by=seat.seat_id,
            shuffled_at=datetime.now(timezone.utc),
            seed="abc123",
        )
        table.turn_state = TurnState(
            active_seat_id=seat.seat_id,
            phase_label="bidding",
        )

        data = table.model_dump(mode="json")
        restored = Table.model_validate(data)

        assert restored.shuffle_state.seed == "abc123"
        assert restored.turn_state.phase_label == "bidding"
        assert restored.turn_state.active_seat_id == seat.seat_id
        assert "public_scratchpad" in restored.scratchpads


# ===================================================================
# 8. Review Fixes
# ===================================================================

class TestReviewFixes:
    def test_optimistic_shuffle_has_determinism(self):
        """Fix #3: Optimistic shuffle must also use seeded RNG."""
        table = _create_test_table()
        table.settings.shuffle_is_optimistic = True
        seat = _join(table, "Player", 0)
        _join(table, "Player2", 1)
        state = _make_state(table)

        intent = ActionIntent(action_type=ActionType.SHUFFLE)
        result = execute_optimistic(intent, seat, state)
        assert result.status == "committed"

        # shuffle_state must be populated
        assert table.shuffle_state.seed is not None
        assert len(table.shuffle_state.seed) == 32
        assert table.shuffle_state.shuffled_by == seat.seat_id

        # Event must have seed hash
        committed = [e for e in state.event_log if e.event_type == EventType.ACTION_COMMITTED]
        assert "shuffle_seed_hash" in committed[-1].data

    def test_leave_table_cleans_up_scratchpad(self):
        """Fix #4: Private scratchpad removed when seat leaves."""
        table = _create_test_table()
        seat = _join(table, "A", 0)
        _join(table, "B", 1)
        sp_id = f"notes_{seat.seat_id}"
        assert sp_id in table.scratchpads

        leave_table(table.table_id, "id_0")
        assert sp_id not in table.scratchpads
        # Public scratchpad still present
        assert "public_scratchpad" in table.scratchpads

    def test_scratchpad_content_size_limit(self):
        """Fix #5: Content exceeding MAX_SCRATCHPAD_CONTENT is rejected."""
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        oversized = "x" * (MAX_SCRATCHPAD_CONTENT + 1)
        edit = ScratchpadEdit(
            scratchpad_id="public_scratchpad",
            action=ScratchpadAction.REPLACE,
            content=oversized,
        )
        with pytest.raises(ValueError, match="maximum size"):
            apply_scratchpad_edit(edit, seat.seat_id, state)

    def test_scratchpad_append_respects_limit(self):
        """Fix #5: Appending past the limit is rejected."""
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        # Fill to near-limit
        table.scratchpads["public_scratchpad"].content = "x" * MAX_SCRATCHPAD_CONTENT
        edit = ScratchpadEdit(
            scratchpad_id="public_scratchpad",
            action=ScratchpadAction.APPEND,
            content="one more",
        )
        with pytest.raises(ValueError, match="maximum size"):
            apply_scratchpad_edit(edit, seat.seat_id, state)

    def test_visibility_excludes_empty_shuffle_state(self):
        """Fix #1: Default empty ShuffleState not included in view."""
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        view = filter_table_for_seat(table, seat.seat_id)
        assert "shuffle_state" not in view

    def test_visibility_excludes_empty_turn_state(self):
        """Fix #1: Default empty TurnState not included in view."""
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        view = filter_table_for_seat(table, seat.seat_id)
        assert "turn_state" not in view

    def test_visibility_includes_populated_shuffle_state(self):
        """Fix #1: ShuffleState included when populated."""
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        state = _make_state(table)

        intent = ActionIntent(action_type=ActionType.SHUFFLE)
        execute_unilateral(intent, seat, state)

        view = filter_table_for_seat(table, seat.seat_id)
        assert "shuffle_state" in view
        assert view["shuffle_state"]["seed"] is not None

    def test_visibility_includes_populated_turn_state(self):
        """Fix #1: TurnState included when it has meaningful data."""
        table = _create_test_table()
        seat = _join(table, "Player", 0)
        _join(table, "Player2", 1)
        state = _make_state(table)

        intent = ActionIntent(action_type=ActionType.SET_PHASE, phase_label="bidding")
        execute_optimistic(intent, seat, state)

        view = filter_table_for_seat(table, seat.seat_id)
        assert "turn_state" in view
        assert view["turn_state"]["phase_label"] == "bidding"
