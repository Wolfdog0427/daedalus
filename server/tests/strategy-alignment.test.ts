import {
  computeAlignment,
  computeAlignmentBreakdown,
  evaluateStrategy,
  scoreSovereignty,
  scoreIdentity,
  scoreGovernance,
  scoreStability,
  deriveStrategyName,
  DEFAULT_ALIGNMENT_WEIGHTS,
  type AlignmentContext,
  type AlignmentBreakdown,
} from "../../shared/daedalus/strategyAlignment";
import { createCanonicalOperator, createCanonicalGuardian } from "../../shared/daedalus/beingOntology";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";

function mkContext(overrides: Partial<AlignmentContext> = {}): AlignmentContext {
  const operator = createCanonicalOperator();
  const guardian = createCanonicalGuardian("guardian-1", "Guardian Alpha");
  const beings = overrides.beings ?? [operator, guardian];
  return {
    beings,
    constitutionReport: overrides.constitutionReport ?? validateBeingConstitution(beings, []),
    posture: overrides.posture ?? "OPEN",
    postureReason: overrides.postureReason ?? "Normal",
    overrides: overrides.overrides ?? [],
    drifts: overrides.drifts ?? [],
    votes: overrides.votes ?? [],
    nodeCount: overrides.nodeCount ?? 3,
    quarantinedCount: overrides.quarantinedCount ?? 0,
    totalErrors: overrides.totalErrors ?? 0,
    activeHeartbeats: overrides.activeHeartbeats ?? 3,
  };
}

describe("Strategy Alignment Engine", () => {
  describe("computeAlignment", () => {
    test("all-100 breakdown produces 100", () => {
      const breakdown: AlignmentBreakdown = { sovereignty: 100, identity: 100, governance: 100, stability: 100 };
      expect(computeAlignment(breakdown)).toBe(100);
    });

    test("all-0 breakdown produces 0", () => {
      const breakdown: AlignmentBreakdown = { sovereignty: 0, identity: 0, governance: 0, stability: 0 };
      expect(computeAlignment(breakdown)).toBe(0);
    });

    test("weights are applied correctly", () => {
      const breakdown: AlignmentBreakdown = { sovereignty: 100, identity: 0, governance: 0, stability: 0 };
      expect(computeAlignment(breakdown)).toBe(Math.round(100 * DEFAULT_ALIGNMENT_WEIGHTS.sovereignty));
    });

    test("mixed scores produce weighted average", () => {
      const breakdown: AlignmentBreakdown = { sovereignty: 80, identity: 60, governance: 70, stability: 50 };
      const expected = Math.round(
        80 * 0.4 + 60 * 0.2 + 70 * 0.3 + 50 * 0.1,
      );
      expect(computeAlignment(breakdown)).toBe(expected);
    });
  });

  describe("scoreSovereignty", () => {
    test("healthy operator presence scores high", () => {
      const ctx = mkContext();
      const score = scoreSovereignty(ctx);
      expect(score).toBeGreaterThanOrEqual(60);
    });

    test("no operator present scores low", () => {
      const guardian = createCanonicalGuardian("g1", "Guardian");
      const ctx = mkContext({ beings: [guardian] });
      const score = scoreSovereignty(ctx);
      expect(score).toBeLessThan(30);
    });

    test("LOCKDOWN posture reduces score", () => {
      const ctx = mkContext({ posture: "LOCKDOWN" });
      const lockdownScore = scoreSovereignty(ctx);
      const openScore = scoreSovereignty(mkContext({ posture: "OPEN" }));
      expect(lockdownScore).toBeLessThan(openScore);
    });

    test("global DENY override severely reduces score", () => {
      const ctx = mkContext({
        overrides: [{
          id: "test",
          createdAt: new Date().toISOString(),
          createdBy: { id: "op", role: "OPERATOR", label: "Op" },
          reason: "test",
          scope: "GLOBAL",
          effect: "DENY",
        }],
      });
      const score = scoreSovereignty(ctx);
      const normalScore = scoreSovereignty(mkContext());
      expect(score).toBeLessThan(normalScore);
    });
  });

  describe("scoreIdentity", () => {
    test("healthy beings with passing constitution scores high", () => {
      const ctx = mkContext();
      const score = scoreIdentity(ctx);
      expect(score).toBeGreaterThanOrEqual(70);
    });

    test("no beings scores low", () => {
      const ctx = mkContext({
        beings: [],
        constitutionReport: validateBeingConstitution([], []),
      });
      const score = scoreIdentity(ctx);
      expect(score).toBeLessThanOrEqual(50);
    });
  });

  describe("scoreGovernance", () => {
    test("OPEN posture with no drifts scores high", () => {
      const ctx = mkContext();
      const score = scoreGovernance(ctx);
      expect(score).toBeGreaterThanOrEqual(70);
    });

    test("HIGH drifts reduce score", () => {
      const ctx = mkContext({
        drifts: [
          { id: "d1", detectedAt: new Date().toISOString(), severity: "HIGH", summary: "test" },
          { id: "d2", detectedAt: new Date().toISOString(), severity: "HIGH", summary: "test2" },
        ],
      });
      const score = scoreGovernance(ctx);
      const normalScore = scoreGovernance(mkContext());
      expect(score).toBeLessThan(normalScore);
    });

    test("LOCKDOWN posture scores low", () => {
      const ctx = mkContext({ posture: "LOCKDOWN" });
      const score = scoreGovernance(ctx);
      expect(score).toBeLessThan(50);
    });
  });

  describe("scoreStability", () => {
    test("healthy nodes with heartbeats score high", () => {
      const ctx = mkContext({ nodeCount: 5, quarantinedCount: 0, totalErrors: 0, activeHeartbeats: 5 });
      const score = scoreStability(ctx);
      expect(score).toBeGreaterThanOrEqual(80);
    });

    test("quarantined nodes reduce score", () => {
      const ctx = mkContext({ nodeCount: 5, quarantinedCount: 3 });
      const normalCtx = mkContext({ nodeCount: 5, quarantinedCount: 0 });
      expect(scoreStability(ctx)).toBeLessThan(scoreStability(normalCtx));
    });

    test("high error count reduces score", () => {
      const ctx = mkContext({ totalErrors: 50 });
      const cleanCtx = mkContext({ totalErrors: 0 });
      expect(scoreStability(ctx)).toBeLessThan(scoreStability(cleanCtx));
    });

    test("zero nodes returns baseline score", () => {
      const ctx = mkContext({ nodeCount: 0, quarantinedCount: 0, activeHeartbeats: 0 });
      const score = scoreStability(ctx);
      expect(score).toBeGreaterThan(0);
    });
  });

  describe("deriveStrategyName", () => {
    test("high alignment with strong sovereignty → sovereignty_stable", () => {
      expect(deriveStrategyName(85, { sovereignty: 90, identity: 80, governance: 85, stability: 80 }, "OPEN"))
        .toBe("sovereignty_stable");
    });

    test("moderate alignment with weak governance and GUARDED → governance_attentive", () => {
      expect(deriveStrategyName(65, { sovereignty: 80, identity: 70, governance: 45, stability: 70 }, "GUARDED"))
        .toBe("governance_attentive");
    });

    test("low alignment → alignment_degraded", () => {
      expect(deriveStrategyName(30, { sovereignty: 30, identity: 30, governance: 30, stability: 30 }, "LOCKDOWN"))
        .toBe("alignment_degraded");
    });
  });

  describe("evaluateStrategy (full integration)", () => {
    test("healthy system produces high alignment and sovereignty_stable or nominal", () => {
      const ctx = mkContext();
      const result = evaluateStrategy(ctx);

      expect(result.alignment).toBeGreaterThanOrEqual(50);
      expect(result.confidence).toBeGreaterThan(0);
      expect(result.confidence).toBeLessThanOrEqual(100);
      expect(result.alignmentBreakdown.sovereignty).toBeGreaterThan(0);
      expect(result.alignmentBreakdown.identity).toBeGreaterThan(0);
      expect(result.alignmentBreakdown.governance).toBeGreaterThan(0);
      expect(result.alignmentBreakdown.stability).toBeGreaterThan(0);
      expect(result.weakestAxis).toBeDefined();
      expect(result.strongestAxis).toBeDefined();
      expect(result.notes).toBeTruthy();
      expect(result.evaluatedAt).toBeTruthy();
    });

    test("degraded system produces lower alignment", () => {
      const ctx = mkContext({
        posture: "LOCKDOWN",
        drifts: [{ id: "d1", detectedAt: "", severity: "HIGH", summary: "test" }],
        quarantinedCount: 3,
        totalErrors: 50,
        overrides: [{
          id: "o1",
          createdAt: "",
          createdBy: { id: "x", role: "OPERATOR", label: "x" },
          reason: "x",
          scope: "GLOBAL",
          effect: "DENY",
        }],
      });
      const degraded = evaluateStrategy(ctx);
      const healthy = evaluateStrategy(mkContext());

      expect(degraded.alignment).toBeLessThan(healthy.alignment);
    });

    test("breakdown axes are all 0-100", () => {
      const ctx = mkContext();
      const result = evaluateStrategy(ctx);
      for (const val of Object.values(result.alignmentBreakdown)) {
        expect(val).toBeGreaterThanOrEqual(0);
        expect(val).toBeLessThanOrEqual(100);
      }
    });

    test("strategy name is a valid enum value", () => {
      const validNames = [
        "sovereignty_stable", "sovereignty_contested", "identity_reinforcement",
        "governance_attentive", "governance_undercorrection", "stability_recovery",
        "alignment_nominal", "alignment_degraded",
      ];
      const ctx = mkContext();
      const result = evaluateStrategy(ctx);
      expect(validNames).toContain(result.name);
    });
  });
});

describe("Strategy API Integration", () => {
  const app = require("../orchestrator").createOrchestratorApp();

  test("GET /daedalus/strategy returns valid evaluation", async () => {
    const request = require("supertest");
    const res = await request(app).get("/daedalus/strategy").expect(200);

    expect(res.body).toHaveProperty("name");
    expect(res.body).toHaveProperty("confidence");
    expect(res.body).toHaveProperty("alignment");
    expect(res.body).toHaveProperty("alignmentBreakdown");
    expect(res.body).toHaveProperty("weakestAxis");
    expect(res.body).toHaveProperty("strongestAxis");
    expect(res.body).toHaveProperty("notes");
    expect(res.body).toHaveProperty("evaluatedAt");

    expect(res.body.alignmentBreakdown).toHaveProperty("sovereignty");
    expect(res.body.alignmentBreakdown).toHaveProperty("identity");
    expect(res.body.alignmentBreakdown).toHaveProperty("governance");
    expect(res.body.alignmentBreakdown).toHaveProperty("stability");

    expect(typeof res.body.alignment).toBe("number");
    expect(res.body.alignment).toBeGreaterThanOrEqual(0);
    expect(res.body.alignment).toBeLessThanOrEqual(100);
  });
});
