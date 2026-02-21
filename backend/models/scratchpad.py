from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ScratchpadVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class ScratchpadAction(str, Enum):
    PROPOSE_EDIT = "propose_edit"
    APPEND = "append"
    CLEAR = "clear"
    REPLACE = "replace"


class Scratchpad(BaseModel):
    scratchpad_id: str
    visibility: ScratchpadVisibility
    owner_seat_id: str | None = None
    content: str = ""
    last_modified_by: str | None = None
    last_modified_at: datetime | None = None


class ScratchpadEdit(BaseModel):
    scratchpad_id: str
    action: ScratchpadAction
    content: str = ""
