import {
  checkShellHealth,
  checkInvariants,
  checkKernelStatus,
  checkOrphanNodes,
  checkEpistemicUnverified,
  checkEpistemicFreshness,
  checkContinuityHealth,
  checkSovereignty,
  computePreSealReport,
} from "../../shared/daedalus/preSealValidationEngine";
import type { PreSealInput } from "../../shared/daedalus/preSealValidationEngine";
import { THRONE_IDLE } from "../../shared/daedalus/kernelThrone";
import { CONNECTIVITY_IDLE } from "../../shared/daedalus/connectivity";
import { EPISTEMIC_IDLE } from "../../shared/daedalus/epistemicIntake";
import { OPERATOR_CONTEXT_IDLE } from "../../shared/daedalus/operatorContext";
import { EMBODIED_IDLE } from "../../shared/daedalus/embodiedPresence";
import { NODE_PRESENCE_IDLE } from "../../shared/daedalus/nodePresence";
import { ATTENTION_TASK_IDLE } from "../../shared/daedalus/attentionTask";
import { SYSTEM_CONTINUITY_IDLE } from "../../shared/daedalus/systemContinuity";

function mkInput(overrides: Partial<PreSealInput> = {}): PreSealInput {
  return {
    throne: THRONE_IDLE,
    connectivity: CONNECTIVITY_IDLE,
    epistemic: EPISTEMIC_IDLE,
    operator: OPERATOR_CONTEXT_IDLE,
    embodied: EMBODIED_IDLE,
    nodePresence: NODE_PRESENCE_IDLE,
    attentionTask: ATTENTION_TASK_IDLE,
    continuity: SYSTEM_CONTINUITY_IDLE,
    ...overrides,
  };
}

// ── checkShellHealth ─────────────────────────────────────────────

describe("checkShellHealth", () => {
  it("returns null for nominal shell", () => {
    expect(checkShellHealth(THRONE_IDLE)).toBeNull();
  });

  it("returns blocking issue for degraded shell", () => {
    const throne = { ...THRONE_IDLE, shellStatus: "degraded" as const };
    const issue = checkShellHealth(throne);
    expect(issue).not.toBeNull();
    expect(issue!.kind).toBe("shell-degraded");
    expect(issue!.blocking).toBe(true);
  });
});

// ── checkInvariants ──────────────────────────────────────────────

describe("checkInvariants", () => {
  it("returns null when all invariants pass", () => {
    const throne = { ...THRONE_IDLE, invariantsPassed: true, invariantsHeld: 9, invariantsTotal: 9 };
    expect(checkInvariants(throne)).toBeNull();
  });

  it("returns blocking issue when invariants fail", () => {
    const throne = { ...THRONE_IDLE, invariantsPassed: false, invariantsHeld: 7, invariantsTotal: 9 };
    const issue = checkInvariants(throne);
    expect(issue).not.toBeNull();
    expect(issue!.kind).toBe("invariant-failure");
    expect(issue!.blocking).toBe(true);
    expect(issue!.description).toContain("2 of 9");
  });
});

// ── checkKernelStatus ────────────────────────────────────────────

describe("checkKernelStatus", () => {
  it("returns null for clean kernel", () => {
    expect(checkKernelStatus(THRONE_IDLE)).toBeNull();
  });

  it("returns null for tuned kernel", () => {
    const throne = { ...THRONE_IDLE, kernelStatus: "tuned" as const };
    expect(checkKernelStatus(throne)).toBeNull();
  });

  it("returns blocking issue for escalated kernel", () => {
    const throne = { ...THRONE_IDLE, kernelStatus: "escalated" as const };
    const issue = checkKernelStatus(throne);
    expect(issue).not.toBeNull();
    expect(issue!.kind).toBe("kernel-escalated");
    expect(issue!.blocking).toBe(true);
  });
});

// ── checkOrphanNodes ─────────────────────────────────────────────

describe("checkOrphanNodes", () => {
  it("returns null when both counts match (zero)", () => {
    expect(checkOrphanNodes(CONNECTIVITY_IDLE, NODE_PRESENCE_IDLE)).toBeNull();
  });

  it("returns warning when connectivity has nodes but presence is empty", () => {
    const conn = { ...CONNECTIVITY_IDLE, totalCount: 3 };
    const issue = checkOrphanNodes(conn, NODE_PRESENCE_IDLE);
    expect(issue).not.toBeNull();
    expect(issue!.kind).toBe("orphan-nodes");
    expect(issue!.blocking).toBe(false);
    expect(issue!.description).toContain("3 node(s) in connectivity");
  });

  it("returns warning when presence has nodes but connectivity is empty", () => {
    const pres = { ...NODE_PRESENCE_IDLE, totalCount: 2 };
    const issue = checkOrphanNodes(CONNECTIVITY_IDLE, pres);
    expect(issue).not.toBeNull();
    expect(issue!.description).toContain("2 node(s) in node presence");
  });

  it("returns null when both sides have nodes", () => {
    const conn = { ...CONNECTIVITY_IDLE, totalCount: 3 };
    const pres = { ...NODE_PRESENCE_IDLE, totalCount: 3 };
    expect(checkOrphanNodes(conn, pres)).toBeNull();
  });
});

// ── checkEpistemicUnverified ─────────────────────────────────────

describe("checkEpistemicUnverified", () => {
  it("returns null when no unverified sources", () => {
    expect(checkEpistemicUnverified(EPISTEMIC_IDLE)).toBeNull();
  });

  it("returns warning when unverified sources exist", () => {
    const ep = { ...EPISTEMIC_IDLE, unverifiedWarning: true, unverifiedCount: 2 };
    const issue = checkEpistemicUnverified(ep);
    expect(issue).not.toBeNull();
    expect(issue!.kind).toBe("epistemic-unverified");
    expect(issue!.blocking).toBe(false);
    expect(issue!.description).toContain("2 unverified");
  });
});

// ── checkEpistemicFreshness ──────────────────────────────────────

describe("checkEpistemicFreshness", () => {
  it("returns null for high freshness", () => {
    expect(checkEpistemicFreshness(EPISTEMIC_IDLE)).toBeNull();
  });

  it("returns null at freshness boundary (0.4)", () => {
    const ep = { ...EPISTEMIC_IDLE, freshness: 0.4 };
    expect(checkEpistemicFreshness(ep)).toBeNull();
  });

  it("returns warning for low freshness", () => {
    const ep = { ...EPISTEMIC_IDLE, freshness: 0.2 };
    const issue = checkEpistemicFreshness(ep);
    expect(issue).not.toBeNull();
    expect(issue!.kind).toBe("epistemic-stale");
    expect(issue!.blocking).toBe(false);
    expect(issue!.description).toContain("20%");
  });
});

// ── checkContinuityHealth ────────────────────────────────────────

describe("checkContinuityHealth", () => {
  it("returns null for healthy continuity", () => {
    expect(checkContinuityHealth(SYSTEM_CONTINUITY_IDLE)).toBeNull();
  });

  it("returns null for shifting continuity", () => {
    const cont = { ...SYSTEM_CONTINUITY_IDLE, health: "shifting" as const, composite: 0.55 };
    expect(checkContinuityHealth(cont)).toBeNull();
  });

  it("returns warning for fragile continuity", () => {
    const cont = { ...SYSTEM_CONTINUITY_IDLE, health: "fragile" as const, composite: 0.25 };
    const issue = checkContinuityHealth(cont);
    expect(issue).not.toBeNull();
    expect(issue!.kind).toBe("continuity-fragile");
    expect(issue!.blocking).toBe(false);
    expect(issue!.description).toContain("25%");
  });
});

// ── checkSovereignty ─────────────────────────────────────────────

describe("checkSovereignty", () => {
  it("returns null for full sovereignty", () => {
    expect(checkSovereignty(OPERATOR_CONTEXT_IDLE)).toBeNull();
  });

  it("returns null at sovereignty boundary (0.5)", () => {
    const op = { ...OPERATOR_CONTEXT_IDLE, sovereignty: 0.5 };
    expect(checkSovereignty(op)).toBeNull();
  });

  it("returns warning for low sovereignty", () => {
    const op = { ...OPERATOR_CONTEXT_IDLE, sovereignty: 0.3 };
    const issue = checkSovereignty(op);
    expect(issue).not.toBeNull();
    expect(issue!.kind).toBe("sovereignty-low");
    expect(issue!.blocking).toBe(false);
    expect(issue!.description).toContain("30%");
  });
});

// ── computePreSealReport ─────────────────────────────────────────

describe("computePreSealReport", () => {
  it("passes for all-idle state", () => {
    const report = computePreSealReport(mkInput());
    expect(report.passed).toBe(true);
    expect(report.blockingCount).toBe(0);
    expect(report.warningCount).toBe(0);
    expect(report.integrationCount).toBe(8);
  });

  it("fails when shell is degraded", () => {
    const report = computePreSealReport(
      mkInput({ throne: { ...THRONE_IDLE, shellStatus: "degraded" as const } }),
    );
    expect(report.passed).toBe(false);
    expect(report.blockingCount).toBeGreaterThanOrEqual(1);
  });

  it("fails when kernel is escalated", () => {
    const report = computePreSealReport(
      mkInput({ throne: { ...THRONE_IDLE, kernelStatus: "escalated" as const } }),
    );
    expect(report.passed).toBe(false);
    expect(report.blockingCount).toBeGreaterThanOrEqual(1);
  });

  it("passes with warnings for non-blocking issues", () => {
    const report = computePreSealReport(
      mkInput({
        epistemic: { ...EPISTEMIC_IDLE, freshness: 0.1 },
        continuity: { ...SYSTEM_CONTINUITY_IDLE, health: "fragile" as const, composite: 0.2 },
      }),
    );
    expect(report.passed).toBe(true);
    expect(report.blockingCount).toBe(0);
    expect(report.warningCount).toBe(2);
  });

  it("accumulates blocking and warning counts independently", () => {
    const report = computePreSealReport(
      mkInput({
        throne: { ...THRONE_IDLE, shellStatus: "degraded" as const, invariantsPassed: false, invariantsHeld: 5, invariantsTotal: 9 },
        epistemic: { ...EPISTEMIC_IDLE, unverifiedWarning: true, unverifiedCount: 1 },
      }),
    );
    expect(report.passed).toBe(false);
    expect(report.blockingCount).toBe(2);
    expect(report.warningCount).toBe(1);
  });

  it("produces a frozen report", () => {
    const report = computePreSealReport(mkInput());
    expect(Object.isFrozen(report)).toBe(true);
    expect(Object.isFrozen(report.issues)).toBe(true);
  });
});
