from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Suit(str, Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"


class Rank(str, Enum):
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"


class DeckRecipe(str, Enum):
    STANDARD_52 = "standard_52"
    EUCHRE_24 = "euchre_24"
    DOUBLE_PINOCHLE_80 = "double_pinochle_80"


class Card(BaseModel):
    unique_id: str
    rank: Rank
    suit: Suit
    face_up: bool = False
    template_id: str = ""
    created_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)
