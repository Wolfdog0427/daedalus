# Daedalus Runtime Identity Architecture

## Overview

Daedalus's runtime identity is a layered, safety-bounded stack that governs how the system presents itself, what it is allowed to do, and how it shapes responses for the operator. Every layer is session-local, non-persistent, and strictly operator-centric. No layer stores personal data, infers emotion, models psychology, or expands autonomy beyond the global safety envelope.

The stack is organised into three tiers of responsibility:

```
┌─────────────────────────────────────────────────┐
│              Operator Interface                  │
│   Cockpit commands · System dashboard            │
├─────────────────────────────────────────────────┤
│            Shaping & Presentation                │
│   Expression engine · Interaction model          │
│   Interaction cycle · Resonance engine           │
├─────────────────────────────────────────────────┤
│            Identity Regulation                   │
│   Session continuity · Identity continuity       │
│   Identity coherence · Self-alignment            │
│   Stability regulator · Long-arc engine          │
├─────────────────────────────────────────────────┤
│            Posture & Autonomy                    │
│   Posture engine · Posture registry/state        │
│   Autonomy tiers · Autonomy engine/state         │
│   Posture-bounded autonomy                       │
├─────────────────────────────────────────────────┤
│            Tier-1 Safety (immutable)             │
└─────────────────────────────────────────────────┘
```

## Layer Descriptions

### Posture & Autonomy

The **posture engine** manages 11 canonical postures (COMPANION, ARCHITECT, ORACLE, SCRIBE, SENTINEL_QUIET, CEREMONIAL, VEIL, SHROUD, TALON, NULL, DORMANT), each carrying distinct constraints on expression and action. The **autonomy engine** manages 5 tiers (TIER_0 through TIER_3, plus TIER_DEFENSIVE), defining which categories of action are permitted. Postures may force lower tiers — SHROUD, NULL, and DORMANT force TIER_0 (read-only); TALON forces TIER_DEFENSIVE. The most restrictive rule always wins: if either the posture or the tier disallows an action, it is blocked.

All posture and tier transitions are explicit, logged, and operator-triggered. No automatic escalation occurs.

### Operator Context & Interaction Model

The **operator context** tracks lightweight, non-persistent interaction signals: intent (explicit, exploratory, reflective, task-driven), focus level, and engagement style. The **interaction model** unifies posture, expression, autonomy tier, and operator context to shape response flow — adjusting verbosity, transitions, and continuity cues based on the operator's current state. The **interaction cycle** manages turn-level transitions and closure markers.

No emotional inference or psychological modeling is performed. Context is derived solely from interaction-level signals and is reset on session boundaries.

### Expression Engine

The **expression engine** applies an 8-step shaping pipeline to every outgoing response:

1. Comfort layer (COMPANION only)
2. Micro-modulation (posture-specific tone/framing adjustments)
3. Resonance shaping (expressive carry-over and signature)
4. Identity continuity (session-level continuity of presence)
5. Long-arc stability smoothing (dampen oscillation and jitter)
6. Self-alignment corrections (resolve coherence mismatches)
7. Continuity cues (link responses within a session)
8. Operator attunement (COMPANION only)

Every step degrades gracefully if its module is unavailable. No step alters factual content, safety behaviour, or autonomy rules.

### Identity Regulation

Four modules work together to keep all identity layers aligned:

- **Session continuity** tracks which posture, tier, intent, and focus were last active and computes a continuity strength (low/medium/high).
- **Identity continuity engine** determines how much the previous turn's expressive character should carry into the current turn, modulated by posture, resonance decay, and operator focus.
- **Identity coherence** detects mismatches between layers (e.g., VEIL posture with high continuity, SHROUD with comfort layer active) and proposes expression-level corrections — never posture or tier changes.
- **Self-alignment engine** applies those corrections, smoothed by the long-arc engine to prevent over-correction.

### Stability & Long-Arc

The **stability regulator** tracks recent posture, tier, continuity, and coherence patterns in bounded windows. It computes three metrics: oscillation index (rapid posture/tier switching), jitter index (continuity/coherence fluctuations), and a composite stability score. The **long-arc engine** uses these metrics to dampen abrupt shifts — reducing micro-modulation intensity when stability is low, suppressing low-severity corrections during high oscillation, and dampening continuity strength during high jitter.

### Resonance

**Resonance profiles** define per-posture expressive signatures: intensity, colour (warm, structured, integrative, etc.), decay rate, and blend rules for transitions. The **resonance engine** applies these to shape responses with a consistent identity "feel" that persists across turns and blends smoothly during posture transitions. Zero-intensity postures (NULL, DORMANT, VEIL, SHROUD) are fully suppressed. Resonance is always subordinate to coherence corrections and stability smoothing.

## Runtime Loop Pipeline

When the runtime loop completes a cycle, the `_apply_expression_shaping` function executes this sequence:

```
1. Gather context       posture ID, autonomy tier, operator context
2. Update continuity    session_continuity.update_continuity()
3. Evaluate coherence   identity_coherence.compute_coherence_state()
4. Update stability     stability_regulator.update_stability()
5. Expression shaping   posture_expression → expression_engine pipeline
6. Interaction cycle    interaction_cycle.shape_interaction()
7. Interaction model    interaction_model.shape_interaction_flow()
8. Capture telemetry    coherence, stability, resonance metrics
```

State updates (steps 2–4) occur before shaping (steps 5–7), ensuring that the expression pipeline always works with current-cycle data. All steps are wrapped in fault-tolerant try/except blocks.

## Why This Design Is Safe

- **No persistence.** All state is process-local and session-scoped. Nothing survives a restart.
- **No emotional inference.** Operator context tracks interaction-level signals only — intent, focus, engagement style. No sentiment analysis, mood detection, or psychological profiling.
- **No autonomy expansion.** Every layer can only further constrain, never expand, what the system is allowed to do. Posture and tier restrictions are intersected; the most restrictive rule always wins.
- **No factual alteration.** Expression shaping adjusts tone, framing, verbosity, and continuity cues. It never modifies the factual content of a response.
- **Graceful degradation.** Every module import is wrapped in fault tolerance. If any layer fails or is unavailable, the system falls back to raw behaviour — never crashes, never blocks.
- **Operator sovereignty.** All posture changes, tier changes, and resets are explicitly operator-triggered. The system never auto-escalates, auto-switches postures, or overrides operator commands (except to enforce Tier-1 safety, which is immutable).

## Operator Mental Model

Think of Daedalus as a governed partner with a consistent presence. The **posture** defines who it is being (companion, architect, sentinel, etc.). The **autonomy tier** defines what it is allowed to do. The **expression engine** defines how it communicates. The **identity regulation layers** ensure these remain coherent and stable across turns, preventing jarring shifts or contradictions.

The operator controls posture and tier directly through the cockpit. Everything else — expression, continuity, coherence, stability, resonance — follows from those two choices, shaped by the operator's own interaction style and the system's internal consistency rules. The result is a fluid, cohesive identity that adapts to the operator's needs without ever crossing the boundaries of safety, autonomy, or factual accuracy.
