import type { AdaptationTuning } from "./sceneAdaptation";
import type { TuningCaps } from "./postAutonomy";
import { POST_AUTONOMY_DEFAULTS } from "./postAutonomy";
import type { KernelState } from "./governanceKernel";
import type { FabricDashboard } from "./governanceFabric";
import type { InvariantCheck, InvariantReport } from "./kernelInvariants";
import { MAX_PENDING_PROPOSALS, MAX_TUNING_FIELDS } from "./kernelInvariants";

/**
 * Validates all kernel invariants against live state.
 *
 * Structural invariants (operator-sovereignty, no-silent-changes,
 * rollback-available, deterministic-merge, no-recursive-governance)
 * always pass — they are guaranteed by architecture. Including them
 * makes the full guarantee set visible in the HUD.
 *
 * Runtime invariants check actual state each cycle.
 */
export function validateInvariants(
  kernel: KernelState,
  dashboard: FabricDashboard,
  effectiveTuning: AdaptationTuning,
  caps: TuningCaps = POST_AUTONOMY_DEFAULTS.caps,
): InvariantReport {
  const checks: InvariantCheck[] = [
    // ── Structural (architecture-guaranteed) ──
    { name: "operator-sovereignty", passed: true },
    { name: "no-silent-changes", passed: true },
    { name: "rollback-available", passed: true },
    { name: "deterministic-merge", passed: true },
    { name: "no-recursive-governance", passed: true },

    // ── Runtime (state-validated) ──
    {
      name: "single-proposal-bounded",
      passed: kernel.pendingCount <= MAX_PENDING_PROPOSALS,
    },
    {
      name: "bounded-overrides",
      passed: kernel.overrideCount <= MAX_TUNING_FIELDS,
    },
    {
      name: "caps-enforced",
      passed: verifyCaps(effectiveTuning, caps),
    },
    {
      name: "no-escalation-leak",
      passed: verifyEscalationConsistency(kernel, dashboard),
    },
  ];

  const failedCount = checks.filter((c) => !c.passed).length;

  return {
    allPassed: failedCount === 0,
    checks,
    failedCount,
  };
}

/**
 * Verifies every defined tuning field falls within its cap bounds.
 */
function verifyCaps(tuning: AdaptationTuning, caps: TuningCaps): boolean {
  const fields: { key: keyof AdaptationTuning; cap: keyof TuningCaps }[] = [
    { key: "governorCooldownMs", cap: "governorCooldownMs" },
    { key: "governorEscalationLockMs", cap: "governorEscalationLockMs" },
    { key: "timelineMomentumHalfLifeMs", cap: "timelineMomentumHalfLifeMs" },
    { key: "narrativeMinIntervalMs", cap: "narrativeMinIntervalMs" },
    { key: "grammarDefaultDwellMs", cap: "grammarDefaultDwellMs" },
    { key: "grammarDefaultBlendMs", cap: "grammarDefaultBlendMs" },
  ];

  for (const { key, cap } of fields) {
    const val = tuning[key];
    if (val === undefined) continue;
    const [min, max] = caps[cap];
    if (val < min || val > max) return false;
  }
  return true;
}

/**
 * Verifies that kernel status reflects the dashboard's escalation
 * state: if escalation is detected, the kernel must be "escalated".
 */
function verifyEscalationConsistency(
  kernel: KernelState,
  dashboard: FabricDashboard,
): boolean {
  if (dashboard.escalationDetected && kernel.status !== "escalated") return false;
  if (dashboard.health.label === "overloaded" && kernel.status !== "escalated") return false;
  return true;
}
