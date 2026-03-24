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
    continuity: { streak: 1, lastCheckIn: new Date().toISOString(), healthy: true },
    autopilot: { enabled: false, scope: "none" },
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe("computeBehavioralField", () => {
  it("returns empty field for no beings", () => {
    const field = computeBehavioralField({});
    expect(field.signals).toHaveLength(0);
    expect(field.dominantBeingId).toBeNull();
  });

  it("computes signals for a single being", () => {
    const field = computeBehavioralField({
      a: makeBeing({ id: "a", influenceLevel: 1 }),
    });

    expect(field.signals).toHaveLength(1);
    expect(field.dominantBeingId).toBe("a");
    expect(field.signals[0].influenceWeight).toBe(1);
  });

  it("selects dominant being by highest influence weight", () => {
    const field = computeBehavioralField({
      low: makeBeing({ id: "low", influenceLevel: 0.2 }),
      high: makeBeing({ id: "high", influenceLevel: 0.8 }),
    });

    expect(field.dominantBeingId).toBe("high");
    expect(field.signals).toHaveLength(2);
  });

  it("normalizes influence weights to sum to 1", () => {
    const field = computeBehavioralField({
      a: makeBeing({ id: "a", influenceLevel: 3 }),
      b: makeBeing({ id: "b", influenceLevel: 1 }),
    });

    const totalWeight = field.signals.reduce((sum, s) => sum + s.influenceWeight, 0);
    expect(totalWeight).toBeCloseTo(1, 5);
    expect(field.signals.find((s) => s.beingId === "a")!.influenceWeight).toBeCloseTo(0.75, 5);
    expect(field.signals.find((s) => s.beingId === "b")!.influenceWeight).toBeCloseTo(0.25, 5);
  });

  it("derives halo intensity based on presence mode", () => {
    const field = computeBehavioralField({
      dom: makeBeing({ id: "dom", presenceMode: "dominant", influenceLevel: 1 }),
    });
    expect(field.signals[0].haloIntensity).toBeGreaterThanOrEqual(0.7);

    const field2 = computeBehavioralField({
      idle: makeBeing({ id: "idle", presenceMode: "idle", influenceLevel: 1 }),
    });
    expect(field2.signals[0].haloIntensity).toBe(0.1);
  });

  it("sets haloColorShift for speaking beings", () => {
    const field = computeBehavioralField({
      sp: makeBeing({ id: "sp", isSpeaking: true }),
    });
    expect(field.signals[0].haloColorShift).toBe(0.6);
  });

  it("sets haloColorShift for guiding beings", () => {
    const field = computeBehavioralField({
      gu: makeBeing({ id: "gu", isGuiding: true }),
    });
    expect(field.signals[0].haloColorShift).toBe(0.3);
  });

  it("assigns avatarMicroMotion based on state", () => {
    const speaking = computeBehavioralField({
      s: makeBeing({ id: "s", isSpeaking: true }),
    });
    expect(speaking.signals[0].avatarMicroMotion).toBe("pulse");

    const guiding = computeBehavioralField({
      g: makeBeing({ id: "g", isGuiding: true }),
    });
    expect(guiding.signals[0].avatarMicroMotion).toBe("lean");

    const active = computeBehavioralField({
      a: makeBeing({ id: "a", presenceMode: "active" }),
    });
    expect(active.signals[0].avatarMicroMotion).toBe("tilt");

    const idle = computeBehavioralField({
      i: makeBeing({ id: "i", presenceMode: "idle" }),
    });
    expect(idle.signals[0].avatarMicroMotion).toBe("none");
  });

  it("assigns guidanceCue based on state", () => {
    const guiding = computeBehavioralField({
      g: makeBeing({ id: "g", isGuiding: true }),
    });
    expect(guiding.signals[0].guidanceCue).toBe("strong");

    const speaking = computeBehavioralField({
      s: makeBeing({ id: "s", isSpeaking: true }),
    });
    expect(speaking.signals[0].guidanceCue).toBe("subtle");

    const neither = computeBehavioralField({
      n: makeBeing({ id: "n" }),
    });
    expect(neither.signals[0].guidanceCue).toBe("none");
  });

  it("handles equal influence levels", () => {
    const field = computeBehavioralField({
      a: makeBeing({ id: "a", influenceLevel: 0.5 }),
      b: makeBeing({ id: "b", influenceLevel: 0.5 }),
    });

    expect(field.dominantBeingId).toBeDefined();
    expect(field.signals.every((s) => s.influenceWeight === 0.5)).toBe(true);
  });
});
