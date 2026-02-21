import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from backend.auth.models import (
    Credential,
    CredentialPublic,
    CredentialWithSecret,
    Principal,
    TokenPayload,
    TokenResponse,
)
from backend.config import settings
from backend.models.seat import PlayerKind

# In-memory stores
_principals: dict[str, Principal] = {}
_credentials: dict[str, Credential] = {}  # keyed by credential_id
_credentials_by_client_id: dict[str, Credential] = {}


def create_principal(display_name: str) -> Principal:
    principal = Principal(
        identity_id=str(uuid.uuid4()),
        display_name=display_name,
        created_at=datetime.now(timezone.utc),
    )
    _principals[principal.identity_id] = principal
    return principal


def get_principal(identity_id: str) -> Principal | None:
    return _principals.get(identity_id)


def create_credential(
    identity_id: str,
    display_name: str,
    player_kind: PlayerKind = PlayerKind.AI,
) -> CredentialWithSecret:
    client_id = f"tav_{uuid.uuid4().hex[:16]}"
    client_secret = secrets.token_urlsafe(32)
    secret_hash = bcrypt.hashpw(
        client_secret.encode(), bcrypt.gensalt()
    ).decode()

    credential = Credential(
        credential_id=str(uuid.uuid4()),
        identity_id=identity_id,
        client_id=client_id,
        client_secret_hash=secret_hash,
        display_name=display_name,
        player_kind=player_kind,
        created_at=datetime.now(timezone.utc),
    )
    _credentials[credential.credential_id] = credential
    _credentials_by_client_id[credential.client_id] = credential

    return CredentialWithSecret(
        credential_id=credential.credential_id,
        client_id=credential.client_id,
        client_secret=client_secret,
        display_name=credential.display_name,
        player_kind=credential.player_kind,
    )


def list_credentials(identity_id: str) -> list[CredentialPublic]:
    return [
        CredentialPublic(
            credential_id=c.credential_id,
            client_id=c.client_id,
            display_name=c.display_name,
            player_kind=c.player_kind,
            created_at=c.created_at,
        )
        for c in _credentials.values()
        if c.identity_id == identity_id
    ]


def revoke_credential(credential_id: str, identity_id: str) -> bool:
    cred = _credentials.get(credential_id)
    if not cred or cred.identity_id != identity_id:
        return False
    _credentials_by_client_id.pop(cred.client_id, None)
    _credentials.pop(credential_id, None)
    return True


def verify_client_credentials(client_id: str, client_secret: str) -> Credential | None:
    cred = _credentials_by_client_id.get(client_id)
    if not cred:
        return None
    if not bcrypt.checkpw(client_secret.encode(), cred.client_secret_hash.encode()):
        return None
    return cred


def create_token(identity_id: str, credential_id: str | None, player_kind: PlayerKind) -> TokenResponse:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "identity_id": identity_id,
        "credential_id": credential_id,
        "player_kind": player_kind.value,
        "exp": expires,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


def verify_token(token: str) -> TokenPayload | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenPayload(
            identity_id=payload["identity_id"],
            credential_id=payload.get("credential_id"),
            player_kind=PlayerKind(payload["player_kind"]),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
    except JWTError:
        return None
