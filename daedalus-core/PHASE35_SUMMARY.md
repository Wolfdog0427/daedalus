# Phase 35: Tier-3 Migration Engine

## What was added

- A governed migration engine that replaces the `apply_migration` stub with real, step-by-step execution. Migrations are sequences of steps drawn from a strict, closed vocabulary: `set_setting`, `retire_action`, `replace_action`, and `note`.
- Each mutation step delegates to the same governed handlers used by the other Tier-3 action types, ensuring all validation, safety checks, and subsystem APIs are reused rather than duplicated.
- A dedicated migration log that records every migration's name, timestamp, overall status, per-step results (index, type, status, detail), and failure reason when applicable. This log is separate from the reversible ledger, consistent with migrations being irreversible.
- Fail-fast semantics: if any step fails, execution halts immediately, the migration is marked as failed, and the failure reason is recorded. No partial-completion ambiguity.
- Two cockpit commands: `t3_migration_status(name)` for inspecting a specific migration's outcome, and `t3_migrations()` for listing recent migrations.
- A dashboard section showing the last five migrations with their name, status, step counts, and timestamps.

## Why it is safe

- The step vocabulary is a fixed set of four types. Unknown step types cause an immediate, logged failure with no mutations attempted. There is no dynamic dispatch, no eval, no arbitrary code execution.
- Every mutating step type calls the same governed handler that the rest of the Tier-3 system uses, inheriting all of their validation (setting type/range checks, registry existence checks, classification checks). The migration engine cannot bypass these checks.
- Migrations are still gated by the full governance chain: proposal approval and envelope pass are required before the dispatcher reaches the migration handler. The engine itself adds no new entry points.
- The migration log is append-only and in-memory. It does not alter the reversible ledger, telemetry, or any other pre-existing audit structure.

## How it prepares for the next phase

- The per-step logging and fail-fast behavior provide the foundation for a dry-run mode that could execute the same step sequence against a snapshot without committing mutations.
- The strict step vocabulary can be extended in future phases (e.g., `add_action`, `update_action_description`) by adding new entries to the vocabulary set and corresponding branches in the step executor, without changing the engine's control flow or safety model.
- The migration log's structured step results enable future approval workflows where an operator can review a migration's projected steps before authorizing execution.
