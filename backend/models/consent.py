"""Consent management models for research mode."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ConsentTier(str, Enum):
    RESEARCH_LOGGING = "research_logging"
    CHAT_STORAGE = "chat_storage"
    TRAINING_USE = "training_use"
    PUBLICATION = "publication"
    PUBLICATION_EXCERPTS = "publication_excerpts"
    LONGITUDINAL_LINKING = "longitudinal_linking"
    AI_DISCLOSURE_ACK = "ai_disclosure_ack"


class ConsentRecord(BaseModel):
    identity_hash: str
    session_id: str
    tiers: dict[ConsentTier, bool] = {}
    granted_at: datetime
    revoked_at: datetime | None = None


class AIParticipationMetadata(BaseModel):
    """A.9 — Metadata about AI participants in research tables."""
    ai_model_name: str | None = None
    ai_model_version: str | None = None
    ai_provider: str | None = None
    client_type: str | None = None
    client_version: str | None = None
    ai_disclosed_to_players: bool = False
    ai_training_use_allowed: bool = False
    ai_model_metadata_exposed: bool = False
