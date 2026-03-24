# Phase 39: Scheduled Policy Evaluation and Policy Windows

## What Was Added

- **Scheduling metadata on policies**: optional `evaluation_interval_seconds`,
  `allowed_windows` (time-of-day ranges), `rate_limit` (max triggers per
  rolling hour window), `last_evaluated_at`, and `trigger_count_window`.
- **Scheduling constraint checks**: pure functions that verify interval
  elapsed, current time within allowed windows (including midnight-wrapping),
  and rate limit not exceeded before evaluating a policy.
- **`evaluate_policies_scheduled()`**: an operator-triggered evaluation path
  that applies all scheduling constraints before evaluating each enabled
  policy. Policies that fail scheduling checks are logged with a reason and
  not evaluated.
- **Scheduling setters**: `set_policy_interval`, `set_policy_window`,
  `set_policy_rate_limit` for dynamic adjustment of scheduling parameters.
- **Cockpit commands**: `t3_policy_schedule`, `t3_policy_windows`,
  `t3_policy_set_window`, `t3_policy_set_interval`,
  `t3_policy_set_rate_limit`, `t3_policy_timers`.
- **Dashboard section**: "Tier-3 Policy Scheduling" showing each policy's
  interval, allowed windows, last evaluation time, next eligible time,
  and rate-limit status.

## Why It Is Safe

- `evaluate_policies_scheduled` only creates proposals and plans — it never
  executes them. All execution remains operator-gated.
- Scheduling constraints are pure, read-only checks. The only state they
  mutate is `last_evaluated_at` and `trigger_count_window` on the policy
  itself.
- No background threads, timers, or async loops. Scheduled evaluation only
  runs when the operator explicitly invokes it.
- Window and rate-limit checks are additive gates — they can only prevent
  evaluation, never force it.
- No new condition types, action types, or mutation pathways.

## How It Prepares for the Next Phase

- The scheduling infrastructure is the foundation for policy-driven
  optimization: adaptive thresholds that adjust settings based on observed
  drift, error rates, or resource usage.
- Rate limits and windows enable safe experimentation with more aggressive
  policies, knowing they cannot fire unboundedly.
- The `trigger_count_window` provides the data needed for frequency analysis
  and policy effectiveness metrics.
- The interval model can be extended with jitter, backoff, or priority-based
  scheduling for multi-policy orchestration.
