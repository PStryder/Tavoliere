"""Research data export and deletion endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from backend.auth.deps import get_current_identity
from backend.auth.models import TokenPayload
from backend.engine.state import get_state
from backend.engine.table_manager import get_seat_for_identity, get_table

router = APIRouter(prefix="/api/tables/{table_id}/research", tags=["research"])


def _require_host(table_id: str, identity: TokenPayload):
    """Verify caller is the host of a research-mode table."""
    table = get_table(table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    if not table.research_mode:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Table is not in research mode")
    seat = get_seat_for_identity(table, identity.effective_identity)
    if not seat or seat.seat_id != table.host_seat_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only host can access research data")

    state = get_state(table_id)
    if not state or not state._research_observer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Research observer not attached")
    return state._research_observer


@router.get("/config")
async def get_research_config(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    observer = _require_host(table_id, identity)
    return observer.config.model_dump()


@router.get("/events")
async def get_research_events(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
    from_seq: int | None = Query(default=None),
    to_seq: int | None = Query(default=None),
    event_type: str | None = Query(default=None),
):
    observer = _require_host(table_id, identity)
    events = observer.research_log

    if from_seq is not None:
        events = [e for e in events if e.server_sequence_number >= from_seq]
    if to_seq is not None:
        events = [e for e in events if e.server_sequence_number <= to_seq]
    if event_type is not None:
        events = [e for e in events if e.event_type == event_type]

    return [e.model_dump(mode="json") for e in events]


@router.get("/events/export")
async def export_research_events_ndjson(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    observer = _require_host(table_id, identity)

    def generate():
        for event in observer.research_log:
            yield event.model_dump_json() + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@router.get("/identities")
async def get_identities(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    observer = _require_host(table_id, identity)
    return [r.model_dump(mode="json") for r in observer.identity_store.values()]


@router.get("/snapshots")
async def get_research_snapshots(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    observer = _require_host(table_id, identity)
    return [s.model_dump(mode="json") for s in observer.snapshots]


@router.delete("/session", status_code=status.HTTP_200_OK)
async def delete_session_data(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    observer = _require_host(table_id, identity)
    count = observer.delete_session_data()
    return {"deleted": count}


@router.delete("/identities/{identity_hash}", status_code=status.HTTP_200_OK)
async def delete_identity_data(
    table_id: str,
    identity_hash: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    observer = _require_host(table_id, identity)
    count = observer.delete_identity_data(identity_hash)
    if count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")
    return {"deleted": count}
