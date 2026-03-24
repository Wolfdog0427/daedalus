# Phase 48: Environment-Scoped Governance Packs & Defaults

## What Was Added

- **Environment default fields** — each environment now carries `default_policy_ids`, `default_scheduling_overrides`, and `default_feature_flags` that act as read-only overlays at evaluation time.
- **Governance packs** — a new `runtime/tier3_envpacks.py` module defines reusable bundles of policies, scheduling overrides, and feature-flag overrides that can be merged into any environment's defaults on operator command.
- **Feature-flag precedence** — flags are now resolved in a clear hierarchy: active profile (highest) > active environment > system default, ensuring environments can tighten defaults while profiles retain final authority.
- **Policy evaluation integration** — both `evaluate_policies` and `evaluate_policies_scheduled` include environment `default_policy_ids` in their evaluation scope and merge environment scheduling overrides beneath profile overrides.
- **Cockpit commands** — `t3_envpack_create`, `t3_envpacks`, `t3_envpack`, `t3_envpack_apply`, and `t3_env_defaults` provide full operator control.
- **Dashboard section** — "Tier-3 Environment Governance Packs" surfaces available packs, applied mappings, merged defaults, and recent application history.

## Why It Is Safe

- All defaults are applied as read-only overlays at evaluation time; no underlying policy, profile, or template definition is ever mutated.
- No pack application, environment switch, profile activation, policy enable, or runbook execution happens automatically.
- Feature-flag overlays can only tighten governance (environment sets a baseline, profile can override), never weaken existing checks.
- The pack registry is purely additive and fully operator-controlled.

## How It Prepares for Phase 49

- With environments carrying rich, composable defaults, the system is ready for **multi-environment drift detection** (comparing default sets across dev/staging/prod), **environment health scoring** (assessing whether an environment's governance coverage is complete), or **promotion policies** that gate cross-environment propagation based on pack compliance.
