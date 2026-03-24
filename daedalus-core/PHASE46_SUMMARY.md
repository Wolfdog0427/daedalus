# Phase 46: Environment-Aware Governance Packs

## What Was Added

- **Environment registry** — named, environment-scoped bundles (e.g. dev, staging, prod) that define which profiles, policies, and runbook templates are usable within that scope.
- **Single-active-environment semantics** — only one environment may be active at a time; switching is fully logged with previous-environment tracking.
- **Profile activation gating** — when an environment is active, profile activation is rejected if the profile is not in the environment's allowlist.
- **Policy evaluation gating** — both `evaluate_policies` and `evaluate_policies_scheduled` skip policies not in the environment's allowlist.
- **Template instantiation gating** — `instantiate_template` rejects templates not in the environment's allowlist.
- **Default profile suggestion** — environments may specify a `default_profile_id` that is surfaced to the operator on activation but never auto-activated.
- **Cockpit commands** — `t3_env_create`, `t3_envs`, `t3_env`, `t3_env_activate`, `t3_env_deactivate`, `t3_env_status`.
- **Dashboard section** — "Tier-3 Environments" showing the active environment, constraint counts, default profile, and recent activation history.

## Why It Is Safe

- Environments only further restrict what is usable; they never weaken existing governance checks.
- No automatic environment switching, profile activation, policy enabling, or runbook execution.
- When no environment is active, all behavior remains exactly as in Phase 45.
- Environment constraints are read-only overlays — they never modify the underlying definitions of profiles, policies, or templates.
- All activation and deactivation events are logged with full audit trail.

## How It Prepares for Phase 47

- Environment-specific defaults can be introduced to pre-populate settings, thresholds, or scheduling windows per environment.
- Cross-environment comparisons can diff governance configurations between dev/staging/prod.
- Promotion workflows can transfer approved proposals, plans, or policy configurations from one environment to another with explicit operator approval.
