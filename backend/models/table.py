from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.card import Card, DeckRecipe
from backend.models.seat import Seat
from backend.models.zone import Zone


class TableSettings(BaseModel):
    max_seats: int = 4
    objection_window_s: float = Field(default=3.0, ge=2.0, le=5.0)
    shuffle_is_optimistic: bool = False
    min_action_delay_ms: int = 0
    phase_locked: bool = False
    dispute_cooldown_s: float = 3.0
    phase_change_cooldown_s: float = 10.0
    shuffle_cooldown_s: float = 15.0
    intent_rate_max_count: int = 3
    intent_rate_window_s: float = 5.0
    zone_create_cooldown_s: float = 30.0


class TableCreate(BaseModel):
    display_name: str
    deck_recipe: DeckRecipe
    max_seats: int = 4
    settings: TableSettings = TableSettings()
    research_mode: bool = False
    research_mode_version: str = "0.1.0"


class Table(BaseModel):
    table_id: str
    display_name: str
    deck_recipe: DeckRecipe
    host_seat_id: str | None = None
    phase: str = ""
    seats: list[Seat] = []
    zones: list[Zone] = []
    cards: dict[str, Card] = {}
    settings: TableSettings = TableSettings()
    dispute_active: bool = False
    dispute_action_id: str | None = None
    research_mode: bool = False
    research_mode_version: str = "0.1.0"
    created_at: datetime
