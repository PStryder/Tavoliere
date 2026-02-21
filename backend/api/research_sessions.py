"""Research session browsing, SPQ-AN metric computation, and export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.auth.deps import require_admin
from backend.auth.models import TokenPayload
from backend.engine.persistence import (
    list_persisted_tables,
    load_research_events,
    load_research_meta,
)
from backend.engine.spqan import SessionSPQAN, compute_session_spqan

router = APIRouter(prefix="/api/research", tags=["research-sessions"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ComputeMetricsRequest(BaseModel):
    table_ids: list[str]
    families: list[str] | None = None  # optional filter: ["ce","rc","ns","ca","ssc"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/sessions")
async def list_research_sessions(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    deck_recipe: str | None = Query(None),
    has_ai: bool | None = Query(None),
    _: TokenPayload = Depends(require_admin),
):
    """List persisted tables that have research data."""
    tables = list_persisted_tables()
    results = [t for t in tables if t.get("has_research_data")]

    if date_from:
        results = [t for t in results if t.get("destroyed_at", "") >= date_from]
    if date_to:
        results = [t for t in results if t.get("destroyed_at", "") <= date_to]
    if deck_recipe:
        results = [t for t in results if t.get("deck_recipe") == deck_recipe]
    if has_ai is not None:
        for t in results:
            ai_present = any(
                s.get("player_kind") == "ai" for s in t.get("seats", [])
            )
            t["_has_ai"] = ai_present
        results = [t for t in results if t.get("_has_ai") == has_ai]
        for t in results:
            t.pop("_has_ai", None)

    results.sort(key=lambda t: t.get("destroyed_at", ""), reverse=True)
    return results


@router.post("/metrics/compute")
async def compute_metrics(
    req: ComputeMetricsRequest,
    _: TokenPayload = Depends(require_admin),
) -> list[dict]:
    """Compute SPQ-AN metrics for one or more research sessions."""
    results: list[dict] = []
    for table_id in req.table_ids:
        events = load_research_events(table_id)
        meta = load_research_meta(table_id)
        if events is None or meta is None:
            continue

        identities = meta.get("identities", {})
        snapshots = meta.get("snapshots", [])
        spqan = compute_session_spqan(events, identities, snapshots)

        # Optionally filter families
        result = spqan.model_dump(mode="json")
        if req.families:
            allowed = set(f.lower() for f in req.families)
            for seat in result.get("seats", []):
                for family in ["ce", "rc", "ns", "ca", "ssc"]:
                    if family not in allowed:
                        seat[family] = None
        results.append(result)

    return results


@router.get("/sessions/{table_id}/events")
async def get_research_events(
    table_id: str,
    from_seq: int | None = Query(None, ge=0),
    to_seq: int | None = Query(None, ge=0),
    event_type: str | None = Query(None),
    _: TokenPayload = Depends(require_admin),
):
    """Return persisted research events with optional filters."""
    events = load_research_events(table_id)
    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research events not found",
        )

    filtered = events
    if from_seq is not None:
        filtered = [e for e in filtered if e.get("server_sequence_number", 0) >= from_seq]
    if to_seq is not None:
        filtered = [e for e in filtered if e.get("server_sequence_number", 0) <= to_seq]
    if event_type:
        filtered = [e for e in filtered if e.get("event_type") == event_type]

    return filtered


@router.get("/sessions/{table_id}/events/export")
async def export_research_events(
    table_id: str,
    _: TokenPayload = Depends(require_admin),
):
    """Stream research events as NDJSON for download."""
    events = load_research_events(table_id)
    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research events not found",
        )

    import json

    def generate():
        for ev in events:
            yield json.dumps(ev, separators=(",", ":")) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f"attachment; filename={table_id}.research.ndjson"},
    )
