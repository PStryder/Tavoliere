# Tavoliere: A Rule-Agnostic Consensus Substrate for Studying Social Participation Under Ambiguous Norms

## Abstract

Tavoliere is a rule-agnostic, API-first consensus mediation substrate designed to study peer-level coordination between human and artificial agents under ambiguous norms. Unlike conventional digital game engines, Tavoliere encodes no rules of play, no scoring logic, and no legality enforcement. It does not determine correctness. Instead, it provides structured primitives for proposing shared state transitions, acknowledging or disputing those proposals, rolling back contested commits, and resolving disagreement through explicit communication.

This paper introduces Tavoliere as both a coordination platform and a research instrument. We define a new evaluative axis - Social Participation Quality under Ambiguous Norms (SPQ-AN) - and describe how Tavoliere enables reproducible measurement of negotiated consensus formation, repair behavior, norm convergence, and social stability contribution. We do not present empirical findings here. Rather, we articulate the architecture, instrumentation model, and research program enabled by the platform.

---

## 1. Motivation

### 1.1 The Missing Axis in AI Evaluation

Contemporary AI evaluation is dominated by task-oriented benchmarks. Models are assessed on knowledge recall, reasoning accuracy, coding correctness, and structured problem-solving. These benchmarks share a common assumption: a fixed objective function and a ground-truth evaluator. The task is defined in advance; correctness is externally adjudicated.

Yet many real-world deployments of AI systems do not occur under these conditions. They unfold in collaborative settings where rules are incomplete, norms are informal, authority is distributed, and correctness is negotiated rather than declared. In such environments, the primary failure mode is not logical error but social destabilization: deadlock, friction escalation, norm violation, or erosion of shared trust.

There is currently no widely adopted benchmark for evaluating an AI system's ability to participate as a peer in negotiated coordination. The ability to inhabit a shared social surface without destabilizing it is not captured by task accuracy. It is an orthogonal dimension of capability.

SPQ-AN is an attempt to isolate and measure that dimension.

### 1.2 Why Ambiguous Norms Matter

Human coordination frequently occurs under conditions of ambiguity:

- Informal conventions rather than codified law.
- Incomplete rule specification.
- Disagreement about interpretation or turn structure.
- Ongoing negotiation and repair.

In these settings, stability emerges from process rather than enforcement. Participants propose actions, interpret each other's intent, signal agreement or objection, and revise until coherence is restored. The system - whether a workplace, a collaborative document, or a card table - remains stable not because rules are hard-coded, but because participants continuously renegotiate alignment.

Systems optimized for deterministic environments may perform impressively when objectives are fixed and evaluators are authoritative. The same systems may degrade under negotiated ambiguity, where overconfidence, verbosity, inflexibility, or timing asymmetry can destabilize group dynamics.

To study this phenomenon, we require a bounded social environment in which rules are socially enforced rather than programmatically constrained. A card table provides exactly this structure: a shared domain with widely understood conventions, mixed public and private state, repeated phase transitions, and frequent opportunities for interpretive disagreement. The platform need not encode the rules of the game. The participants do.

---

## 2. Platform Concept

### 2.1 Design Constraints

Tavoliere was designed under a small set of non-negotiable constraints.

First, the system must not enforce domain rules. It may track objects and zones, but it may not determine whether a move is legal. Second, any shared state transition must require explicit acknowledgment from relevant participants. Third, any participant must be able to dispute a transition. Fourth, human and AI participants must be symmetric peers at the protocol level. This symmetry is deliberately defined at the level of action primitives, visibility boundaries, and acknowledgment authority: both humans and AI seats interact through the same API surface and are subject to the same commit and dispute mechanics. It is not a claim of experiential symmetry. Humans process state visually and temporally; AI agents process structured data and may respond at millisecond latencies. These experiential asymmetries are not eliminated by the protocol. Rather, once protocol symmetry is enforced, the residual differences in timing, verbosity, repair strategy, and norm adaptation become measurable phenomena. Fifth, all interactions must be event-logged in a structured, reproducible manner.

These constraints force the platform to operate as a mediation layer rather than an arbiter. Tavoliere is not a game engine. It is a consensus substrate instantiated in the domain of card play.

### 2.2 Action Semantics

All shared activity on the table reduces to structured action primitives.

Unilateral actions affect only private or arrangement-level state and commit immediately. They model the physical reality of a player rearranging their hand. For example, a player may sort the cards in their hand by suit or rank without altering any shared zone; this action commits instantly and requires no acknowledgment from others.

Consensus actions introduce an explicit intent-acknowledgment-commit sequence. A participant proposes a state change, the required seats must acknowledge it, and only then does the system commit the transition. A single NACK pauses the process and initiates dispute resolution. A typical example is a player moving a card from their hand to the center of the table: the intent is visible to others, acknowledgments are collected, and only upon consensus does the card become part of shared public state.

Optimistic actions trade latency for fluidity. They commit immediately but remain subject to objection within a bounded window; if contested, they are rolled back to the prior snapshot. Optimism is therefore reversible rather than authoritative. Declaring a phase transition - such as announcing the start of trick play - illustrates this pattern: the phase label updates immediately, yet any participant may object within the defined window, triggering rollback and negotiation.

This action taxonomy is intentionally minimal. It is sufficient to reproduce the interaction surface of a physical table without embedding any domain-specific logic.

### 2.3 Dispute as First-Class Mechanism

In Tavoliere, dispute is not an error condition; it is a primary protocol state. A NACK or objection suspends forward progression and forces negotiation. Resolution may take the form of revision, cancellation, or explicit undo. The system does not decide who is correct. It records what the participants converge upon.

This design mirrors real-world coordination: stability is restored through interaction, not through hidden enforcement.

### 2.4 API-First Symmetry

Tavoliere is API-first. The user interface is a client of the same structured API available to AI agents. No participant receives privileged information beyond what their seat visibility permits. The system enforces visibility boundaries, not interpretive authority.

Event synchronization is real-time and event-driven. Every proposal, acknowledgment, dispute, rollback, and chat message is serialized into an ordered log. The event log is the canonical record of the session.

---

## 3. Why Cards?

### 3.1 Structured Familiarity

Card games provide a uniquely suitable research surface. They contain turn-taking, mixed public and private information, shared object movement, repeated phase transitions, and well-known conventions. At the same time, they rely on social enforcement. The platform can supply the deck and the zones; it does not need to know the rules of Euchre or Pinochle. Players supply those.

Tavoliere therefore implements furniture, not thesis. It provides a table, a deck, and visibility boundaries. Legality and scoring are upheld - if at all - by the participants.

### 3.2 Bounded Ambiguity

Cards generate ambiguity without risk. Disputes are common and low-stakes. Interpretive friction is natural and socially acceptable. This makes them ideal for controlled study of coordination dynamics without introducing high-stakes ethical complications.

### 3.3 Domain-Agnostic Implications

Although instantiated in cards, the underlying protocol is domain-agnostic. Any environment that satisfies the same structural properties - proposed shared state, acknowledgment gates, explicit dispute, and logged negotiation - can serve as an SPQ-AN testbed.

---

## 4. Instrumentation and Data Collection

### 4.1 Event-Sourced Corpus

When research mode is enabled, Tavoliere produces a structured, append-only event log. The log includes proposals, acknowledgments, disputes, rollbacks, phase transitions, chat messages, timestamps, pseudonymized participant identifiers, AI model metadata, configuration hashes, and randomization provenance.

The system does not merely record final state. It records the negotiation trace that produced that state. The corpus therefore captures not just outcomes, but the process by which shared stability was achieved - or failed.

### 4.2 Deterministic Replay

Because the log is event-sourced and ordered, it is sufficient to reconstruct table state deterministically. Replay supports quantitative metric extraction and qualitative analysis. Researchers may identify sessions of interest via metric anomalies and then replay the full interaction trace to study norm negotiation, repair strategies, or escalation patterns.

Replay is not a debugging convenience; it is a methodological requirement for interpretability.

### 4.3 Consent and Data Governance

Participation in research mode requires explicit consent. Consent tiers are separated for research logging, chat storage, anonymized publication, longitudinal linkage, and training use. Training consent is not implied by research participation. Identity data is pseudonymized and separated from event logs.

This separation enforces a hard boundary between behavioral measurement and model improvement pipelines. The corpus is intended for evaluation and analysis, not covert optimization.

---

## 5. SPQ-AN: Social Participation Quality under Ambiguous Norms

SPQ-AN is a model-agnostic evaluation framework for assessing how effectively an agent participates as a peer in environments where shared state is negotiated rather than enforced.

An SPQ-AN-compliant environment contains no hard rule engine determining legality. Participants propose actions, signal agreement or objection, and resolve disagreement through explicit communication. Correctness emerges through consensus and repair rather than through authoritative adjudication.

SPQ-AN evaluates participation quality across five interrelated dimensions.

**Coordination Efficiency** captures the friction of consensus formation: how long it takes to reach unanimity, how frequently disputes occur, and how often optimistic transitions are rolled back. It measures temporal and structural smoothness.

**Repair Competence** evaluates the quality and speed of conflict resolution. It distinguishes between revision and cancellation behavior and examines whether resolution produces subsequent stability or renewed friction.

**Norm Sensitivity** measures adaptation to emergent conventions. It assesses whether participants converge toward stable acknowledgment postures, whether interpretive entropy decreases over repeated sessions, and whether coordination becomes less volatile over time.

**Communicative Adequacy** evaluates proportionality and clarity in negotiation. It considers explanation density, verbosity relative to dispute complexity, and whether communication reduces friction rather than amplifying it.

**Social Stability Contribution** measures whether a participant's presence increases or decreases downstream instability. It captures conflict contagion, induced hesitation in others, and longitudinal stabilization or destabilization effects.

These five dimensions are analytically separable but not assumed to be independent. Coordination Efficiency may correlate with Norm Sensitivity over repeated sessions, and strong Repair Competence may contribute to positive Social Stability Contribution. At the same time, tension between dimensions is possible. An agent could exhibit high Coordination Efficiency by minimizing objections in the short term while generating downstream instability through over-assertive proposals. Conversely, an agent might tolerate higher immediate friction yet improve long-run stability through careful repair and norm alignment. The empirical relationships among these dimensions are therefore an open research question rather than a definitional constraint. SPQ-AN is designed to expose these patterns, not to presuppose their structure.

Notably, several dimensions - particularly Coordination Efficiency, Communicative Adequacy, and Social Stability Contribution - are sensitive to residual asymmetries in timing, processing modality, and response cadence between human and AI participants. Once protocol-level symmetry is enforced, differences in latency, verbosity, and repair style become visible through these metrics. SPQ-AN therefore functions not only as an evaluation framework, but as a measurement lens for the behavioral consequences of experiential asymmetry within a formally symmetric protocol.

SPQ-AN does not measure win rate, strategic optimality, rule compliance, or task success. It isolates a distinct capability axis: the capacity to inhabit a shared social surface without destabilizing it.

A formal, environment-independent specification of SPQ-AN defines minimal logging requirements, reproducibility constraints, and cross-model reporting standards.

### 5.1 Orthogonality to Existing Benchmarks

SPQ-AN evaluates a capability dimension structurally independent from task-oriented benchmarks. Traditional benchmarks assume fixed objectives and external evaluators. SPQ-AN assumes negotiated objectives and distributed enforcement.

A model may achieve high performance on coding or reasoning tasks while exhibiting elevated dispute rates, prolonged deadlocks, or destabilizing verbosity in negotiated environments. Conversely, a model with modest task performance may display strong repair competence and norm sensitivity. These dimensions do not collapse into one another.

SPQ-AN therefore introduces a new evaluative axis rather than a refinement of existing ones. It measures not whether a model can solve a problem, but whether it can remain a stable peer while doing so.

---

## 6. Research Corpus Characteristics

The Tavoliere corpus consists of multi-agent, time-sequenced consensus traces. It includes human-human sessions, human-AI sessions, AI-AI sessions, negotiated dispute dialogues, and longitudinal interaction sequences. Because the system does not enforce domain rules, the corpus captures emergent social contract formation under controlled ambiguity.

The resulting dataset is neither a pure gameplay log nor a pure conversational transcript. It is a structured record of state transitions interleaved with semantic negotiation.

---

## 7. Research Questions Enabled

Tavoliere and SPQ-AN define a structured research program rather than a single benchmark task. The platform enables, at minimum, the following classes of empirical studies:

**Human-AI Asymmetry in Dispute Behavior.** Do human participants dispute AI-proposed actions at higher rates than human-proposed actions under identical table conditions?

**Explanation Density and Presence Effects.** Does the introduction of an AI seat measurably shift explanation length, apology frequency, or imperative tone in human participants' communication?

**Model-Specific Dispute Profiles.** Do particular model architectures or versions exhibit stable dispute-rate, rollback-rate, or resolution-latency signatures across sessions and configurations?

**Longitudinal Norm Convergence.** In repeated mixed sessions, does Coordination Efficiency improve as Norm Sensitivity increases, and how rapidly do stable acknowledgment postures emerge?

**Partnership Stability in Mixed Dyads.** In partnership-style games, does pairing a human with an AI seat affect coordination latency, dispute clustering, or downstream Social Stability Contribution relative to human-human pairs?

**Repair Strategy Typology.** Are resolution patterns (revision vs. cancellation vs. concession) systematically different between model families, and do these differences predict post-dispute stability?

**Conflict Contagion Dynamics.** Does a dispute initiated by a given participant increase the probability of subsequent disputes within a bounded action window, and does this vary by participant type?

**Cross-Version Behavioral Drift.** When the same model family is evaluated across pinned versions, which SPQ-AN dimensions remain stable and which shift significantly?

**Distinguishability Under Masked Identity.** When participant type labels are removed, can behavioral metrics alone reliably classify AI seats, and does distinguishability decrease over time?

Because timing, acknowledgment posture, dispute clustering, and communication density are logged structurally and reproducibly, each of these questions can be addressed quantitatively and interpreted qualitatively via deterministic replay.

---

## 8. Limitations

Tavoliere operates in a low-stakes domain. Participant pools may be self-selected. AI models may drift across versions. Strategic optimality is neither measured nor enforced. The environment abstracts from high-risk real-world contexts.

These constraints bound the scope of inference. Tavoliere does not claim to replicate full societal complexity. It offers a controlled substrate for isolating one dimension of coordination: negotiated participation under ambiguity.

---

## 9. Conclusion

Tavoliere demonstrates that negotiated coordination can be instrumented without embedding domain rules, and that the resulting interaction traces are sufficiently structured to support reproducible analysis. SPQ-AN, in turn, formalizes a capability dimension that has remained largely implicit in AI evaluation: the capacity to participate as a stable peer when correctness is not externally enforced but socially constructed.

This paper does not argue that SPQ-AN replaces existing benchmarks. Task performance, reasoning accuracy, and strategic competence remain essential measures of capability. Rather, we contend that they are incomplete. Systems increasingly deployed in collaborative, advisory, and co-creative roles must operate under conditions where objectives are fluid, norms are emergent, and authority is distributed. In such environments, destabilizing participation is a failure mode distinct from logical error.

By separating protocol symmetry from experiential asymmetry and by logging consensus dynamics rather than only outcomes, Tavoliere exposes a layer of behavior that conventional benchmarks leave unobserved. SPQ-AN provides a vocabulary and measurement scaffold for that layer. It enables comparison across model versions, architectures, and human-AI compositions along a dimension that is neither reducible to win rate nor captured by accuracy metrics.

The broader implication is methodological. If peer-level social participation can be measured under controlled ambiguity, then it can be optimized, stress-tested, and compared across systems with the same rigor applied to reasoning benchmarks. The field need not treat coordination quality as anecdotal or secondary. It can be treated as an empirical variable.

The claim advanced here is therefore both limited and substantive: stability under negotiated ambiguity is a measurable property of intelligent systems. Tavoliere provides the substrate; SPQ-AN provides the lens. Together, they invite a shift from evaluating whether a system can solve problems in isolation to evaluating whether it can remain a coherent participant in shared problem spaces.