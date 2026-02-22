import type {
  Suit,
  Rank,
  DeckRecipe,
  ZoneKind,
  ZoneVisibility,
  ZoneOrdering,
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
  template_id?: string;
  created_at?: string;
  metadata?: Record<string, unknown>;
}

export interface Zone {
  zone_id: string;
  kind: ZoneKind;
  visibility: ZoneVisibility;
  owner_seat_id: string | null;
  card_ids: string[];
  label: string;
  capacity?: number | null;
  ordering?: ZoneOrdering;
  seat_visibility?: string[];
  metadata?: Record<string, unknown>;
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

export interface ShuffleState {
  shuffled_by?: string | null;
  shuffled_at?: string | null;
  seed?: string | null;
}

export interface TurnState {
  active_seat_id?: string | null;
  phase_label?: string;
  metadata?: Record<string, unknown>;
}

export interface Scratchpad {
  scratchpad_id: string;
  visibility: "public" | "private";
  owner_seat_id?: string | null;
  content: string;
  last_modified_by?: string | null;
  last_modified_at?: string | null;
}

export interface ScratchpadEdit {
  scratchpad_id: string;
  action: "propose_edit" | "append" | "clear" | "replace";
  content?: string;
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
  shuffle_state?: ShuffleState;
  turn_state?: TurnState;
  scratchpads?: Record<string, Scratchpad>;
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
  channel?: string;
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

export interface TableMeta {
  table_id: string;
  display_name: string;
  deck_recipe: string;
  seats: { seat_id: string; display_name: string; identity_id: string | null; player_kind: string }[];
  research_mode: boolean;
  research_mode_version: string;
  created_at: string;
  destroyed_at: string;
  event_count: number;
}

export interface CredentialPublic {
  credential_id: string;
  client_id: string;
  display_name: string;
  player_kind: PlayerKind;
  created_at: string;
}

export interface ProfileInfo {
  identity_id: string;
  display_name: string;
  is_admin: boolean;
  created_at: string;
  credential_count: number;
}

export interface ConventionTemplate {
  template_id: string;
  name: string;
  deck_recipe: string;
  seat_count: number;
  suggested_phases: string[];
  suggested_settings: Record<string, unknown>;
  notes: Record<string, string>;
  built_in: boolean;
  created_at: string;
}

export interface ResearchHealth {
  active_tables: number;
  active_research_tables: number;
  persisted_sessions: number;
  total_persisted_events: number;
}

export interface PrincipalInfo {
  identity_id: string;
  display_name: string;
  is_admin: boolean;
  created_at: string;
  credential_count: number;
}

export interface GameSummary {
  table_id: string;
  display_name: string;
  deck_recipe: string;
  seats: { seat_id: string; display_name: string; identity_id: string | null }[];
  research_mode: boolean;
  created_at: string;
  destroyed_at?: string;
  duration_s: number;
  total_events: number;
  total_actions: number;
  total_disputes: number;
  total_undos: number;
  spqan?: SessionSPQAN;
}

// ---------------------------------------------------------------------------
// SPQ-AN metric types
// ---------------------------------------------------------------------------

export interface CEMetrics {
  mean_ack_latency_ms: number | null;
  dispute_density: number;
  rollback_rate: number;
}

export interface RCMetrics {
  mean_resolution_latency_ms: number | null;
  mean_chat_per_dispute: number;
  resolution_distribution: Record<string, number>;
}

export interface NSMetrics {
  auto_ack_adoption_rate: number;
  auto_ack_churn: number;
  phase_label_diversity: number;
}

export interface CAMetrics {
  mean_message_length_chars: number;
  resolution_related_chat_ratio: number;
  messages_per_dispute: number;
}

export interface SSCMetrics {
  dispute_initiation_rate: number;
  dispute_involvement_rate: number;
  dispute_clustering_score: number;
}

export interface SeatSPQAN {
  seat_id: string;
  pseudonym_id: string;
  seat_type: string;
  ce: CEMetrics;
  rc: RCMetrics;
  ns: NSMetrics;
  ca: CAMetrics;
  ssc: SSCMetrics;
}

export interface SessionSPQAN {
  session_id: string;
  table_id: string;
  seats: SeatSPQAN[];
  event_count: number;
  duration_ms: number;
}

export interface ResearchSession extends TableMeta {
  has_research_data: boolean;
}

export interface ResearchEvent {
  event_id: string;
  table_id: string;
  session_id: string;
  event_type: string;
  timestamp_utc_ms: number;
  server_sequence_number: number;
  phase_label: string;
  previous_event_id: string | null;
  gameplay_seq: number;
  seat_snapshot?: Record<string, unknown>;
  action_enrichment?: Record<string, unknown>;
  chat_enrichment?: Record<string, unknown>;
  rng_provenance?: Record<string, unknown>;
}
