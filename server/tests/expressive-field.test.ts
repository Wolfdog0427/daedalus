import { computeExpressiveField, EXPRESSIVE_DEFAULTS } from "../../shared/daedalus/expressiveFieldEngine";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import type { BeingPresenceDetail } from "../../shared/daedalus/contracts";

function makeBeing(overrides: Partial<BeingPresenceDetail> & { id: string }): BeingPresenceDetail {
  return {
    name: overrides.id,
    posture: "companion",
    glow: { level: "medium", intensity: 0.5 },
    attention: { level: "aware" },
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

describe("computeExpressiveField", () => {
  it("returns defaults when no beings exist", () => {
    const behavioral = computeBehavioralField({});
    const field = computeExpressiveField({}, behavioral);

    expect(field.posture).toBe(EXPRESSIVE_DEFAULTS.fallbackPosture);
    expect(field.glow).toEqual(EXPRESSIVE_DEFAULTS.defaultGlow);
    expect(field.attention).toEqual(EXPRESSIVE_DEFAULTS.defaultAttention);
    expect(field.arousal).toBe(0);
    expect(field.focus).toBe(0);
    expect(field.stability).toBe(1);
  });

  it("derives posture from dominant being", () => {
    const beings = {
      a: makeBeing({ id: "a", influenceLevel: 0.2, posture: "observer" }),
      b: makeBeing({ id: "b", influenceLevel: 0.8, posture: "sentinel" }),
    };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.posture).toBe("sentinel");
  });

  it("derives glow from dominant being", () => {
    const beings = {
      a: makeBeing({ id: "a", influenceLevel: 1, glow: { level: "high", intensity: 0.9 } }),
    };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.glow.level).toBe("high");
    expect(field.glow.intensity).toBe(0.9);
  });

  it("derives attention from dominant being", () => {
    const beings = {
      a: makeBeing({ id: "a", influenceLevel: 1, attention: { level: "locked", targetNodeId: "n1" } }),
    };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.attention.level).toBe("locked");
    expect(field.attention.targetNodeId).toBe("n1");
  });

  it("selects continuity with highest streak", () => {
    const beings = {
      a: makeBeing({ id: "a", continuity: { streak: 3, lastCheckIn: new Date().toISOString(), healthy: true } }),
      b: makeBeing({ id: "b", continuity: { streak: 12, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.continuity.streak).toBe(12);
  });

  it("computes arousal > 0.6 when dominant being is speaking", () => {
    const beings = {
      a: makeBeing({ id: "a", influenceLevel: 1, isSpeaking: true }),
    };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.arousal).toBeGreaterThanOrEqual(0.6);
  });

  it("computes arousal at 0.3 base for non-speaking active beings", () => {
    const beings = {
      a: makeBeing({ id: "a", influenceLevel: 1, presenceMode: "active" }),
    };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.arousal).toBeGreaterThanOrEqual(0.3);
    expect(field.arousal).toBeLessThan(1);
  });

  it("computes focus based on dominant influence weight", () => {
    const beings = {
      a: makeBeing({ id: "a", influenceLevel: 3 }),
      b: makeBeing({ id: "b", influenceLevel: 1 }),
    };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.focus).toBeGreaterThan(0.5);
    expect(field.focus).toBeLessThanOrEqual(1);
  });

  it("computes stability = 1 when all beings are healthy", () => {
    const beings = {
      a: makeBeing({ id: "a", continuity: { streak: 5, lastCheckIn: new Date().toISOString(), healthy: true } }),
      b: makeBeing({ id: "b", continuity: { streak: 3, lastCheckIn: new Date().toISOString(), healthy: true } }),
    };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.stability).toBe(1);
  });

  it("computes stability = 0.5 when half of beings are unhealthy", () => {
    const beings = {
      a: makeBeing({ id: "a", continuity: { streak: 5, lastCheckIn: new Date().toISOString(), healthy: true } }),
      b: makeBeing({ id: "b", continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: false } }),
    };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.stability).toBe(0.5);
  });

  it("computes stability = 0 when all beings are unhealthy", () => {
    const beings = {
      a: makeBeing({ id: "a", continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: false } }),
    };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.stability).toBe(0);
  });

  it("includes behavioral field in output", () => {
    const beings = { a: makeBeing({ id: "a" }) };
    const behavioral = computeBehavioralField(beings);
    const field = computeExpressiveField(beings, behavioral);

    expect(field.behavioral).toBe(behavioral);
    expect(field.behavioral.signals).toHaveLength(1);
    expect(field.behavioral.dominantBeingId).toBe("a");
  });

  it("accepts custom defaults", () => {
    const behavioral = computeBehavioralField({});
    const field = computeExpressiveField({}, behavioral, {
      fallbackPosture: "dormant",
      defaultGlow: { level: "none", intensity: 0 },
      defaultAttention: { level: "unfocused" },
      defaultContinuity: { streak: 0, lastCheckIn: "", healthy: false },
    });

    expect(field.posture).toBe("dormant");
    expect(field.glow.intensity).toBe(0);
  });
});
