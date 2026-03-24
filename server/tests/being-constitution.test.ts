/**
 * Phase 7 — Being Constitution Validation
 *
 * Validates: all 10 constitutional laws, boundary conditions,
 * and that the seeded store passes the constitution.
 */

import {
  validateBeingConstitution,
  BEING_CONSTITUTION_VERSION,
  MAX_BEINGS,
  MAX_INFLUENCE_LEVEL,
  MIN_INFLUENCE_LEVEL,
  ANCHOR_STREAK_MINIMUM,
} from "../../shared/daedalus/beingConstitution";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import type { BeingPresenceDetail, BeingVote } from "../../shared/daedalus/contracts";

function mkBeing(id: string, overrides: Partial<BeingPresenceDetail> = {}): BeingPresenceDetail {
  return {
    id,
    name: `Being ${id}`,
    posture: "companion",
    glow: { level: "medium", intensity: 0.5 },
    attention: { level: "aware" },
    heartbeat: Date.now(),
    influenceLevel: 0.5,
    presenceMode: "active",
    isSpeaking: false,
    isGuiding: false,
    continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true },
    autopilot: { enabled: false, scope: "none" },
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

// ─── Constitution Version ────────────────────────────────────────────

describe("Being Constitution version", () => {
  test("version is defined", () => {
    expect(BEING_CONSTITUTION_VERSION).toBe("1.0.0");
  });
});

// ─── Seeded Store Passes Constitution ────────────────────────────────

describe("Seeded store passes being constitution", () => {
  test("all seeded beings pass all 10 laws", () => {
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;

    const behavioral = computeBehavioralField(beingMap);
    const report = validateBeingConstitution(beings, [], behavioral.dominantBeingId);

    expect(report.allPassed).toBe(true);
    expect(report.failedCount).toBe(0);
    expect(report.checks).toHaveLength(10);
  });
});

// ─── Law 1: Valid Posture ────────────────────────────────────────────

describe("Law 1: valid-posture", () => {
  test("passes for valid postures", () => {
    const beings = [mkBeing("op", { posture: "sentinel" }), mkBeing("g1", { posture: "dormant" })];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "valid-posture")!.passed).toBe(true);
  });

  test("fails for invalid posture", () => {
    const beings = [mkBeing("op", { posture: "invalid" as any })];
    const report = validateBeingConstitution(beings);
    const check = report.checks.find(c => c.name === "valid-posture")!;
    expect(check.passed).toBe(false);
    expect(check.detail).toContain("invalid");
  });
});

// ─── Law 2: Valid Presence Mode ──────────────────────────────────────

describe("Law 2: valid-presence-mode", () => {
  test("passes for valid modes", () => {
    const beings = [mkBeing("op", { presenceMode: "dominant" })];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "valid-presence-mode")!.passed).toBe(true);
  });

  test("fails for invalid mode", () => {
    const beings = [mkBeing("op", { presenceMode: "flying" as any })];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "valid-presence-mode")!.passed).toBe(false);
  });
});

// ─── Law 3: Valid Attention Level ────────────────────────────────────

describe("Law 3: valid-attention-level", () => {
  test("passes for valid levels", () => {
    const beings = [mkBeing("op", { attention: { level: "locked" } })];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "valid-attention-level")!.passed).toBe(true);
  });

  test("fails for invalid level", () => {
    const beings = [mkBeing("op", { attention: { level: "hyperfocused" as any } })];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "valid-attention-level")!.passed).toBe(false);
  });
});

// ─── Law 4: Bounded Influence ────────────────────────────────────────

describe("Law 4: bounded-influence", () => {
  test("passes for influence in [0, 1]", () => {
    const beings = [mkBeing("op", { influenceLevel: 0.5 })];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "bounded-influence")!.passed).toBe(true);
  });

  test("fails for influence > 1", () => {
    const beings = [mkBeing("op", { influenceLevel: 1.5 })];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "bounded-influence")!.passed).toBe(false);
  });

  test("fails for influence < 0", () => {
    const beings = [mkBeing("op", { influenceLevel: -0.1 })];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "bounded-influence")!.passed).toBe(false);
  });

  test("boundary values pass", () => {
    const beings = [
      mkBeing("op", { influenceLevel: MIN_INFLUENCE_LEVEL }),
      mkBeing("g1", { influenceLevel: MAX_INFLUENCE_LEVEL }),
    ];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "bounded-influence")!.passed).toBe(true);
  });
});

// ─── Law 6: Anchor Exists ────────────────────────────────────────────

describe("Law 6: anchor-exists", () => {
  test("passes when best streak >= ANCHOR_STREAK_MINIMUM", () => {
    const beings = [mkBeing("op", { continuity: { streak: ANCHOR_STREAK_MINIMUM, lastCheckIn: new Date().toISOString(), healthy: true } })];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "anchor-exists")!.passed).toBe(true);
  });

  test("passes for sole being even with low streak", () => {
    const beings = [mkBeing("op", { continuity: { streak: 1, lastCheckIn: new Date().toISOString(), healthy: true } })];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "anchor-exists")!.passed).toBe(true);
  });

  test("fails when no beings", () => {
    const report = validateBeingConstitution([]);
    expect(report.checks.find(c => c.name === "anchor-exists")!.passed).toBe(false);
  });

  test("fails when best streak < minimum with multiple beings", () => {
    const beings = [
      mkBeing("op", { continuity: { streak: 1, lastCheckIn: new Date().toISOString(), healthy: true } }),
      mkBeing("g1", { continuity: { streak: 2, lastCheckIn: new Date().toISOString(), healthy: true } }),
    ];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "anchor-exists")!.passed).toBe(false);
  });
});

// ─── Law 7: Single Vote Per Being ────────────────────────────────────

describe("Law 7: single-vote-per-being", () => {
  test("passes with unique votes", () => {
    const votes: BeingVote[] = [
      { being: { id: "op", role: "OPERATOR", label: "Op" }, vote: "ALLOW", weight: 0.5 },
      { being: { id: "g1", role: "GUARDIAN", label: "G1" }, vote: "DENY", weight: 0.5 },
    ];
    const report = validateBeingConstitution([mkBeing("op"), mkBeing("g1")], votes);
    expect(report.checks.find(c => c.name === "single-vote-per-being")!.passed).toBe(true);
  });

  test("fails with duplicate votes from same being", () => {
    const votes: BeingVote[] = [
      { being: { id: "op", role: "OPERATOR", label: "Op" }, vote: "ALLOW", weight: 0.5 },
      { being: { id: "op", role: "OPERATOR", label: "Op" }, vote: "DENY", weight: 0.5 },
    ];
    const report = validateBeingConstitution([mkBeing("op")], votes);
    expect(report.checks.find(c => c.name === "single-vote-per-being")!.passed).toBe(false);
  });
});

// ─── Law 8: Vote Weight Bounded ──────────────────────────────────────

describe("Law 8: vote-weight-bounded", () => {
  test("passes for weight in [0, 1]", () => {
    const votes: BeingVote[] = [
      { being: { id: "op", role: "OPERATOR", label: "Op" }, vote: "ALLOW", weight: 0.7 },
    ];
    const report = validateBeingConstitution([mkBeing("op")], votes);
    expect(report.checks.find(c => c.name === "vote-weight-bounded")!.passed).toBe(true);
  });

  test("fails for weight > 1", () => {
    const votes: BeingVote[] = [
      { being: { id: "op", role: "OPERATOR", label: "Op" }, vote: "ALLOW", weight: 1.5 },
    ];
    const report = validateBeingConstitution([mkBeing("op")], votes);
    expect(report.checks.find(c => c.name === "vote-weight-bounded")!.passed).toBe(false);
  });
});

// ─── Law 9: Dominant Is Present ──────────────────────────────────────

describe("Law 9: dominant-is-present", () => {
  test("passes when dominant being is in list", () => {
    const beings = [mkBeing("op"), mkBeing("g1")];
    const report = validateBeingConstitution(beings, [], "op");
    expect(report.checks.find(c => c.name === "dominant-is-present")!.passed).toBe(true);
  });

  test("fails when dominant being is missing", () => {
    const beings = [mkBeing("op")];
    const report = validateBeingConstitution(beings, [], "phantom");
    expect(report.checks.find(c => c.name === "dominant-is-present")!.passed).toBe(false);
  });

  test("passes when no dominant and no beings", () => {
    const report = validateBeingConstitution([], [], null);
    const check = report.checks.find(c => c.name === "dominant-is-present")!;
    expect(check.passed).toBe(true);
  });
});

// ─── Law 10: Operator Always Present ─────────────────────────────────

describe("Law 10: operator-always-present", () => {
  test("passes when operator exists", () => {
    const beings = [mkBeing("operator"), mkBeing("g1")];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "operator-always-present")!.passed).toBe(true);
  });

  test("fails when operator is missing", () => {
    const beings = [mkBeing("g1"), mkBeing("s1")];
    const report = validateBeingConstitution(beings);
    expect(report.checks.find(c => c.name === "operator-always-present")!.passed).toBe(false);
  });
});

// ─── Full Report Structure ───────────────────────────────────────────

describe("Constitution report structure", () => {
  test("report has exactly 10 checks", () => {
    const report = validateBeingConstitution([mkBeing("operator")]);
    expect(report.checks).toHaveLength(10);
  });

  test("allPassed is true when all pass", () => {
    const report = validateBeingConstitution([mkBeing("operator", { continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true } })]);
    expect(report.allPassed).toBe(true);
  });

  test("allPassed is false when any fails", () => {
    const report = validateBeingConstitution([mkBeing("not-operator")]);
    expect(report.allPassed).toBe(false);
    expect(report.failedCount).toBeGreaterThan(0);
  });

  test("failedCount matches actual failed checks", () => {
    const report = validateBeingConstitution([mkBeing("not-operator", { posture: "bad" as any, influenceLevel: 5 })]);
    const actualFailed = report.checks.filter(c => !c.passed).length;
    expect(report.failedCount).toBe(actualFailed);
  });
});
