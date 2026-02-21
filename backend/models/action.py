from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel

from backend.models.zone import ZoneKind, ZoneVisibility


class ActionClass(str, Enum):
    UNILATERAL = "unilateral"
    CONSENSUS = "consensus"
    OPTIMISTIC = "optimistic"


class ActionType(str, Enum):
    # Unilateral
    REORDER = "reorder"
    SHUFFLE = "shuffle"
    SELF_REVEAL = "self_reveal"
    # Consensus
    MOVE_CARD = "move_card"
    MOVE_CARDS_BATCH = "move_cards_batch"
    DEAL_ROUND_ROBIN = "deal_round_robin"
    CREATE_ZONE = "create_zone"
    UNDO = "undo"
    # Optimistic
    SET_PHASE = "set_phase"


class ActionIntent(BaseModel):
    action_type: ActionType
    card_ids: list[str] = []
    source_zone_id: str | None = None
    target_zone_id: str | None = None
    target_zone_ids: list[str] = []
    new_order: list[str] = []
    phase_label: str | None = None
    zone_kind: ZoneKind | None = None
    zone_visibility: ZoneVisibility | None = None
    zone_label: str | None = None
    target_event_seq: int | None = None


class PendingAction(BaseModel):
    action_id: str
    action_class: ActionClass
    intent: ActionIntent
    proposer_seat_id: str
    required_acks: set[str] = set()
    received_acks: set[str] = set()
    received_nacks: set[str] = set()
    created_at: datetime
    objection_deadline: datetime | None = None
    pre_commit_snapshot_seq: int | None = None
    committed: bool = False
    finalized: bool = False


class ActionResult(BaseModel):
    action_id: str
    status: Literal["committed", "pending", "rejected", "rolled_back", "finalized"]
    reason: str | None = None
