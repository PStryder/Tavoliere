# Tavoliere — Frontend Build Spec (v0.1)

## Stack

- **Framework:** React 18+ with Vite
- **Styling:** Tailwind CSS
- **State:** React Context + useReducer (no Redux needed at this scale)
- **Routing:** React Router v6
- **WebSocket:** Native WebSocket API, wrapped in a custom hook
- **HTTP:** fetch or lightweight wrapper (no axios needed)
- **Build output:** Static files, served alongside FastAPI or deployed separately

## Project Structure

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes.tsx
│   ├── api/
│   │   ├── client.ts          # HTTP client (base URL, auth headers)
│   │   ├── auth.ts            # login, bootstrap, token management
│   │   ├── tables.ts          # CRUD tables, join/leave
│   │   ├── actions.ts         # submit action, ack, nack, dispute
│   │   ├── chat.ts            # send chat (REST fallback)
│   │   ├── research.ts        # export, events, identities
│   │   └── consent.ts         # consent CRUD
│   ├── ws/
│   │   ├── useTableSocket.ts  # WebSocket hook: connect, send, receive
│   │   └── protocol.ts        # WSInbound/WSOutbound type definitions
│   ├── state/
│   │   ├── AuthContext.tsx     # auth state: token, identity, credentials
│   │   ├── TableContext.tsx    # table state: zones, cards, seats, events
│   │   └── reducers.ts        # state reducers for event-driven updates
│   ├── pages/
│   │   ├── LandingPage.tsx
│   │   ├── LobbyPage.tsx
│   │   ├── TablePage.tsx
│   │   ├── SpectatorPage.tsx
│   │   ├── ReplayPage.tsx
│   │   ├── GameLogPage.tsx
│   │   ├── ProfilePage.tsx
│   │   ├── ApiKeysPage.tsx
│   │   ├── AdminPage.tsx
│   │   └── DataExplorerPage.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── PageLayout.tsx
│   │   ├── auth/
│   │   │   └── LoginModal.tsx
│   │   ├── lobby/
│   │   │   ├── TableList.tsx
│   │   │   └── CreateTableModal.tsx
│   │   ├── table/
│   │   │   ├── TableSurface.tsx      # main table layout container
│   │   │   ├── HandZone.tsx          # player's private hand
│   │   │   ├── PublicZone.tsx        # center, discard, deck
│   │   │   ├── SeatOwnedZone.tsx     # meld, tricks_won
│   │   │   ├── CardView.tsx          # single card rendering
│   │   │   ├── DeckPile.tsx          # face-down deck with count
│   │   │   ├── SeatDisplay.tsx       # seat info: name, presence, AI flag
│   │   │   ├── PendingActionBar.tsx  # ACK/NACK buttons for pending actions
│   │   │   ├── DisputeBanner.tsx     # dispute state indicator + resolution UI
│   │   │   ├── PhaseLabel.tsx        # current phase display + edit
│   │   │   ├── AckPosturePanel.tsx   # AUTO_ACK toggle controls
│   │   │   └── ActionMenu.tsx        # context menu for card/zone actions
│   │   ├── chat/
│   │   │   ├── ChatPanel.tsx         # main chat (player or spectator)
│   │   │   └── ChatMessage.tsx       # single message rendering
│   │   ├── spectator/
│   │   │   └── SpectatorOverlay.tsx  # spectator-specific controls
│   │   ├── replay/
│   │   │   ├── ReplayControls.tsx    # play/pause/scrub/step
│   │   │   ├── ReplayTimeline.tsx    # event timeline visualization
│   │   │   └── SeatPerspectivePicker.tsx
│   │   ├── admin/
│   │   │   ├── UserManager.tsx
│   │   │   ├── ApiKeyAdmin.tsx
│   │   │   ├── DatasetExport.tsx
│   │   │   ├── PiiPurge.tsx
│   │   │   ├── DeckRecipeEditor.tsx
│   │   │   ├── ConventionTemplateEditor.tsx
│   │   │   └── ResearchDashboard.tsx
│   │   └── consent/
│   │       └── ConsentModal.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useTable.ts
│   │   └── useReplay.ts
│   └── types/
│       ├── models.ts           # mirrors backend Pydantic models
│       └── enums.ts            # ActionType, EventType, etc.
```

---

## Authentication Flow

The backend uses JWT tokens via client credentials (AI) or dev bootstrap (human).

### v0.1 Human Auth Flow
1. User lands on LandingPage.
2. Clicks "Play" → LoginModal opens.
3. LoginModal calls `POST /dev/bootstrap` with display_name.
4. Receives principal + credentials. Stores token in memory (React state). No localStorage needed for v0.1.
5. Token is included in all REST calls as `Authorization: Bearer {token}` and passed as query param on WebSocket connect (`/ws/{table_id}?token={token}`).

### v0.1 AI Auth Flow
1. AI developer creates credentials via API Key management page or direct API.
2. AI calls `POST /api/token` with client_id + client_secret.
3. Receives JWT. Uses for REST and WebSocket same as human.

---

## Page Specifications

### 1. LandingPage

**Route:** `/`

**Purpose:** Front door. What is Tavoliere, and get to playing.

**Content:**
- Tagline and brief description (static)
- "Play" button → triggers LoginModal if not authenticated, else navigates to LobbyPage
- "Spectate" button → navigates to LobbyPage in spectator mode
- Link to GitHub repo
- Link to SPQ-AN documentation

**State:** Reads auth state only. No API calls unless login triggered.

---

### 2. LoginModal

**Route:** N/A (modal overlay, triggered from any page)

**Purpose:** Authenticate human player.

**Content:**
- Display name input field
- "Enter" button → calls `POST /dev/bootstrap`
- Loading state while request in flight
- Error display if bootstrap fails
- On success: close modal, store token in AuthContext, redirect to LobbyPage

**Notes:**
- v0.1 uses dev bootstrap. Future: proper auth (OAuth, etc.)
- Modal should be dismissable via ESC or click-outside

---

### 3. LobbyPage

**Route:** `/lobby`

**Purpose:** Find and join games, or create one.

**Requires auth:** Yes. Redirect to `/` if not authenticated.

**Content:**
- **Table List** (TableList component)
  - Calls `GET /api/tables` on mount and polls every 5 seconds (or refresh button)
  - Each row shows: table display name, deck recipe, seats filled/max, created time
  - Click row → join flow:
    - If seats available: calls `POST /api/tables/{id}/join`, then navigates to `/table/{id}`
    - If full: option to spectate → navigates to `/spectate/{id}`
  - Visual indicator for research mode tables
- **Create Table** button → opens CreateTableModal
- **My Active Games** section (if seated at any tables)

**CreateTableModal:**
- Display name input
- Deck recipe selector (Standard 52, Euchre 24, Double Pinochle 80)
- Max seats (default 4, range 2-8)
- Research mode toggle
- Advanced settings (collapsible): objection window, rate limits, AI pacing
- "Create" → calls `POST /api/tables`, then auto-joins as host, navigates to `/table/{id}`

---

### 4. TablePage (Player UI)

**Route:** `/table/:tableId`

**Purpose:** The game. This is the core experience.

**Requires auth:** Yes + must be seated.

**Connection:** Opens WebSocket to `/ws/{tableId}?token={token}` on mount. Receives `state_sync` with full table state, then processes event stream.

**Layout (4-player optimized):**
```
┌─────────────────────────────────────────────┐
│  Phase Label          Seat Status Bar       │
├──────────┬────────────────────┬─────────────┤
│ Seat L   │   Table Center     │  Seat R     │
│ (name,   │   (center zone)    │  (name,     │
│  meld,   │                    │   meld,     │
│  tricks) │   Deck    Discard  │   tricks)   │
├──────────┴────────────────────┴─────────────┤
│  Partner Seat (top, name + meld + tricks)   │
├─────────────────────────────────────────────┤
│  Pending Action Bar (ACK/NACK buttons)      │
├─────────────────────────────────────────────┤
│  Your Hand (fan of cards, draggable)        │
├────────────────────┬────────────────────────┤
│  ACK Posture Panel │  Chat Panel            │
└────────────────────┴────────────────────────┘
```

**Components and behavior:**

**TableSurface** — master container. Receives table state from TableContext. Renders all zones and seats in the layout above.

**HandZone** — renders the player's private hand.
- Cards displayed as a fan, selectable
- Drag-and-drop to center zone = propose move_card action
- Right-click or long-press on card = ActionMenu (move to meld, reveal, etc.)
- Reorder by dragging within hand (unilateral, no ACK needed)

**PublicZone** — renders center, discard, deck.
- Center: shows face-up cards currently in play
- Discard: pile with top card visible
- Deck: face-down pile with card count badge
- Click deck = draw action (consensus)

**SeatOwnedZone** — renders meld(seat) and tricks_won(seat) for each seat.
- Shows cards in the zone
- Your own meld/tricks: can interact
- Others' meld/tricks: view only

**CardView** — single card component.
- Shows rank + suit
- Face-down state (blank back)
- Duplicate indicator (subtle badge with short unique_id suffix) when table has duplicate cards
- Selected state highlight
- Drag source

**DeckPile** — face-down stack.
- Shows card count
- Click to draw (triggers deal/draw intent)

**SeatDisplay** — per-seat info block.
- Display name
- AI badge if player_kind == "ai"
- Presence indicator (green=active, yellow=disconnected, gray=absent)
- Card count in hand (number only, no card visibility)

**PendingActionBar** — shown when consensus actions are pending.
- For each pending action:
  - Summary text (e.g., "Seat A wants to play J♠ to center")
  - ACK button (green ✓)
  - NACK button (red ✗) → opens reason selector (Rules / Turn / Clarify / Other)
  - Shows who has ACK'd, who hasn't
- Sends `ack` or `nack` via WebSocket

**DisputeBanner** — shown when table.dispute_active is true.
- "DISPUTE ACTIVE" banner
- Shows disputed action summary
- Shows who disputed and reason tag
- Resolution options for the action proposer: Revise, Cancel, Undo
- Highlights that canonical commits are paused

**PhaseLabel** — displays current phase.
- Click to edit (sends set_phase action via WebSocket)
- Shows phase text prominently

**AckPosturePanel** — per-seat AUTO_ACK configuration.
- Toggle switches for each action type: move_card, deal, set_phase, create_zone, undo
- Sends `set_ack_posture` via WebSocket on toggle
- Shows current posture state

**ActionMenu** — context menu on right-click/long-press.
- Options depend on context:
  - Card in hand: "Play to center", "Move to meld", "Reveal"
  - Card in meld: "Return to hand"
  - Zone: "Create custom zone"
- Each option constructs and submits appropriate ActionIntent via WebSocket

**ChatPanel** — right side or bottom panel.
- Scrollable message list
- Each message shows: seat display name, AI badge if applicable, timestamp, text
- Input field + send button
- Sends `chat` message via WebSocket
- Auto-scrolls on new message
- Visual separator when dispute starts/ends

**WebSocket Event Handling:**
- On `state_sync`: replace full table state in TableContext
- On `event`: apply event to state via reducer
  - `action_committed` / `action_finalized`: update zones (move cards)
  - `action_rolled_back`: revert zone state
  - `intent_created`: add to pending actions list
  - `ack_received` / `nack_received`: update pending action ACK status
  - `dispute_opened` / `dispute_resolved`: toggle dispute banner
  - `chat_message`: append to chat
  - `presence_changed`: update seat display
  - `phase_changed`: update phase label
  - `zone_created`: add zone to layout
  - `ack_posture_changed`: update posture display

---

### 5. SpectatorPage

**Route:** `/spectate/:tableId`

**Purpose:** Watch a live game without participating.

**Requires auth:** Yes (for identity tracking), but does NOT require being seated.

**Connection:** WebSocket to `/ws/{tableId}?token={token}` — backend returns observer-filtered state (public zones only, no private hands).

**Layout:** Same as TablePage but:
- No HandZone (spectator has no hand)
- No PendingActionBar (spectator can't ACK/NACK)
- No ActionMenu (spectator can't act)
- No AckPosturePanel
- All seat card counts visible but hand contents hidden
- Chat panel is SPECTATOR CHAT — separate channel from player chat
  - Spectator messages do NOT appear in player chat
  - Spectator messages are tagged with "[Spectator]" prefix
  - Spectators can see player chat (read-only)

**Implementation note:** The backend currently has observer support via `filter_table_for_seat(table, "__observer__")`. Spectator WebSocket connection needs a separate endpoint or a flag on the existing one. If backend doesn't support spectator WS yet, spec it as:
- `GET /api/tables/{table_id}` already returns public-only view for non-seated identities
- Spectator WS: `/ws/{table_id}?token={token}&mode=spectate`
- Backend should accept spectator connections without seat assignment
- Spectator receives events but cannot send actions, only spectator chat

**Spectator chat backend requirement (may need to be added):**
- Chat messages with a `channel` field: `"player"` or `"spectator"`
- Player chat visible to all; spectator chat visible only to spectators
- Spectator chat is logged in event log (for research: spectator AI commentary)

---

### 6. ReplayPage

**Route:** `/replay/:tableId`

**Purpose:** Replay a completed game from the event log.

**Requires auth:** Yes (research access or personal game log).

**Data source:** `GET /api/tables/{tableId}/research/events` — fetches full event log.

**Layout:** Same as SpectatorPage (no interaction controls) plus:

**ReplayControls:**
- Play / Pause button
- Step Forward / Step Back (one event at a time)
- Speed control (0.5x, 1x, 2x, 4x)
- Event index display ("Event 47 / 312")

**ReplayTimeline:**
- Horizontal timeline bar
- Scrub handle (click or drag to any point)
- Color-coded event markers:
  - Green: commits
  - Red: disputes
  - Yellow: rollbacks
  - Blue: chat messages
- Current position indicator

**SeatPerspectivePicker:**
- Buttons for each seat + "Observer" view
- Selecting a seat shows what that seat could see at the current replay position
- Observer view shows public-only (default)

**State reconstruction:**
- Load full event log
- Build state by replaying events from start to current position
- On scrub: replay from nearest snapshot + events forward
- Seat perspective: apply visibility filter for selected seat

**Chat synchronized with replay:**
- Chat panel shows messages up to current replay position
- Messages appear as timeline advances

---

### 7. GameLogPage (Personal History)

**Route:** `/games`

**Purpose:** Show all games the current user has participated in.

**Requires auth:** Yes.

**Data source:** Needs a backend endpoint (may need to be added):
- `GET /api/games` — returns list of tables the authenticated identity has been seated at
- Each entry: table_id, display_name, deck_recipe, date, seats (with names and AI flags), session duration, research_mode flag

**Content:**
- Sortable table of past games
- Columns: Date, Game Name, Deck, Players, Duration, Research Mode
- Click row → navigates to `/replay/{tableId}` (if events available)
- Filter by date range, deck type, human-only/mixed/AI-only

**Backend requirement:** The backend currently manages tables in-memory and they're ephemeral. For game log to work, completed table metadata and event logs must be persisted somewhere. Options for v0.1:
- Write event log to disk (NDJSON file per session) on table close
- Index file mapping identity → sessions
- Or: game log only works for tables still in memory (acceptable for v0.1 with caveat)

---

### 8. ProfilePage

**Route:** `/profile`

**Purpose:** User settings, consent management, display preferences.

**Requires auth:** Yes.

**Content:**
- Display name (editable)
- Account info (identity_id, created date)
- **Consent Management:**
  - Shows current consent status across all research tables
  - Toggle consent tiers (same checkboxes as ConsentModal)
  - Longitudinal tracking opt-in/opt-out with clear explanation
- **Preferences:**
  - Default AUTO_ACK posture (applied when joining new tables)
  - Card display preferences (future: themes, card backs)
- **Data Rights:**
  - "Export my data" button → triggers export of all personal game data
  - "Delete my data" button → triggers PII purge (with confirmation dialog)

---

### 9. ApiKeysPage

**Route:** `/api-keys`

**Purpose:** Manage API credentials for AI players.

**Requires auth:** Yes.

**Data source:** `GET /api/credentials`

**Content:**
- List of existing credentials:
  - Display name, client_id (shown), created date, status
  - "Revoke" button per credential → `DELETE /api/credentials/{id}`
- "Create New Key" button:
  - Display name input
  - On create → calls `POST /api/credentials`
  - Shows client_id + client_secret ONCE (with copy button and warning: "save this now, it won't be shown again")
- Usage instructions / code snippet for connecting an AI agent

---

### 10. AdminPage

**Route:** `/admin`

**Purpose:** System administration.

**Requires auth:** Yes + admin role (v0.1: host-level or hardcoded admin identity).

**Tabs/sections:**

**UserManager:**
- List all principals
- Search by display name or identity_id
- Actions per user: view details, suspend, delete (with PII purge confirmation)
- Delete shows consequence: "PII will be removed. Anonymized research data retained per consent."

**ApiKeyAdmin:**
- List ALL credentials across all principals
- Filter by principal, player_kind, active/revoked
- Revoke any key
- Audit: show which tables a credential has connected to

**DatasetExport:**
- Select sessions by: date range, deck recipe, research mode, participant composition
- Consent-tier filter: automatically excludes data not covered by consent
- Export format: NDJSON
- Preview: show event count, participant count, consent coverage before export
- Download button

**PiiPurge:**
- Search for identity by hash or display name
- Show what will be deleted vs retained
- Confirm + execute
- Audit log of purge actions

**DeckRecipeEditor:**
- List existing recipes (built-in + custom)
- Create new recipe:
  - Name
  - Rank set (checkboxes or range selector)
  - Suit set (checkboxes)
  - Copy count (how many copies of each card)
  - Preview: shows total card count and card list
- Edit/delete custom recipes (built-in recipes are read-only)

**ConventionTemplateEditor:**
- List existing templates
- Create new template:
  - Template name (e.g., "Euchre - Standard", "Double Pinochle - House Rules")
  - Associated deck recipe (dropdown)
  - Seat count
  - Partnership configuration (e.g., "1&3 vs 2&4" or "none")
  - Suggested zones (checkboxes: meld, tricks_won, custom names)
  - Suggested phases (ordered list: "Deal", "Bid", "Play", "Score")
  - Suggested AUTO_ACK defaults
  - Convention notes (semi-structured):
    - Sections: Bidding, Trumps, Scoring, Special Rules, House Rules
    - Each section: freeform text
  - None of this is enforced. Template pre-fills table creation and provides a reference doc visible at the table.
- Edit/delete templates

**ResearchDashboard:**
- Active research sessions count
- Total events collected
- Consent tier distribution (pie chart or bar: how many users at each tier)
- Data health: any sessions with sequence gaps, missing events
- Storage estimate
- Quick links to export and purge tools

---

### 11. DataExplorerPage

**Route:** `/research/explorer`

**Purpose:** Query and browse the research corpus.

**Requires auth:** Yes + admin/researcher role.

**Content:**
- **Session Browser:**
  - Filter by: date range, deck recipe, participant composition (human-only, mixed, AI-only), model name/version
  - Sort by: date, event count, dispute density, duration
  - Results as table rows, click to expand or navigate to replay
- **Metric Calculator:**
  - Select sessions (multi-select from browser, or "all matching filter")
  - Select metric family (CE, RC, NS, CA, SSC)
  - Compute and display metrics
  - Compare across selections (e.g., "Claude sessions vs GPT sessions")
- **Event Inspector:**
  - Select a session
  - Scrollable event log with filtering by event type
  - Click event → shows full event detail JSON
  - Link to replay at that event position
- **Export:**
  - Export filtered results as NDJSON or CSV
  - Export computed metrics as CSV

---

### 12. ConsentModal

**Route:** N/A (modal, triggered when joining a research-mode table)

**Purpose:** Obtain informed consent before research logging begins.

**Trigger:** After `POST /api/tables/{id}/join` succeeds AND table.research_mode is true, show ConsentModal before connecting WebSocket.

**Content:**
- Research Mode disclosure text (from spec A.8):
  - What is recorded
  - What is NOT stored (PII)
  - Rights (export, deletion, leave)
- Required checkbox:
  - [ ] I consent to Research Mode logging
- Optional checkboxes:
  - [ ] I consent to storage of chat message text
  - [ ] I consent to use of my data for AI training / model improvement
  - [ ] I consent to anonymized publication of aggregate findings
  - [ ] I consent to anonymized publication of short chat excerpts
  - [ ] I consent to my pseudonymized data being linked across sessions for longitudinal research
- AI participation acknowledgment:
  - [ ] I understand that AI participants may be seated at this table and are visibly flagged as AI
- "Accept and Continue" button (requires at minimum the required checkbox + AI acknowledgment)
- "Decline" button → leaves the table, returns to lobby

**On accept:** Calls `POST /api/tables/{id}/consent` with tier selections, then opens WebSocket connection.

---

### 13. PostGameSummary

**Route:** `/table/:tableId/summary` (or modal on table close)

**Purpose:** Session summary after a game ends.

**Trigger:** When table is closed/destroyed by host, all connected clients navigate to summary.

**Content:**
- Session duration
- Total actions, disputes, undos
- Players at table (names, AI flags)
- If research mode: basic SPQ-AN metrics per seat (CE, RC, NS, CA, SSC)
- "Watch Replay" button → `/replay/{tableId}`
- "Return to Lobby" button → `/lobby`
- "Share" → copy link to replay

---

## Shared Components

### Header
- Tavoliere logo/wordmark
- Nav links: Lobby, My Games, API Keys, Profile
- Admin link (if admin)
- Research Explorer link (if researcher/admin)
- User display name + logout

### ConsentModal
- Reusable; can be triggered from table join or from ProfilePage

---

## WebSocket Hook: useTableSocket

```typescript
interface UseTableSocket {
  connect(tableId: string, token: string, mode?: "player" | "spectate"): void;
  disconnect(): void;
  sendAction(intent: ActionIntent): void;
  sendAck(actionId: string): void;
  sendNack(actionId: string, reason?: DisputeReason, reasonText?: string): void;
  sendDispute(actionId: string, reason?: DisputeReason, reasonText?: string): void;
  sendChat(text: string): void;
  sendAckPosture(posture: AckPosture): void;
  sendPing(): void;
  connected: boolean;
  lastError: string | null;
}
```

Events received are dispatched to TableContext reducer.

---

## State Management

### AuthContext
```
{
  token: string | null
  identity: { identity_id, display_name, player_kind } | null
  credentials: Credential[]
  isAuthenticated: boolean
}
```

### TableContext
```
{
  table: {
    table_id, display_name, deck_recipe, phase, dispute_active,
    research_mode, settings
  }
  seats: Seat[]
  zones: Zone[]
  cards: Record<string, Card>
  mySeatId: string | null
  pendingActions: PendingAction[]
  chatMessages: ChatMessage[]
  events: Event[]  // recent events for UI updates
}
```

Reducer handles each EventType and updates the appropriate slice of state.

---

## Backend Endpoints Needed (Not Yet Implemented)

The following are required by the frontend but may not exist yet in the backend:

1. **Spectator WebSocket** — `/ws/{table_id}?token={token}&mode=spectate`
   - Accepts connection without seat assignment
   - Returns observer-filtered state
   - Receives events but cannot send actions
   - Can send spectator chat

2. **Spectator Chat Channel** — chat messages need a `channel` field (`player` | `spectator`)
   - Player chat visible to all
   - Spectator chat visible only to spectators and in event log

3. **Game History** — `GET /api/games`
   - Returns list of tables the identity has participated in
   - Requires some form of session persistence (at minimum: metadata + event log to disk on table close)

4. **Event Log Persistence** — write NDJSON to disk on table close for replay/history
   - Index file: identity_id → [session_ids]

5. **Admin Endpoints:**
   - `GET /api/admin/principals` — list all users
   - `DELETE /api/admin/principals/{id}` — delete user + PII purge
   - `GET /api/admin/credentials` — list all credentials (cross-principal)
   - `POST /api/admin/deck-recipes` — CRUD custom deck recipes
   - `POST /api/admin/convention-templates` — CRUD convention templates
   - `GET /api/admin/research/health` — research dashboard metrics

6. **Convention Templates** — `GET /api/convention-templates`
   - Available during table creation to pre-fill settings

7. **Post-Game Summary** — `GET /api/tables/{id}/summary`
   - Returns session stats (duration, action count, dispute count, participants)
   - If research mode: computed SPQ-AN metrics

---

## Build Priority

### Phase 1 — Playable (MVP)
1. AuthContext + LoginModal (dev bootstrap)
2. LobbyPage + CreateTableModal + TableList
3. TablePage (full player UI with WebSocket)
4. ChatPanel
5. ConsentModal

This gets 4 humans to a table playing cards.

### Phase 2 — Observable
6. SpectatorPage + spectator chat
7. ReplayPage + ReplayControls + timeline
8. GameLogPage
9. PostGameSummary

### Phase 3 — Manageable
10. ApiKeysPage
11. ProfilePage
12. AdminPage (all tabs)

### Phase 4 — Researchable
13. DataExplorerPage
14. ResearchDashboard
15. SPQ-AN metric computation UI

---

## Design Notes

- **No decorative UI in v0.1.** Clean, functional, readable. Tailwind utility classes only. No custom illustrations, no animations beyond basic transitions. Cards can be simple rectangles with rank/suit text. Pretty comes later.

- **Cards are the hardest UI element.** They need to: show rank/suit clearly, indicate face-up/face-down, show duplicate badge when needed, be selectable, be draggable, and work at different zone scales (fanned in hand, stacked in deck, spread in center). Get this component right first and everything else follows.

- **Mobile is not a v0.1 target** but the layout should not be actively hostile to tablets. Responsive breakpoints are nice-to-have, not required.

- **Accessibility basics:** keyboard navigation for card selection and ACK/NACK buttons. Screen reader labels for card rank/suit. Color should not be the only indicator of state (add icons/text to presence, dispute, etc.).

- **Error handling:** WebSocket disconnection should show a reconnecting banner, auto-retry with backoff. REST errors should show inline, not alert boxes.