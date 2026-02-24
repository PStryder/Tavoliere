import { EventType, type ZoneKind, type ZoneVisibility } from "../types/enums";
import type {
  TableState,
  PendingAction,
  ChatMessage,
  Event,
  Seat,
  Zone,
  AckPosture,
} from "../types/models";

export interface TableContextState {
  table: TableState | null;
  mySeatId: string | null;
  pendingActions: PendingAction[];
  chatMessages: ChatMessage[];
  needsResync: boolean;
  tableDestroyed: boolean;
  lastCommittedSeq: number | null;
}

export type TableAction =
  | { type: "STATE_SYNC"; state: TableState; mySeatId: string | null }
  | { type: "EVENT"; event: Event }
  | { type: "SET_MY_SEAT"; seatId: string }
  | { type: "CLEAR" };

export const initialTableState: TableContextState = {
  table: null,
  mySeatId: null,
  pendingActions: [],
  chatMessages: [],
  needsResync: false,
  tableDestroyed: false,
  lastCommittedSeq: null,
};

export function tableReducer(
  state: TableContextState,
  action: TableAction,
): TableContextState {
  switch (action.type) {
    case "STATE_SYNC":
      return {
        ...state,
        table: action.state,
        mySeatId: action.mySeatId ?? state.mySeatId,
        pendingActions: [],
        needsResync: false,
      };

    case "SET_MY_SEAT":
      return { ...state, mySeatId: action.seatId };

    case "CLEAR":
      return initialTableState;

    case "EVENT":
      return handleEvent(state, action.event);
  }
}

function handleEvent(
  state: TableContextState,
  event: Event,
): TableContextState {
  const table = state.table;
  if (!table) return state;

  switch (event.event_type) {
    case EventType.ACTION_COMMITTED: {
      // For v0.1: request resync for complex state mutations
      // Also remove from pending so the bar doesn't flash briefly
      return {
        ...state,
        needsResync: true,
        lastCommittedSeq: event.seq ?? state.lastCommittedSeq,
        pendingActions: state.pendingActions.filter(
          (p) => p.action_id !== event.action_id,
        ),
      };
    }

    case EventType.ACTION_ROLLED_BACK:
      return {
        ...state,
        needsResync: true,
        pendingActions: state.pendingActions.filter(
          (p) => p.action_id !== event.action_id,
        ),
      };

    case EventType.ACTION_FINALIZED: {
      const actionId = event.action_id;
      return {
        ...state,
        pendingActions: state.pendingActions.filter(
          (p) => p.action_id !== actionId,
        ),
      };
    }

    case EventType.INTENT_CREATED: {
      const data = event.data as {
        action_id: string;
        action_class: string;
        intent: Record<string, unknown>;
        proposer_seat_id: string;
        required_acks: string[];
      };
      const pending: PendingAction = {
        action_id: data.action_id ?? event.action_id ?? "",
        action_class: data.action_class as PendingAction["action_class"],
        intent: data.intent as unknown as PendingAction["intent"],
        proposer_seat_id: data.proposer_seat_id ?? event.seat_id ?? "",
        required_acks: data.required_acks ?? [],
        received_acks: [],
        received_nacks: [],
        created_at: event.timestamp,
        committed: false,
        finalized: false,
      };
      return {
        ...state,
        pendingActions: [...state.pendingActions, pending],
      };
    }

    case EventType.ACK_RECEIVED: {
      const actionId = event.action_id;
      const seatId = event.seat_id ?? "";
      return {
        ...state,
        pendingActions: state.pendingActions.map((p) =>
          p.action_id === actionId
            ? {
                ...p,
                received_acks: [...p.received_acks, seatId],
              }
            : p,
        ),
      };
    }

    case EventType.NACK_RECEIVED: {
      const actionId = event.action_id;
      return {
        ...state,
        pendingActions: state.pendingActions.filter(
          (p) => p.action_id !== actionId,
        ),
      };
    }

    case EventType.DISPUTE_OPENED: {
      const data = event.data as { action_id?: string };
      return {
        ...state,
        table: {
          ...table,
          dispute_active: true,
          dispute_action_id: data.action_id ?? event.action_id ?? null,
        },
      };
    }

    case EventType.DISPUTE_RESOLVED:
      return {
        ...state,
        table: {
          ...table,
          dispute_active: false,
          dispute_action_id: null,
        },
        needsResync: true,
      };

    case EventType.CHAT_MESSAGE: {
      const data = event.data as {
        message_id: string;
        text: string;
        channel?: string;
        thread_id?: string;
        identity_id?: string;
      };
      const msg: ChatMessage = {
        message_id: data.message_id ?? crypto.randomUUID(),
        seat_id: event.seat_id ?? data.identity_id ?? "",
        identity_id: data.identity_id ?? "",
        text: data.text ?? "",
        channel: data.channel,
        thread_id: data.thread_id,
        timestamp: event.timestamp,
      };
      return {
        ...state,
        chatMessages: [...state.chatMessages, msg],
      };
    }

    case EventType.PHASE_CHANGED: {
      const data = event.data as { phase: string };
      return {
        ...state,
        table: { ...table, phase: data.phase ?? table.phase },
      };
    }

    case EventType.SEAT_JOINED: {
      const data = event.data as { seat: Seat };
      if (!data.seat) return { ...state, needsResync: true };
      return {
        ...state,
        table: {
          ...table,
          seats: [...table.seats.filter((s) => s.seat_id !== data.seat.seat_id), data.seat],
        },
      };
    }

    case EventType.SEAT_LEFT: {
      const seatId = event.seat_id ?? (event.data as { seat_id?: string }).seat_id;
      return {
        ...state,
        table: {
          ...table,
          seats: table.seats.filter((s) => s.seat_id !== seatId),
        },
      };
    }

    case EventType.PRESENCE_CHANGED: {
      const data = event.data as { presence: string };
      const seatId = event.seat_id;
      return {
        ...state,
        table: {
          ...table,
          seats: table.seats.map((s) =>
            s.seat_id === seatId
              ? { ...s, presence: data.presence as Seat["presence"] }
              : s,
          ),
        },
      };
    }

    case EventType.ZONE_CREATED: {
      const data = event.data as {
        zone_id: string;
        kind: ZoneKind;
        visibility: ZoneVisibility;
        owner_seat_id?: string;
        label?: string;
      };
      const zone: Zone = {
        zone_id: data.zone_id,
        kind: data.kind,
        visibility: data.visibility,
        owner_seat_id: data.owner_seat_id ?? null,
        card_ids: [],
        label: data.label ?? "",
      };
      return {
        ...state,
        table: { ...table, zones: [...table.zones, zone] },
      };
    }

    case EventType.ACK_POSTURE_CHANGED: {
      const data = event.data as { ack_posture: AckPosture };
      const seatId = event.seat_id;
      return {
        ...state,
        table: {
          ...table,
          seats: table.seats.map((s) =>
            s.seat_id === seatId
              ? { ...s, ack_posture: data.ack_posture }
              : s,
          ),
        },
      };
    }

    case EventType.TABLE_DESTROYED:
      return { ...state, tableDestroyed: true };

    default:
      return state;
  }
}
