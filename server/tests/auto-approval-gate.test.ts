/**
 * Auto-Approval Gate — Comprehensive Test Suite
 *
 * Tests the multi-axis safety gate:
 *   - Core shouldAutoApprove logic
 *   - Impact classification (derived from kind + payload)
 *   - Invariant touch detection
 *   - Reversibility assessment
 *   - Rate limiting / cooldown
 *   - Safe mode blocking
 *   - Configurable thresholds
 *   - Integration with tickKernel pipeline
 *   - Edge cases and boundary conditions
 */

import {
  shouldAutoApprove,
  evaluateProposals,
  getApprovalGateConfig,
  updateApprovalGateConfig,
  getRecentApprovalDecisions,
  resetApprovalGate,
  tickKernel,
  resetDispatcher,
  kernelTelemetry,
  resetSafeMode,
  resetIdentityState,
  resetIntentState,
  updateSafeModeFromAlignment,
  DEFAULT_KERNEL_CONFIG,
  DEFAULT_ALIGNMENT_CONFIG,
  DEFAULT_APPROVAL_GATE_CONFIG,
} from "../../kernel/src";
import type {
  ChangeProposal,
  StrategyEvaluation,
  SafeModeState,
  AlignmentConfig,
  ApprovalGateConfig,
  AlignmentContext,
} from "../../kernel/src";
import type { BeingPresenceDetail, PostureState } from "../../shared/daedalus/contracts";

// ── Factories ───────────────────────────────────────────────────────

let proposalCounter = 0;

function mkProposal(overrides: Partial<ChangeProposal> = {}): ChangeProposal {
  proposalCounter++;
  return {
    id: overrides.id ?? `test-${proposalCounter}`,
    kind: overrides.kind ?? "alignment_config",
    description: overrides.description ?? "test change",
    payload: overrides.payload ?? {},
    proposedAt: overrides.proposedAt ?? Date.now(),
    proposedBy: overrides.proposedBy ?? "test",
  };
}

function mkEvaluation(overrides: Partial<StrategyEvaluation> = {}): StrategyEvaluation {
  return {
    name: "sovereignty_stable",
    confidence: 95,
    alignment: 98,
    alignmentBreakdown: { sovereignty: 98, identity: 96, governance: 99, stability: 97 },
    weakestAxis: "identity",
    strongestAxis: "governance",
    notes: "",
    evaluatedAt: new Date().toISOString(),
    ...overrides,
  } as StrategyEvaluation;
}

const safeModeOff: SafeModeState = { active: false };
const safeModeOn: SafeModeState = { active: true, reason: "test", since: Date.now() };

function mkBeing(): BeingPresenceDetail {
  return {
    id: "operator", label: "Operator", role: "operator",
    presenceMode: "active", isGuiding: true, influenceLevel: 0.9,
    continuity: { healthy: true, streak: 10, lastCheckedAt: new Date().toISOString() },
  } as unknown as BeingPresenceDetail;
}

function mkContext(overrides: Partial<AlignmentContext> = {}): AlignmentContext {
  return {
    beings: [mkBeing()],
    constitutionReport: { allPassed: true, failedCount: 0, checks: [] },
    posture: "OPEN" as PostureState,
    postureReason: "default",
    overrides: [], drifts: [], votes: [],
    nodeCount: 10, quarantinedCount: 0, totalErrors: 0, activeHeartbeats: 10,
    ...overrides,
  };
}

// ── Setup ───────────────────────────────────────────────────────────

beforeEach(() => {
  resetApprovalGate();
  resetDispatcher();
  kernelTelemetry.clear();
  resetSafeMode();
  resetIdentityState();
  resetIntentState();
  proposalCounter = 0;
});

// ── Core Gate Logic ─────────────────────────────────────────────────

describe("shouldAutoApprove — core logic", () => {
  test("approves when all conditions met", () => {
    const decision = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation(),
      safeModeOff,
      { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(decision.autoApprove).toBe(true);
    expect(decision.reasons.alignmentOK).toBe(true);
    expect(decision.reasons.confidenceOK).toBe(true);
    expect(decision.reasons.impactOK).toBe(true);
    expect(decision.reasons.invariantsOK).toBe(true);
    expect(decision.reasons.reversibleOK).toBe(true);
    expect(decision.reasons.safeModeOK).toBe(true);
    expect(decision.reasons.cooldownOK).toBe(true);
  });

  test("rejects when alignment below threshold", () => {
    const decision = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation({ alignment: 90 }),
      safeModeOff,
      { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(decision.autoApprove).toBe(false);
    expect(decision.reasons.alignmentOK).toBe(false);
  });

  test("rejects when confidence below threshold", () => {
    const decision = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation({ confidence: 70 }),
      safeModeOff,
      { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(decision.autoApprove).toBe(false);
    expect(decision.reasons.confidenceOK).toBe(false);
  });

  test("rejects when safe mode active", () => {
    const decision = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation(),
      safeModeOn,
      { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(decision.autoApprove).toBe(false);
    expect(decision.reasons.safeModeOK).toBe(false);
  });

  test("allows during safe mode when config permits", () => {
    updateApprovalGateConfig({ allowDuringSafeMode: true });
    const decision = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation(),
      safeModeOn,
      { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(decision.reasons.safeModeOK).toBe(true);
  });

  test("boundary: alignment exactly at threshold passes", () => {
    const decision = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation({ alignment: 95 }),
      safeModeOff,
      { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(decision.reasons.alignmentOK).toBe(true);
  });

  test("boundary: confidence exactly at threshold passes", () => {
    const decision = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation({ confidence: 80 }),
      safeModeOff,
      { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(decision.reasons.confidenceOK).toBe(true);
  });
});

// ── Impact Classification ───────────────────────────────────────────

describe("Impact classification", () => {
  test("alignment_config small floor change → low", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "alignment_config", payload: { alignmentFloor: 63 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.derivedImpact).toBe("low");
    expect(d.reasons.impactOK).toBe(true);
  });

  test("alignment_config medium weight change → medium", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "alignment_config", payload: { sovereigntyWeight: 0.54 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.derivedImpact).toBe("medium");
    expect(d.reasons.impactOK).toBe(false);
  });

  test("alignment_config large weight change → high", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "alignment_config", payload: { sovereigntyWeight: 0.9 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.derivedImpact).toBe("high");
  });

  test("strategy_override → medium", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "strategy_override", payload: { strategy: "alignment_nominal" } }),
      mkEvaluation(), safeModeOff,
    );
    expect(d.derivedImpact).toBe("medium");
    expect(d.reasons.impactOK).toBe(false);
  });

  test("safe_mode_toggle → high", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "safe_mode_toggle", payload: { active: true } }),
      mkEvaluation(), safeModeOff,
    );
    expect(d.derivedImpact).toBe("high");
  });

  test("governance_override with GLOBAL scope → high", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "governance_override", payload: { scope: "GLOBAL" } }),
      mkEvaluation(), safeModeOff,
    );
    expect(d.derivedImpact).toBe("high");
  });

  test("governance_override with non-global scope → medium", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "governance_override", payload: { scope: "NODE" } }),
      mkEvaluation(), safeModeOff,
    );
    expect(d.derivedImpact).toBe("medium");
  });

  test("kernel_config small change → low", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "kernel_config", payload: { strategySensitivity: 0.95 } }),
      mkEvaluation(), safeModeOff,
    );
    expect(d.derivedImpact).toBe("low");
  });

  test("kernel_config large change → high", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "kernel_config", payload: { strategySensitivity: 0.1 } }),
      mkEvaluation(), safeModeOff,
    );
    expect(d.derivedImpact).toBe("high");
  });
});

// ── Invariant Detection ─────────────────────────────────────────────

describe("Invariant detection", () => {
  test("weights summing to 1.0 → no invariant touch", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "alignment_config", payload: {
        sovereigntyWeight: 0.35, identityWeight: 0.25, governanceWeight: 0.3, stabilityWeight: 0.1,
      }}),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.touchesInvariants).toBe(false);
    expect(d.reasons.invariantsOK).toBe(true);
  });

  test("weights not summing to 1.0 → invariant touch", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "alignment_config", payload: {
        sovereigntyWeight: 0.5, identityWeight: 0.5, governanceWeight: 0.5, stabilityWeight: 0.5,
      }}),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.touchesInvariants).toBe(true);
    expect(d.reasons.invariantsOK).toBe(false);
  });

  test("alignment floor too low → invariant touch", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "alignment_config", payload: { alignmentFloor: 10 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.touchesInvariants).toBe(true);
  });

  test("alignment floor too high → invariant touch", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "alignment_config", payload: { alignmentFloor: 100 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.touchesInvariants).toBe(true);
  });

  test("safe_mode_toggle always touches invariants", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "safe_mode_toggle", payload: {} }),
      mkEvaluation(), safeModeOff,
    );
    expect(d.touchesInvariants).toBe(true);
  });

  test("global DENY governance override touches invariants", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "governance_override", payload: { scope: "GLOBAL", effect: "DENY" } }),
      mkEvaluation(), safeModeOff,
    );
    expect(d.touchesInvariants).toBe(true);
  });
});

// ── Reversibility ───────────────────────────────────────────────────

describe("Reversibility assessment", () => {
  test("alignment_config is reversible", () => {
    const d = shouldAutoApprove(mkProposal({ kind: "alignment_config" }), mkEvaluation(), safeModeOff);
    expect(d.reversible).toBe(true);
  });

  test("kernel_config is reversible", () => {
    const d = shouldAutoApprove(mkProposal({ kind: "kernel_config" }), mkEvaluation(), safeModeOff);
    expect(d.reversible).toBe(true);
  });

  test("governance_override with GLOBAL scope is not reversible", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "governance_override", payload: { scope: "GLOBAL" } }),
      mkEvaluation(), safeModeOff,
    );
    expect(d.reversible).toBe(false);
  });

  test("governance_override with NODE scope is reversible", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "governance_override", payload: { scope: "NODE" } }),
      mkEvaluation(), safeModeOff,
    );
    expect(d.reversible).toBe(true);
  });
});

// ── Rate Limiting ───────────────────────────────────────────────────

describe("Rate limiting / cooldown", () => {
  test("first proposal passes cooldown", () => {
    const d = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.reasons.cooldownOK).toBe(true);
  });

  test("rapid second proposal fails cooldown", () => {
    shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    const d2 = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 63 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d2.reasons.cooldownOK).toBe(false);
    expect(d2.autoApprove).toBe(false);
  });

  test("cooldown of 0ms allows rapid approvals", () => {
    updateApprovalGateConfig({ cooldownMs: 0 });
    shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    const d2 = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 63 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d2.reasons.cooldownOK).toBe(true);
    expect(d2.autoApprove).toBe(true);
  });
});

// ── Configurable Thresholds ─────────────────────────────────────────

describe("Configurable thresholds", () => {
  test("default thresholds match constants", () => {
    const cfg = getApprovalGateConfig();
    expect(cfg.alignmentThreshold).toBe(95);
    expect(cfg.confidenceThreshold).toBe(80);
    expect(cfg.cooldownMs).toBe(5000);
    expect(cfg.allowDuringSafeMode).toBe(false);
  });

  test("lowered alignment threshold allows lower-alignment approvals", () => {
    updateApprovalGateConfig({ alignmentThreshold: 70 });
    const d = shouldAutoApprove(
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkEvaluation({ alignment: 75 }),
      safeModeOff,
      { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.reasons.alignmentOK).toBe(true);
    expect(d.autoApprove).toBe(true);
  });

  test("lowered confidence threshold allows lower-confidence approvals", () => {
    updateApprovalGateConfig({ confidenceThreshold: 50 });
    const d = shouldAutoApprove(
      mkProposal({ payload: { sovereigntyWeight: 0.41 } }),
      mkEvaluation({ confidence: 55 }),
      safeModeOff,
      { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.reasons.confidenceOK).toBe(true);
  });
});

// ── Batch Evaluation ────────────────────────────────────────────────

describe("evaluateProposals — batch", () => {
  test("evaluates multiple proposals", () => {
    updateApprovalGateConfig({ cooldownMs: 0 });
    const proposals = [
      mkProposal({ payload: { alignmentFloor: 62 } }),
      mkProposal({ kind: "safe_mode_toggle", payload: {} }),
      mkProposal({ kind: "strategy_override", payload: { strategy: "test" } }),
    ];
    const decisions = evaluateProposals(proposals, mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG });
    expect(decisions).toHaveLength(3);
    expect(decisions[0].autoApprove).toBe(true);
    expect(decisions[1].autoApprove).toBe(false);
    expect(decisions[2].autoApprove).toBe(false);
  });
});

// ── Decision History ────────────────────────────────────────────────

describe("Decision history", () => {
  test("tracks recent decisions", () => {
    updateApprovalGateConfig({ cooldownMs: 0 });
    shouldAutoApprove(mkProposal(), mkEvaluation(), safeModeOff);
    shouldAutoApprove(mkProposal(), mkEvaluation(), safeModeOff);
    const decisions = getRecentApprovalDecisions();
    expect(decisions.length).toBe(2);
  });

  test("decision history is bounded", () => {
    updateApprovalGateConfig({ cooldownMs: 0 });
    for (let i = 0; i < 60; i++) {
      shouldAutoApprove(mkProposal(), mkEvaluation(), safeModeOff);
    }
    const decisions = getRecentApprovalDecisions();
    expect(decisions.length).toBeLessThanOrEqual(50);
  });

  test("reset clears history", () => {
    shouldAutoApprove(mkProposal(), mkEvaluation(), safeModeOff);
    resetApprovalGate();
    expect(getRecentApprovalDecisions().length).toBe(0);
  });
});

// ── tickKernel Integration ──────────────────────────────────────────

describe("tickKernel integration", () => {
  test("tick without proposals returns empty approvals", () => {
    const result = tickKernel(mkContext());
    expect(result.approvals).toEqual([]);
  });

  test("tick with proposals evaluates them", () => {
    updateApprovalGateConfig({ cooldownMs: 0 });
    const proposals = [
      mkProposal({ payload: { sovereigntyWeight: 0.41 } }),
    ];
    const result = tickKernel(
      mkContext(), { ...DEFAULT_KERNEL_CONFIG }, undefined,
      proposals, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(result.approvals.length).toBe(1);
    expect(result.approvals[0].derivedImpact).toBeDefined();
    expect(typeof result.approvals[0].autoApprove).toBe("boolean");
  });

  test("telemetry snapshot includes recent approvals", () => {
    updateApprovalGateConfig({ cooldownMs: 0 });
    shouldAutoApprove(mkProposal(), mkEvaluation(), safeModeOff);
    tickKernel(mkContext());
    const snap = kernelTelemetry.getSnapshot();
    expect(snap.recentApprovals.length).toBeGreaterThan(0);
  });
});

// ── Multi-axis rejection scenarios ──────────────────────────────────

describe("Multi-axis rejection", () => {
  test("all axes fail simultaneously", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "safe_mode_toggle", payload: {} }),
      mkEvaluation({ alignment: 40, confidence: 30 }),
      safeModeOn,
    );
    expect(d.autoApprove).toBe(false);
    expect(d.reasons.alignmentOK).toBe(false);
    expect(d.reasons.confidenceOK).toBe(false);
    expect(d.reasons.impactOK).toBe(false);
    expect(d.reasons.invariantsOK).toBe(false);
    expect(d.reasons.safeModeOK).toBe(false);
  });

  test("single failing axis blocks approval", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "strategy_override" }),
      mkEvaluation({ alignment: 98, confidence: 95 }),
      safeModeOff,
    );
    expect(d.autoApprove).toBe(false);
    expect(d.reasons.impactOK).toBe(false);
    expect(d.reasons.alignmentOK).toBe(true);
    expect(d.reasons.confidenceOK).toBe(true);
  });
});

// ── Edge Cases ──────────────────────────────────────────────────────

describe("Edge cases", () => {
  test("empty payload → low impact for alignment_config", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "alignment_config", payload: {} }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.derivedImpact).toBe("low");
  });

  test("proposal with no matching weight keys → low impact", () => {
    const d = shouldAutoApprove(
      mkProposal({ kind: "alignment_config", payload: { randomField: 42 } }),
      mkEvaluation(), safeModeOff, { ...DEFAULT_ALIGNMENT_CONFIG },
    );
    expect(d.derivedImpact).toBe("low");
  });

  test("decision includes correct alignment and confidence from evaluation", () => {
    const d = shouldAutoApprove(
      mkProposal(), mkEvaluation({ alignment: 88, confidence: 72 }), safeModeOff,
    );
    expect(d.alignment).toBe(88);
    expect(d.confidence).toBe(72);
  });

  test("decidedAt is a valid timestamp", () => {
    const before = Date.now();
    const d = shouldAutoApprove(mkProposal(), mkEvaluation(), safeModeOff);
    const after = Date.now();
    expect(d.decidedAt).toBeGreaterThanOrEqual(before);
    expect(d.decidedAt).toBeLessThanOrEqual(after);
  });
});
