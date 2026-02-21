from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from backend.models.schema_version import EVENT_SCHEMA_VERSION


class EventType(str, Enum):
    ACTION_COMMITTED = "action_committed"
    ACTION_FINALIZED = "action_finalized"
    ACTION_ROLLED_BACK = "action_rolled_back"
    INTENT_CREATED = "intent_created"
    ACK_RECEIVED = "ack_received"
    NACK_RECEIVED = "nack_received"
    DISPUTE_OPENED = "dispute_opened"
    DISPUTE_RESOLVED = "dispute_resolved"
    SEAT_JOINED = "seat_joined"
    SEAT_LEFT = "seat_left"
    PRESENCE_CHANGED = "presence_changed"
    PHASE_CHANGED = "phase_changed"
    CHAT_MESSAGE = "chat_message"
    TABLE_CREATED = "table_created"
    ZONE_CREATED = "zone_created"
    ACK_POSTURE_CHANGED = "ack_posture_changed"


class Event(BaseModel):
    schema_version: str = EVENT_SCHEMA_VERSION
    seq: int
    event_type: EventType
    table_id: str
    seat_id: str | None = None
    action_id: str | None = None
    timestamp: datetime
    data: dict = {}
