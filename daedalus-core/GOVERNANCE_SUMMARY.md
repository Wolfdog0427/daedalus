# Daedalus Governance Architecture

## Overview

The governance layer is a safety-bounded, operator-sovereign control plane that governs all changes to Daedalus's runtime identity and behaviour. It sits above the runtime identity stack and ensures that no posture change, tier change, expression modification, or structural patch occurs without passing through constitutional checks, change contracts, risk scoring, and operator approval gates.

## Personas & Modes

**Governance personas** define *how* governance decisions are made:

- **Architect** — structural, system-integrity focus, moderate risk tolerance
- **Sentinel** — defensive, safety-first, lowest risk tolerance, strictest approval
- **Oracle** — integrative analysis, drift forecasting, no direct patching
- **Scribe** — documentation-focused, audit trail emphasis, read-heavy
- **Companion** — operator-centric advisory, supportive framing, balanced risk

**Governance modes** define *how much* governance enforcement is applied:

- **Strict** — all changes require explicit approval, highest safety multiplier
- **Advisory** — proposals generated and scored, operator approves non-trivial changes
- **Reflective** — analysis and insight generation, minimal active intervention
- **Dormant** — governance suspended, only safety invariants enforced
- **Defensive** — only defensive/stabilising changes permitted

**Envelopes** are computed from the intersection of the active persona and mode. They define the effective allowed operations, risk ceilings, escalation behaviour, and reversibility requirements. Envelopes are never persisted — they are recomputed on demand.

## Governance Kernel

The kernel is the central authority. Every change request passes through its evaluation pipeline:

1. **Kill switch / stabilise / circuit breaker** — hard blocks when active
2. **Safety invariants** — eight unconditional rules (no autonomy expansion, no safety bypass, no persistence of personal data, no emotional inference, no psychological modeling, no self-modification without approval, operator sovereignty, default reversibility)
3. **Change contracts** — type-level allow/forbid/reversibility/approval rules
4. **Persona/mode envelope** — risk ceiling, forbidden operations, escalation

The kernel also provides:
- **Kill switch** — blocks all changes immediately
- **Stabilise mode** — allows only governance meta-changes
- **Circuit breakers** — auto-trip when governance health degrades critically
- **Health scoring** — 0-100 composite of drift, invariant status, and circuit state

## Proposal & Patch System

**Proposals** are scored, classified, and queued for operator review. The proposal engine generates proposals from drift detection, diagnostics, stability signals, coherence signals, or operator requests. Every proposal receives a risk score (0-100), a risk classification (low/medium/high/critical), and an approval requirement.

**Patches** follow a strict lifecycle: draft → pending_approval → approved → applied → (optionally) rolled_back. Before application, every patch is validated against the kernel. Rollback is always available for reversible patches.

All lifecycle transitions are recorded in the **audit log** — an append-only, session-local, operator-readable event stream.

## Drift Detection

The drift detector continuously evaluates five dimensions:
- **Posture drift** — oscillation in posture switching
- **Expression drift** — resonance blend instability
- **Continuity drift** — session continuity strength degradation
- **Coherence drift** — identity coherence score decline
- **Stability drift** — jitter and stability score degradation

Drift sensitivity is modulated by the active governance mode. Alerts trigger when weighted drift exceeds thresholds.

## Governance–Runtime Integration

The governance layer hooks into the runtime identity stack at four points:

- **Posture engine** — every `request_posture()` call passes through `kernel.evaluate_change()` before executing
- **Autonomy engine** — every `request_tier()` call passes through the kernel
- **Expression engine** — every `shape_response()` call checks the kernel before applying expression profiles
- **Runtime loop** — every cycle logs a governance audit event and captures governance context

When the kernel blocks a change (kill switch, stabilise mode, circuit breaker, invariant violation, contract violation, or envelope breach), the runtime falls back to its previous state. All governance hooks degrade gracefully — if the governance layer is unavailable, runtime behaviour continues unchanged.

## Why This Design Is Safe

- **Operator sovereignty is absolute.** Every persona defines `operator_override: always_honoured`. The kernel never overrides an operator command except to enforce Tier-1 safety.
- **No automatic self-modification.** Proposals are generated but never auto-executed. Patches require validation and approval.
- **No autonomy expansion.** Safety invariants unconditionally block any change flagged with autonomy expansion.
- **No persistence.** All governance state is session-local and in-memory.
- **No emotional inference or psychological modeling.** These are unconditionally blocked by safety invariants.
- **All changes default to reversible.** Irreversible changes require explicit operator approval.
- **Graceful degradation.** Every governance import is wrapped in fault tolerance. The runtime never crashes if governance modules are unavailable.
