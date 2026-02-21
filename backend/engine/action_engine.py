import random
import uuid

from backend.engine.rate_limiter import RateLimiter, RateLimitError
from backend.engine.state import TableState
from backend.models.action import ActionClass, ActionIntent, ActionResult, ActionType, PendingAction
from backend.models.event import EventType
from backend.models.seat import Seat
from backend.models.table import Table
from backend.models.zone import Zone, ZoneVisibility

# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _rate_limiter


def classify_action(intent: ActionIntent, table: Table) -> ActionClass:
    """Determine the action class for an intent."""
    if intent.action_type in (ActionType.REORDER, ActionType.SELF_REVEAL):
        return ActionClass.UNILATERAL

    if intent.action_type == ActionType.SHUFFLE:
        if table.settings.shuffle_is_optimistic:
            return ActionClass.OPTIMISTIC
        return ActionClass.UNILATERAL

    if intent.action_type == ActionType.SET_PHASE:
        return ActionClass.OPTIMISTIC

    # Consensus types — check for AUTO_ACK promotion
    if intent.action_type in (
        ActionType.MOVE_CARD,
        ActionType.MOVE_CARDS_BATCH,
        ActionType.DEAL_ROUND_ROBIN,
        ActionType.CREATE_ZONE,
        ActionType.UNDO,
    ):
        # Check if all active seats have AUTO_ACK for this action type
        ack_field = _action_type_to_ack_field(intent.action_type)
        if ack_field and _all_seats_auto_ack(table, ack_field):
            return ActionClass.OPTIMISTIC
        return ActionClass.CONSENSUS

    return ActionClass.CONSENSUS


def execute_unilateral(
    intent: ActionIntent,
    seat: Seat,
    table_state: TableState,
) -> ActionResult:
    """Execute a unilateral action (immediate commit)."""
    table = table_state.table
    _check_rate_limits(seat.seat_id, intent, table)

    action_id = table_state.generate_action_id()
    table_state.take_snapshot()

    if intent.action_type == ActionType.REORDER:
        _apply_reorder(intent, seat, table)
    elif intent.action_type == ActionType.SHUFFLE:
        _apply_shuffle(intent, table)
    elif intent.action_type == ActionType.SELF_REVEAL:
        _apply_self_reveal(intent, seat, table)
    else:
        return ActionResult(action_id=action_id, status="rejected", reason="Unknown unilateral action")

    table_state.append_event(
        event_type=EventType.ACTION_COMMITTED,
        seat_id=seat.seat_id,
        action_id=action_id,
        data={
            "action_type": intent.action_type.value,
            "action_class": ActionClass.UNILATERAL.value,
            "intent": intent.model_dump(mode="json"),
        },
    )

    return ActionResult(action_id=action_id, status="committed")


def _apply_reorder(intent: ActionIntent, seat: Seat, table: Table) -> None:
    """Reorder cards within a zone owned by the seat."""
    zone = _find_zone(table, intent.source_zone_id)
    if not zone:
        raise ValueError(f"Zone {intent.source_zone_id} not found")
    if zone.owner_seat_id != seat.seat_id:
        raise ValueError("Can only reorder your own zones")
    # Validate the new order contains the same cards
    if set(intent.new_order) != set(zone.card_ids):
        raise ValueError("New order must contain exactly the same cards")
    zone.card_ids = intent.new_order


def _apply_shuffle(intent: ActionIntent, table: Table) -> None:
    """Shuffle the deck zone."""
    deck = _find_zone(table, "deck")
    if not deck:
        raise ValueError("Deck zone not found")
    random.shuffle(deck.card_ids)


def _apply_self_reveal(intent: ActionIntent, seat: Seat, table: Table) -> None:
    """Reveal cards in the seat's private zones (set face_up=True)."""
    for card_id in intent.card_ids:
        card = table.cards.get(card_id)
        if not card:
            raise ValueError(f"Card {card_id} not found")
        # Verify the card is in a zone owned by this seat
        owner_zone = _find_zone_containing_card(table, card_id)
        if not owner_zone or owner_zone.owner_seat_id != seat.seat_id:
            raise ValueError(f"Can only reveal your own cards")
        card.face_up = True


def _find_zone(table: Table, zone_id: str | None) -> Zone | None:
    if not zone_id:
        return None
    for zone in table.zones:
        if zone.zone_id == zone_id:
            return zone
    return None


def _find_zone_containing_card(table: Table, card_id: str) -> Zone | None:
    for zone in table.zones:
        if card_id in zone.card_ids:
            return zone
    return None


def _check_rate_limits(seat_id: str, intent: ActionIntent, table: Table) -> None:
    settings = table.settings
    limiter = _rate_limiter

    if intent.action_type == ActionType.SHUFFLE:
        limiter.check(seat_id, "shuffle", 1, settings.shuffle_cooldown_s)
    elif intent.action_type == ActionType.SET_PHASE:
        limiter.check(seat_id, "phase_change", 1, settings.phase_change_cooldown_s)

    # General intent rate limit
    limiter.check(
        seat_id, "intent",
        settings.intent_rate_max_count,
        settings.intent_rate_window_s,
    )


def _action_type_to_ack_field(action_type: ActionType) -> str | None:
    mapping = {
        ActionType.MOVE_CARD: "move_card",
        ActionType.MOVE_CARDS_BATCH: "move_card",
        ActionType.DEAL_ROUND_ROBIN: "deal",
        ActionType.CREATE_ZONE: "create_zone",
        ActionType.UNDO: "undo",
        ActionType.SET_PHASE: "set_phase",
    }
    return mapping.get(action_type)


def _all_seats_auto_ack(table: Table, ack_field: str) -> bool:
    active_seats = [s for s in table.seats if s.presence.value == "active"]
    if len(active_seats) < 2:
        return False
    return all(getattr(s.ack_posture, ack_field, False) for s in active_seats)
