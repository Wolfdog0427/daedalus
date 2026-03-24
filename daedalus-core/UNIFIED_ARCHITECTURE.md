# Daedalus Unified Architecture

## 1. Overview

Daedalus is a governed, expressive, operator-centric runtime. It consists of two major halves — a **Runtime Identity Stack** that shapes how Daedalus presents, communicates, and behaves, and a **Governance Stack** that constrains what changes are permitted and ensures safety, sovereignty, and reversibility. A **Binding Contract** defines the explicit boundary between them.

The operator is sovereign. Every structural change requires operator awareness or approval. Per-turn expression shaping remains runtime-local and fluid. Safety invariants are unconditional and cannot be overridden by any persona, mode, or command.

## 2. Runtime Identity Stack

The runtime identity stack governs Daedalus's moment-to-moment presence, expression, and behavioral coherence. All state is session-local and non-persistent.

### Posture & Autonomy

- **Posture Engine** — manages 11 canonical postures (COMPANION, ARCHITECT, ORACLE, SCRIBE, SENTINEL_QUIET, CEREMONIAL, VEIL, SHROUD, TALON, NULL, DORMANT). Posture defines identity, constraints, and defensive flags. All transitions are explicit and operator-triggered.
- **Autonomy Tiers** — 5 tiers (TIER_0 read-only, TIER_1 basic actions, TIER_2 analytical, TIER_3 integrative, TIER_DEFENSIVE). Each defines allowed/disallowed action categories.
- **Autonomy Engine** — evaluates action permission at the intersection of tier and posture. Postures may force lower tiers (SHROUD/NULL/DORMANT force TIER_0, TALON forces TIER_DEFENSIVE). The most restrictive rule always wins.

### Operator Context & Interaction

- **Operator Context** — tracks interaction-level signals: intent, focus, engagement style. No emotional inference, no persistence.
- **Interaction Model** — unifies posture, expression, tier, and operator context into flow shaping. Per-posture behavior rules govern transitions, verbosity, and continuity.
- **Interaction Cycle** — manages turn-level transitions and closure markers.

### Expression Engine

Applies an 8-step shaping pipeline to every outgoing response:

1. Comfort layer (COMPANION only)
2. Micro-modulation
3. Resonance shaping
4. Identity continuity
5. Long-arc stability smoothing
6. Self-alignment corrections
7. Continuity cues
8. Operator attunement (COMPANION only)

No step alters factual content, safety behaviour, or autonomy rules.

### Continuity, Coherence, Stability, Resonance

- **Session Continuity** — tracks which posture, tier, intent, and focus were last active. Computes continuity strength.
- **Identity Continuity Engine** — determines how much expressive character carries between turns, modulated by posture, resonance decay, and operator focus.
- **Identity Coherence** — detects mismatches between layers (e.g., VEIL + high continuity) and proposes expression-level corrections.
- **Self-Alignment Engine** — applies coherence corrections, smoothed by long-arc stability.
- **Stability Regulator** — tracks oscillation, jitter, and composite stability across bounded windows.
- **Long-Arc Engine** — dampens abrupt shifts when stability is low.
- **Resonance Engine** — applies per-posture expressive signatures with intensity, colour, decay, and posture-transition blending.

### Runtime Pipeline

The canonical pipeline order in `_apply_expression_shaping`:

```
1. Context gathering      (posture, tier, operator context)
2. Governance audit       (filtered through binding contract)
3. Session continuity     (update_continuity)
4. Identity coherence     (compute_coherence_state)
5. Stability regulator    (update_stability)
6. Expression shaping     (posture_expression -> expression_engine pipeline)
7. Interaction cycle      (shape_interaction)
8. Interaction model      (shape_interaction_flow)
9. Telemetry capture      (coherence, stability, resonance, governance health)
```

State updates (steps 3-5) run before shaping (steps 6-8), ensuring expression always uses current-cycle data.

## 3. Governance Stack

The governance stack constrains all structural changes to Daedalus's runtime identity. It never auto-executes — all proposals require operator review.

### Personas & Modes

- **Personas** — 5 governance personas (Architect, Sentinel, Oracle, Scribe, Companion) defining decision style, risk posture, allowed/forbidden operations, and escalation rules.
- **Modes** — 5 governance modes (Strict, Advisory, Reflective, Dormant, Defensive) defining autonomy constraints, drift sensitivity, safety multipliers, and approval thresholds.
- **Envelopes** — computed from the intersection of active persona and mode. Define effective risk ceilings, allowed operations, and reversibility requirements.

### Governance Kernel

The single authority for all governance decisions. Every structural change passes through its evaluation pipeline:

1. Kill switch / stabilise mode / circuit breaker checks
2. Safety invariant enforcement (8 unconditional invariants)
3. Change contract evaluation (type-level allow/forbid/risk/approval rules)
4. Persona/mode envelope checks (risk ceilings, forbidden operations)

Also provides: kill switch (blocks all changes), stabilise mode (allows only meta-changes), circuit breakers (auto-trip on critical health degradation), and health scoring.

### Safety Invariants

Eight unconditional constitutional invariants:

- No autonomy expansion
- No safety bypass
- No personal data persistence
- No emotional inference
- No psychological modeling
- No self-modification without operator approval
- Operator sovereignty (commands override suggestions, except Tier-1 safety)
- Default reversibility

### Proposal & Patch System

- **Proposal Engine** — generates, scores, and classifies proposals. Never auto-executes.
- **Patch Lifecycle** — draft, pending_approval, approved, applied, rolled_back. All patches validated through the kernel before application.
- **Drift Detector** — monitors 5 dimensions (posture, expression, continuity, coherence, stability).
- **Audit Log** — append-only, session-local, operator-readable event stream.

## 4. Runtime <-> Governance Binding Contract

The binding contract (`governance/runtime_binding.py`) defines the explicit boundary between the two stacks.

### What governance can read

Governance reads runtime signals only — never raw operator content or personal data. The readable signals are: posture ID, tier ID, continuity strength/active, coherence score/mismatches, stability score/oscillation/jitter, resonance intensity/colour/blend, interaction intent, operator focus level, and engagement style.

### What changes require governance review

Structural changes that alter the system's configuration or identity rules pass through `kernel.evaluate_change()`:

- Posture transitions
- Autonomy tier changes
- Governance persona changes
- Governance mode changes
- Patch application/rollback
- Self-modification

### What changes are unconditionally forbidden

- Safety invariant modification
- Tier-1 safety bypass
- Autonomy expansion
- Personal data persistence

### What remains purely runtime-local

Per-turn shaping never requires governance review:

- Expression shaping and micro-modulation
- Resonance shaping
- Identity continuity shaping
- Coherence evaluation and self-alignment
- Stability updates and long-arc smoothing
- Interaction cycle and flow shaping

This separation ensures fluid, low-latency expression while maintaining governance authority over structural changes.

## 5. Safety & Sovereignty

### Operator Sovereignty

The operator is the ultimate authority. Every persona defines `operator_override: always_honoured`. The kernel never overrides an operator command except to enforce Tier-1 safety. Kill switch and stabilise mode are operator-only controls.

### No Autonomy Expansion

Safety invariants unconditionally block any change flagged with autonomy expansion. The autonomy tier set (TIER_0 through TIER_3 plus TIER_DEFENSIVE) is canonical and immutable. Governance assertions verify no extra tiers exist.

### No Persistence, No Inference

All state is session-local and in-memory. No personal data persists across sessions. No module infers or models emotional state or psychology. These invariants are enforced by the kernel on every structural change and verified by diagnostic assertions.

### Reversibility

All changes default to reversible. Irreversible changes require explicit operator approval via the kernel's invariant check. Patches support rollback. Posture and tier transitions are inherently reversible.

### Kill Switch & Circuit Breakers

The kill switch immediately blocks all structural changes across the system. Circuit breakers auto-trip when governance health drops critically. Stabilise mode allows only governance meta-changes (persona/mode adjustments) while freezing all other structural changes.

## 6. Operator Mental Model

Think of Daedalus as having three layers:

- **Runtime** is the being you interact with — its posture, expression, continuity, coherence, and resonance create a fluid, cohesive identity that adapts to your needs.

- **Governance** is the constitution that constrains it — personas, modes, envelopes, invariants, and contracts ensure the system cannot self-modify, expand its autonomy, or bypass safety without your explicit approval.

- **Binding** is the treaty between them — it defines exactly where governance authority begins and ends. Per-turn expression is free and fluid. Structural changes are governed and auditable. Forbidden operations are unconditionally blocked.

The cockpit gives you direct control over both layers. The dashboard gives you visibility into both layers. The audit log gives you a chronological record of every governance decision. At any point, you can activate the kill switch to freeze all changes, or reset the kernel to restore defaults.

The system is designed so that you never have to trust it — you can verify it. Every invariant, every assertion, every binding rule is inspectable, testable, and operator-readable.

---

## 7. Introspection Layer

The introspection layer provides a unified, operator-safe surface for Daedalus to describe its current identity state. It is a **presentation layer only** — it introduces no new behavior, no new autonomy, and no new shaping.

### Purpose

Allow the operator to query — at any time — a coherent summary of the full identity stack: posture, autonomy tier, operator context, continuity, coherence, stability, resonance, and governance persona/mode/envelope/kernel health.

### Surfaces

| Surface | Entry point |
|---------|-------------|
| Module | `runtime/self_description.py` — `describe_current_state()`, `describe_posture()`, `describe_autonomy()`, `describe_governance()`, `describe_expression_stack()` |
| Cockpit | `identity_introspect`, `identity_layers`, `identity_posture`, `identity_autonomy`, `identity_governance`, `identity_expression` |
| Dashboard | "Identity Introspection" section in the system dashboard |

### Guarantees

- **Read-only.** No function in the introspection layer modifies posture, tier, expression, continuity, coherence, stability, resonance, or governance state.
- **No autonomy expansion.** Introspection never triggers `kernel.evaluate_change()` or any structural change.
- **No safety bypass.** Safety invariants are never touched.
- **No personal data.** No raw content, no model internals, no operator-identifying data is ever included.
- **Posture-safe.** Under suppressed postures (SHROUD, VEIL, NULL, DORMANT), introspection returns a valid, minimal state with continuity/coherence/resonance marked as suppressed.

### Relationship to Runtime

The introspection layer **consumes** runtime signals — it reads posture state, autonomy tier, operator context, continuity state, coherence state, stability metrics, and resonance summaries. It **does not influence** shaping, transitions, or any runtime pipeline step.

### Relationship to Governance

Governance signals are accessed through `governance/runtime_binding.get_governance_view()`, ensuring only governance-safe data is surfaced. Introspection **never triggers governance review**, never modifies persona/mode/envelope, and never touches the audit log.
