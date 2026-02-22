import uuid
from datetime import datetime, timezone

from backend.models.card import Card, DeckRecipe, Rank, Suit

_EUCHRE_RANKS = [Rank.NINE, Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE]
_PINOCHLE_RANKS = [Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE]
_ALL_SUITS = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]


def create_deck(recipe: DeckRecipe) -> list[Card]:
    """Instantiate a list of Card objects from a deck recipe."""
    if recipe == DeckRecipe.STANDARD_52:
        return _make_cards(list(Rank), _ALL_SUITS, copies=1, template_id=recipe.value)
    elif recipe == DeckRecipe.EUCHRE_24:
        return _make_cards(_EUCHRE_RANKS, _ALL_SUITS, copies=1, template_id=recipe.value)
    elif recipe == DeckRecipe.DOUBLE_PINOCHLE_80:
        return _make_cards(_PINOCHLE_RANKS, _ALL_SUITS, copies=4, template_id=recipe.value)
    else:
        raise ValueError(f"Unknown deck recipe: {recipe}")


def _make_cards(
    ranks: list[Rank],
    suits: list[Suit],
    copies: int,
    template_id: str = "",
) -> list[Card]:
    now = datetime.now(timezone.utc)
    cards = []
    for _ in range(copies):
        for suit in suits:
            for rank in ranks:
                cards.append(Card(
                    unique_id=str(uuid.uuid4()),
                    rank=rank,
                    suit=suit,
                    template_id=template_id,
                    created_at=now,
                ))
    return cards
