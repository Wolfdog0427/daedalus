# Phase 34: Real, Governed Tier-3 Action Execution

## What was added

- Three stub handlers from Phase 33 were replaced with real, governed implementations that perform actual mutations through existing validated APIs:
  - **update_setting** calls the system settings module, captures old and new values.
  - **retire_action** removes an action from the appropriate tier registry via the existing demotion/retirement APIs.
  - **replace_action** atomically removes an old action and registers a new one within a single tier registry.
- The **apply_migration** handler remains a stub, logging intent without performing mutations, as a preparation surface for Phase 35.
- A **reversible-state ledger** records every successful governed dispatch with the proposal id, action type, old values, new values, reversibility flag, and timestamp. Irreversible actions are logged in the ledger without old/new values for audit completeness.
- The dispatcher was updated to write to the ledger after successful handler execution and to pass the proposal id through the dispatch chain.
- Two cockpit commands were added: `t3_history()` shows the reversible ledger and `t3_last()` shows the most recent Tier-3 execution.
- A dashboard section renders the last five ledger entries with old/new state snapshots.

## Why it is safe

- Every handler delegates to an existing, validated API (`set_setting`, `demote_action_from_tier1`, `retire_tier2_action`, `register_tier1_action`, `register_tier2_action`) that already enforces its own validation rules. The handlers do not bypass any subsystem's internal safety checks.
- The full governance chain remains intact: a proposal must be operator-approved and the maintenance envelope must pass before any handler is reached.
- The reversible ledger captures before-and-after state for every mutation, providing the data needed for future rollback without introducing rollback machinery in this phase.
- The apply_migration handler explicitly refuses to execute, ensuring irreversible structural changes cannot occur until a dedicated migration framework is built.

## How it prepares for Phase 35

- The ledger provides a complete audit trail with old values, which Phase 35 can use to implement a `t3_revert(proposal_id)` command that reads the ledger and applies the inverse operation.
- The apply_migration handler's stub interface is ready to accept a real implementation once migration safety contracts are defined.
- The dispatcher's handler map makes it straightforward to add new action types or swap implementations without changing the governance or logging infrastructure.
