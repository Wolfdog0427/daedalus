# Phase 47: Cross-Environment Promotion & Comparison

## What Was Added

- **Environment relations** — each environment can declare an upstream and downstream list, forming a directed promotion graph (e.g. dev -> staging -> prod).
- **Promotion path resolution** — `get_promotion_path` walks downstream links to find a valid ordered path between any two environments, detecting cycles and missing links.
- **Cross-environment comparison** — read-only helpers that diff policies, profiles, and templates between two environments, reporting items only-in-source, only-in-target, and shared.
- **Promotion planning** — `plan_promotion` builds a structured plan describing which items would need to be added to the target environment's allowlists, with conflict detection.
- **Promotion runbook generation** — `create_promotion_runbook_from_plan` produces a concrete draft runbook capturing the promotion steps, registered but never executed.
- **Cockpit commands** — `t3_env_relations`, `t3_env_set_relations`, `t3_env_compare`, `t3_env_promotion_plan`, `t3_env_promotion_runbook`.
- **Dashboard section** — "Tier-3 Environment Promotion" showing defined relations, recent comparisons, promotion plans, and associated runbook statuses.

## Why It Is Safe

- All comparisons and promotion plans are purely read-only with no side effects.
- Promotion runbooks are created in draft status and require explicit operator execution.
- No automatic promotion, cloning, or modification of policies, profiles, or templates.
- When mutations eventually occur through runbook execution, they go through existing governed helpers.
- Environment relations are purely structural metadata with no automatic behavioral consequences.

## How It Prepares for Phase 48

- Promotion policies can be introduced to define guardrails for what can be promoted between specific environments.
- Promotion audit trails can track the full history of cross-environment changes with before/after snapshots.
- Automated promotion gates can require specific checks (e.g. all dry-runs passed, no pending approvals) before allowing a promotion runbook to execute.
