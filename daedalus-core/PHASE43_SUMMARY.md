# Phase 43: Tier-3 Governance Profiles

## What Was Added

- **Governance profile registry** — named, selectable bundles of policy scope, scheduling overrides, and feature flags (e.g., conservative, normal, aggressive).
- **Single-active-profile semantics** — only one profile may be active at a time; switching is fully logged with previous-profile tracking.
- **Profile-scoped policy evaluation** — when a profile is active, only its attached policies are considered during both `evaluate_policies` and `evaluate_policies_scheduled`.
- **Scheduling overrides** — profiles can overlay per-policy interval, window, and rate-limit constraints without mutating the base policy objects.
- **Feature flags** — `allow_plans`, `allow_migrations`, and `allow_policy_generated_proposals` gates that restrict artifact creation and execution at evaluation and dispatch time.
- **Cockpit commands** — `t3_profile_create`, `t3_profiles`, `t3_profile`, `t3_profile_activate`, `t3_profile_deactivate`, `t3_profile_status`.
- **Dashboard section** — "Tier-3 Governance Profiles" showing the active profile, flags, scheduling overrides, and recent activation history.

## Why It Is Safe

- Profiles only constrain or further gate behavior; they never weaken existing safety checks.
- No automatic profile switching, policy enabling, or artifact execution.
- When no profile is active, all behavior remains exactly as in Phase 42.
- Scheduling overrides are read at evaluation time and never persisted into the base policy objects.
- Feature flags block creation and execution but never grant additional permissions.
- All activation and deactivation events are logged with full audit trail.

## How It Prepares for Phase 44

- Environment-specific profile presets (production-conservative, staging-aggressive) can be introduced as built-in profiles.
- Operator-defined "runbooks" can reference profiles alongside sequenced plan execution.
- Scenario-based profile switching (e.g., incident mode) becomes possible with explicit operator triggers.
