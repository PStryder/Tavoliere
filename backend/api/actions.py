from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.deps import get_current_identity
from backend.auth.models import TokenPayload
from backend.engine.action_engine import classify_action, execute_unilateral
from backend.engine.consensus import (
    create_consensus_intent,
    get_pending_actions,
    handle_ack,
    handle_nack,
    resolve_dispute,
)
from backend.engine.optimistic import dispute_optimistic, execute_optimistic
from backend.engine.rate_limiter import RateLimitError
from backend.engine.state import get_or_create_state
from backend.engine.table_manager import get_seat_for_identity, get_table
from backend.models.action import ActionClass, ActionIntent, ActionResult
from backend.models.dispute import DisputeReason
from backend.models.event import EventType
from backend.models.seat import AckPosture

router = APIRouter(prefix="/api/tables/{table_id}", tags=["actions"])


class DisputeRequest(BaseModel):
    reason: DisputeReason | None = None
    reason_text: str | None = None


class ResolveDisputeRequest(BaseModel):
    resolution: str  # "revised", "cancelled", "undone", "absent_marked"


def _get_table_and_seat(table_id: str, identity: TokenPayload):
    table = get_table(table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    seat = get_seat_for_identity(table, identity.effective_identity)
    if not seat:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not seated at this table")
    return table, seat


@router.post("/actions", response_model=ActionResult)
async def submit_action(
    table_id: str,
    intent: ActionIntent,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Submit an action intent."""
    table, seat = _get_table_and_seat(table_id, identity)
    table_state = get_or_create_state(table)

    action_class = classify_action(intent, table)

    try:
        if action_class == ActionClass.UNILATERAL:
            return execute_unilateral(intent, seat, table_state)
        elif action_class == ActionClass.CONSENSUS:
            return create_consensus_intent(intent, seat, table_state)
        elif action_class == ActionClass.OPTIMISTIC:
            return execute_optimistic(intent, seat, table_state)
    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/actions/{action_id}/ack", response_model=ActionResult)
async def ack_action(
    table_id: str,
    action_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    """ACK a pending consensus action."""
    table, seat = _get_table_and_seat(table_id, identity)
    table_state = get_or_create_state(table)
    return handle_ack(table_id, action_id, seat.seat_id, table_state)


@router.post("/actions/{action_id}/nack", response_model=ActionResult)
async def nack_action(
    table_id: str,
    action_id: str,
    req: DisputeRequest | None = None,
    identity: TokenPayload = Depends(get_current_identity),
):
    """NACK a pending consensus action (triggers dispute)."""
    table, seat = _get_table_and_seat(table_id, identity)
    table_state = get_or_create_state(table)

    reason = req.reason.value if req and req.reason else None
    reason_text = req.reason_text if req else None

    return handle_nack(
        table_id, action_id, seat.seat_id, table_state,
        reason=reason, reason_text=reason_text,
    )


@router.get("/actions/pending")
async def list_pending_actions(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    """List pending consensus actions."""
    _get_table_and_seat(table_id, identity)  # auth check
    pending = get_pending_actions(table_id)
    return [
        {
            "action_id": pa.action_id,
            "action_type": pa.intent.action_type.value,
            "proposer_seat_id": pa.proposer_seat_id,
            "required_acks": list(pa.required_acks),
            "received_acks": list(pa.received_acks),
            "received_nacks": list(pa.received_nacks),
        }
        for pa in pending.values()
    ]


@router.post("/actions/{action_id}/dispute")
async def dispute_action(
    table_id: str,
    action_id: str,
    req: DisputeRequest | None = None,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Dispute an optimistic action within the objection window."""
    table, seat = _get_table_and_seat(table_id, identity)
    table_state = get_or_create_state(table)

    reason = req.reason.value if req and req.reason else None
    reason_text = req.reason_text if req else None

    result = dispute_optimistic(
        table_id, action_id, seat.seat_id, table_state,
        reason=reason, reason_text=reason_text,
    )
    if result.status == "rejected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.reason)
    return result


@router.post("/dispute/resolve")
async def resolve_table_dispute(
    table_id: str,
    req: ResolveDisputeRequest,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Resolve an active dispute."""
    table, seat = _get_table_and_seat(table_id, identity)
    if not table.dispute_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active dispute")
    table_state = get_or_create_state(table)
    resolve_dispute(table_state, req.resolution, seat.seat_id)
    return {"status": "resolved", "resolution": req.resolution}


@router.patch("/seats/{seat_id}/ack_posture")
async def update_ack_posture(
    table_id: str,
    seat_id: str,
    posture: AckPosture,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Update a seat's AUTO_ACK posture."""
    table, seat = _get_table_and_seat(table_id, identity)
    if seat.seat_id != seat_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only update your own ACK posture")
    seat.ack_posture = posture
    table_state = get_or_create_state(table)
    table_state.append_event(
        event_type=EventType.ACK_POSTURE_CHANGED,
        seat_id=seat_id,
        data=posture.model_dump(),
    )
    return posture.model_dump()
