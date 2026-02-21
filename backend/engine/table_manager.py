import uuid
from datetime import datetime, timezone

from backend.engine.deck import create_deck
from backend.models.card import Card
from backend.models.seat import PlayerKind, Presence, Seat
from backend.models.table import Table, TableCreate
from backend.models.zone import Zone, ZoneKind, ZoneVisibility

# In-memory table registry
_tables: dict[str, Table] = {}


def create_table(req: TableCreate) -> Table:
    table = Table(
        table_id=str(uuid.uuid4()),
        display_name=req.display_name,
        deck_recipe=req.deck_recipe,
        settings=req.settings,
        created_at=datetime.now(timezone.utc),
    )

    # Instantiate deck and populate card registry
    cards = create_deck(req.deck_recipe)
    table.cards = {c.unique_id: c for c in cards}

    # Create default public zones
    deck_zone = Zone(
        zone_id="deck",
        kind=ZoneKind.DECK,
        visibility=ZoneVisibility.PUBLIC,
        label="Deck",
        card_ids=[c.unique_id for c in cards],
    )
    discard_zone = Zone(
        zone_id="discard",
        kind=ZoneKind.DISCARD,
        visibility=ZoneVisibility.PUBLIC,
        label="Discard",
    )
    center_zone = Zone(
        zone_id="center",
        kind=ZoneKind.CENTER,
        visibility=ZoneVisibility.PUBLIC,
        label="Center",
    )
    table.zones = [deck_zone, discard_zone, center_zone]

    _tables[table.table_id] = table
    return table


def get_table(table_id: str) -> Table | None:
    return _tables.get(table_id)


def list_tables() -> list[Table]:
    return list(_tables.values())


def delete_table(table_id: str) -> bool:
    return _tables.pop(table_id, None) is not None


def join_table(
    table_id: str,
    identity_id: str,
    display_name: str,
    player_kind: PlayerKind = PlayerKind.HUMAN,
) -> Seat | None:
    """Join a seat at the table. Returns the Seat or None if table is full."""
    table = _tables.get(table_id)
    if not table:
        return None

    # Check if already seated
    for seat in table.seats:
        if seat.identity_id == identity_id:
            return seat

    # Check capacity
    if len(table.seats) >= table.settings.max_seats:
        return None

    seat_index = len(table.seats)
    seat_id = f"seat_{seat_index}"

    seat = Seat(
        seat_id=seat_id,
        display_name=display_name,
        identity_id=identity_id,
        player_kind=player_kind,
        presence=Presence.ACTIVE,
    )
    table.seats.append(seat)

    # First seat becomes host
    if table.host_seat_id is None:
        table.host_seat_id = seat_id

    # Create per-seat zones
    hand_zone = Zone(
        zone_id=f"hand_{seat_id}",
        kind=ZoneKind.HAND,
        visibility=ZoneVisibility.PRIVATE,
        owner_seat_id=seat_id,
        label=f"{display_name}'s Hand",
    )
    meld_zone = Zone(
        zone_id=f"meld_{seat_id}",
        kind=ZoneKind.MELD,
        visibility=ZoneVisibility.SEAT_PUBLIC,
        owner_seat_id=seat_id,
        label=f"{display_name}'s Melds",
    )
    tricks_zone = Zone(
        zone_id=f"tricks_{seat_id}",
        kind=ZoneKind.TRICKS_WON,
        visibility=ZoneVisibility.SEAT_PUBLIC,
        owner_seat_id=seat_id,
        label=f"{display_name}'s Tricks",
    )
    table.zones.extend([hand_zone, meld_zone, tricks_zone])

    return seat


def leave_table(table_id: str, identity_id: str) -> bool:
    """Remove a seat from the table. Returns True if seat was found."""
    table = _tables.get(table_id)
    if not table:
        return False

    seat = next((s for s in table.seats if s.identity_id == identity_id), None)
    if not seat:
        return False

    seat_id = seat.seat_id

    # Remove per-seat zones and return cards to deck
    deck_zone = next((z for z in table.zones if z.zone_id == "deck"), None)
    zones_to_remove = []
    for zone in table.zones:
        if zone.owner_seat_id == seat_id:
            if deck_zone:
                deck_zone.card_ids.extend(zone.card_ids)
            zones_to_remove.append(zone)

    table.zones = [z for z in table.zones if z not in zones_to_remove]
    table.seats = [s for s in table.seats if s.seat_id != seat_id]

    # Reassign host if needed
    if table.host_seat_id == seat_id:
        table.host_seat_id = table.seats[0].seat_id if table.seats else None

    return True


def get_seat_for_identity(table: Table, identity_id: str) -> Seat | None:
    """Find a seat by identity_id."""
    return next((s for s in table.seats if s.identity_id == identity_id), None)
