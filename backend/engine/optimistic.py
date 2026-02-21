import asyncio
from datetime import datetime, timezone, timedelta

from backend.engine.consensus import _apply_consensus_mutation
from backend.engine.state import TableState
from backend.models.action import ActionClass, ActionIntent, ActionResult, ActionType, PendingAction
from backend.models.event import EventType
from backend.models.seat import Seat
from backend.models.table import Table

# Optimistic actions awaiting finalization
_optimistic_actions: dict[str, dict[str, PendingAction]] = {}
# Finalization tasks
_finalization_tasks: dict[str, asyncio.Task] = {}


def get_optimistic_actions(table_id: str) -> dict[str, PendingAction]:
    if table_id not in _optimistic_actions:
        _optimistic_actions[table_id] = {}
    return _optimistic_actions[table_id]


def clear_optimistic(table_id: str) -> None:
    _optimistic_actions.pop(table_id, None)
    # Cancel any pending finalization tasks for this table
    to_remove = [k for k in _finalization_tasks if k.startswith(f"{table_id}:")]
    for k in to_remove:
        _finalization_tasks[k].cancel()
        del _finalization_tasks[k]


def execute_optimistic(
    intent: ActionIntent,
    seat: Seat,
    table_state: TableState,
) -> ActionResult:
    """Execute an optimistic action: commit immediately, start objection window."""
    table = table_state.table

    if table.dispute_active:
        return ActionResult(action_id="", status="rejected", reason="Table is in dispute mode")

    action_id = table_state.generate_action_id()
    snapshot_seq = table_state.take_snapshot()

    # Apply mutation immediately
    _apply_optimistic_mutation(intent, seat, table)

    # Set up objection window
    window_s = table.settings.objection_window_s
    deadline = datetime.now(timezone.utc) + timedelta(seconds=window_s)

    pa = PendingAction(
        action_id=action_id,
        action_class=ActionClass.OPTIMISTIC,
        intent=intent,
        proposer_seat_id=seat.seat_id,
        created_at=datetime.now(timezone.utc),
        objection_deadline=deadline,
        pre_commit_snapshot_seq=snapshot_seq,
        committed=True,
    )

    optimistic = get_optimistic_actions(table.table_id)
    optimistic[action_id] = pa

    table_state.append_event(
        event_type=EventType.ACTION_COMMITTED,
        seat_id=seat.seat_id,
        action_id=action_id,
        data={
            "action_type": intent.action_type.value,
            "action_class": ActionClass.OPTIMISTIC.value,
            "intent": intent.model_dump(mode="json"),
            "objection_deadline": deadline.isoformat(),
        },
    )

    # Schedule finalization
    _schedule_finalization(table.table_id, action_id, window_s, table_state)

    return ActionResult(action_id=action_id, status="committed")


def dispute_optimistic(
    table_id: str,
    action_id: str,
    seat_id: str,
    table_state: TableState,
    reason: str | None = None,
    reason_text: str | None = None,
) -> ActionResult:
    """Dispute an optimistic action within the objection window."""
    optimistic = get_optimistic_actions(table_id)
    pa = optimistic.get(action_id)
    if not pa:
        return ActionResult(action_id=action_id, status="rejected", reason="Action not found or already finalized")

    now = datetime.now(timezone.utc)
    if pa.objection_deadline and now > pa.objection_deadline:
        return ActionResult(action_id=action_id, status="rejected", reason="Objection window has closed")

    # Cancel finalization task
    task_key = f"{table_id}:{action_id}"
    task = _finalization_tasks.pop(task_key, None)
    if task:
        task.cancel()

    # Rollback
    table_state.rollback_to(pa.pre_commit_snapshot_seq)
    optimistic.pop(action_id, None)

    table_state.append_event(
        event_type=EventType.ACTION_ROLLED_BACK,
        seat_id=seat_id,
        action_id=action_id,
        data={"reason": reason, "reason_text": reason_text},
    )

    # Enter dispute mode
    table = table_state.table
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

    return ActionResult(action_id=action_id, status="rolled_back")


def _apply_optimistic_mutation(intent: ActionIntent, seat: Seat, table: Table) -> None:
    """Apply an optimistic action mutation."""
    if intent.action_type == ActionType.SET_PHASE:
        if table.settings.phase_locked:
            raise ValueError("Phase changes are locked")
        table.phase = intent.phase_label or ""
    else:
        # Promoted consensus actions use the same mutation logic
        _apply_consensus_mutation(intent, seat.seat_id, table)


def _schedule_finalization(
    table_id: str,
    action_id: str,
    delay_s: float,
    table_state: TableState,
) -> None:
    """Schedule finalization after the objection window."""
    async def _finalize():
        await asyncio.sleep(delay_s)
        optimistic = get_optimistic_actions(table_id)
        pa = optimistic.pop(action_id, None)
        if pa and not pa.finalized:
            pa.finalized = True
            table_state.append_event(
                event_type=EventType.ACTION_FINALIZED,
                seat_id=pa.proposer_seat_id,
                action_id=action_id,
                data={"action_type": pa.intent.action_type.value},
            )
        _finalization_tasks.pop(f"{table_id}:{action_id}", None)

    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(_finalize())
        _finalization_tasks[f"{table_id}:{action_id}"] = task
    except RuntimeError:
        # No event loop running (e.g., in sync tests)
        pass
