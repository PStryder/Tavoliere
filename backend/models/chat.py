from datetime import datetime

from pydantic import BaseModel


class ChatMessage(BaseModel):
    message_id: str
    seat_id: str
    identity_id: str
    text: str
    channel: str = "game"
    thread_id: str | None = None
    timestamp: datetime
