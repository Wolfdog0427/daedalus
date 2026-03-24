# Phase 50: Promotion-Readiness Scoring & Environment Guardrails

## What Was Added

- **Promotion-readiness scoring** (`compute_promotion_readiness`) — produces a structured 0–100 score for any source-to-target environment pair, incorporating health grades, drift analysis, feature-flag compatibility, promotion-path existence, pack validation against the target, and promotion-plan conflicts. Results include blockers, warnings, and descriptive recommendations.
- **Environment guardrails** (`runtime/tier3_env_guardrails.py`) — a new module providing read-only pre-action safety checks for profile activation, plan execution, template instantiation, migration execution, and promotion runbook creation. Each check returns a structured result with allowed/blocked status, blocking reasons, and warnings.
- **Guardrail integration** — `activate_profile`, `execute_tier3_proposal` (for migrations), `instantiate_template`, and `create_promotion_runbook_from_plan` now run guardrail checks before proceeding. If a guardrail blocks, the action is rejected with a clear error message.
- **Unified guardrail dispatcher** (`run_guardrail_check`) — accepts an action name and parameters to manually invoke any guardrail, with `list_guardrail_categories` exposing all supported check types.
- **Cockpit commands** — `t3_env_promotion_readiness`, `t3_env_guardrails`, and `t3_env_guardrail_check` for full operator observability.
- **Dashboard section** — "Tier-3 Promotion Readiness & Guardrails" surfaces recent readiness scores, guardrail evaluations, blockers, and warnings.

## Why It Is Safe

- All readiness scoring and guardrail checks are strictly read-only — they never mutate state, never auto-promote, and never auto-correct.
- Guardrails can only further restrict operator actions, never weaken existing governance checks (environment allowlists, profile scope, feature flags all remain enforced independently).
- Guardrail blocking reasons are always surfaced explicitly; nothing is silently suppressed.
- Existing behavior is completely preserved when no environment is active or when guardrails pass.

## How It Prepares for Phase 51

- With readiness scoring and guardrails in place, the system is ready for **multi-environment orchestration** (chaining promotion runbooks across dev → staging → prod with readiness gates), **environment lineage tracking** (auditing the full history of what was promoted and when), or **governance-wide audits** (comprehensive compliance checks across all environments and their promotion chains).
