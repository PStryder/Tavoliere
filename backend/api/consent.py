"""Consent management endpoints for research mode."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.auth.deps import get_current_identity
from backend.auth.models import TokenPayload
from backend.engine.research_observer import compute_identity_hash
from backend.engine.state import get_state
from backend.engine.table_manager import get_seat_for_identity, get_table
from backend.models.consent import ConsentRecord, ConsentTier

router = APIRouter(prefix="/api/tables/{table_id}/consent", tags=["consent"])


class ConsentSubmission(BaseModel):
    tiers: dict[ConsentTier, bool]


def _require_research_table(table_id: str):
    table = get_table(table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    if not table.research_mode:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Table is not in research mode")
    state = get_state(table_id)
    if not state or not state._research_observer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Research observer not attached")
    return table, state._research_observer


def _require_seated(table, identity: TokenPayload):
    seat = get_seat_for_identity(table, identity.effective_identity)
    if not seat:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be seated at this table")
    return seat


@router.get("/requirements")
async def get_consent_requirements(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    _require_research_table(table_id)
    return {
        "required": [ConsentTier.RESEARCH_LOGGING.value],
        "optional": [
            t.value for t in ConsentTier
            if t != ConsentTier.RESEARCH_LOGGING
        ],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_consent(
    table_id: str,
    body: ConsentSubmission,
    identity: TokenPayload = Depends(get_current_identity),
):
    table, observer = _require_research_table(table_id)
    seat = _require_seated(table, identity)

    identity_hash = compute_identity_hash(
        identity.effective_identity, observer.config.identity_salt
    )

    record = ConsentRecord(
        identity_hash=identity_hash,
        session_id=observer.config.session_id,
        tiers=body.tiers,
        granted_at=datetime.now(timezone.utc),
    )
    observer.consent_store[identity_hash] = record

    # Handle longitudinal linking consent
    if body.tiers.get(ConsentTier.LONGITUDINAL_LINKING):
        observer.grant_longitudinal_linking(identity_hash)
    else:
        observer.revoke_longitudinal_linking(identity_hash)

    return record.model_dump(mode="json")


@router.get("")
async def get_consent(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    table, observer = _require_research_table(table_id)
    seat = _require_seated(table, identity)

    identity_hash = compute_identity_hash(
        identity.effective_identity, observer.config.identity_salt
    )
    record = observer.consent_store.get(identity_hash)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No consent record found")
    return record.model_dump(mode="json")


@router.delete("", status_code=status.HTTP_200_OK)
async def revoke_consent(
    table_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    table, observer = _require_research_table(table_id)
    seat = _require_seated(table, identity)

    identity_hash = compute_identity_hash(
        identity.effective_identity, observer.config.identity_salt
    )
    record = observer.consent_store.get(identity_hash)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No consent record found")

    record.revoked_at = datetime.now(timezone.utc)
    # Scrub longitudinal linking on revocation
    observer.revoke_longitudinal_linking(identity_hash)
    return {"status": "revoked"}
