import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.auth.service import verify_token
from backend.engine.action_engine import classify_action, execute_unilateral
from backend.engine.consensus import (
    create_consensus_intent,
    handle_ack,
    handle_nack,
    resolve_dispute,
)
from backend.engine.optimistic import dispute_optimistic, execute_optimistic
from backend.engine.rate_limiter import RateLimitError
from backend.engine.state import get_or_create_state
from backend.engine.table_manager import get_seat_for_identity, get_table
from backend.engine.visibility import filter_table_for_seat
from backend.models.action import ActionClass, ActionIntent
from backend.models.chat import ChatMessage
from backend.models.event import EventType
from backend.models.protocol import WSInbound, WSOutbound
from backend.models.seat import AckPosture, Presence

router = APIRouter()

# Connection registry: table_id -> {seat_id -> WebSocket}
_connections: dict[str, dict[str, WebSocket]] = defaultdict(dict)

# Observer registry: table_id -> {identity_id -> WebSocket}
_observers: dict[str, dict[str, WebSocket]] = defaultdict(dict)


def get_connections(table_id: str) -> dict[str, WebSocket]:
    return _connections[table_id]


async def broadcast_event(table_id: str, event_data: dict, table=None, channel: str | None = None) -> None:
    """Broadcast an event to all connected seats and observers."""
    # Send to players
    conns = _connections.get(table_id, {})
    for seat_id, ws in list(conns.items()):
        msg = WSOutbound(msg_type="event", event=event_data)
        try:
            await ws.send_text(msg.model_dump_json())
        except Exception:
            conns.pop(seat_id, None)

    # Send to observers (skip spectator-only chat for players, game chat goes to observers read-only)
    if channel != "spectator":
        observers = _observers.get(table_id, {})
        for obs_id, ws in list(observers.items()):
            msg = WSOutbound(msg_type="event", event=event_data)
            try:
                await ws.send_text(msg.model_dump_json())
            except Exception:
                observers.pop(obs_id, None)


async def _broadcast_to_observers(table_id: str, event_data: dict) -> None:
    """Broadcast an event only to observers (for spectator chat)."""
    observers = _observers.get(table_id, {})
    for obs_id, ws in list(observers.items()):
        msg = WSOutbound(msg_type="event", event=event_data)
        try:
            await ws.send_text(msg.model_dump_json())
        except Exception:
            observers.pop(obs_id, None)


async def send_state_sync(ws: WebSocket, table_id: str, seat_id: str, observer: bool = False) -> None:
    """Send full visibility-filtered state to a seat or observer."""
    table = get_table(table_id)
    if not table:
        return
    filter_id = "__observer__" if observer else seat_id
    state = filter_table_for_seat(table, filter_id)
    msg = WSOutbound(msg_type="state_sync", state=state)
    await ws.send_text(msg.model_dump_json())


async def send_error(ws: WebSocket, error: str, error_code: str = "ERROR") -> None:
    msg = WSOutbound(msg_type="error", error=error, error_code=error_code)
    await ws.send_text(msg.model_dump_json())


@router.websocket("/ws/{table_id}")
async def websocket_endpoint(websocket: WebSocket, table_id: str, token: str = "", mode: str = "player"):
    """Per-seat or spectator WebSocket connection for event streaming."""
    # Authenticate
    token_data = verify_token(token)
    if not token_data:
        await websocket.close(code=4001, reason="Invalid token")
        return

    table = get_table(table_id)
    if not table:
        await websocket.close(code=4004, reason="Table not found")
        return

    identity_id = token_data.effective_identity

    if mode == "spectate":
        await _handle_spectator(websocket, table_id, identity_id)
    else:
        seat = get_seat_for_identity(table, identity_id)
        if not seat:
            await websocket.close(code=4003, reason="Not seated at this table")
            return
        await _handle_player(websocket, table_id, seat)


async def _handle_player(websocket: WebSocket, table_id: str, seat) -> None:
    """Handle a player WebSocket connection."""
    import logging
    logger = logging.getLogger("tavoliere.ws")

    await websocket.accept()

    # Register connection
    _connections[table_id][seat.seat_id] = websocket

    # Update presence
    try:
        seat.presence = Presence.ACTIVE
        table = get_table(table_id)
        table_state = get_or_create_state(table)
        event = table_state.append_event(
            event_type=EventType.PRESENCE_CHANGED,
            seat_id=seat.seat_id,
            data={"presence": "active"},
        )
        await broadcast_event(table_id, event.model_dump(mode="json"))

        # Send initial state sync
        await send_state_sync(websocket, table_id, seat.seat_id)
        logger.info("state_sync sent to %s", seat.seat_id)
    except Exception:
        logger.exception("Error during WS setup for %s", seat.seat_id)
        await websocket.close(code=1011, reason="Internal error during setup")
        return

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = WSInbound.model_validate_json(raw)
                await _handle_inbound(msg, table_id, seat.seat_id, websocket)
            except Exception as e:
                await send_error(websocket, str(e), "INVALID_MESSAGE")
    except WebSocketDisconnect:
        pass
    finally:
        # Clean up connection
        _connections.get(table_id, {}).pop(seat.seat_id, None)
        # Update presence
        seat.presence = Presence.DISCONNECTED
        event = table_state.append_event(
            event_type=EventType.PRESENCE_CHANGED,
            seat_id=seat.seat_id,
            data={"presence": "disconnected"},
        )
        await broadcast_event(table_id, event.model_dump(mode="json"))


async def _handle_spectator(websocket: WebSocket, table_id: str, identity_id: str) -> None:
    """Handle a spectator WebSocket connection."""
    await websocket.accept()

    # Register in observer registry
    _observers[table_id][identity_id] = websocket

    # Send initial state sync (observer view)
    await send_state_sync(websocket, table_id, identity_id, observer=True)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = WSInbound.model_validate_json(raw)
                await _handle_spectator_inbound(msg, table_id, identity_id, websocket)
            except Exception as e:
                await send_error(websocket, str(e), "INVALID_MESSAGE")
    except WebSocketDisconnect:
        pass
    finally:
        _observers.get(table_id, {}).pop(identity_id, None)


async def _handle_spectator_inbound(
    msg: WSInbound, table_id: str, identity_id: str, ws: WebSocket
) -> None:
    """Handle inbound messages from spectators (only ping and spectator chat allowed)."""
    if msg.msg_type == "ping":
        pong = WSOutbound(msg_type="pong")
        await ws.send_text(pong.model_dump_json())

    elif msg.msg_type == "chat":
        if not msg.text:
            await send_error(ws, "Missing text", "MISSING_TEXT")
            return
        table = get_table(table_id)
        if not table:
            await send_error(ws, "Table not found")
            return
        table_state = get_or_create_state(table)
        chat_msg = ChatMessage(
            message_id=str(uuid.uuid4()),
            seat_id="__spectator__",
            identity_id=identity_id,
            text=msg.text,
            channel="spectator",
            timestamp=datetime.now(timezone.utc),
        )
        event = table_state.append_event(
            event_type=EventType.CHAT_MESSAGE,
            data=chat_msg.model_dump(mode="json"),
        )
        # Spectator chat only goes to observers
        await _broadcast_to_observers(table_id, event.model_dump(mode="json"))
    else:
        await send_error(ws, "Spectators can only send ping and chat", "SPECTATOR_RESTRICTED")


async def _handle_inbound(msg: WSInbound, table_id: str, seat_id: str, ws: WebSocket) -> None:
    """Handle an inbound WebSocket message."""
    table = get_table(table_id)
    if not table:
        await send_error(ws, "Table not found")
        return

    seat = None
    for s in table.seats:
        if s.seat_id == seat_id:
            seat = s
            break
    if not seat:
        await send_error(ws, "Seat not found")
        return

    table_state = get_or_create_state(table)

    if msg.msg_type == "ping":
        pong = WSOutbound(msg_type="pong")
        await ws.send_text(pong.model_dump_json())

    elif msg.msg_type == "action":
        if not msg.intent:
            await send_error(ws, "Missing intent", "MISSING_INTENT")
            return
        try:
            action_class = classify_action(msg.intent, table)
            if action_class == ActionClass.UNILATERAL:
                result = execute_unilateral(msg.intent, seat, table_state)
            elif action_class == ActionClass.CONSENSUS:
                result = create_consensus_intent(msg.intent, seat, table_state)
            elif action_class == ActionClass.OPTIMISTIC:
                result = execute_optimistic(msg.intent, seat, table_state)
            # Broadcast latest events
            for event in table_state.event_log[-3:]:
                await broadcast_event(table_id, event.model_dump(mode="json"))
        except (RateLimitError, ValueError) as e:
            await send_error(ws, str(e), "ACTION_ERROR")

    elif msg.msg_type == "ack":
        if not msg.action_id:
            await send_error(ws, "Missing action_id", "MISSING_ACTION_ID")
            return
        result = handle_ack(table_id, msg.action_id, seat_id, table_state)
        for event in table_state.event_log[-3:]:
            await broadcast_event(table_id, event.model_dump(mode="json"))

    elif msg.msg_type == "nack":
        if not msg.action_id:
            await send_error(ws, "Missing action_id", "MISSING_ACTION_ID")
            return
        reason = msg.reason.value if msg.reason else None
        result = handle_nack(
            table_id, msg.action_id, seat_id, table_state,
            reason=reason, reason_text=msg.reason_text,
        )
        for event in table_state.event_log[-3:]:
            await broadcast_event(table_id, event.model_dump(mode="json"))

    elif msg.msg_type == "dispute":
        if not msg.action_id:
            await send_error(ws, "Missing action_id", "MISSING_ACTION_ID")
            return
        reason = msg.reason.value if msg.reason else None
        result = dispute_optimistic(
            table_id, msg.action_id, seat_id, table_state,
            reason=reason, reason_text=msg.reason_text,
        )
        if result.status == "rejected":
            await send_error(ws, result.reason or "Dispute failed", "DISPUTE_FAILED")
        else:
            for event in table_state.event_log[-3:]:
                await broadcast_event(table_id, event.model_dump(mode="json"))

    elif msg.msg_type == "chat":
        if not msg.text:
            await send_error(ws, "Missing text", "MISSING_TEXT")
            return
        # Players always chat on "game" channel
        chat_msg = ChatMessage(
            message_id=str(uuid.uuid4()),
            seat_id=seat_id,
            identity_id=seat.identity_id or "",
            text=msg.text,
            channel="game",
            timestamp=datetime.now(timezone.utc),
        )
        event = table_state.append_event(
            event_type=EventType.CHAT_MESSAGE,
            seat_id=seat_id,
            data=chat_msg.model_dump(mode="json"),
        )
        # Game chat goes to players + observers
        await broadcast_event(table_id, event.model_dump(mode="json"))

    elif msg.msg_type == "set_ack_posture":
        if not msg.ack_posture:
            await send_error(ws, "Missing ack_posture", "MISSING_ACK_POSTURE")
            return
        seat.ack_posture = msg.ack_posture
        event = table_state.append_event(
            event_type=EventType.ACK_POSTURE_CHANGED,
            seat_id=seat_id,
            data=msg.ack_posture.model_dump(),
        )
        await broadcast_event(table_id, event.model_dump(mode="json"))
