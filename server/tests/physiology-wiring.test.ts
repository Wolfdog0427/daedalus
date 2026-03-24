import { computeExpressiveField, EXPRESSIVE_DEFAULTS } from "../../shared/daedalus/expressiveFieldEngine";
import type { BeingPresenceDetail, BehavioralField, BehavioralSignal } from "../../shared/daedalus/contracts";

function makeBeing(overrides: Partial<BeingPresenceDetail> = {}): BeingPresenceDetail {
  return {
    id: "a",
    name: "A",
    posture: "companion",
    glow: { level: "medium", intensity: 0.7 },
    attention: { level: "focused" },
    heartbeat: 1,
    influenceLevel: 1,
    presenceMode: "active",
    isSpeaking: false,
    isGuiding: false,
    continuity: { streak: 5, lastCheckIn: new Date().toISOString(), healthy: true },
    autopilot: { enabled: false, scope: "none" },
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

function makeSignal(overrides: Partial<BehavioralSignal> = {}): BehavioralSignal {
  return {
    beingId: "a",
    haloIntensity: 0.8,
    haloColorShift: 0.4,
    avatarMicroMotion: "pulse",
    guidanceCue: "strong",
    influenceWeight: 1,
    updatedAt: Date.now(),
    ...overrides,
  };
}

function makeBehavioral(signals: BehavioralSignal[], dominantBeingId: string | null = "a"): BehavioralField {
  return { signals, dominantBeingId, updatedAt: Date.now() };
}

describe("physiology wiring", () => {
  it("produces non-zero arousal/focus when behavioral signals exist", () => {
    const being = makeBeing({ isSpeaking: true });
    const field = computeExpressiveField(
      { a: being },
      makeBehavioral([makeSignal()]),
      EXPRESSIVE_DEFAULTS,
    );

    expect(field.arousal).toBeGreaterThan(0.3);
    expect(field.focus).toBeGreaterThan(0.4);
  });

  it("returns defaults when no beings present", () => {
    const field = computeExpressiveField(
      {},
      makeBehavioral([], null),
      EXPRESSIVE_DEFAULTS,
    );

    expect(field.posture).toBe(EXPRESSIVE_DEFAULTS.fallbackPosture);
    expect(field.glow).toEqual(EXPRESSIVE_DEFAULTS.defaultGlow);
    expect(field.arousal).toBe(0);
    expect(field.focus).toBe(0);
    expect(field.stability).toBe(1);
  });

  it("derives posture from dominant being", () => {
    const field = computeExpressiveField(
      { a: makeBeing({ posture: "sentinel" }) },
      makeBehavioral([makeSignal()]),
    );

    expect(field.posture).toBe("sentinel");
  });

  it("derives stability from continuity health", () => {
    const healthy = makeBeing({ id: "h", continuity: { streak: 3, lastCheckIn: new Date().toISOString(), healthy: true } });
    const unhealthy = makeBeing({ id: "u", continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: false } });
    const field = computeExpressiveField(
      { h: healthy, u: unhealthy },
      makeBehavioral([
        makeSignal({ beingId: "h", influenceWeight: 0.5 }),
        makeSignal({ beingId: "u", influenceWeight: 0.5 }),
      ], "h"),
    );

    expect(field.stability).toBe(0.5);
  });

  it("passes behavioral field through unchanged", () => {
    const behavioral = makeBehavioral([makeSignal()]);
    const field = computeExpressiveField(
      { a: makeBeing() },
      behavioral,
    );

    expect(field.behavioral).toBe(behavioral);
  });
});
