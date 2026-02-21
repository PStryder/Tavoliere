from typing import Literal

from pydantic import BaseModel

from backend.models.action import ActionIntent
from backend.models.dispute import DisputeReason
from backend.models.event import Event
from backend.models.seat import AckPosture


class WSInbound(BaseModel):
    msg_type: Literal["action", "ack", "nack", "dispute", "chat",
                       "set_ack_posture", "ping"]
    intent: ActionIntent | None = None
    action_id: str | None = None
    reason: DisputeReason | None = None
    reason_text: str | None = None
    text: str | None = None
    channel: str | None = None
    ack_posture: AckPosture | None = None


class WSOutbound(BaseModel):
    msg_type: Literal["event", "state_sync", "error", "pong"]
    event: Event | None = None
    state: dict | None = None
    error: str | None = None
    error_code: str | None = None
