"""Convention template model — preset table configurations for known card games."""

from datetime import datetime

from pydantic import BaseModel


class ConventionTemplate(BaseModel):
    template_id: str
    name: str
    deck_recipe: str
    seat_count: int
    suggested_phases: list[str] = []
    suggested_settings: dict = {}
    notes: dict[str, str] = {}
    built_in: bool = False
    created_at: datetime


class ConventionCreate(BaseModel):
    name: str
    deck_recipe: str
    seat_count: int
    suggested_phases: list[str] = []
    suggested_settings: dict = {}
    notes: dict[str, str] = {}


class ConventionUpdate(BaseModel):
    name: str | None = None
    deck_recipe: str | None = None
    seat_count: int | None = None
    suggested_phases: list[str] | None = None
    suggested_settings: dict | None = None
    notes: dict[str, str] | None = None
