from backend.models.card import Card
from backend.models.scratchpad import ScratchpadVisibility
from backend.models.table import Table
from backend.models.zone import Zone, ZoneVisibility


def filter_table_for_seat(table: Table, seat_id: str) -> dict:
    """Return a visibility-filtered view of the table for a specific seat.

    Private zones owned by other seats have their card identities hidden —
    only the count is visible. All other zones are fully visible.
    """
    filtered_zones = []
    for zone in table.zones:
        if _can_see_contents(zone, seat_id):
            filtered_zones.append(zone.model_dump())
        else:
            # Hide card identities — only show count
            z = zone.model_dump()
            z["card_ids"] = []
            z["card_count"] = len(zone.card_ids)
            filtered_zones.append(z)

    # Only include cards that this seat can see
    visible_card_ids = set()
    for zone in table.zones:
        if _can_see_contents(zone, seat_id):
            visible_card_ids.update(zone.card_ids)

    visible_cards = {
        cid: table.cards[cid].model_dump()
        for cid in visible_card_ids
        if cid in table.cards
    }

    # Cards that are face_up are always visible regardless of zone
    for zone in table.zones:
        if not _can_see_contents(zone, seat_id):
            for cid in zone.card_ids:
                card = table.cards.get(cid)
                if card and card.face_up:
                    visible_cards[cid] = card.model_dump()

    # Filter scratchpads — private pads only shown to owner, public to all
    filtered_scratchpads = {}
    for sp_id, sp in table.scratchpads.items():
        if sp.visibility == ScratchpadVisibility.PUBLIC or sp.owner_seat_id == seat_id:
            filtered_scratchpads[sp_id] = sp.model_dump()

    result = {
        "table_id": table.table_id,
        "display_name": table.display_name,
        "deck_recipe": table.deck_recipe.value,
        "host_seat_id": table.host_seat_id,
        "phase": table.phase,
        "seats": [s.model_dump() for s in table.seats],
        "zones": filtered_zones,
        "cards": visible_cards,
        "settings": table.settings.model_dump(),
        "dispute_active": table.dispute_active,
        "dispute_action_id": table.dispute_action_id,
        "created_at": table.created_at.isoformat(),
    }

    if filtered_scratchpads:
        result["scratchpads"] = filtered_scratchpads

    if table.shuffle_state.seed is not None:
        result["shuffle_state"] = table.shuffle_state.model_dump(exclude={"seed"})

    if table.turn_state.active_seat_id is not None or table.turn_state.phase_label:
        result["turn_state"] = table.turn_state.model_dump()

    return result


def _can_see_contents(zone: Zone, seat_id: str) -> bool:
    """Check if a seat can see the contents of a zone."""
    # seat_visibility narrowing: if non-empty, only listed seat_ids can see
    if zone.seat_visibility and seat_id not in zone.seat_visibility:
        return False

    if zone.visibility == ZoneVisibility.PUBLIC:
        return True
    if zone.visibility == ZoneVisibility.SHARED_CONTROL:
        # Visible to all (like PUBLIC), write-gated by consensus elsewhere
        return True
    if zone.visibility == ZoneVisibility.SEAT_PUBLIC:
        return True
    if zone.visibility == ZoneVisibility.PRIVATE:
        return zone.owner_seat_id == seat_id
    return False
