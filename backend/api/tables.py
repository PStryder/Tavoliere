from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.deps import get_current_identity
from backend.auth.models import TokenPayload
from backend.engine.state import get_or_create_state
from backend.engine.table_manager import (
    create_table,
    delete_table,
    get_seat_for_identity,
    get_table,
    join_table,
    leave_table,
    list_tables,
)
from backend.engine.visibility import filter_table_for_seat
from backend.api.ws import broadcast_event
from backend.models.consent import AIParticipationMetadata
from backend.models.seat import Seat
from backend.models.table import Table, TableCreate, TableSettings

router = APIRouter(prefix="/api/tables", tags=["tables"])


class JoinRequest(BaseModel):
    display_name: str
    ai_metadata: AIParticipationMetadata | None = None


@router.post("", response_model=Table, status_code=status.HTTP_201_CREATED)
async def create_new_table(
    req: TableCreate,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Create a new table."""
    return create_table(req)


@router.get("")
async def get_tables(
    identity: TokenPayload = Depends(get_current_identity),
):
    """List all active tables (summary only)."""
    tables = list_tables()
    return [
        {
            "table_id": t.table_id,
            "display_name": t.display_name,
            "deck_recipe": t.deck_recipe.value,
            "seat_count": len(t.seats),
            "max_seats": t.settings.max_seats,
            "research_mode": t.research_mode,
            "created_at": t.created_at.isoformat(),
        }
        for t in tables
    ]


@router.get("/{table_id}")
async def get_table_by_id(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Get visibility-filtered table state."""
    table = get_table(table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    seat = get_seat_for_identity(table, identity.effective_identity)
    if seat:
        return filter_table_for_seat(table, seat.seat_id)
    # Not seated — return public-only view (no private zone contents)
    return filter_table_for_seat(table, "__observer__")


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def destroy_table(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Destroy a table (host only)."""
    table = get_table(table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    seat = get_seat_for_identity(table, identity.effective_identity)
    if not seat or seat.seat_id != table.host_seat_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only host can destroy table")

    # Fire TABLE_DESTROYED event and broadcast to all connected clients before deletion
    from backend.models.event import EventType

    table_state = get_or_create_state(table)
    event = table_state.append_event(
        event_type=EventType.TABLE_DESTROYED,
        seat_id=seat.seat_id,
        data={"reason": "host_destroyed"},
    )
    await broadcast_event(table_id, event.model_dump(mode="json"))

    delete_table(table_id)


@router.post("/{table_id}/join", response_model=Seat)
async def join_seat(
    table_id: str,
    req: JoinRequest,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Join a seat at the table."""
    seat = join_table(
        table_id=table_id,
        identity_id=identity.effective_identity,
        display_name=req.display_name,
        player_kind=identity.player_kind,
        ai_metadata=req.ai_metadata,
    )
    if seat is None:
        table = get_table(table_id)
        if not table:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Table is full")
    return seat


@router.post("/{table_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_seat(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Leave a seat at the table."""
    if not leave_table(table_id, identity.effective_identity):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not seated at this table")


@router.patch("/{table_id}/settings")
async def update_settings(
    table_id: str,
    updates: dict,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Update table settings (host only)."""
    table = get_table(table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    seat = get_seat_for_identity(table, identity.effective_identity)
    if not seat or seat.seat_id != table.host_seat_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only host can update settings")

    current = table.settings.model_dump()
    current.update(updates)
    table.settings = TableSettings(**current)
    return table.settings.model_dump()
