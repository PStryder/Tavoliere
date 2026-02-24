from enum import Enum

from pydantic import BaseModel, Field


class ZoneVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    SEAT_PUBLIC = "seat_public"
    SHARED_CONTROL = "shared_control"


class ZoneKind(str, Enum):
    DECK = "deck"
    DISCARD = "discard"
    CENTER = "center"
    HAND = "hand"
    MELD = "meld"
    TRICKS_WON = "tricks_won"
    CUSTOM = "custom"
    TRICK_PLAY = "trick_play"
    SCRATCHPAD = "scratchpad"


class ZoneOrdering(str, Enum):
    STACKED = "stacked"
    ORDERED = "ordered"
    UNORDERED = "unordered"


class Zone(BaseModel):
    zone_id: str
    kind: ZoneKind
    visibility: ZoneVisibility
    owner_seat_id: str | None = None
    card_ids: list[str] = []
    label: str = ""
    capacity: int | None = None
    ordering: ZoneOrdering = ZoneOrdering.ORDERED
    face_up_default: bool | None = None
    seat_visibility: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
