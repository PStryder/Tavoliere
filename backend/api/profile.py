"""Self-service profile management endpoints."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.deps import get_current_identity
from backend.auth.models import TokenPayload
from backend.auth.service import (
    delete_principal,
    get_principal,
    list_credentials,
    update_principal_name,
)
from backend.engine.persistence import list_persisted_tables, load_events

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    display_name: str


@router.get("")
async def get_profile(
    identity: TokenPayload = Depends(get_current_identity),
):
    """Return current principal info + credential count."""
    principal = get_principal(identity.identity_id)
    if not principal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Principal not found")
    creds = list_credentials(identity.identity_id)
    return {
        "identity_id": principal.identity_id,
        "display_name": principal.display_name,
        "is_admin": principal.is_admin,
        "created_at": principal.created_at.isoformat(),
        "credential_count": len(creds),
    }


@router.patch("")
async def update_profile(
    body: ProfileUpdate,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Update display name."""
    principal = update_principal_name(identity.identity_id, body.display_name)
    if not principal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Principal not found")
    return {
        "identity_id": principal.identity_id,
        "display_name": principal.display_name,
        "is_admin": principal.is_admin,
        "created_at": principal.created_at.isoformat(),
    }


@router.get("/data-export")
async def export_data(
    identity: TokenPayload = Depends(get_current_identity),
):
    """Export all personal game data (persisted events where identity was seated)."""
    identity_id = identity.effective_identity
    results = []
    for meta in list_persisted_tables():
        seated = any(s.get("identity_id") == identity_id for s in meta.get("seats", []))
        if seated:
            events = load_events(meta["table_id"])
            results.append({
                "meta": meta,
                "events": [e.model_dump(mode="json") for e in events] if events else [],
            })
    return {"tables": results, "total_tables": len(results)}


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    identity: TokenPayload = Depends(get_current_identity),
):
    """Delete principal + PII purge."""
    if not delete_principal(identity.identity_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Principal not found")
