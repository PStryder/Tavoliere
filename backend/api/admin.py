"""Admin endpoints for principal/credential management and research health."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.deps import require_admin
from backend.auth.models import TokenPayload
from backend.auth.service import (
    delete_principal,
    force_revoke_credential,
    list_all_credentials,
    list_all_principals,
    list_credentials,
)
from backend.engine.persistence import list_persisted_tables
from backend.engine.table_manager import list_tables

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/principals")
async def get_principals(
    _: TokenPayload = Depends(require_admin),
):
    """List all principals with credential counts."""
    principals = list_all_principals()
    return [
        {
            "identity_id": p.identity_id,
            "display_name": p.display_name,
            "is_admin": p.is_admin,
            "created_at": p.created_at.isoformat(),
            "credential_count": len(list_credentials(p.identity_id)),
        }
        for p in principals
    ]


@router.delete("/principals/{identity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_principal(
    identity_id: str,
    _: TokenPayload = Depends(require_admin),
):
    """Delete a principal + all their credentials."""
    if not delete_principal(identity_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Principal not found")


@router.get("/credentials")
async def get_all_credentials(
    _: TokenPayload = Depends(require_admin),
):
    """List all credentials across all principals."""
    creds = list_all_credentials()
    return [c.model_dump(mode="json") for c in creds]


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_revoke_credential(
    credential_id: str,
    _: TokenPayload = Depends(require_admin),
):
    """Force-revoke any credential."""
    if not force_revoke_credential(credential_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")


@router.get("/research/health")
async def research_health(
    _: TokenPayload = Depends(require_admin),
):
    """Research dashboard metrics."""
    live_tables = list_tables()
    persisted = list_persisted_tables()

    active_research = sum(1 for t in live_tables if t.research_mode)
    total_events = sum(m.get("event_count", 0) for m in persisted)

    # Consent distribution from persisted research metadata
    from backend.engine.persistence import load_research_meta

    consent_distribution: dict[str, int] = {}
    for meta in persisted:
        tid = meta.get("table_id", "")
        r_meta = load_research_meta(tid)
        if r_meta:
            for _hash, consent in r_meta.get("consent", {}).items():
                tiers = consent.get("tiers", {})
                for tier_name, granted in tiers.items():
                    if granted:
                        consent_distribution[tier_name] = consent_distribution.get(tier_name, 0) + 1

    return {
        "active_tables": len(live_tables),
        "active_research_tables": active_research,
        "persisted_sessions": len(persisted),
        "total_persisted_events": total_events,
        "consent_distribution": consent_distribution,
    }
