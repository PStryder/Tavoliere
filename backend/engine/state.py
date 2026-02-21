import uuid
from datetime import datetime, timezone

from backend.models.event import Event, EventType
from backend.models.snapshot import Snapshot
from backend.models.table import Table


class TableState:
    """Manages mutable table state, event log, and snapshots."""

    def __init__(self, table: Table):
        self.table = table
        self.event_log: list[Event] = []
        self.snapshots: dict[int, Snapshot] = {}
        self._seq = 0
        self._research_observer = None

    def attach_research(self, observer):
        """Attach a ResearchObserver for parallel instrumentation."""
        self._research_observer = observer

    def next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def take_snapshot(self) -> int:
        """Snapshot current table state. Returns the snapshot seq."""
        seq = self._seq
        snapshot = Snapshot(
            seq=seq,
            table_state=self.table.model_dump(mode="json"),
            timestamp=datetime.now(timezone.utc),
        )
        self.snapshots[seq] = snapshot
        return seq

    def rollback_to(self, seq: int) -> bool:
        """Restore table state from a snapshot."""
        snapshot = self.snapshots.get(seq)
        if not snapshot:
            return False

        restored = Table.model_validate(snapshot.table_state)
        # Preserve table_id and transfer state
        self.table.seats = restored.seats
        self.table.zones = restored.zones
        self.table.cards = restored.cards
        self.table.phase = restored.phase
        self.table.dispute_active = restored.dispute_active
        self.table.dispute_action_id = restored.dispute_action_id
        return True

    def append_event(
        self,
        event_type: EventType,
        seat_id: str | None = None,
        action_id: str | None = None,
        data: dict | None = None,
    ) -> Event:
        """Append an event to the log and return it."""
        event = Event(
            seq=self.next_seq(),
            event_type=event_type,
            table_id=self.table.table_id,
            seat_id=seat_id,
            action_id=action_id,
            timestamp=datetime.now(timezone.utc),
            data=data or {},
        )
        self.event_log.append(event)
        if self._research_observer:
            self._research_observer.on_event(event, self.table)
        return event

    def generate_action_id(self) -> str:
        return str(uuid.uuid4())


# Registry of table states
_table_states: dict[str, TableState] = {}


def get_or_create_state(table: Table) -> TableState:
    if table.table_id not in _table_states:
        _table_states[table.table_id] = TableState(table)
    return _table_states[table.table_id]


def get_state(table_id: str) -> TableState | None:
    return _table_states.get(table_id)


def remove_state(table_id: str) -> None:
    _table_states.pop(table_id, None)
