from backend.models.card import Card, DeckRecipe, Rank, Suit
from backend.models.zone import Zone, ZoneKind, ZoneVisibility
from backend.models.seat import AckPosture, Seat, Presence, PlayerKind
from backend.models.table import Table, TableCreate, TableSettings
from backend.models.action import ActionClass, ActionIntent, ActionType, PendingAction
from backend.models.event import Event, EventType
from backend.models.chat import ChatMessage
from backend.models.dispute import Dispute, DisputeReason
from backend.models.protocol import WSInbound, WSOutbound


class TestCardModels:
    def test_card_creation(self):
        card = Card(unique_id="c1", rank=Rank.ACE, suit=Suit.SPADES)
        assert card.unique_id == "c1"
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES
        assert card.face_up is False

    def test_card_face_up(self):
        card = Card(unique_id="c1", rank=Rank.KING, suit=Suit.HEARTS, face_up=True)
        assert card.face_up is True

    def test_deck_recipes(self):
        assert DeckRecipe.STANDARD_52 == "standard_52"
        assert DeckRecipe.EUCHRE_24 == "euchre_24"
        assert DeckRecipe.DOUBLE_PINOCHLE_80 == "double_pinochle_80"

    def test_all_ranks(self):
        assert len(Rank) == 13

    def test_all_suits(self):
        assert len(Suit) == 4


class TestZoneModels:
    def test_public_zone(self):
        zone = Zone(zone_id="z1", kind=ZoneKind.CENTER, visibility=ZoneVisibility.PUBLIC)
        assert zone.owner_seat_id is None
        assert zone.card_ids == []

    def test_private_zone(self):
        zone = Zone(
            zone_id="z2",
            kind=ZoneKind.HAND,
            visibility=ZoneVisibility.PRIVATE,
            owner_seat_id="s1",
        )
        assert zone.owner_seat_id == "s1"

    def test_seat_public_zone(self):
        zone = Zone(
            zone_id="z3",
            kind=ZoneKind.MELD,
            visibility=ZoneVisibility.SEAT_PUBLIC,
            owner_seat_id="s1",
            label="Seat 1 Melds",
        )
        assert zone.visibility == ZoneVisibility.SEAT_PUBLIC


class TestSeatModels:
    def test_seat_defaults(self):
        seat = Seat(seat_id="s1", display_name="North")
        assert seat.presence == Presence.ACTIVE
        assert seat.player_kind == PlayerKind.HUMAN
        assert seat.ack_posture.move_card is False

    def test_ai_seat(self):
        seat = Seat(
            seat_id="s1",
            display_name="AI North",
            player_kind=PlayerKind.AI,
            identity_id="id1",
        )
        assert seat.player_kind == PlayerKind.AI


class TestActionModels:
    def test_action_intent(self):
        intent = ActionIntent(
            action_type=ActionType.MOVE_CARD,
            card_ids=["c1"],
            source_zone_id="hand_1",
            target_zone_id="center",
        )
        assert intent.action_type == ActionType.MOVE_CARD
        assert intent.card_ids == ["c1"]

    def test_reorder_intent(self):
        intent = ActionIntent(
            action_type=ActionType.REORDER,
            source_zone_id="hand_1",
            new_order=["c3", "c1", "c2"],
        )
        assert intent.new_order == ["c3", "c1", "c2"]

    def test_set_phase_intent(self):
        intent = ActionIntent(
            action_type=ActionType.SET_PHASE,
            phase_label="bidding",
        )
        assert intent.phase_label == "bidding"


class TestProtocolModels:
    def test_ws_inbound_action(self):
        msg = WSInbound(
            msg_type="action",
            intent=ActionIntent(action_type=ActionType.SHUFFLE),
        )
        assert msg.msg_type == "action"

    def test_ws_inbound_ping(self):
        msg = WSInbound(msg_type="ping")
        assert msg.msg_type == "ping"

    def test_ws_outbound_error(self):
        msg = WSOutbound(
            msg_type="error",
            error="Rate limited",
            error_code="RATE_LIMITED",
        )
        assert msg.error_code == "RATE_LIMITED"
