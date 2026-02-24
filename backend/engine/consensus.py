import asyncio
import uuid
from datetime import datetime, timezone

from backend.engine.state import TableState
from backend.models.action import ActionClass, ActionIntent, ActionResult, ActionType, PendingAction
from backend.models.event import EventType
from backend.models.seat import Presence, Seat
from backend.models.table import Table
from backend.models.zone import Zone, ZoneKind, ZoneVisibility

# Pending actions per table
_pending_actions: dict[str, dict[str, PendingAction]] = {}
# Timeout tasks per pending action (keyed "{table_id}:{action_id}")
_timeout_tasks: dict[str, asyncio.Task] = {}


def get_pending_actions(table_id: str) -> dict[str, PendingAction]:
    if table_id not in _pending_actions:
        _pending_actions[table_id] = {}
    return _pending_actions[table_id]


def clear_pending(table_id: str) -> None:
    _pending_actions.pop(table_id, None)
    # Cancel any timeout tasks for this table
    to_remove = [k for k in _timeout_tasks if k.startswith(f"{table_id}:")]
    for k in to_remove:
        _timeout_tasks[k].cancel()
        del _timeout_tasks[k]


def create_consensus_intent(
    intent: ActionIntent,
    seat: Seat,
    table_state: TableState,
) -> ActionResult:
    """Create a pending consensus action and broadcast INTENT_CREATED."""
    table = table_state.table
    pending = get_pending_actions(table.table_id)

    # Check: only 1 pending per seat
    for pa in pending.values():
        if pa.proposer_seat_id == seat.seat_id:
            return ActionResult(
                action_id="",
                status="rejected",
                reason="You already have a pending consensus action",
            )

    # Check: not in dispute
    if table.dispute_active:
        return ActionResult(
            action_id="",
            status="rejected",
            reason="Table is in dispute mode",
        )

    # Validate the intent
    _validate_consensus_intent(intent, seat, table)

    action_id = table_state.generate_action_id()
    required_acks = {
        s.seat_id
        for s in table.seats
        if s.presence == Presence.ACTIVE and s.seat_id != seat.seat_id
    }

    pa = PendingAction(
        action_id=action_id,
        action_class=ActionClass.CONSENSUS,
        intent=intent,
        proposer_seat_id=seat.seat_id,
        required_acks=required_acks,
        created_at=datetime.now(timezone.utc),
    )
    pending[action_id] = pa

    table_state.append_event(
        event_type=EventType.INTENT_CREATED,
        seat_id=seat.seat_id,
        action_id=action_id,
        data={
            "action_type": intent.action_type.value,
            "intent": intent.model_dump(mode="json"),
            "required_acks": list(required_acks),
        },
    )

    # If no ACKs required (solo player), commit immediately
    if not required_acks:
        return _commit_consensus(pa, table_state)

    # Schedule consensus timeout
    _schedule_timeout(table.table_id, action_id, table_state)

    return ActionResult(action_id=action_id, status="pending")


def handle_ack(
    table_id: str,
    action_id: str,
    seat_id: str,
    table_state: TableState,
) -> ActionResult:
    """Process an ACK for a pending consensus action."""
    pending = get_pending_actions(table_id)
    pa = pending.get(action_id)
    if not pa:
        return ActionResult(action_id=action_id, status="rejected", reason="Action not found or already resolved")
    if seat_id not in pa.required_acks:
        return ActionResult(action_id=action_id, status="rejected", reason="ACK not required from this seat")
    if seat_id in pa.received_acks:
        return ActionResult(action_id=action_id, status="rejected", reason="Already ACKed")

    pa.received_acks.add(seat_id)

    table_state.append_event(
        event_type=EventType.ACK_RECEIVED,
        seat_id=seat_id,
        action_id=action_id,
        data={"acks_remaining": list(pa.required_acks - pa.received_acks)},
    )

    # Check if all ACKs received
    if pa.required_acks <= pa.received_acks:
        return _commit_consensus(pa, table_state)

    return ActionResult(action_id=action_id, status="pending")


def handle_nack(
    table_id: str,
    action_id: str,
    seat_id: str,
    table_state: TableState,
    reason: str | None = None,
    reason_text: str | None = None,
) -> ActionResult:
    """Process a NACK — triggers dispute mode."""
    pending = get_pending_actions(table_id)
    pa = pending.get(action_id)
    if not pa:
        return ActionResult(action_id=action_id, status="rejected", reason="Action not found or already resolved")

    pa.received_nacks.add(seat_id)
    table = table_state.table

    # Cancel timeout task — dispute takes over
    _cancel_timeout(table_id, action_id)

    table_state.append_event(
        event_type=EventType.NACK_RECEIVED,
        seat_id=seat_id,
        action_id=action_id,
        data={"reason": reason, "reason_text": reason_text},
    )

    # Enter dispute mode
    table.dispute_active = True
    table.dispute_action_id = action_id

    table_state.append_event(
        event_type=EventType.DISPUTE_OPENED,
        seat_id=seat_id,
        action_id=action_id,
        data={
            "disputer_seat_id": seat_id,
            "reason": reason,
            "reason_text": reason_text,
        },
    )

    # Remove from pending (dispute takes over)
    pending.pop(action_id, None)

    return ActionResult(action_id=action_id, status="rejected", reason="Disputed")


def resolve_dispute(
    table_state: TableState,
    resolution: str,
    seat_id: str,
) -> None:
    """Resolve an active dispute."""
    table = table_state.table
    action_id = table.dispute_action_id
    table.dispute_active = False
    table.dispute_action_id = None

    table_state.append_event(
        event_type=EventType.DISPUTE_RESOLVED,
        seat_id=seat_id,
        action_id=action_id,
        data={"resolution": resolution},
    )


def _commit_consensus(pa: PendingAction, table_state: TableState) -> ActionResult:
    """Commit a fully-ACKed consensus action."""
    table = table_state.table
    pending = get_pending_actions(table.table_id)

    # Cancel timeout task if running
    _cancel_timeout(table.table_id, pa.action_id)

    # Handle UNDO via snapshot rollback before normal mutation path
    if pa.intent.action_type == ActionType.UNDO:
        if pa.intent.target_event_seq is None:
            pending.pop(pa.action_id, None)
            return ActionResult(action_id=pa.action_id, status="rejected", reason="Missing target_event_seq")
        success = table_state.rollback_to(pa.intent.target_event_seq)
        if not success:
            pending.pop(pa.action_id, None)
            return ActionResult(action_id=pa.action_id, status="rejected", reason="Snapshot not found for target seq")
        pending.pop(pa.action_id, None)
        table_state.append_event(
            event_type=EventType.ACTION_COMMITTED,
            seat_id=pa.proposer_seat_id,
            action_id=pa.action_id,
            data={
                "action_type": pa.intent.action_type.value,
                "action_class": ActionClass.CONSENSUS.value,
                "intent": pa.intent.model_dump(mode="json"),
            },
        )
        return ActionResult(action_id=pa.action_id, status="committed")

    table_state.take_snapshot()
    _apply_consensus_mutation(pa.intent, pa.proposer_seat_id, table)
    pending.pop(pa.action_id, None)

    table_state.append_event(
        event_type=EventType.ACTION_COMMITTED,
        seat_id=pa.proposer_seat_id,
        action_id=pa.action_id,
        data={
            "action_type": pa.intent.action_type.value,
            "action_class": ActionClass.CONSENSUS.value,
            "intent": pa.intent.model_dump(mode="json"),
        },
    )

    return ActionResult(action_id=pa.action_id, status="committed")


def _cancel_timeout(table_id: str, action_id: str) -> None:
    """Cancel a pending timeout task if it exists."""
    task_key = f"{table_id}:{action_id}"
    task = _timeout_tasks.pop(task_key, None)
    if task:
        task.cancel()


def _schedule_timeout(
    table_id: str,
    action_id: str,
    table_state: TableState,
) -> None:
    """Schedule auto-rollback after consensus_timeout_s."""
    timeout_s = table_state.table.settings.consensus_timeout_s

    async def _timeout_consensus():
        await asyncio.sleep(timeout_s)
        pending = get_pending_actions(table_id)
        pa = pending.pop(action_id, None)
        if pa:
            log_start = len(table_state.event_log)
            table_state.append_event(
                event_type=EventType.ACTION_ROLLED_BACK,
                seat_id=pa.proposer_seat_id,
                action_id=action_id,
                data={"reason": "consensus_timeout"},
            )
            from backend.api.ws import broadcast_event

            for event in table_state.event_log[log_start:]:
                await broadcast_event(table_id, event)
        _timeout_tasks.pop(f"{table_id}:{action_id}", None)

    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(_timeout_consensus())
        _timeout_tasks[f"{table_id}:{action_id}"] = task
    except RuntimeError:
        # No event loop running (e.g., in sync tests)
        pass


def _validate_consensus_intent(intent: ActionIntent, seat: Seat, table: Table) -> None:
    """Validate a consensus intent before creating it as pending."""
    if intent.action_type == ActionType.MOVE_CARD:
        if not intent.card_ids:
            raise ValueError("move_card requires card_ids")
        if not intent.source_zone_id or not intent.target_zone_id:
            raise ValueError("move_card requires source_zone_id and target_zone_id")
        _validate_cards_in_zone(intent.card_ids, intent.source_zone_id, table)

    elif intent.action_type == ActionType.MOVE_CARDS_BATCH:
        if not intent.card_ids:
            raise ValueError("move_cards_batch requires card_ids")
        if not intent.source_zone_id or not intent.target_zone_id:
            raise ValueError("move_cards_batch requires source_zone_id and target_zone_id")
        _validate_cards_in_zone(intent.card_ids, intent.source_zone_id, table)

    elif intent.action_type == ActionType.DEAL_ROUND_ROBIN:
        if not intent.target_zone_ids:
            raise ValueError("deal_round_robin requires target_zone_ids")
        if not intent.card_ids:
            raise ValueError("deal_round_robin requires card_ids (cards to deal)")

    elif intent.action_type == ActionType.CREATE_ZONE:
        if not intent.zone_label:
            raise ValueError("create_zone requires zone_label")

    elif intent.action_type == ActionType.UNDO:
        if intent.target_event_seq is None:
            raise ValueError("undo requires target_event_seq")


def _validate_cards_in_zone(card_ids: list[str], zone_id: str, table: Table) -> None:
    zone = None
    for z in table.zones:
        if z.zone_id == zone_id:
            zone = z
            break
    if not zone:
        raise ValueError(f"Zone {zone_id} not found")
    for cid in card_ids:
        if cid not in zone.card_ids:
            raise ValueError(f"Card {cid} not in zone {zone_id}")


def _apply_consensus_mutation(intent: ActionIntent, proposer_seat_id: str, table: Table) -> None:
    """Apply a consensus action mutation to the table state."""
    if intent.action_type in (ActionType.MOVE_CARD, ActionType.MOVE_CARDS_BATCH):
        _move_cards(intent.card_ids, intent.source_zone_id, intent.target_zone_id, table)

    elif intent.action_type == ActionType.DEAL_ROUND_ROBIN:
        _deal_round_robin(intent.card_ids, intent.source_zone_id or "deck", intent.target_zone_ids, table)

    elif intent.action_type == ActionType.CREATE_ZONE:
        _create_zone(intent, proposer_seat_id, table)

    elif intent.action_type == ActionType.UNDO:
        # Undo handled at a higher level via snapshot rollback
        pass


def _move_cards(card_ids: list[str], source_id: str, target_id: str, table: Table) -> None:
    source = target = None
    for z in table.zones:
        if z.zone_id == source_id:
            source = z
        if z.zone_id == target_id:
            target = z
    if not source or not target:
        raise ValueError("Source or target zone not found")

    # Pre-validate all cards exist in source before mutating
    for cid in card_ids:
        if cid not in source.card_ids:
            raise ValueError(f"Card {cid} not in source zone {source_id}")

    for cid in card_ids:
        source.card_ids.remove(cid)
        target.card_ids.append(cid)
        if target.face_up_default is not None:
            card = table.cards.get(cid)
            if card:
                card.face_up = target.face_up_default


def _deal_round_robin(
    card_ids: list[str],
    source_zone_id: str,
    target_zone_ids: list[str],
    table: Table,
) -> None:
    source = None
    targets = []
    for z in table.zones:
        if z.zone_id == source_zone_id:
            source = z
        if z.zone_id in target_zone_ids:
            targets.append(z)

    if not source:
        raise ValueError(f"Source zone {source_zone_id} not found")

    # Sort targets to match requested order
    target_map = {z.zone_id: z for z in targets}
    ordered_targets = [target_map[zid] for zid in target_zone_ids if zid in target_map]

    if not ordered_targets:
        raise ValueError("No valid target zones found")

    # Pre-validate all cards exist in source before mutating
    for cid in card_ids:
        if cid not in source.card_ids:
            raise ValueError(f"Card {cid} not in source zone {source_zone_id}")

    # Deal round-robin
    for i, cid in enumerate(card_ids):
        target = ordered_targets[i % len(ordered_targets)]
        source.card_ids.remove(cid)
        target.card_ids.append(cid)
        if target.face_up_default is not None:
            card = table.cards.get(cid)
            if card:
                card.face_up = target.face_up_default


def _create_zone(intent: ActionIntent, proposer_seat_id: str, table: Table) -> None:
    zone_id = f"custom_{uuid.uuid4().hex[:8]}"
    zone = Zone(
        zone_id=zone_id,
        kind=intent.zone_kind or ZoneKind.CUSTOM,
        visibility=intent.zone_visibility or ZoneVisibility.PUBLIC,
        owner_seat_id=proposer_seat_id if intent.zone_visibility in (
            ZoneVisibility.PRIVATE, ZoneVisibility.SEAT_PUBLIC
        ) else None,
        label=intent.zone_label or "",
    )
    table.zones.append(zone)
