import { useRef, useCallback, useState, useEffect } from "react";
import type { WSInbound, WSOutbound } from "./protocol";
import type { ActionIntent, AckPosture } from "../types/models";
import type { DisputeReason } from "../types/enums";
import type { TableAction } from "../state/reducers";

interface UseTableSocketOptions {
  tableId: string;
  token: string;
  identityId: string;
  dispatch: React.Dispatch<TableAction>;
  onNeedsResync?: () => void;
  mode?: "player" | "spectate";
}

export function useTableSocket({
  tableId,
  token,
  dispatch,
  identityId,
  onNeedsResync,
  mode = "player",
}: UseTableSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const backoff = useRef(1000);
  const [connected, setConnected] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);

  // Keep latest values in refs so connect() doesn't need them as deps
  const dispatchRef = useRef(dispatch);
  dispatchRef.current = dispatch;
  const identityIdRef = useRef(identityId);
  identityIdRef.current = identityId;
  const modeRef = useRef(mode);
  modeRef.current = mode;
  const onNeedsResyncRef = useRef(onNeedsResync);
  onNeedsResyncRef.current = onNeedsResync;

  const send = useCallback((msg: WSInbound) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    let url = `${protocol}//${host}/ws/${tableId}?token=${token}`;
    if (modeRef.current === "spectate") {
      url += "&mode=spectate";
    }
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      const isReconnect = backoff.current > 1000;
      setConnected(true);
      setLastError(null);
      backoff.current = 1000;

      // Trigger resync on reconnect to recover missed events
      if (isReconnect && onNeedsResyncRef.current) {
        onNeedsResyncRef.current();
      }

      // Keepalive ping every 30s
      pingTimer.current = setInterval(() => {
        send({ msg_type: "ping" });
      }, 30000);
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data) as WSOutbound;

        switch (msg.msg_type) {
          case "state_sync": {
            const mySeat =
              modeRef.current === "spectate"
                ? null
                : msg.state.seats.find(
                    (s) => s.identity_id === identityIdRef.current,
                  );
            dispatchRef.current({
              type: "STATE_SYNC",
              state: msg.state,
              mySeatId: mySeat?.seat_id ?? null,
            });
            break;
          }
          case "event":
            dispatchRef.current({ type: "EVENT", event: msg.event });
            break;
          case "error":
            setLastError(`${msg.error_code}: ${msg.error}`);
            break;
          case "pong":
            break;
        }
      } catch {
        /* malformed message, ignore */
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (pingTimer.current) clearInterval(pingTimer.current);

      // Auto-reconnect with exponential backoff
      reconnectTimer.current = setTimeout(() => {
        backoff.current = Math.min(backoff.current * 2, 30000);
        connect();
      }, backoff.current);
    };

    ws.onerror = () => {
      setLastError("WebSocket connection error");
    };
  }, [tableId, token, send]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    if (pingTimer.current) clearInterval(pingTimer.current);
    if (wsRef.current) {
      wsRef.current.onclose = null; // prevent auto-reconnect
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    if (tableId && token) {
      connect();
    }
    return disconnect;
  }, [tableId, token, connect, disconnect]);

  const sendAction = useCallback(
    (intent: ActionIntent) => {
      if (modeRef.current === "spectate") return;
      send({ msg_type: "action", intent });
    },
    [send],
  );

  const sendAck = useCallback(
    (actionId: string) => {
      if (modeRef.current === "spectate") return;
      send({ msg_type: "ack", action_id: actionId });
    },
    [send],
  );

  const sendNack = useCallback(
    (actionId: string, reason?: DisputeReason, reasonText?: string) => {
      if (modeRef.current === "spectate") return;
      send({
        msg_type: "nack",
        action_id: actionId,
        reason,
        reason_text: reasonText,
      });
    },
    [send],
  );

  const sendDispute = useCallback(
    (actionId: string, reason?: DisputeReason, reasonText?: string) => {
      if (modeRef.current === "spectate") return;
      send({
        msg_type: "dispute",
        action_id: actionId,
        reason,
        reason_text: reasonText,
      });
    },
    [send],
  );

  const sendChat = useCallback(
    (text: string, channel?: string) => {
      send({ msg_type: "chat", text, channel });
    },
    [send],
  );

  const sendAckPosture = useCallback(
    (ackPosture: AckPosture) => {
      if (modeRef.current === "spectate") return;
      send({ msg_type: "set_ack_posture", ack_posture: ackPosture });
    },
    [send],
  );

  return {
    connected,
    lastError,
    sendAction,
    sendAck,
    sendNack,
    sendDispute,
    sendChat,
    sendAckPosture,
    mode,
  };
}
