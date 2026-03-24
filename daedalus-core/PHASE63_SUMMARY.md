# Phase 63 — Autonomy Tier Integration

## What Was Added

- **Autonomy tier registry** — five canonical tiers (TIER_0 through TIER_3 plus TIER_DEFENSIVE) with declarative metadata defining allowed and disallowed action categories and safety flags.
- **Autonomy state manager** — process-local, in-memory tier tracking with full transition history.  Resets on process restart; no persistence.
- **Autonomy engine** — central evaluator that determines whether an action is permitted at the effective tier.  Integrates with posture autonomy so that both tier and posture must agree before an action proceeds.  Supports operator-driven tier changes and posture-forced overrides.
- **Posture autonomy integration** — the existing posture autonomy module now delegates to the autonomy engine when available, providing tier-aware constraints while maintaining backward compatibility.
- **Runtime loop integration** — the runtime loop's autonomy gate now consults the engine first, falling back gracefully if unavailable.
- **Cockpit commands** — `autonomy_current`, `autonomy_history`, `autonomy_set`, and `autonomy_explain` for operator inspection and control.
- **Dashboard section** — "Autonomy Tiers" displays the effective tier, posture-forced status, allowed/disallowed categories, and recent transitions.

## Why It Is Safe

- No tier may expand autonomy beyond existing global rules.  Tiers only constrain — posture restrictions layer on top, and both must agree.
- TIER_0 restricts to read and analysis only.  TIER_DEFENSIVE restricts to defensive actions within the existing defense envelope.
- Postures SHROUD, NULL, and DORMANT force TIER_0 unless the operator explicitly overrides.  TALON forces TIER_DEFENSIVE.
- There is no automatic tier escalation.  All transitions are explicit, operator-triggered, and logged.
- Operator overrides never bypass Tier-1 safety — they only choose which tier the engine applies.
- All modules degrade gracefully if unavailable, preserving pre-Phase 63 behavior.

## How It Unifies Posture, Safety, and Behavior

The autonomy tier system provides a structured, inspectable layer between high-level posture intent and low-level action gating.  Postures express *what kind of presence* Daedalus adopts; tiers express *what categories of action* are permitted.  The engine intersects both, ensuring that the most restrictive constraint always wins.  This creates a unified model where operators can independently adjust posture (expression and presence) and tier (action scope) with confidence that safety is preserved at every combination.
