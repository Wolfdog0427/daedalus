import type { PreSealIssue, PreSealReport } from "./preSealValidation";
import type { ThroneView } from "./kernelThrone";
import type { ConnectivitySnapshot } from "./connectivity";
import type { EpistemicReport } from "./epistemicIntake";
import type { OperatorContextSnapshot } from "./operatorContext";
import type { EmbodiedPresenceSnapshot } from "./embodiedPresence";
import type { NodePresenceSnapshot } from "./nodePresence";
import type { AttentionTaskSnapshot } from "./attentionTask";
import type { SystemContinuitySnapshot } from "./systemContinuity";

export interface PreSealInput {
  throne: ThroneView;
  connectivity: ConnectivitySnapshot;
  epistemic: EpistemicReport;
  operator: OperatorContextSnapshot;
  embodied: EmbodiedPresenceSnapshot;
  nodePresence: NodePresenceSnapshot;
  attentionTask: AttentionTaskSnapshot;
  continuity: SystemContinuitySnapshot;
}

/**
 * A shell in "degraded" status means kernel invariants were violated.
 * This is a blocking issue — the Seal cannot be applied.
 */
export function checkShellHealth(throne: ThroneView): PreSealIssue | null {
  if (throne.shellStatus === "degraded") {
    return {
      kind: "shell-degraded",
      description: "Kernel Shell is in degraded mode — one or more invariants violated",
      blocking: true,
    };
  }
  return null;
}

/**
 * Any invariant failure is a blocking issue.
 */
export function checkInvariants(throne: ThroneView): PreSealIssue | null {
  if (!throne.invariantsPassed) {
    return {
      kind: "invariant-failure",
      description: `${throne.invariantsTotal - throne.invariantsHeld} of ${throne.invariantsTotal} invariants failed`,
      blocking: true,
    };
  }
  return null;
}

/**
 * Kernel in "escalated" state means the autonomy stack is overloaded.
 * Blocking — the system should settle before the Seal.
 */
export function checkKernelStatus(throne: ThroneView): PreSealIssue | null {
  if (throne.kernelStatus === "escalated") {
    return {
      kind: "kernel-escalated",
      description: "Kernel is in escalated state — tier overload or governance conflict",
      blocking: true,
    };
  }
  return null;
}

/**
 * Nodes in connectivity but absent from nodePresence (or vice versa)
 * indicate a wiring gap. Warning only.
 */
export function checkOrphanNodes(
  connectivity: ConnectivitySnapshot,
  nodePresence: NodePresenceSnapshot,
): PreSealIssue | null {
  if (connectivity.totalCount > 0 && nodePresence.totalCount === 0) {
    return {
      kind: "orphan-nodes",
      description: `${connectivity.totalCount} node(s) in connectivity but absent from node presence`,
      blocking: false,
    };
  }
  if (connectivity.totalCount === 0 && nodePresence.totalCount > 0) {
    return {
      kind: "orphan-nodes",
      description: `${nodePresence.totalCount} node(s) in node presence but absent from connectivity`,
      blocking: false,
    };
  }
  return null;
}

/**
 * Unverified data sources are a warning — the operator should review.
 */
export function checkEpistemicUnverified(epistemic: EpistemicReport): PreSealIssue | null {
  if (epistemic.unverifiedWarning) {
    return {
      kind: "epistemic-unverified",
      description: `${epistemic.unverifiedCount} unverified data source(s) — untrusted, no heartbeat`,
      blocking: false,
    };
  }
  return null;
}

/**
 * Low freshness (< 0.4) means most knowledge is stale. Warning.
 */
export function checkEpistemicFreshness(epistemic: EpistemicReport): PreSealIssue | null {
  if (epistemic.freshness < 0.4) {
    return {
      kind: "epistemic-stale",
      description: `Knowledge freshness is ${(epistemic.freshness * 100).toFixed(0)}% — most sources are stale`,
      blocking: false,
    };
  }
  return null;
}

/**
 * Fragile continuity is a warning — the system is coherent but unstable.
 */
export function checkContinuityHealth(continuity: SystemContinuitySnapshot): PreSealIssue | null {
  if (continuity.health === "fragile") {
    return {
      kind: "continuity-fragile",
      description: `System continuity is fragile (composite ${(continuity.composite * 100).toFixed(0)}%)`,
      blocking: false,
    };
  }
  return null;
}

/**
 * Low sovereignty (< 0.5) means the operator is losing control. Warning.
 */
export function checkSovereignty(operator: OperatorContextSnapshot): PreSealIssue | null {
  if (operator.sovereignty < 0.5) {
    return {
      kind: "sovereignty-low",
      description: `Operator sovereignty is ${(operator.sovereignty * 100).toFixed(0)}% — excessive overrides or pending proposals`,
      blocking: false,
    };
  }
  return null;
}

/**
 * Runs the full pre-seal validation suite and produces a frozen report.
 */
export function computePreSealReport(input: PreSealInput): PreSealReport {
  const checks: (PreSealIssue | null)[] = [
    checkShellHealth(input.throne),
    checkInvariants(input.throne),
    checkKernelStatus(input.throne),
    checkOrphanNodes(input.connectivity, input.nodePresence),
    checkEpistemicUnverified(input.epistemic),
    checkEpistemicFreshness(input.epistemic),
    checkContinuityHealth(input.continuity),
    checkSovereignty(input.operator),
  ];

  const issues: PreSealIssue[] = checks.filter(
    (c): c is PreSealIssue => c !== null,
  );

  const blockingCount = issues.filter((i) => i.blocking).length;
  const warningCount = issues.length - blockingCount;

  return Object.freeze({
    issues: Object.freeze(issues),
    blockingCount,
    warningCount,
    passed: blockingCount === 0,
    integrationCount: checks.length,
    checkedAt: Date.now(),
  });
}
