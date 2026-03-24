import { computeHealth, buildDashboard } from "../../shared/daedalus/governanceFabricEngine";
import type { AutonomyDecision } from "../../shared/daedalus/sceneAutonomy";
import type { GovernanceFabricSnapshot } from "../../shared/daedalus/postAutonomy";
import { FABRIC_CONFIG_DEFAULTS } from "../../shared/daedalus/governanceFabric";

const NOW = 300_000;
const WIN = FABRIC_CONFIG_DEFAULTS.windowMs;

function mkDecision(approved: boolean, ageMs: number = 0): AutonomyDecision {
  return { proposalId: Math.random(), approved, timestamp: NOW - ageMs };
}

function mkFabric(overrides: Partial<GovernanceFabricSnapshot> = {}): GovernanceFabricSnapshot {
  return {
    activeTierCount: 0,
    activeTiers: [],
    escalationDetected: false,
    cappingApplied: false,
    effectiveTuning: {},
    ...overrides,
  };
}

// ── computeHealth ──────────────────────────────────────────────

describe("computeHealth", () => {
  it("returns stable with zero decisions", () => {
    const h = computeHealth([], FABRIC_CONFIG_DEFAULTS, NOW);
    expect(h.label).toBe("stable");
    expect(h.totalDecisions).toBe(0);
    expect(h.approvals).toBe(0);
    expect(h.rejections).toBe(0);
    expect(h.decisionRate).toBe(0);
  });

  it("returns active with a few decisions", () => {
    const decisions = [mkDecision(true), mkDecision(false)];
    const h = computeHealth(decisions, FABRIC_CONFIG_DEFAULTS, NOW);
    expect(h.label).toBe("active");
    expect(h.totalDecisions).toBe(2);
    expect(h.approvals).toBe(1);
    expect(h.rejections).toBe(1);
  });

  it("returns busy when decision rate exceeds busyThreshold", () => {
    const count = Math.ceil(FABRIC_CONFIG_DEFAULTS.busyThreshold * (WIN / 60_000));
    const decisions = Array.from({ length: count }, () => mkDecision(true));
    const h = computeHealth(decisions, FABRIC_CONFIG_DEFAULTS, NOW);
    expect(h.label).toBe("busy");
  });

  it("returns overloaded when decision rate exceeds overloadedThreshold", () => {
    const count = Math.ceil(FABRIC_CONFIG_DEFAULTS.overloadedThreshold * (WIN / 60_000));
    const decisions = Array.from({ length: count }, () => mkDecision(true));
    const h = computeHealth(decisions, FABRIC_CONFIG_DEFAULTS, NOW);
    expect(h.label).toBe("overloaded");
  });

  it("filters out decisions older than the window", () => {
    const decisions = [
      mkDecision(true, 0),
      mkDecision(true, WIN + 1000),
    ];
    const h = computeHealth(decisions, FABRIC_CONFIG_DEFAULTS, NOW);
    expect(h.totalDecisions).toBe(1);
  });

  it("counts approvals and rejections correctly", () => {
    const decisions = [
      mkDecision(true),
      mkDecision(true),
      mkDecision(false),
      mkDecision(true),
      mkDecision(false),
    ];
    const h = computeHealth(decisions, FABRIC_CONFIG_DEFAULTS, NOW);
    expect(h.approvals).toBe(3);
    expect(h.rejections).toBe(2);
  });

  it("computes decisionRate as count / windowMinutes", () => {
    const decisions = [mkDecision(true), mkDecision(false)];
    const h = computeHealth(decisions, FABRIC_CONFIG_DEFAULTS, NOW);
    const expectedRate = 2 / (WIN / 60_000);
    expect(h.decisionRate).toBeCloseTo(expectedRate);
  });

  it("uses custom config thresholds", () => {
    const config = { ...FABRIC_CONFIG_DEFAULTS, busyThreshold: 0.5, overloadedThreshold: 1 };
    const decisions = [mkDecision(true)];
    const h = computeHealth(decisions, config, NOW);
    expect(h.label).toBe("busy");
  });
});

// ── buildDashboard ─────────────────────────────────────────────

describe("buildDashboard", () => {
  it("combines fabric snapshot with health from decisions", () => {
    const fabric = mkFabric({
      activeTierCount: 2,
      activeTiers: ["adaptation", "tier-0"],
      escalationDetected: false,
      cappingApplied: true,
    });
    const decisions = [mkDecision(true), mkDecision(false)];
    const d = buildDashboard(fabric, decisions, 1, FABRIC_CONFIG_DEFAULTS, NOW);
    expect(d.activeTierCount).toBe(2);
    expect(d.activeTiers).toEqual(["adaptation", "tier-0"]);
    expect(d.cappingApplied).toBe(true);
    expect(d.escalationDetected).toBe(false);
    expect(d.pendingCount).toBe(1);
    expect(d.health.totalDecisions).toBe(2);
  });

  it("reports escalation from fabric snapshot", () => {
    const fabric = mkFabric({ escalationDetected: true, activeTierCount: 5 });
    const d = buildDashboard(fabric, [], 0, FABRIC_CONFIG_DEFAULTS, NOW);
    expect(d.escalationDetected).toBe(true);
    expect(d.activeTierCount).toBe(5);
  });

  it("returns idle health when no decisions exist", () => {
    const d = buildDashboard(mkFabric(), [], 0, FABRIC_CONFIG_DEFAULTS, NOW);
    expect(d.health.label).toBe("stable");
    expect(d.health.totalDecisions).toBe(0);
    expect(d.pendingCount).toBe(0);
  });

  it("passes through pending count", () => {
    const d = buildDashboard(mkFabric(), [], 3, FABRIC_CONFIG_DEFAULTS, NOW);
    expect(d.pendingCount).toBe(3);
  });

  it("does not mutate the input activeTiers array", () => {
    const tiers: any = ["tier-0", "tier-3"];
    const fabric = mkFabric({ activeTiers: tiers, activeTierCount: 2 });
    const d = buildDashboard(fabric, [], 0, FABRIC_CONFIG_DEFAULTS, NOW);
    d.activeTiers.push("tier-5" as any);
    expect(tiers).toHaveLength(2);
  });
});
