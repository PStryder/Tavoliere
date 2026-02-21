"""Game history, event replay, and session summary endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth.deps import get_current_identity
from backend.auth.models import TokenPayload
from backend.engine.persistence import list_persisted_tables, load_events, load_meta
from backend.engine.state import get_state
from backend.engine.table_manager import get_table

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/games")
async def list_games(
    identity: TokenPayload = Depends(get_current_identity),
):
    """List persisted tables where the authenticated identity was seated."""
    identity_id = identity.effective_identity
    results = []
    for meta in list_persisted_tables():
        seated = any(s.get("identity_id") == identity_id for s in meta.get("seats", []))
        if seated:
            results.append(meta)
    results.sort(key=lambda m: m.get("destroyed_at", ""), reverse=True)
    return results


@router.get("/tables/{table_id}/events")
async def get_events(
    table_id: str,
    from_seq: int | None = Query(None, ge=0),
    to_seq: int | None = Query(None, ge=0),
    event_type: str | None = Query(None),
    identity: TokenPayload = Depends(get_current_identity),
):
    """Return event log for a table (live or persisted)."""
    # Try live table first
    from backend.engine.table_manager import get_table as get_live_table

    live_table = get_live_table(table_id)
    state = get_state(table_id)
    if state:
        events = state.event_log
    elif live_table:
        events = []  # Live table exists but no events yet
    else:
        events = load_events(table_id)
        if events is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")

    # Apply filters
    filtered = events
    if from_seq is not None:
        filtered = [e for e in filtered if e.seq >= from_seq]
    if to_seq is not None:
        filtered = [e for e in filtered if e.seq <= to_seq]
    if event_type:
        filtered = [e for e in filtered if e.event_type.value == event_type]

    return [e.model_dump(mode="json") for e in filtered]


@router.get("/tables/{table_id}/summary")
async def get_summary(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Return a session summary for a table (live or persisted)."""
    # Try live table
    table = get_table(table_id)
    state = get_state(table_id) if table else None

    if state and table:
        events = state.event_log
        meta = {
            "table_id": table.table_id,
            "display_name": table.display_name,
            "deck_recipe": table.deck_recipe.value,
            "seats": [
                {"seat_id": s.seat_id, "display_name": s.display_name, "identity_id": s.identity_id}
                for s in table.seats
            ],
            "research_mode": table.research_mode,
            "created_at": table.created_at.isoformat(),
        }
    else:
        meta = load_meta(table_id)
        events_list = load_events(table_id)
        if meta is None or events_list is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
        from backend.models.event import Event
        events = events_list

    # Compute summary stats
    from backend.models.event import EventType

    total_actions = sum(1 for e in events if e.event_type == EventType.ACTION_COMMITTED)
    total_disputes = sum(1 for e in events if e.event_type == EventType.DISPUTE_OPENED)
    total_undos = sum(
        1 for e in events
        if e.event_type == EventType.ACTION_COMMITTED
        and e.data.get("intent", {}).get("action_type") == "undo"
    )

    # Duration
    duration_s = 0.0
    if events:
        first_ts = events[0].timestamp
        last_ts = events[-1].timestamp
        duration_s = (last_ts - first_ts).total_seconds()

    result = {
        **meta,
        "duration_s": round(duration_s, 1),
        "total_events": len(events),
        "total_actions": total_actions,
        "total_disputes": total_disputes,
        "total_undos": total_undos,
    }

    # If research mode, compute SPQ-AN
    if meta.get("research_mode"):
        from backend.engine.persistence import load_research_events, load_research_meta
        from backend.engine.spqan import compute_session_spqan

        r_events = load_research_events(table_id)
        r_meta = load_research_meta(table_id)
        if r_events and r_meta:
            spqan = compute_session_spqan(
                r_events,
                r_meta.get("identities", {}),
                r_meta.get("snapshots", []),
            )
            result["spqan"] = spqan.model_dump(mode="json")

    return result
