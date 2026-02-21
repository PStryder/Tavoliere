# Appendix A — Research Instrumentation & Data Governance

Tavoliere v0.1 may optionally operate in **Research Mode**, which captures a structured, timestamped record of all interaction events.

This mode is opt-in per table and requires explicit consent from all human participants (see Section A.8).

The purpose of this appendix is to define:

- The complete event schema
- Derived research metrics
- Identity handling
- Anonymization guarantees
- Consent language requirements

---

## A.0 New Term and Benchmark Definition

### A.0.1 Social Participation Quality under Ambiguous Norms (SPQ-AN)

**Definition:**
Social Participation Quality under Ambiguous Norms (SPQ-AN) is an evaluation framework for AI (and human) participants operating as peers in an environment where:

- No rule engine enforces legality or turn structure.
- Shared state changes require negotiated agreement (consensus and/or objection windows).
- "Correctness" is socially constructed and resolved via dispute + chat.
- Participants must coordinate under partial information and evolving conventions.

SPQ-AN evaluates a participant not by task accuracy, but by the **quality of their social participation** in maintaining coherent, cooperative play under ambiguity.

SPQ-AN is measured from the Tavoliere corpus using:

- **Coordination Efficiency:** time-to-consensus, dispute frequency, resolution latency
- **Repair Competence:** how conflicts are de-escalated, revised, or repaired
- **Norm Sensitivity:** adoption and stability of AUTO_ACK norms; phase label convergence; reduced friction over time
- **Communicative Adequacy:** appropriate explanation, clarity, and negotiation behavior via chat
- **Social Stability Contribution:** whether the participant's presence decreases conflict contagion and deadlocks over sessions

**Reproducibility:** SPQ-AN results must report model name + pinned version + table settings and corpus scope (see A.6.8).

---

## A.1 Research Mode Flag

Each table includes:

```
research_mode: boolean
research_mode_version: string
```

- If **false**, event logs may still exist for gameplay but are not retained beyond session.
- If **true**, enhanced logging fields are captured and retained per policy.

---

## A.2 Event Schema — Canonical Research Log

All events are append-only and timestamped in UTC with millisecond precision.

Each event contains:

### A.2.1 Core Event Envelope

- `event_id`: UUID
- `table_id`: UUID
- `session_id`: UUID
- `event_type`: enum
- `timestamp_utc_ms`: int
- `server_sequence_number`: int
- `phase_label`: string

### A.2.2 Seat Metadata Snapshot

Captured at time of event:

- `seat_id`: string
- `seat_type`: enum {human, ai}
- `seat_display_name`: string
- `seat_pseudonym_id`: string
- `seat_presence_state`: enum {active, disconnected, absent}
- `auto_ack_posture`: dict[action_type → boolean]

### A.2.3 Identity Metadata (Research Layer Only)

Stored separately from gameplay log:

- `identity_hash`: SHA256(user_id + salt)
- `longitudinal_link_id`: string | null
- `longitudinal_link_consent`: boolean
- `ai_model_name`: string (if seat_type == ai)
- `ai_model_version`: string
- `ai_provider`: string
- `client_type`: enum {web_ui, api_client}
- `client_version`: string

No raw emails, usernames, IP addresses, or API keys are stored in research corpus.

**Longitudinal linking note:**

- `identity_hash` is per-identity.
- `longitudinal_link_id` is generated only if the user explicitly opts in via the longitudinal consent tier (see A.8).
- Without longitudinal consent, sessions must not be linkable even pseudonymously. This prevents accidental cross-session inference.

---

## A.3 Action Events

For all Intent, Commit, Dispute, and Undo events:

- `action_id`: UUID
- `action_type`: enum
- `visibility_transition`: enum {none, private_to_public, public_to_private, private_to_private}
- `object_ids`: list[string]
- `source_zone_id`: string
- `destination_zone_id`: string
- `is_optimistic`: boolean
- `required_ack_set`: list[seat_id]

### A.3.1 ACK Events

- `ack_type`: enum {ack, nack}
- `ack_latency_ms`: int — from intent creation
- `ack_posture_at_time`: boolean

### A.3.2 Dispute Events

- `dispute_reason_tag`: enum {rules, turn_order, clarify, other}
- `dispute_latency_ms`: int — from commit or intent
- `dispute_window_ms_remaining`: int

### A.3.3 Resolution Events

- `resolution_type`: enum {revise_intent, cancel_intent, undo, mark_absent}
- `resolution_latency_ms`: int — from dispute start
- `chat_messages_during_resolution`: int

---

## A.4 Chat Events

Each chat message includes:

- `chat_message_id`: UUID
- `sender_seat_id`: string
- `timestamp_utc_ms`: int
- `message_length_chars`: int
- `message_length_tokens`: int (if tokenized)
- `in_response_to_action_id`: UUID | null
- `is_resolution_related`: boolean

**Optional (computed offline):**

- `embedding_vector`: optional
- `sentiment_score`: optional
- `politeness_score`: optional
- `explanation_marker`: boolean
- `apology_marker`: boolean
- `imperative_marker`: boolean

Raw text may be stored or optionally redacted depending on consent level (see A.8).

---

## A.5 Table State Snapshot Fields

Captured periodically:

- `snapshot_id`: UUID
- `active_phase_label`: string
- `seat_auto_ack_distribution`: dict[seat_id → enabled_action_types]
- `pending_actions_count`: int
- `dispute_active`: boolean
- `table_configuration_hash`: string

**Table Configuration Hash:**
A deterministic hash of the table's configuration at session start, computed from:

- objection window duration
- rate limits
- AUTO_ACK defaults
- shuffle policy
- AI pacing settings
- deck recipe
- seat count

This enables machine-verifiable reproducibility. SPQ-AN results can reference a single `config_hash` rather than manually enumerating settings.

---

## A.6 Derived Metrics (Recommended Computations)

Derived metrics are not stored in canonical log but computed for analysis.

### A.6.1 Consensus Metrics

- Mean ACK latency per seat
- Variance of ACK latency
- Time-to-unanimity
- % actions disputed
- % optimistic actions rolled back
- Undo frequency per 100 actions
- Deadlock frequency
- Mark-absent events per session

### A.6.2 Compression Friction Metrics

- Disputes per 100 actions
- Resolution latency mean/variance
- Chat volume per dispute
- Repeat dispute on same action type
- Dispute density clustering (disputes within N actions)

### A.6.3 Trust / Norm Formation Metrics

- AUTO_ACK adoption rate
- AUTO_ACK churn rate
- Stable AUTO_ACK sets duration
- Phase label entropy per session
- Phase label convergence across sessions

### A.6.4 Human–AI Interaction Metrics

- Differential ACK latency (human→AI vs human→human)
- Differential dispute rate targeting AI seats
- Chat verbosity toward AI vs human
- Apology rate toward AI vs human
- Imperative rate toward AI vs human
- AI vs human dispute initiation frequency
- AI rollback rate

### A.6.5 Partnership Modeling Metrics

For partnership games:

- Disputes between partners vs opponents
- Coordination latency between partners
- Phase-stability when partner is AI vs human
- Convergence rate over repeated sessions

### A.6.6 Cross-Session Learning Metrics

- Dispute rate delta over sessions
- Resolution latency delta
- AUTO_ACK stabilization over time
- Language compression (message length reduction)

### A.6.7 Behavioral Signature Metrics

- Timing distribution shape
- Dispute style classification
- Repair style classification (concede vs justify)
- Conflict contagion probability
- Social temperature metric (chat volume + dispute density)

### A.6.8 Cross-Model Comparison and Version Pinning

Cross-model studies must record and report model identity precisely.

**Required fields** (already in schema, now elevated in methodology):

- `ai_provider`
- `ai_model_name`
- `ai_model_version`
- `client_version`

**Methodology requirement:**

Any comparison claim of the form:

- "Model X disputes more than Model Y"
- "Claude is more cooperative than GPT"
- "Model A is a better table companion"

…must include:

- Pinned versions for all models in the comparison (e.g., `claude-3.x.y`, `gpt-4.x.y`)
- Table settings:
  - objection window
  - rate limits
  - AUTO_ACK eligibility
  - any AI pacing settings
- Session selection criteria
- Seat composition (human/AI mix)
- Time range (since model behavior can drift even within versioned labels via provider updates)

**Stability across versions** (optional but valuable):

If the same model family is tested across versions, report:

- which SPQ-AN metrics are stable
- which change significantly
- whether changes align with release notes (if available)

This turns "drift" into a measurable phenomenon rather than noise.

---

## A.7 Training Signal Extraction (Optional, With Consent Firewall)

> **Important:** Research logging consent is not training consent.

The Tavoliere corpus may contain training signals (ACK/NACK labels, revised intents, negotiation text). However:

**No corpus content may be used for training, fine-tuning, preference optimization, or model improvement** unless the participant explicitly opted into the Training Consent Tier (see A.8).

This includes:

- supervised learning
- RLHF / DPO / preference learning
- retrieval-augmented fine-tuning corpora
- synthetic dataset distillation using human chat or action traces

### A.7.1 Training Consent Tier Requirement

Training use requires **all** of the following:

- Research Mode consent (required)
- Chat storage consent (if chat is used)
- Training use consent (required)
- Publication consent (only if publishing excerpts)

If Training Use Consent is **not** granted:

- training extraction must be disabled
- dataset export must exclude any training-derived labels intended for training pipelines
- chat embeddings may still be computed for analysis if permitted by consent tier, but must not be repurposed for training.

### A.7.2 Dataset Partitioning Rule (Hard Separation)

If training consent exists:

- Training datasets must be stored separately from research datasets.
- Must include a machine-verifiable `consent_scope_id` in each record.
- Must support deletion that propagates to training datasets (right-to-delete).

---

## A.8 Consent Language (Updated With Training Tier Clarity)

Add this explicit line to the Research Mode disclosure:

> **Training Use:**
> Your participation in Research Mode does not automatically allow your data to be used to train or improve AI models.
> Training use requires a separate, explicit opt-in.

And add separate checkboxes:

- [ ] I consent to Research Mode logging.
- [ ] I consent to storage of chat message text.
- [ ] I consent to use of my data for AI training / model improvement.
- [ ] I consent to anonymized publication of aggregate findings.
- [ ] I consent to anonymized publication of short chat excerpts (optional, separate).
- [ ] I consent to my pseudonymized data being linked across sessions for longitudinal research.

Also include an "AI participant disclosure" acknowledgement:

- [ ] I understand that AI participants may be seated at this table and are visibly flagged as AI.

---

## A.9 AI Participation Metadata

AI seats must include:

- `ai_disclosed_to_players`: boolean
- `ai_training_use_allowed`: boolean
- `ai_model_metadata_exposed`: boolean

AI seats must **not**:

- Access hidden zones
- Access logs beyond per-seat visibility
- Access identity hashes
- Receive research-only metadata not visible to humans

**AI consent requirement:**

If AI model is owned by external party:

- Must comply with provider's data use policy.
- Must not store raw chat unless permitted by host.

---

## A.10 Anonymization & Data Governance

Research dataset must:

- Replace user identifiers with salted hash.
- Separate identity table from event table.
- Allow per-session deletion.
- Allow per-identity purge.
- Strip IP addresses and connection metadata.
- Support export in structured JSON format.

**Optional:**

- Differential privacy for published aggregates.
- Chat redaction mode (store embeddings only).

---

## A.11 Retention Policy (v0.1 Suggested)

**Default:**

- 90 days retention unless exported.
- Immediate deletion upon user request.
- Session-level deletion available.

---

## A.12 Storage Considerations

Storage is expected to be minimal:

- Average session < 1MB structured JSON.
- Embeddings optional.
- Token counts negligible relative to modern storage.
- Compression encouraged but not required.

---

## A.13 Ethical Boundary

Tavoliere is **not**:

- A deception experiment
- A covert behavioral study
- A psychological manipulation tool

> **The Tavoliere research corpus shall not be used to develop systems intended to covertly manipulate, exploit, or psychologically steer human participants without their knowledge and consent.**

Participants must be informed that:

- AI seats may be present.
- Logging is active.
- The table records negotiation behavior.
- No hidden instrumentation.

---

## A.14 Research Mode Toggle Summary

**When Research Mode is ON:**

- Enhanced event logging active.
- Identity pseudonymization enforced.
- Consent required.
- Export/delete endpoints enabled.

**When OFF:**

- Event log used only for session runtime.
- No retention beyond server lifetime.

---

## Final Structural Note

The corpus generated under Research Mode represents:

> A timestamped, attributed record of multi-agent consensus formation under ambiguity, including both state transitions and semantic negotiation.

This dataset enables:

- Consensus dynamics research
- Human–AI interaction analysis
- Norm formation study
- Model behavioral signature comparison
- Social repair and conflict resolution modeling
- AI social-participation training

Without any rule engine mediating behavior.

---

## A.15 Replay (Deterministic Reconstruction + Viewer)

A complete Tavoliere event log enables deterministic replay of sessions. Replay is a first-class research tool and a key legibility layer for non-research stakeholders.

### A.15.1 Replay Definition

A Replay is the deterministic reconstruction of:

- table state
- visible state per seat
- event timeline (intents, ACKs, disputes, chat)
- rollbacks and undo history

Replay supports:

- Qualitative review of interesting sessions identified via metrics
- Demonstrations ("watch this human–AI game unfold")
- Annotation for later analysis
- Debugging protocol edge cases

### A.15.2 Determinism Requirements (Replay-Ready Logging)

To guarantee replay fidelity, the corpus must include:

**RNG provenance** (for shuffles and any randomization):

- `rng_scheme`: enum {server_authoritative, seed_commit_reveal, other}
- `rng_seed_id`: string
- `rng_seed_hash`: string (optional)
- `rng_seed_revealed`: boolean

Minimum v0.1 acceptable: server-authoritative ordering logged as outcomes (deck order after shuffle).

**AI Latency Simulation Metadata:**

- `ai_min_action_delay_ms`: int | null
- `ai_latency_simulation_enabled`: boolean

AI timing distribution is a behavioral signature. If artificial pacing is applied, it materially affects SPQ-AN timing metrics. Researchers must know whether timing was raw or simulated to interpret results correctly.

**State reconstruction anchors:**

- `snapshot_frequency_events`: int
- `snapshot_id`
- `snapshot_hash`: string (optional)

**Event causality integrity:**

- `server_sequence_number`
- `event_id`
- `previous_event_id` (optional)

> **Future hardening note:** a hash chain (`previous_event_hash`) would provide stronger integrity verification than reference IDs, enabling detection of missing or tampered events. Not required for v0.1.

### A.15.3 Replay Viewer Requirements (Non-Normative, Recommended)

A replay viewer should be able to:

- scrub timeline by event index or timestamp
- render table state at any point
- switch seat perspective (visibility filtering)
- show pending actions + ACK state as overlays
- show dispute windows and rollbacks
- display chat synchronized with events
- export "highlight clips" (event ranges) for qualitative review

### A.15.4 Qualitative Research Workflow Enablement

Replay enables a hybrid workflow:

1. **Use metrics to detect notable sessions:**
   - high dispute density
   - unusual trust adoption patterns
   - atypical AI/human interaction

2. **Replay the session to examine:**
   - how norms were negotiated
   - repair behavior and tone
   - emergent conventions

3. **Tag/annotate moments** for later coding.

To support this, optional annotation events may be allowed (researcher-only, not visible to players) stored in a separate overlay log:

> **Critical:** Annotations must never be stored in or appended to the canonical event log, as this would compromise replay determinism and corpus integrity.

- `annotation_id`
- `timestamp_utc_ms`
- `event_id_reference`
- `tag_labels`
- `freeform_note`
