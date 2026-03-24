# Phase 49: Environment Drift Detection & Governance Pack Validation

## What Was Added

- **Effective-state helpers** on each environment — `get_effective_policies`, `get_effective_profiles`, `get_effective_templates`, and `get_effective_feature_flags` return the merged view (allowlists + defaults + packs) without mutating anything.
- **Drift detection** (`runtime/tier3_env_drift.py`) — compares any two environments across policies, profiles, templates, and feature flags, reporting items only in one side, shared items, and value differences. All comparisons are side-effect-free and logged for dashboard visibility.
- **Governance pack validation** (`validate_envpack_against_environment`) — checks a pack's policies, profiles, scheduling overrides, and feature-flag keys against an environment's allowlists and known flag vocabulary, returning structured issue lists without modifying state.
- **Environment health scoring** (`runtime/tier3_env_health.py`) — computes a structured report per environment covering missing defaults, unused allowlist entries, orphaned scheduling overrides, pack validation issues, and upstream drift. Grades range from "healthy" to "needs_attention."
- **Cockpit commands** — `t3_env_drift`, `t3_envpack_validate`, `t3_env_health`, and `t3_env_health_all` give operators full observability.
- **Dashboard section** — "Tier-3 Environment Health & Drift" surfaces recent health evaluations and drift comparisons.

## Why It Is Safe

- Every new function is strictly read-only: no state mutation, no auto-promotion, no auto-correction, no auto-activation of profiles or policies.
- Drift reports and health scores are observational artifacts — they inform the operator but never trigger action.
- Pack validation only reads existing registries and checks structural compatibility; it never modifies packs or environments.

## How It Prepares for Phase 50

- With per-environment health scores and cross-environment drift reports available, the system is ready for **promotion-readiness scoring** (gating promotion runbooks on health thresholds), **environment-aware guardrails** (blocking risky promotions when drift is excessive), or **multi-environment governance dashboards** (aggregating health across the full environment topology).
