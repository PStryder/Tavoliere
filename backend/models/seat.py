from enum import Enum

from pydantic import BaseModel


class Presence(str, Enum):
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    ABSENT = "absent"


class PlayerKind(str, Enum):
    HUMAN = "human"
    AI = "ai"


class AckPosture(BaseModel):
    move_card: bool = False
    deal: bool = False
    set_phase: bool = False
    create_zone: bool = False
    undo: bool = False


class Seat(BaseModel):
    seat_id: str
    display_name: str
    identity_id: str | None = None
    presence: Presence = Presence.ACTIVE
    player_kind: PlayerKind = PlayerKind.HUMAN
    ack_posture: AckPosture = AckPosture()
