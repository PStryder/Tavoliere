from datetime import datetime

from pydantic import BaseModel

from backend.models.seat import PlayerKind


class Principal(BaseModel):
    identity_id: str
    display_name: str
    created_at: datetime


class Credential(BaseModel):
    credential_id: str
    identity_id: str
    client_id: str
    client_secret_hash: str
    display_name: str
    player_kind: PlayerKind = PlayerKind.AI
    created_at: datetime


class CredentialWithSecret(BaseModel):
    credential_id: str
    client_id: str
    client_secret: str
    display_name: str
    player_kind: PlayerKind = PlayerKind.AI


class CredentialPublic(BaseModel):
    credential_id: str
    client_id: str
    display_name: str
    player_kind: PlayerKind
    created_at: datetime


class TokenPayload(BaseModel):
    identity_id: str
    credential_id: str | None = None
    player_kind: PlayerKind
    exp: datetime

    @property
    def effective_identity(self) -> str:
        """Unique identity for seat binding.

        AI agents use credential_id (each credential = unique player).
        Humans use identity_id (principal).
        """
        return self.credential_id or self.identity_id


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class BootstrapRequest(BaseModel):
    display_name: str = "Dev Principal"
    num_credentials: int = 4
    credential_prefix: str = "AI Agent"


class BootstrapResponse(BaseModel):
    principal: Principal
    credentials: list[CredentialWithSecret]
