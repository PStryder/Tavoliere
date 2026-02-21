from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class DisputeReason(str, Enum):
    RULES = "rules"
    TURN = "turn"
    CLARIFY = "clarify"
    OTHER = "other"


class Dispute(BaseModel):
    dispute_id: str
    action_id: str
    disputer_seat_id: str
    reason: DisputeReason | None = None
    reason_text: str | None = None
    created_at: datetime
    resolved: bool = False
    resolution: Literal["revised", "cancelled", "undone", "absent_marked"] | None = None
