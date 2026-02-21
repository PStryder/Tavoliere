"""Event log persistence — writes NDJSON event logs and metadata to disk."""

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.models.event import Event
from backend.models.table import Table

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "events"


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def persist_table(table: Table, events: list[Event]) -> Path:
    """Write event log and metadata for a destroyed table."""
    _ensure_dir()
    tid = table.table_id

    # Write NDJSON event log
    events_path = DATA_DIR / f"{tid}.ndjson"
    with events_path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(ev.model_dump_json() + "\n")

    # Write metadata
    meta = {
        "table_id": tid,
        "display_name": table.display_name,
        "deck_recipe": table.deck_recipe.value,
        "seats": [
            {
                "seat_id": s.seat_id,
                "display_name": s.display_name,
                "identity_id": s.identity_id,
                "player_kind": s.player_kind.value,
            }
            for s in table.seats
        ],
        "research_mode": table.research_mode,
        "research_mode_version": table.research_mode_version,
        "created_at": table.created_at.isoformat(),
        "destroyed_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
    }
    meta_path = DATA_DIR / f"{tid}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return events_path


def load_events(table_id: str) -> list[Event] | None:
    """Read persisted events from disk."""
    path = DATA_DIR / f"{table_id}.ndjson"
    if not path.exists():
        return None
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(Event.model_validate_json(line))
    return events


def load_meta(table_id: str) -> dict | None:
    """Read persisted table metadata."""
    path = DATA_DIR / f"{table_id}.meta.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_persisted_tables() -> list[dict]:
    """Scan data/events/ for all persisted table metadata."""
    _ensure_dir()
    results = []
    for meta_path in DATA_DIR.glob("*.meta.json"):
        if meta_path.name.endswith(".research.meta.json"):
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            tid = meta.get("table_id", "")
            meta["has_research_data"] = (DATA_DIR / f"{tid}.research.ndjson").exists()
            results.append(meta)
        except (json.JSONDecodeError, OSError):
            continue
    return results


# ---------------------------------------------------------------------------
# Research data persistence
# ---------------------------------------------------------------------------


def persist_research_data(table_id: str, observer: object) -> Path | None:
    """Write research events and metadata for a destroyed table.

    Args:
        table_id: The table identifier.
        observer: A ResearchObserver instance (typed as object to avoid circular imports).

    Returns:
        Path to the research NDJSON file, or None if no research data.
    """
    from backend.engine.research_observer import ResearchObserver

    if not isinstance(observer, ResearchObserver):
        return None
    if not observer.research_log:
        return None

    _ensure_dir()

    # Write research events as NDJSON
    events_path = DATA_DIR / f"{table_id}.research.ndjson"
    with events_path.open("w", encoding="utf-8") as f:
        for rev in observer.research_log:
            f.write(rev.model_dump_json() + "\n")

    # Write research metadata
    meta = {
        "table_id": table_id,
        "session_id": observer.config.session_id,
        "config": observer.config.model_dump(mode="json"),
        "identities": {
            k: v.model_dump(mode="json") for k, v in observer.identity_store.items()
        },
        "consent": {
            k: v.model_dump(mode="json") for k, v in observer.consent_store.items()
        },
        "snapshots": [s.model_dump(mode="json") for s in observer.snapshots],
        "event_count": len(observer.research_log),
    }
    meta_path = DATA_DIR / f"{table_id}.research.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return events_path


def load_research_events(table_id: str) -> list[dict] | None:
    """Read persisted research events from disk."""
    path = DATA_DIR / f"{table_id}.research.ndjson"
    if not path.exists():
        return None
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def load_research_meta(table_id: str) -> dict | None:
    """Read persisted research metadata."""
    path = DATA_DIR / f"{table_id}.research.meta.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
