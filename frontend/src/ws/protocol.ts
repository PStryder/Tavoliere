import type {
  ActionIntent,
  AckPosture,
  Event,
  TableState,
} from "../types/models";
import type { DisputeReason } from "../types/enums";

export type WSInbound =
  | { msg_type: "action"; intent: ActionIntent }
  | { msg_type: "ack"; action_id: string }
  | {
      msg_type: "nack";
      action_id: string;
      reason?: DisputeReason;
      reason_text?: string;
    }
  | {
      msg_type: "dispute";
      action_id: string;
      reason?: DisputeReason;
      reason_text?: string;
    }
  | { msg_type: "chat"; text: string; channel?: string }
  | { msg_type: "set_ack_posture"; ack_posture: AckPosture }
  | { msg_type: "ping" };

export type WSOutbound =
  | { msg_type: "state_sync"; state: TableState }
  | { msg_type: "event"; event: Event }
  | { msg_type: "error"; error: string; error_code: string }
  | { msg_type: "pong" };
