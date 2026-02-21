"""In-memory convention template store with built-in presets."""

import uuid
from datetime import datetime, timezone

from backend.models.convention import ConventionCreate, ConventionTemplate, ConventionUpdate

_conventions: dict[str, ConventionTemplate] = {}


def _seed_builtins() -> None:
    """Register built-in convention templates."""
    builtins = [
        ConventionTemplate(
            template_id="builtin_euchre",
            name="Euchre - Standard",
            deck_recipe="euchre_24",
            seat_count=4,
            suggested_phases=["Deal", "Bid", "Play", "Score"],
            suggested_settings={"max_seats": 4},
            notes={
                "Bidding": "Dealer turns up top card. Players may order it up or pass. "
                "Second round: players name any suit except the turned-down suit.",
                "Trumps": "Right bower (J of trump) is highest, then left bower "
                "(J of same colour).",
                "Scoring": "Team that called trump must take 3+ tricks. "
                "Euchre (callers take <3) awards 2 points to defenders.",
            },
            built_in=True,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
        ConventionTemplate(
            template_id="builtin_pinochle",
            name="Double Pinochle",
            deck_recipe="pinochle_80",
            seat_count=4,
            suggested_phases=["Deal", "Bid", "Meld", "Play", "Score"],
            suggested_settings={"max_seats": 4},
            notes={
                "Deck": "80 cards — two copies of 9-A in each suit.",
                "Bidding": "Minimum bid 50. Partners combine melds.",
                "Melding": "Lay melds face-up. Common melds: marriage, pinochle, "
                "around, run.",
                "Play": "Must follow suit. Must play higher if possible. "
                "Must trump if void in led suit.",
            },
            built_in=True,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
    ]
    for t in builtins:
        _conventions[t.template_id] = t


_seed_builtins()


def list_conventions() -> list[ConventionTemplate]:
    return list(_conventions.values())


def get_convention(template_id: str) -> ConventionTemplate | None:
    return _conventions.get(template_id)


def create_convention(req: ConventionCreate) -> ConventionTemplate:
    template = ConventionTemplate(
        template_id=str(uuid.uuid4()),
        name=req.name,
        deck_recipe=req.deck_recipe,
        seat_count=req.seat_count,
        suggested_phases=req.suggested_phases,
        suggested_settings=req.suggested_settings,
        notes=req.notes,
        built_in=False,
        created_at=datetime.now(timezone.utc),
    )
    _conventions[template.template_id] = template
    return template


def update_convention(template_id: str, updates: ConventionUpdate) -> ConventionTemplate | None:
    template = _conventions.get(template_id)
    if not template or template.built_in:
        return None
    for field, value in updates.model_dump(exclude_none=True).items():
        setattr(template, field, value)
    return template


def delete_convention(template_id: str) -> bool:
    template = _conventions.get(template_id)
    if not template or template.built_in:
        return False
    _conventions.pop(template_id, None)
    return True
