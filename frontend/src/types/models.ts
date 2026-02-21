import type {
  Suit,
  Rank,
  DeckRecipe,
  ZoneKind,
  ZoneVisibility,
  Presence,
  PlayerKind,
  ActionType,
  ActionClass,
  EventType,
  DisputeReason,
  ConsentTier,
} from "./enums";

export interface Card {
  unique_id: string;
  rank: Rank;
  suit: Suit;
  face_up: boolean;
}

export interface Zone {
  zone_id: string;
  kind: ZoneKind;
  visibility: ZoneVisibility;
  owner_seat_id: string | null;
  card_ids: string[];
  label: string;
}

export interface AckPosture {
  move_card: boolean;
  deal: boolean;
  set_phase: boolean;
  create_zone: boolean;
  undo: boolean;
}

export interface Seat {
  seat_id: string;
  display_name: string;
  identity_id: string | null;
  presence: Presence;
  player_kind: PlayerKind;
  ack_posture: AckPosture;
}

export interface TableSettings {
  max_seats: number;
  objection_window_s: number;
  shuffle_is_optimistic: boolean;
  min_action_delay_ms: number;
  phase_locked: boolean;
  dispute_cooldown_s: number;
  phase_change_cooldown_s: number;
  shuffle_cooldown_s: number;
  intent_rate_max_count: number;
  intent_rate_window_s: number;
  zone_create_cooldown_s: number;
}

export interface TableState {
  table_id: string;
  display_name: string;
  deck_recipe: DeckRecipe;
  host_seat_id: string | null;
  phase: string;
  seats: Seat[];
  zones: Zone[];
  cards: Record<string, Card>;
  settings: TableSettings;
  dispute_active: boolean;
  dispute_action_id: string | null;
  research_mode: boolean;
  research_mode_version: string;
  created_at: string;
}

export interface ActionIntent {
  action_type: ActionType;
  card_ids?: string[];
  source_zone_id?: string;
  target_zone_id?: string;
  target_zone_ids?: string[];
  new_order?: string[];
  phase_label?: string;
  zone_kind?: ZoneKind;
  zone_visibility?: ZoneVisibility;
  zone_label?: string;
  target_event_seq?: number;
}

export interface PendingAction {
  action_id: string;
  action_class: ActionClass;
  intent: ActionIntent;
  proposer_seat_id: string;
  required_acks: string[];
  received_acks: string[];
  received_nacks: string[];
  created_at: string;
  objection_deadline?: string;
  committed: boolean;
  finalized: boolean;
}

export interface ActionResult {
  action_id: string;
  status: "committed" | "pending" | "rejected" | "rolled_back" | "finalized";
  reason?: string;
}

export interface Event {
  schema_version: string;
  seq: number;
  event_type: EventType;
  table_id: string;
  seat_id?: string;
  action_id?: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface ChatMessage {
  message_id: string;
  seat_id: string;
  identity_id: string;
  text: string;
  thread_id?: string;
  timestamp: string;
}

export interface Dispute {
  dispute_id: string;
  action_id: string;
  disputer_seat_id: string;
  reason?: DisputeReason;
  reason_text?: string;
  created_at: string;
  resolved: boolean;
  resolution?: "revised" | "cancelled" | "undone" | "absent_marked";
}

export interface ConsentRecord {
  identity_hash: string;
  session_id: string;
  tiers: Record<ConsentTier, boolean>;
  granted_at: string;
  revoked_at?: string;
}

export interface Principal {
  identity_id: string;
  display_name: string;
  created_at: string;
}

export interface CredentialWithSecret {
  credential_id: string;
  client_id: string;
  client_secret: string;
  display_name: string;
  player_kind: PlayerKind;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface BootstrapResponse {
  principal: Principal;
  credentials: CredentialWithSecret[];
}

export interface TableSummary {
  table_id: string;
  display_name: string;
  deck_recipe: DeckRecipe;
  seat_count: number;
  max_seats: number;
  research_mode: boolean;
  created_at: string;
}
