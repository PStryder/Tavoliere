from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth.models import TokenPayload
from backend.auth.service import get_principal, verify_token

_bearer_scheme = HTTPBearer()


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> TokenPayload:
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return token_data


async def require_admin(
    identity: TokenPayload = Depends(get_current_identity),
) -> TokenPayload:
    principal = get_principal(identity.identity_id)
    if not principal or not principal.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return identity
