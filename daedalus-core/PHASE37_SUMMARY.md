# Phase 37: Tier-3 Execution Plans and Orchestration

## What Was Added

- **Execution plan concept**: a structured object that references one or more
  existing Tier-3 proposals by ID, with optional inter-proposal dependencies,
  and executes them as a single governed batch.
- **Plan registry**: an in-memory registry for creating, listing, inspecting,
  and tracking execution plans — consistent with all existing registry designs.
- **Dependency resolution**: a topological-sort engine that computes a valid
  execution order respecting declared dependencies and rejects cycles at plan
  creation time.
- **Orchestrator**: an operator-triggered `execute_plan` function that walks
  the dependency-ordered proposal list, validates each proposal through the
  existing governance gates, delegates to the existing dispatcher, stops on
  first failure, and marks remaining proposals as skipped.
- **Cockpit commands**: `t3_plan_create`, `t3_plan`, `t3_plans`, and
  `t3_plan_execute` for full operator control over the plan lifecycle.
- **Dashboard section**: a "Tier-3 Execution Plans" panel showing recent plans
  with status, proposal count, and success/failure/skip tallies.

## Why It Is Safe

- No new mutation pathways: all execution flows through the existing governed
  dispatcher, reversible ledger, and migration engine.
- Approval and dry-run requirements for irreversible migrations remain fully
  enforced — the orchestrator calls `validate_proposal_for_execution` before
  each proposal.
- Stop-on-first-failure semantics prevent partial, uncontrolled state changes.
- Plans are operator-created and operator-triggered only; no background threads,
  scheduling, or automatic plan generation.
- The dependency resolver runs at creation time and rejects invalid or cyclic
  graphs before any execution begins.
- All plan state is in-memory and non-persistent, consistent with the existing
  data model.

## How It Prepares for the Next Phase

- The plan abstraction is a natural anchor for scheduling policies, recurring
  plan templates, or higher-level strategy objects that compose plans.
- Per-proposal result tracking inside a plan enables future rollback strategies
  (e.g., undo succeeded proposals when a later one fails).
- Dependency metadata can be extended with conditions or guards for
  more expressive orchestration without changing the core model.
