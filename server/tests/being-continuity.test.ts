/**
 * Phase 3 — Continuity–Being Integration Audit
 *
 * Validates: anchorBeingId, continuity streak → identity score,
 * drift detection & recovery, continuity → glow/posture mapping,
 * and system continuity computation from being inputs.
 */

import type { BeingPresenceDetail } from "../../shared/daedalus/contracts";
import { narrateContinuity, STREAK_THRESHOLDS } from "../../shared/daedalus/continuityNarrator";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import { computeExpressiveField, EXPRESSIVE_DEFAULTS } from "../../shared/daedalus/expressiveFieldEngine";
import {
  computeIdentityContinuity,
  computeSystemContinuity,
  deriveContinuityHealth,
  computeComposite,
} from "../../shared/daedalus/systemContinuityEngine";
import type { SystemContinuityInput } from "../../shared/daedalus/systemContinuityEngine";

function mkBeing(overrides: Partial<BeingPresenceDetail> & { id: string; name: string }): BeingPresenceDetail {
  return {
    posture: "companion",
    glow: { level: "high", intensity: 0.8 },
    attention: { level: "focused" },
    heartbeat: Date.now(),
    influenceLevel: 0.5,
    presenceMode: "active",
    isSpeaking: false,
    isGuiding: false,
    continuity: { streak: 5, lastCheckIn: new Date().toISOString(), healthy: true },
    autopilot: { enabled: false, scope: "none" },
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

function mkInput(overrides: Partial<SystemContinuityInput> = {}): SystemContinuityInput {
  return {
    beingStability: 1,
    beingCount: 2,
    bestStreak: 12,
    driftSignalCount: 0,
    anchorBeingId: "operator",
    orchestrationStability: 0.8,
    continuityBlend: 0.9,
    embodiedContinuity: 0.8,
    motionGrammar: 0.8,
    timelineMomentum: 0.7,
    persistenceRestored: true,
    ...overrides,
  };
}

// ─── anchorBeingId Validation ────────────────────────────────────────

describe("anchorBeingId computation", () => {
  test("anchor is the being with the highest streak (>3, multiple beings)", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", continuity: { streak: 20, lastCheckIn: new Date().toISOString(), healthy: true } }),
      g1: mkBeing({ id: "g1", name: "Guardian", continuity: { streak: 5, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };

    const signals = narrateContinuity(beings);
    const anchor = signals.find(s => s.kind === "anchor");
    expect(anchor).toBeDefined();
    expect(anchor!.beingId).toBe("op");
  });

  test("no anchor signal if only one being", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", continuity: { streak: 50, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };

    const signals = narrateContinuity(beings);
    expect(signals.find(s => s.kind === "anchor")).toBeUndefined();
  });

  test("no anchor signal if max streak <= 3", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", continuity: { streak: 2, lastCheckIn: new Date().toISOString(), healthy: true } }),
      g1: mkBeing({ id: "g1", name: "Guardian", continuity: { streak: 3, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };

    const signals = narrateContinuity(beings);
    expect(signals.find(s => s.kind === "anchor")).toBeUndefined();
  });

  test("anchor includes streak detail in signal", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", continuity: { streak: 25, lastCheckIn: new Date().toISOString(), healthy: true } }),
      g1: mkBeing({ id: "g1", name: "Guardian", continuity: { streak: 4, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };

    const anchor = narrateContinuity(beings).find(s => s.kind === "anchor")!;
    expect(anchor.detail).toContain("25");
  });
});

// ─── Continuity Streak Effects ───────────────────────────────────────

describe("Continuity streak effects", () => {
  test("streak threshold crossings emit threshold signals", () => {
    for (const threshold of STREAK_THRESHOLDS) {
      const beings: Record<string, BeingPresenceDetail> = {
        op: mkBeing({ id: "op", name: "Operator", continuity: { streak: threshold, lastCheckIn: new Date().toISOString(), healthy: true } }),
      };
      const signals = narrateContinuity(beings);
      const thresholdSignal = signals.find(s => s.kind === "threshold");
      expect(thresholdSignal).toBeDefined();
      expect(thresholdSignal!.label).toContain(`${threshold}`);
    }
  });

  test("streak = 1 emits 'newly joined' signal", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", continuity: { streak: 1, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };
    const signals = narrateContinuity(beings);
    expect(signals.find(s => s.kind === "streak" && s.label === "Newly joined")).toBeDefined();
  });

  test("streak = 0 emits 'newly joined' signal", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };
    const signals = narrateContinuity(beings);
    expect(signals.find(s => s.kind === "streak" && s.label === "Newly joined")).toBeDefined();
  });

  test("identity continuity score rises with streak depth", () => {
    const low = computeIdentityContinuity(1, 1, 2);
    const mid = computeIdentityContinuity(1, 1, 12);
    const high = computeIdentityContinuity(1, 1, 25);

    expect(low).toBeLessThan(mid);
    expect(mid).toBeLessThan(high);
    expect(high).toBeCloseTo(1, 1);
  });

  test("identity continuity is 0 when no beings present", () => {
    expect(computeIdentityContinuity(1, 0, 50)).toBe(0);
  });
});

// ─── Drift Detection & Recovery ──────────────────────────────────────

describe("Drift detection and recovery", () => {
  test("drift-recovery signal fires when being goes unhealthy → healthy", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };
    const prevHealthMap: Record<string, boolean> = { op: false };

    const signals = narrateContinuity(beings, prevHealthMap);
    const recovery = signals.find(s => s.kind === "drift-recovery");
    expect(recovery).toBeDefined();
    expect(recovery!.beingId).toBe("op");
    expect(recovery!.label).toBe("Recovered");
  });

  test("no drift-recovery if being was already healthy", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };
    const prevHealthMap: Record<string, boolean> = { op: true };

    const signals = narrateContinuity(beings, prevHealthMap);
    expect(signals.find(s => s.kind === "drift-recovery")).toBeUndefined();
  });

  test("no drift-recovery if no prevHealthMap provided", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };

    const signals = narrateContinuity(beings);
    expect(signals.find(s => s.kind === "drift-recovery")).toBeUndefined();
  });

  test("multiple beings can have independent drift-recovery", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true } }),
      g1: mkBeing({ id: "g1", name: "Guardian", continuity: { streak: 3, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };
    const prevHealthMap: Record<string, boolean> = { op: false, g1: false };

    const signals = narrateContinuity(beings, prevHealthMap);
    const recoveries = signals.filter(s => s.kind === "drift-recovery");
    expect(recoveries).toHaveLength(2);
  });
});

// ─── Continuity → Glow/Posture Mapping ──────────────────────────────

describe("Continuity → glow/posture mapping via expressive field", () => {
  test("dominant being's posture becomes system posture", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", posture: "sentinel", influenceLevel: 0.9 }),
      g1: mkBeing({ id: "g1", name: "Guardian", posture: "dormant", influenceLevel: 0.1 }),
    };

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.posture).toBe("sentinel");
  });

  test("dominant being's glow becomes system glow", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Operator", glow: { level: "high", intensity: 0.95 }, influenceLevel: 0.9 }),
      g1: mkBeing({ id: "g1", name: "Guardian", glow: { level: "low", intensity: 0.1 }, influenceLevel: 0.1 }),
    };

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.glow.level).toBe("high");
    expect(field.glow.intensity).toBeCloseTo(0.95, 1);
  });

  test("stability reflects fraction of healthy beings", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Op", continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true } }),
      g1: mkBeing({ id: "g1", name: "G1", continuity: { streak: 5, lastCheckIn: new Date().toISOString(), healthy: false } }),
    };

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.stability).toBeCloseTo(0.5, 1);
  });

  test("all beings unhealthy → stability = 0", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Op", continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: false } }),
      g1: mkBeing({ id: "g1", name: "G1", continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: false } }),
    };

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.stability).toBe(0);
  });

  test("all beings healthy → stability = 1", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Op", continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true } }),
      g1: mkBeing({ id: "g1", name: "G1", continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.stability).toBe(1);
  });

  test("best continuity streak becomes system continuity", () => {
    const beings: Record<string, BeingPresenceDetail> = {
      op: mkBeing({ id: "op", name: "Op", continuity: { streak: 25, lastCheckIn: new Date().toISOString(), healthy: true } }),
      g1: mkBeing({ id: "g1", name: "G1", continuity: { streak: 3, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };

    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.continuity.streak).toBe(25);
  });

  test("fallback defaults when no beings present", () => {
    const behavioral = computeBehavioralField({});
    const field = computeExpressiveField({}, behavioral);

    expect(field.posture).toBe(EXPRESSIVE_DEFAULTS.fallbackPosture);
    expect(field.glow).toEqual(EXPRESSIVE_DEFAULTS.defaultGlow);
    expect(field.stability).toBe(1);
  });
});

// ─── System Continuity Computation ───────────────────────────────────

describe("System continuity from being inputs", () => {
  test("full health inputs → healthy composite", () => {
    const result = computeSystemContinuity(mkInput());
    expect(result.health).toBe("healthy");
    expect(result.composite).toBeGreaterThan(0.7);
    expect(result.anchorBeingId).toBe("operator");
  });

  test("zero beings → fragile identity continuity", () => {
    const result = computeSystemContinuity(mkInput({ beingCount: 0, beingStability: 0, bestStreak: 0 }));
    expect(result.identity).toBe(0);
  });

  test("drift signals are passed through to snapshot", () => {
    const result = computeSystemContinuity(mkInput({ driftSignalCount: 3 }));
    expect(result.driftSignalCount).toBe(3);
  });

  test("anchorBeingId is passed through to snapshot", () => {
    const result = computeSystemContinuity(mkInput({ anchorBeingId: "guardian-1" }));
    expect(result.anchorBeingId).toBe("guardian-1");
  });

  test("low orchestration stability → shifting health", () => {
    const result = computeSystemContinuity(mkInput({
      orchestrationStability: 0.5,
      continuityBlend: 0.5,
      beingStability: 0.5,
      bestStreak: 10,
      embodiedContinuity: 0.5,
      motionGrammar: 0.5,
      timelineMomentum: 0.5,
      persistenceRestored: false,
    }));
    expect(result.health).toBe("shifting");
    expect(result.composite).toBeGreaterThan(0.4);
    expect(result.composite).toBeLessThanOrEqual(0.7);
  });

  test("all axes at zero → fragile", () => {
    const result = computeSystemContinuity(mkInput({
      beingStability: 0,
      beingCount: 0,
      bestStreak: 0,
      orchestrationStability: 0,
      continuityBlend: 0,
      embodiedContinuity: 0,
      motionGrammar: 0,
      timelineMomentum: 0,
      persistenceRestored: false,
    }));
    expect(result.health).toBe("fragile");
    expect(result.composite).toBe(0);
  });

  test("persistence restored adds temporal continuity bonus", () => {
    const withPersistence = computeSystemContinuity(mkInput({ persistenceRestored: true }));
    const noPersistence = computeSystemContinuity(mkInput({ persistenceRestored: false }));
    expect(withPersistence.temporal).toBeGreaterThan(noPersistence.temporal);
  });

  test("health labels match composite thresholds", () => {
    expect(deriveContinuityHealth(0.8)).toBe("healthy");
    expect(deriveContinuityHealth(0.7)).toBe("shifting");
    expect(deriveContinuityHealth(0.71)).toBe("healthy");
    expect(deriveContinuityHealth(0.5)).toBe("shifting");
    expect(deriveContinuityHealth(0.4)).toBe("fragile");
    expect(deriveContinuityHealth(0.3)).toBe("fragile");
    expect(deriveContinuityHealth(0)).toBe("fragile");
  });
});
