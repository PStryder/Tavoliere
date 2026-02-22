from fastapi import APIRouter, Depends, HTTPException

from backend.auth.deps import get_current_identity
from backend.engine.action_engine import get_rate_limiter
from backend.engine.rate_limiter import RateLimitError
from backend.engine.scratchpad import apply_scratchpad_edit
from backend.engine.state import get_state
from backend.engine.table_manager import get_seat_for_identity, get_table
from backend.models.scratchpad import ScratchpadEdit, ScratchpadVisibility

router = APIRouter(prefix="/api/tables/{table_id}/scratchpads", tags=["scratchpads"])

# Scratchpad rate limit: 10 edits per 5 seconds per seat
_SP_RATE_MAX = 10
_SP_RATE_WINDOW_S = 5.0


def _resolve_seat(table_id: str, identity_id: str):
    table = get_table(table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    seat = get_seat_for_identity(table, identity_id)
    if not seat:
        raise HTTPException(status_code=403, detail="Not seated at this table")
    return table, seat


@router.get("")
async def list_scratchpads(
    table_id: str,
    identity_id: str = Depends(get_current_identity),
):
    """List scratchpads visible to the requesting seat."""
    table, seat = _resolve_seat(table_id, identity_id)
    result = {}
    for sp_id, sp in table.scratchpads.items():
        if sp.visibility == ScratchpadVisibility.PUBLIC or sp.owner_seat_id == seat.seat_id:
            result[sp_id] = sp.model_dump(mode="json")
    return result


@router.get("/{scratchpad_id}")
async def get_scratchpad(
    table_id: str,
    scratchpad_id: str,
    identity_id: str = Depends(get_current_identity),
):
    """Get a single scratchpad."""
    table, seat = _resolve_seat(table_id, identity_id)
    sp = table.scratchpads.get(scratchpad_id)
    if not sp:
        raise HTTPException(status_code=404, detail="Scratchpad not found")
    if sp.visibility == ScratchpadVisibility.PRIVATE and sp.owner_seat_id != seat.seat_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this scratchpad")
    return sp.model_dump(mode="json")


@router.post("/{scratchpad_id}/edit")
async def edit_scratchpad(
    table_id: str,
    scratchpad_id: str,
    body: ScratchpadEdit,
    identity_id: str = Depends(get_current_identity),
):
    """Submit a scratchpad edit."""
    table, seat = _resolve_seat(table_id, identity_id)
    state = get_state(table_id)
    if not state:
        raise HTTPException(status_code=404, detail="Table state not found")

    # Rate limit scratchpad edits
    try:
        get_rate_limiter().check(seat.seat_id, "scratchpad_edit", _SP_RATE_MAX, _SP_RATE_WINDOW_S)
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Scratchpad edit rate limit exceeded")

    # Override scratchpad_id from path
    body.scratchpad_id = scratchpad_id

    try:
        event_data = apply_scratchpad_edit(body, seat.seat_id, state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "ok", "event_data": event_data}
