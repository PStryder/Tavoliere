from enum import Enum

from pydantic import BaseModel


class ZoneVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    SEAT_PUBLIC = "seat_public"


class ZoneKind(str, Enum):
    DECK = "deck"
    DISCARD = "discard"
    CENTER = "center"
    HAND = "hand"
    MELD = "meld"
    TRICKS_WON = "tricks_won"
    CUSTOM = "custom"


class Zone(BaseModel):
    zone_id: str
    kind: ZoneKind
    visibility: ZoneVisibility
    owner_seat_id: str | None = None
    card_ids: list[str] = []
    label: str = ""
