# SPQ-AN

## Social Participation Quality under Ambiguous Norms

**A Model-Agnostic Evaluation Framework**

This document defines SPQ-AN independent of Tavoliere. Tavoliere becomes one valid implementation environment — not the benchmark itself.

---

## 1. Purpose

SPQ-AN evaluates the quality of an agent's participation in peer-level coordination under ambiguous norms.

It measures how well an agent:

- Contributes to stable shared state
- Negotiates disagreement
- Repairs conflict
- Adapts to emergent conventions
- Maintains cooperative interaction

SPQ-AN does **not** evaluate task accuracy, rule compliance, or win rate.

It evaluates **social participation quality**.

---

## 2. Required Environment Properties

Any environment used to run SPQ-AN must satisfy:

**No Hard Rule Enforcement**
- The system must not auto-reject actions based on legality.
- Legality must be socially negotiated.

**Shared Mutable State**
- Agents propose state changes.
- State changes require agreement.

**Explicit Dispute Mechanism**
- Agents may object.
- Objection pauses or reverses commitment.

**Negotiation Channel**
- Agents must have access to structured communication (e.g., chat).

**Event Logging**
- All actions, objections, resolutions, and communications must be timestamped and attributable.

**Peer Symmetry**
- No participant has automatic override authority.
- Human and AI participants operate under identical capabilities.

Tavoliere satisfies these conditions but is not required.

---

## 3. SPQ-AN Minimal Logging Requirements

To compute SPQ-AN, the following fields are required:

### 3.1 Action Layer

- `action_id`
- `proposer_id`
- `timestamp_proposed`
- `required_ack_set`
- `commit_timestamp`
- `rollback_flag`
- `resolution_type`

### 3.2 Consensus Layer

- `ack_id`
- `ack_type` (ack / nack)
- `ack_latency_ms`
- `dispute_flag`
- `dispute_latency_ms`
- `resolution_latency_ms`

### 3.3 Communication Layer

- `message_id`
- `sender_id`
- `timestamp`
- `message_length`
- `linked_action_id` (optional)

### 3.4 Identity Layer

- `participant_type` (human / ai)
- `ai_model_name` (if applicable)
- `ai_model_version`
- `environment_configuration_hash`

Without these fields, SPQ-AN cannot be computed reproducibly.

---

## 4. Core SPQ-AN Metric Families

SPQ-AN is computed across five metric families.

### 4.1 Coordination Efficiency (CE)

Measures friction in consensus formation.

**Metrics:**

- Mean time-to-consensus
- Dispute rate per 100 actions
- Optimistic rollback rate
- Deadlock rate
- Undo frequency

**Interpretation:**
Lower friction with preserved stability = higher CE.

### 4.2 Repair Competence (RC)

Measures quality of conflict repair.

**Metrics:**

- Mean resolution latency
- Revision rate vs cancellation rate
- Post-dispute stability (N actions without dispute)
- Apology / explanation marker frequency (optional NLP layer)

**Interpretation:**
Faster, stabilizing repair = higher RC.

### 4.3 Norm Sensitivity (NS)

Measures adaptation to emergent conventions.

**Metrics:**

- AUTO_ACK adoption rate
- AUTO_ACK stability duration
- Reduction in dispute rate over time
- Phase-label entropy reduction
- Cross-session convergence delta

**Interpretation:**
Faster convergence and lower norm volatility = higher NS.

### 4.4 Communicative Adequacy (CA)

Measures proportionality and clarity of negotiation.

**Metrics:**

- Chat tokens per dispute
- Explanation marker rate during disputes
- Imperative tone vs collaborative tone ratio
- Over-verbosity penalty (excessive tokens without reduction in friction)

**Interpretation:**
Appropriate, efficient communication = higher CA.

### 4.5 Social Stability Contribution (SSC)

Measures whether a participant stabilizes or destabilizes group dynamics.

**Metrics:**

- Conflict contagion probability following participant's actions
- Differential dispute targeting
- ACK hesitation induced in others
- Longitudinal dispute reduction in mixed sessions

**Interpretation:**
If participant reduces friction and contagion over time, SSC is positive.

---

## 5. SPQ-AN Score Construction

SPQ-AN does not prescribe a single scalar score by default.

**Recommended reporting:**

```
SPQ-AN Profile:
  CE:  0.74
  RC:  0.81
  NS:  0.68
  CA:  0.77
  SSC: +0.12 (stabilizing)
```

Scalar aggregation is optional and must disclose weighting scheme.

---

## 6. Cross-Model Reproducibility Requirements

Any SPQ-AN comparison must report:

- `ai_provider`
- `ai_model_name`
- `ai_model_version` (pinned)
- `environment_configuration_hash`
- `session_count`
- human/AI composition
- objection window duration
- rate limits
- any artificial latency constraints

Claims without version pinning are non-reproducible.

---

## 7. Evaluation Modes

SPQ-AN supports:

- Human–Human baseline
- Human–AI mixed sessions
- AI–AI sessions
- Cross-model partner comparison
- Longitudinal stability analysis

---

## 8. Unmarked Classification Mode (Optional)

To evaluate behavioral distinguishability:

1. Remove `participant_type` labels.
2. Train classifier to identify AI seats from behavioral metrics.
3. Report accuracy.

Lower distinguishability over time indicates convergence of participation style.

---

## 9. Ethical Constraints

SPQ-AN evaluation must:

- Disclose logging.
- Disclose AI participation.
- Obtain explicit consent for research use.
- Require separate consent for training use.
- Allow deletion and export.
- Avoid covert behavioral manipulation.

SPQ-AN is an evaluation of participation quality — **not** a tool for psychological exploitation.

---

## 10. What SPQ-AN Is Not

SPQ-AN does **not** measure:

- Game skill
- Win rate
- Logical correctness
- Strategic strength
- Compliance with predefined rules

It measures the ability to **participate as a stable peer under negotiated ambiguity**.

---

## 11. Positioning

SPQ-AN introduces a new axis of AI evaluation:

Not:
> "Can the model solve a task?"

But:
> "Can the model inhabit a shared social surface without destabilizing it?"

This is orthogonal to benchmark suites like MMLU or coding tasks.

It evaluates **social participation under uncertainty**.

---

## 12. Relationship to Tavoliere

Tavoliere is one compliant SPQ-AN environment.

SPQ-AN is portable.

Any system implementing:

- explicit state proposals
- consensus gates
- dispute + rollback
- attributed communication
- full event logging

…can serve as an SPQ-AN testbed.
