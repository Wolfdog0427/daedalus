# Phase 36: Dry-Run Engine, Structural Diff, and Approval Gate

## What was added

- A **dry-run engine** that simulates a migration step-by-step without performing any mutations. Each step is evaluated against current system state to predict whether it would succeed or fail, and the engine produces a per-step verdict with an overall pass/fail status.
- A **structural diff generator** that computes human-readable before/after diffs for each migration step. Setting changes show current and proposed values; registry changes show the action being added or removed; notes produce no diff.
- An **operator approval gate** with two new proposal statuses: `awaiting_approval` (dry-run passed, waiting for explicit operator sign-off) and `invalid` (dry-run failed, cannot be approved or executed). A dedicated `t3_approve` cockpit command transitions a proposal from `awaiting_approval` to `approved` only when the dry-run has passed.
- A **migration-aware proposal creator** (`create_migration_proposal`) that automatically runs the dry-run at proposal creation time and sets the initial status based on the result.
- A **dry-run log** that records every dry-run execution for audit and dashboard visibility.
- Four new cockpit commands: `t3_dryrun(id)` to inspect dry-run results, `t3_diff(id)` to view only the structural diffs, `t3_pending_approvals()` to list proposals awaiting sign-off, and `t3_approve(id)` to approve a validated migration.
- Two new dashboard sections: "Tier-3 Migration Approvals" showing pending proposals with their diffs, and "Tier-3 Dry-Run Results" showing recent dry-run outcomes.

## Why it is safe

- The dry-run engine reads current state but never writes to it. Settings, registries, and telemetry are unchanged after any number of dry-run invocations.
- The diff generator calls only read-only accessors (`get_setting`, `is_action_registered_tier1`, `get_registered_tier2_actions`) and returns structured data without side effects.
- The approval gate enforces a strict prerequisite chain: a migration proposal can only reach `approved` status if it was first created with a passing dry-run and then explicitly approved by the operator. Invalid proposals are permanently blocked from approval.
- The existing execution path still requires `approved` status and a passing maintenance envelope before any real mutation occurs.

## How it prepares for Phase 37

- The dry-run results and structural diffs provide the data substrate for a future migration comparison view, where operators can compare predicted changes across multiple migration candidates before selecting one.
- The approval gate establishes the governance pattern for multi-step approval workflows, where future phases could add review comments, conditional approvals, or multi-operator sign-off.
- The dry-run log enables trend analysis over migration success rates and common failure patterns.
