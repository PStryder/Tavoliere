"""Offline replay of research event NDJSON exports.

Reconstructs session state step by step from an NDJSON file produced by
the ``/research/events/export`` endpoint. Designed for qualitative analysis
— the bridge between metrics and understanding.

Usage::

    uv run tavoliere replay session.ndjson
    uv run tavoliere replay session.ndjson --step
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend.models.research import ResearchEvent


def load_events(path: Path) -> list[ResearchEvent]:
    """Read an NDJSON file and parse each line as a ResearchEvent."""
    events: list[ResearchEvent] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(ResearchEvent.model_validate_json(line))
            except Exception as e:
                print(f"WARNING: skipping line {line_num}: {e}", file=sys.stderr)
    return events


class ReplayState:
    """Lightweight state tracker for replay.

    Tracks phase transitions, action lifecycle, disputes, chat, and seat
    pseudonyms — enough for qualitative review without full TableState
    reconstruction.
    """

    def __init__(self) -> None:
        self.phase: str = ""
        self.dispute_active: bool = False
        self.dispute_action_id: str | None = None
        self.committed_actions: list[str] = []
        self.rolled_back_actions: list[str] = []
        self.event_count: int = 0
        self.event_type_counts: dict[str, int] = {}
        self.seat_pseudonyms: dict[str, str] = {}  # seat_id -> pseudonym

    def apply(self, event: ResearchEvent) -> str:
        """Apply one event and return a human-readable description."""
        self.event_count += 1
        et = event.event_type
        self.event_type_counts[et] = self.event_type_counts.get(et, 0) + 1

        # Track seat pseudonyms from snapshots
        if event.seat_snapshot:
            ss = event.seat_snapshot
            self.seat_pseudonyms[ss.seat_id] = ss.pseudonym_id

        actor = self._actor_label(event)

        if et == "phase_changed":
            old = self.phase
            self.phase = event.phase_label
            return f"Phase: '{old}' -> '{self.phase}'"

        if et == "action_committed":
            ae = event.action_enrichment
            action_desc = ae.action_type if ae else "unknown"
            action_class = ae.action_class if ae else "?"
            aid = ae.action_id if ae else "?"
            self.committed_actions.append(aid)
            return f"COMMIT [{action_class}] {action_desc} (action={aid[:8]}) by {actor}"

        if et == "action_rolled_back":
            ae = event.action_enrichment
            aid = ae.action_id if ae else "?"
            self.rolled_back_actions.append(aid)
            return f"ROLLBACK action={aid[:8]} by {actor}"

        if et == "action_finalized":
            ae = event.action_enrichment
            aid = ae.action_id if ae else "?"
            return f"FINALIZED action={aid[:8]}"

        if et == "intent_created":
            ae = event.action_enrichment
            action_desc = ae.action_type if ae else "unknown"
            vis = ""
            if ae and ae.visibility_transition != "none":
                vis = f" [{ae.visibility_transition}]"
            return f"INTENT {action_desc}{vis} by {actor}"

        if et == "ack_received":
            ae = event.action_enrichment
            latency = f" ({ae.ack_latency_ms}ms)" if ae and ae.ack_latency_ms else ""
            return f"ACK on action={ae.action_id[:8] if ae else '?'}{latency} by {actor}"

        if et == "nack_received":
            ae = event.action_enrichment
            return f"NACK on action={ae.action_id[:8] if ae else '?'} by {actor}"

        if et == "dispute_opened":
            ae = event.action_enrichment
            reason = ae.dispute_reason_tag if ae else "?"
            self.dispute_active = True
            self.dispute_action_id = ae.action_id if ae else None
            return f"DISPUTE OPENED reason='{reason}' by {actor}"

        if et == "dispute_resolved":
            ae = event.action_enrichment
            resolution = ae.resolution_type if ae else "?"
            chat_count = ae.chat_messages_during_resolution if ae else 0
            self.dispute_active = False
            self.dispute_action_id = None
            return f"DISPUTE RESOLVED resolution='{resolution}' ({chat_count} chat msgs)"

        if et == "chat_message":
            ce = event.chat_enrichment
            chars = ce.message_length_chars if ce else 0
            dispute_tag = " [during dispute]" if (ce and ce.is_resolution_related) else ""
            return f"CHAT by {actor} ({chars} chars){dispute_tag}"

        if et == "seat_joined":
            return f"SEAT JOINED: {actor}"

        if et == "seat_left":
            return f"SEAT LEFT: {actor}"

        if et == "presence_changed":
            return f"PRESENCE CHANGED: {actor}"

        if et == "ack_posture_changed":
            return f"ACK POSTURE CHANGED: {actor}"

        if et == "zone_created":
            return f"ZONE CREATED by {actor}"

        if et == "table_created":
            return "TABLE CREATED"

        return f"{et} by {actor}"

    def _actor_label(self, event: ResearchEvent) -> str:
        if event.seat_snapshot:
            return event.seat_snapshot.pseudonym_id
        return "system"

    def summary(self) -> str:
        """Generate a summary report of the replayed session."""
        lines = [
            "",
            "=" * 60,
            "REPLAY SUMMARY",
            "=" * 60,
            f"Total events: {self.event_count}",
            f"Actions committed: {len(self.committed_actions)}",
            f"Actions rolled back: {len(self.rolled_back_actions)}",
            f"Final phase: '{self.phase}'",
            "",
            "Event type breakdown:",
        ]
        for et, count in sorted(self.event_type_counts.items()):
            lines.append(f"  {et}: {count}")
        lines.append("")
        lines.append(f"Seats observed: {len(self.seat_pseudonyms)}")
        for seat_id, pseudo in self.seat_pseudonyms.items():
            lines.append(f"  {seat_id} -> {pseudo}")
        return "\n".join(lines)


def replay(path: Path, step_mode: bool = False) -> None:
    """Main replay loop — load events and step through them."""
    events = load_events(path)
    if not events:
        print("No events found in file.")
        return

    first = events[0]
    print(f"Schema version: {first.schema_version}")
    print(f"Session: {first.session_id}")
    print(f"Table: {first.table_id}")
    print(f"Events to replay: {len(events)}")
    print("-" * 60)

    state = ReplayState()
    for i, event in enumerate(events):
        description = state.apply(event)
        print(f"[{i + 1:4d} | seq={event.gameplay_seq:4d}] {description}")

        if step_mode:
            try:
                input("  Press Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                print("\nReplay interrupted.")
                break

    print(state.summary())


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="tavoliere",
        description="Tavoliere CLI tools",
    )
    subparsers = parser.add_subparsers(dest="command")

    replay_parser = subparsers.add_parser(
        "replay",
        help="Replay a research event NDJSON export",
    )
    replay_parser.add_argument(
        "session_file",
        type=Path,
        help="Path to NDJSON file",
    )
    replay_parser.add_argument(
        "--step",
        action="store_true",
        help="Step through events one at a time (press Enter to advance)",
    )

    args = parser.parse_args()

    if args.command == "replay":
        if not args.session_file.exists():
            print(f"File not found: {args.session_file}", file=sys.stderr)
            sys.exit(1)
        replay(args.session_file, step_mode=args.step)
    else:
        parser.print_help()
        sys.exit(1)
