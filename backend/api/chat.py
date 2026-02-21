import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.deps import get_current_identity
from backend.auth.models import TokenPayload
from backend.engine.state import get_or_create_state
from backend.engine.table_manager import get_seat_for_identity, get_table
from backend.models.chat import ChatMessage
from backend.models.event import EventType

router = APIRouter(prefix="/api/tables/{table_id}", tags=["chat"])


class ChatRequest(BaseModel):
    text: str
    thread_id: str | None = None


@router.post("/chat", response_model=ChatMessage)
async def send_chat(
    table_id: str,
    req: ChatRequest,
    identity: TokenPayload = Depends(get_current_identity),
):
    """Send a chat message."""
    table = get_table(table_id)
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    seat = get_seat_for_identity(table, identity.effective_identity)
    if not seat:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not seated at this table")

    msg = ChatMessage(
        message_id=str(uuid.uuid4()),
        seat_id=seat.seat_id,
        identity_id=identity.effective_identity,
        text=req.text,
        thread_id=req.thread_id,
        timestamp=datetime.now(timezone.utc),
    )

    table_state = get_or_create_state(table)
    table_state.append_event(
        event_type=EventType.CHAT_MESSAGE,
        seat_id=seat.seat_id,
        data=msg.model_dump(mode="json"),
    )

    return msg
