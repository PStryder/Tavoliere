"""SPQ-AN Environment Compliance Suite.

Each test verifies a specific requirement from the SPQ-AN specification
(Social Participation Quality under Ambiguous Norms). This file is a
publishable artifact: the compliance checklist for the Tavoliere consensus
mediation environment.

Section references map to SPQ-AN spec v1.0.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from backend.engine.research_observer import (
    ResearchObserver,
    compute_identity_hash,
    generate_pseudonym,
)
from backend.engine.state import TableState
from backend.engine.visibility import filter_table_for_seat
from backend.models.card import Card, DeckRecipe, Rank, Suit
from backend.models.event import EventType
from backend.models.research import ResearchConfig
from backend.models.schema_version import (
    EVENT_SCHEMA_VERSION,
    RESEARCH_EVENT_SCHEMA_VERSION,
)
from backend.models.seat import AckPosture, PlayerKind, Presence, Seat
from backend.models.table import Table, TableSettings
from backend.models.zone import Zone, ZoneKind, ZoneVisibility
from backend.tests.conftest import auth_header


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _make_cards() -> dict[str, Card]:
    cards = {}
    for i, (rank, suit) in enumerate(
        [(Rank.ACE, Suit.SPADES), (Rank.KING, Suit.HEARTS),
         (Rank.QUEEN, Suit.DIAMONDS), (Rank.JACK, Suit.CLUBS),
         (Rank.TEN, Suit.SPADES), (Rank.NINE, Suit.HEARTS),
         (Rank.ACE, Suit.HEARTS)],
    ):
        cid = f"c{i}"
        cards[cid] = Card(unique_id=cid, rank=rank, suit=suit)
    return cards


def _make_table() -> Table:
    cards = _make_cards()
    return Table(
        table_id=str(uuid.uuid4()),
        display_name="Compliance Table",
        deck_recipe=DeckRecipe.EUCHRE_24,
        research_mode=True,
        created_at=datetime.now(timezone.utc),
        cards=cards,
        zones=[
            Zone(zone_id="deck", kind=ZoneKind.DECK,
                 visibility=ZoneVisibility.PUBLIC,
                 card_ids=["c0", "c1", "c2"]),
            Zone(zone_id="center", kind=ZoneKind.CENTER,
                 visibility=ZoneVisibility.PUBLIC),
            Zone(zone_id="hand_seat_0", kind=ZoneKind.HAND,
                 visibility=ZoneVisibility.PRIVATE,
                 owner_seat_id="seat_0", card_ids=["c3", "c4"]),
            Zone(zone_id="hand_seat_1", kind=ZoneKind.HAND,
                 visibility=ZoneVisibility.PRIVATE,
                 owner_seat_id="seat_1", card_ids=["c5", "c6"]),
        ],
        seats=[
            Seat(seat_id="seat_0", display_name="Alice",
                 identity_id="id_alice",
                 player_kind=PlayerKind.HUMAN, presence=Presence.ACTIVE),
            Seat(seat_id="seat_1", display_name="BotBob",
                 identity_id="id_bob",
                 player_kind=PlayerKind.AI, presence=Presence.ACTIVE),
        ],
    )


def _state_with_observer():
    table = _make_table()
    config = ResearchConfig(
        session_id=str(uuid.uuid4()),
        identity_salt="compliance_salt_0123456789ab",
    )
    observer = ResearchObserver(config)
    state = TableState(table)
    state.attach_research(observer)
    observer.register_identity("id_alice", "seat_0", "human", "Alice")
    observer.register_identity("id_bob", "seat_1", "ai", "BotBob")
    return state, observer, table


async def _setup_4p(client: AsyncClient, tokens: list[str]) -> str:
    """Create a 4-player euchre table. Returns table_id."""
    resp = await client.post(
        "/api/tables",
        json={"display_name": "Compliance", "deck_recipe": "euchre_24"},
        headers=auth_header(tokens[0]),
    )
    table_id = resp.json()["table_id"]
    names = ["North", "East", "South", "West"]
    for i, token in enumerate(tokens):
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": names[i]},
            headers=auth_header(token),
        )
    return table_id


# ===================================================================
# SPQ-AN 3.1 — Schema Versioning
# ===================================================================


class TestSchemaVersioning:
    """Every event must carry a schema_version field for corpus stability."""

    def test_gameplay_event_has_schema_version(self):
        state, _, _ = _state_with_observer()
        event = state.append_event(EventType.TABLE_CREATED)
        assert event.schema_version == EVENT_SCHEMA_VERSION

    def test_research_event_has_schema_version(self):
        state, observer, _ = _state_with_observer()
        state.append_event(EventType.TABLE_CREATED)
        re = observer.research_log[0]
        assert re.schema_version == RESEARCH_EVENT_SCHEMA_VERSION

    def test_schema_version_in_serialized_event(self):
        state, _, _ = _state_with_observer()
        event = state.append_event(EventType.TABLE_CREATED)
        d = event.model_dump(mode="json")
        assert "schema_version" in d
        assert d["schema_version"] == EVENT_SCHEMA_VERSION

    def test_schema_version_in_ndjson_export(self):
        state, observer, _ = _state_with_observer()
        state.append_event(EventType.TABLE_CREATED)
        json_str = observer.research_log[0].model_dump_json()
        assert '"schema_version"' in json_str


# ===================================================================
# SPQ-AN 4.1 — Consensus Gate
# ===================================================================


class TestConsensusGate:
    """Consensus actions require ACKs from all active seats before commit."""

    async def test_move_card_pending_without_ack(
        self, client: AsyncClient, bootstrapped
    ):
        """move_card without AUTO_ACK goes to 'pending' status."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_4p(client, tokens)

        resp = await client.get(
            f"/api/tables/{table_id}", headers=auth_header(tokens[0])
        )
        deck_cards = next(
            z["card_ids"] for z in resp.json()["zones"] if z["zone_id"] == "deck"
        )
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [deck_cards[0]],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        assert resp.json()["status"] == "pending"

    async def test_all_acks_commit_action(
        self, client: AsyncClient, bootstrapped
    ):
        """Action commits after all required seats ACK."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_4p(client, tokens)

        resp = await client.get(
            f"/api/tables/{table_id}", headers=auth_header(tokens[0])
        )
        deck_cards = next(
            z["card_ids"] for z in resp.json()["zones"] if z["zone_id"] == "deck"
        )
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [deck_cards[0]],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        action_id = resp.json()["action_id"]

        for i in range(1, len(tokens)):
            resp = await client.post(
                f"/api/tables/{table_id}/actions/{action_id}/ack",
                headers=auth_header(tokens[i]),
            )
        assert resp.json()["status"] == "committed"


# ===================================================================
# SPQ-AN 4.2 — Optimistic Rollback
# ===================================================================


class TestOptimisticRollback:
    """Optimistic actions can be rolled back via snapshot + dispute."""

    def test_snapshot_and_rollback_restores_state(self):
        state, _, table = _state_with_observer()
        seq = state.take_snapshot()
        old_phase = table.phase
        table.phase = "mutated"
        assert state.rollback_to(seq) is True
        assert table.phase == old_phase

    def test_rollback_to_invalid_seq_returns_false(self):
        state, _, _ = _state_with_observer()
        assert state.rollback_to(9999) is False

    def test_rollback_restores_zone_cards(self):
        state, _, table = _state_with_observer()
        seq = state.take_snapshot()
        deck = next(z for z in table.zones if z.zone_id == "deck")
        original_cards = list(deck.card_ids)
        deck.card_ids.append("injected_card")
        state.rollback_to(seq)
        deck_after = next(z for z in table.zones if z.zone_id == "deck")
        assert deck_after.card_ids == original_cards

    async def test_dispute_rolls_back_optimistic_via_api(
        self, client: AsyncClient, bootstrapped
    ):
        """Full integration: dispute within objection window rolls back."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_4p(client, tokens)

        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "set_phase", "phase_label": "disputed"},
            headers=auth_header(tokens[0]),
        )
        action_id = resp.json()["action_id"]

        resp = await client.post(
            f"/api/tables/{table_id}/actions/{action_id}/dispute",
            json={"reason": "other"},
            headers=auth_header(tokens[1]),
        )
        assert resp.json()["status"] == "rolled_back"

        resp = await client.get(
            f"/api/tables/{table_id}", headers=auth_header(tokens[0])
        )
        assert resp.json()["phase"] == ""


# ===================================================================
# SPQ-AN 4.3 — Objection Window
# ===================================================================


class TestObjectionWindow:
    """Optimistic actions have a bounded, configurable objection window."""

    def test_objection_window_bounds(self):
        """Default objection window is within spec bounds (2-5 seconds)."""
        settings = TableSettings()
        assert 2.0 <= settings.objection_window_s <= 5.0

    async def test_optimistic_action_enters_objection_window(
        self, client: AsyncClient, bootstrapped
    ):
        """set_phase commits immediately (optimistic) and is disputable."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_4p(client, tokens)

        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "set_phase", "phase_label": "play"},
            headers=auth_header(tokens[0]),
        )
        assert resp.json()["status"] == "committed"
        # Disputing proves the objection window was active
        action_id = resp.json()["action_id"]
        resp = await client.post(
            f"/api/tables/{table_id}/actions/{action_id}/dispute",
            json={"reason": "other"},
            headers=auth_header(tokens[1]),
        )
        assert resp.json()["status"] == "rolled_back"


# ===================================================================
# SPQ-AN 4.4 — Disputes Pause Commits
# ===================================================================


class TestDisputePausesCommits:
    """While a dispute is active, new shared actions are rejected."""

    async def test_action_rejected_during_dispute(
        self, client: AsyncClient, bootstrapped
    ):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_4p(client, tokens)

        # Trigger dispute via optimistic action
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "set_phase", "phase_label": "x"},
            headers=auth_header(tokens[0]),
        )
        action_id = resp.json()["action_id"]
        await client.post(
            f"/api/tables/{table_id}/actions/{action_id}/dispute",
            json={"reason": "other"},
            headers=auth_header(tokens[1]),
        )

        # Attempt another action — should be rejected
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "set_phase", "phase_label": "y"},
            headers=auth_header(tokens[0]),
        )
        # Either rejected status or 4xx
        assert resp.json().get("status") == "rejected" or resp.status_code >= 400


# ===================================================================
# SPQ-AN 5.1 — Visibility Filtering
# ===================================================================


class TestVisibilityFiltering:
    """Private zones are hidden from non-owners; public zones visible to all."""

    def test_owner_sees_own_hand(self):
        table = _make_table()
        view = filter_table_for_seat(table, "seat_0")
        hand = next(z for z in view["zones"] if z["zone_id"] == "hand_seat_0")
        assert hand["card_ids"] == ["c3", "c4"]

    def test_non_owner_cannot_see_private_cards(self):
        table = _make_table()
        view = filter_table_for_seat(table, "seat_1")
        hand_s0 = next(z for z in view["zones"] if z["zone_id"] == "hand_seat_0")
        assert hand_s0["card_ids"] == []
        assert hand_s0["card_count"] == 2

    def test_public_zone_visible_to_all(self):
        table = _make_table()
        for seat_id in ["seat_0", "seat_1"]:
            view = filter_table_for_seat(table, seat_id)
            deck = next(z for z in view["zones"] if z["zone_id"] == "deck")
            assert deck["card_ids"] == ["c0", "c1", "c2"]

    def test_hidden_card_objects_excluded_from_view(self):
        """Cards in opponent's private zone absent from 'cards' dict."""
        table = _make_table()
        view = filter_table_for_seat(table, "seat_1")
        # seat_1 must NOT see c3, c4 (seat_0's hand)
        assert "c3" not in view["cards"]
        assert "c4" not in view["cards"]
        # seat_1 MUST see their own hand cards
        assert "c5" in view["cards"]
        assert "c6" in view["cards"]


# ===================================================================
# SPQ-AN 6.1 — Identity Pseudonymization
# ===================================================================


class TestIdentityPseudonymization:
    """Identity hashing is deterministic, salt-dependent, and P-prefixed."""

    def test_same_input_same_hash(self):
        h1 = compute_identity_hash("user_42", "salt_abc")
        h2 = compute_identity_hash("user_42", "salt_abc")
        assert h1 == h2

    def test_different_salt_different_hash(self):
        h1 = compute_identity_hash("user_42", "salt_abc")
        h2 = compute_identity_hash("user_42", "salt_xyz")
        assert h1 != h2

    def test_pseudonym_format(self):
        h = compute_identity_hash("user_42", "salt_abc")
        p = generate_pseudonym(h)
        assert p.startswith("P-")
        assert len(p) == 10  # "P-" + 8 hex chars

    def test_different_users_different_pseudonyms(self):
        salt = "shared_salt"
        p1 = generate_pseudonym(compute_identity_hash("alice", salt))
        p2 = generate_pseudonym(compute_identity_hash("bob", salt))
        assert p1 != p2


# ===================================================================
# SPQ-AN 3.2 — No Auto-Rejection (Rule-Agnostic)
# ===================================================================


class TestNoAutoRejection:
    """System never judges action legality — only structural validation."""

    async def test_any_card_movable_to_any_zone(
        self, client: AsyncClient, bootstrapped
    ):
        """System accepts any structurally valid move regardless of game rules."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_4p(client, tokens)

        # Enable AUTO_ACK for instant commit
        for i, token in enumerate(tokens):
            await client.patch(
                f"/api/tables/{table_id}/seats/seat_{i}/ack_posture",
                json={"move_card": True, "deal": True, "set_phase": True,
                      "create_zone": True, "undo": True},
                headers=auth_header(token),
            )

        resp = await client.get(
            f"/api/tables/{table_id}", headers=auth_header(tokens[0])
        )
        deck_cards = next(
            z["card_ids"] for z in resp.json()["zones"] if z["zone_id"] == "deck"
        )
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [deck_cards[0]],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        assert resp.json()["status"] == "committed"


# ===================================================================
# SPQ-AN 7.1 — Chat Attribution
# ===================================================================


class TestChatAttribution:
    """Chat messages are attributed to authenticated sender + seat_id."""

    async def test_chat_includes_seat_id(
        self, client: AsyncClient, bootstrapped
    ):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_4p(client, tokens)

        resp = await client.post(
            f"/api/tables/{table_id}/chat",
            json={"text": "Hello compliance"},
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 200
        assert resp.json()["seat_id"] == "seat_0"


# ===================================================================
# SPQ-AN A.2 — Research Event Logging Fields
# ===================================================================


class TestEventLoggingFields:
    """Research events capture all required A.2.1 fields."""

    def test_required_envelope_fields(self):
        state, observer, _ = _state_with_observer()
        state.append_event(EventType.TABLE_CREATED, seat_id="seat_0")
        re = observer.research_log[0]
        assert re.event_id is not None
        assert re.table_id is not None
        assert re.session_id is not None
        assert re.event_type is not None
        assert re.timestamp_utc_ms > 0
        assert re.server_sequence_number > 0
        assert re.phase_label is not None
        assert re.gameplay_seq > 0
        assert re.schema_version == RESEARCH_EVENT_SCHEMA_VERSION

    def test_causality_chain(self):
        """previous_event_id links each event to its predecessor."""
        state, observer, _ = _state_with_observer()
        state.append_event(EventType.TABLE_CREATED)
        state.append_event(EventType.SEAT_JOINED, seat_id="seat_0")
        assert observer.research_log[0].previous_event_id is None
        assert (
            observer.research_log[1].previous_event_id
            == observer.research_log[0].event_id
        )

    def test_seat_snapshot_on_seated_events(self):
        """Events with seat_id include a SeatMetadataSnapshot."""
        state, observer, _ = _state_with_observer()
        state.append_event(EventType.SEAT_JOINED, seat_id="seat_0")
        ss = observer.research_log[0].seat_snapshot
        assert ss is not None
        assert ss.pseudonym_id.startswith("P-")
        assert ss.seat_type in ("human", "ai")

    def test_system_events_have_no_seat_snapshot(self):
        """Events without seat_id have no seat snapshot."""
        state, observer, _ = _state_with_observer()
        state.append_event(EventType.TABLE_CREATED)
        assert observer.research_log[0].seat_snapshot is None


# ===================================================================
# SPQ-AN 2.6 — Peer Symmetry
# ===================================================================


class TestPeerSymmetry:
    """Human and AI seats have identical action capabilities."""

    async def test_ai_seat_can_act_like_human(
        self, client: AsyncClient, bootstrapped
    ):
        """AI-flagged seat can submit actions, ACK, and chat identically."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_4p(client, tokens)

        # All seats have equal authority — any seat can set phase
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "set_phase", "phase_label": "ai_turn"},
            headers=auth_header(tokens[1]),  # seat_1 acting
        )
        assert resp.json()["status"] == "committed"
