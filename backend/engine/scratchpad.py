"""Scratchpad engine — applies edits, validates access, emits events."""

import hashlib
from datetime import datetime, timezone

from backend.engine.state import TableState
from backend.models.event import EventType
from backend.models.scratchpad import Scratchpad, ScratchpadAction, ScratchpadEdit, ScratchpadVisibility

# Maximum scratchpad content size in characters (~64KB)
MAX_SCRATCHPAD_CONTENT = 65_536


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def apply_scratchpad_edit(
    edit: ScratchpadEdit,
    seat_id: str,
    table_state: TableState,
) -> dict:
    """Validate access, apply mutation, emit SCRATCHPAD_EDITED event.

    Returns the event data dict.
    """
    table = table_state.table
    sp = table.scratchpads.get(edit.scratchpad_id)
    if not sp:
        raise ValueError(f"Scratchpad {edit.scratchpad_id} not found")

    # Access control: private pads only editable by owner
    if sp.visibility == ScratchpadVisibility.PRIVATE and sp.owner_seat_id != seat_id:
        raise ValueError("Cannot edit another seat's private scratchpad")

    content_before = sp.content
    hash_before = _content_hash(content_before)

    if edit.action == ScratchpadAction.APPEND:
        new_content = sp.content + edit.content
    elif edit.action == ScratchpadAction.REPLACE:
        new_content = edit.content
    elif edit.action == ScratchpadAction.CLEAR:
        new_content = ""
    elif edit.action == ScratchpadAction.PROPOSE_EDIT:
        # For shared pads, propose_edit acts as replace (consensus gating TBD)
        new_content = edit.content
    else:
        raise ValueError(f"Unknown scratchpad action: {edit.action}")

    if len(new_content) > MAX_SCRATCHPAD_CONTENT:
        raise ValueError(
            f"Scratchpad content exceeds maximum size "
            f"({len(new_content)}/{MAX_SCRATCHPAD_CONTENT} chars)"
        )

    sp.content = new_content
    hash_after = _content_hash(sp.content)
    now = datetime.now(timezone.utc)
    sp.last_modified_by = seat_id
    sp.last_modified_at = now

    event_data = {
        "scratchpad_id": edit.scratchpad_id,
        "action": edit.action.value,
        "seat_id": seat_id,
        "content_hash_before": hash_before,
        "content_hash_after": hash_after,
    }

    table_state.append_event(
        event_type=EventType.SCRATCHPAD_EDITED,
        seat_id=seat_id,
        data=event_data,
    )

    return event_data
