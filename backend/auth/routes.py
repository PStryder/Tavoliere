from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.deps import get_current_identity
from backend.config import settings
from backend.auth.models import (
    BootstrapRequest,
    BootstrapResponse,
    CredentialPublic,
    CredentialWithSecret,
    TokenPayload,
    TokenRequest,
    TokenResponse,
)
from backend.auth.service import (
    create_credential,
    create_principal,
    create_token,
    list_credentials,
    revoke_credential,
    verify_client_credentials,
)

router = APIRouter()


@router.post("/dev/bootstrap", response_model=BootstrapResponse)
async def dev_bootstrap(req: BootstrapRequest):
    """Create a principal and N AI credentials. Dev/testing only."""
    if not settings.debug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    principal = create_principal(req.display_name)
    creds = [
        create_credential(
            identity_id=principal.identity_id,
            display_name=f"{req.credential_prefix} {i + 1}",
        )
        for i in range(req.num_credentials)
    ]
    return BootstrapResponse(principal=principal, credentials=creds)


@router.post("/api/token", response_model=TokenResponse)
async def token_exchange(req: TokenRequest):
    """Client-credentials token exchange for AI agents."""
    cred = verify_client_credentials(req.client_id, req.client_secret)
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        )
    return create_token(
        identity_id=cred.identity_id,
        credential_id=cred.credential_id,
        player_kind=cred.player_kind,
    )


@router.get("/api/credentials", response_model=list[CredentialPublic])
async def get_credentials(
    identity: TokenPayload = Depends(get_current_identity),
):
    """List credentials for the authenticated principal."""
    return list_credentials(identity.identity_id)


@router.post("/api/credentials", response_model=CredentialWithSecret)
async def create_new_credential(
    display_name: str = "AI Agent",
    identity: TokenPayload = Depends(get_current_identity),
):
    """Create a new AI agent credential."""
    return create_credential(
        identity_id=identity.identity_id,
        display_name=display_name,
    )


@router.delete("/api/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: str,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Revoke an AI agent credential."""
    if not revoke_credential(credential_id, identity.identity_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
