export enum Suit {
  HEARTS = "hearts",
  DIAMONDS = "diamonds",
  CLUBS = "clubs",
  SPADES = "spades",
}

export enum Rank {
  TWO = "2",
  THREE = "3",
  FOUR = "4",
  FIVE = "5",
  SIX = "6",
  SEVEN = "7",
  EIGHT = "8",
  NINE = "9",
  TEN = "10",
  JACK = "J",
  QUEEN = "Q",
  KING = "K",
  ACE = "A",
}

export enum DeckRecipe {
  STANDARD_52 = "standard_52",
  EUCHRE_24 = "euchre_24",
  DOUBLE_PINOCHLE_80 = "double_pinochle_80",
}

export enum ZoneVisibility {
  PUBLIC = "public",
  PRIVATE = "private",
  SEAT_PUBLIC = "seat_public",
  SHARED_CONTROL = "shared_control",
}

export enum ZoneKind {
  DECK = "deck",
  DISCARD = "discard",
  CENTER = "center",
  HAND = "hand",
  MELD = "meld",
  TRICKS_WON = "tricks_won",
  CUSTOM = "custom",
  TRICK_PLAY = "trick_play",
  SCRATCHPAD = "scratchpad",
}

export enum ZoneOrdering {
  STACKED = "stacked",
  ORDERED = "ordered",
  UNORDERED = "unordered",
}

export enum Presence {
  ACTIVE = "active",
  DISCONNECTED = "disconnected",
  ABSENT = "absent",
}

export enum PlayerKind {
  HUMAN = "human",
  AI = "ai",
}

export enum ActionClass {
  UNILATERAL = "unilateral",
  CONSENSUS = "consensus",
  OPTIMISTIC = "optimistic",
}

export enum ActionType {
  REORDER = "reorder",
  SHUFFLE = "shuffle",
  SELF_REVEAL = "self_reveal",
  MOVE_CARD = "move_card",
  MOVE_CARDS_BATCH = "move_cards_batch",
  DEAL_ROUND_ROBIN = "deal_round_robin",
  CREATE_ZONE = "create_zone",
  UNDO = "undo",
  SET_PHASE = "set_phase",
}

export enum EventType {
  ACTION_COMMITTED = "action_committed",
  ACTION_FINALIZED = "action_finalized",
  ACTION_ROLLED_BACK = "action_rolled_back",
  INTENT_CREATED = "intent_created",
  ACK_RECEIVED = "ack_received",
  NACK_RECEIVED = "nack_received",
  DISPUTE_OPENED = "dispute_opened",
  DISPUTE_RESOLVED = "dispute_resolved",
  SEAT_JOINED = "seat_joined",
  SEAT_LEFT = "seat_left",
  PRESENCE_CHANGED = "presence_changed",
  PHASE_CHANGED = "phase_changed",
  CHAT_MESSAGE = "chat_message",
  TABLE_CREATED = "table_created",
  ZONE_CREATED = "zone_created",
  ACK_POSTURE_CHANGED = "ack_posture_changed",
  TABLE_DESTROYED = "table_destroyed",
  SCRATCHPAD_EDITED = "scratchpad_edited",
}

export enum DisputeReason {
  RULES = "rules",
  TURN = "turn",
  CLARIFY = "clarify",
  OTHER = "other",
}

export enum ConsentTier {
  RESEARCH_LOGGING = "research_logging",
  CHAT_STORAGE = "chat_storage",
  TRAINING_USE = "training_use",
  PUBLICATION = "publication",
  PUBLICATION_EXCERPTS = "publication_excerpts",
  LONGITUDINAL_LINKING = "longitudinal_linking",
  AI_DISCLOSURE_ACK = "ai_disclosure_ack",
}
