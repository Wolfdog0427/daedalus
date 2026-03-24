import { computeOrchestrationState } from "../../shared/daedalus/orchestrationEngine";
import { ORCHESTRATION_DEFAULTS } from "../../shared/daedalus/orchestration";
import type { ExpressiveField, BehavioralSignal } from "../../shared/daedalus/contracts";

function makeField(overrides: Partial<ExpressiveField> = {}): ExpressiveField {
  return {
    posture: "companion",
    glow: { level: "low", intensity: 0.3 },
    attention: { level: "unfocused" },
    continuity: { streak: 3, lastCheckIn: new Date().toISOString(), healthy: true },
    behavioral: { signals: [], dominantBeingId: null, updatedAt: 0 },
    arousal: 0,
    focus: 0,
    stability: 1,
    updatedAt: 0,
    ...overrides,
  };
}

function makeSignal(overrides: Partial<BehavioralSignal> = {}): BehavioralSignal {
  return {
    beingId: "a",
    haloIntensity: 0.8,
    haloColorShift: 0,
    avatarMicroMotion: "none",
    guidanceCue: "none",
    influenceWeight: 1,
    updatedAt: 0,
    ...overrides,
  };
}

describe("computeOrchestrationState", () => {
  it("defaults to companion posture and idle intent", () => {
    const state = computeOrchestrationState(makeField());
    expect(state.orchestratedPosture).toBe("companion");
    expect(state.intent).toBe("idle");
  });

  it("shifts to sentinel when arousal > 0.7", () => {
    const state = computeOrchestrationState(makeField({ arousal: 0.9 }));
    expect(state.orchestratedPosture).toBe("sentinel");
  });

  it("shifts to sentinel when stability < 0.3", () => {
    const state = computeOrchestrationState(makeField({ stability: 0.2 }));
    expect(state.orchestratedPosture).toBe("sentinel");
  });

  it("shifts to companion when dominant has strong guidance cue", () => {
    const state = computeOrchestrationState(makeField({
      posture: "observer",
      behavioral: {
        dominantBeingId: "a",
        signals: [makeSignal({ guidanceCue: "strong" })],
        updatedAt: 0,
      },
    }));
    expect(state.orchestratedPosture).toBe("companion");
  });

  it("follows expressive posture otherwise", () => {
    const state = computeOrchestrationState(makeField({ posture: "dormant" }));
    expect(state.orchestratedPosture).toBe("dormant");
  });

  it("intent is guiding when strong guidance cue present", () => {
    const state = computeOrchestrationState(makeField({
      behavioral: {
        dominantBeingId: "a",
        signals: [makeSignal({ guidanceCue: "strong" })],
        updatedAt: 0,
      },
    }));
    expect(state.intent).toBe("guiding");
  });

  it("intent is alert when arousal > 0.7", () => {
    const state = computeOrchestrationState(makeField({ arousal: 0.8 }));
    expect(state.intent).toBe("alert");
  });

  it("intent is supporting when focus > 0.6", () => {
    const state = computeOrchestrationState(makeField({ focus: 0.7 }));
    expect(state.intent).toBe("supporting");
  });

  it("intent is escalating when stability < 0.4 and arousal <= 0.7", () => {
    const state = computeOrchestrationState(makeField({ stability: 0.3, arousal: 0.5 }));
    expect(state.intent).toBe("escalating");
  });

  it("passes affect values through from field", () => {
    const state = computeOrchestrationState(makeField({ arousal: 0.5, focus: 0.6, stability: 0.8 }));
    expect(state.affect).toEqual({ arousal: 0.5, focus: 0.6, stability: 0.8 });
  });

  it("transition postureShift is none when posture unchanged", () => {
    const prev = { ...ORCHESTRATION_DEFAULTS, orchestratedPosture: "companion" as const };
    const state = computeOrchestrationState(makeField({ posture: "companion" }), prev);
    expect(state.transition.postureShift).toBe("none");
  });

  it("transition postureShift is soft when posture changes with low arousal", () => {
    const prev = { ...ORCHESTRATION_DEFAULTS, orchestratedPosture: "companion" as const };
    const state = computeOrchestrationState(makeField({ posture: "dormant", arousal: 0.2 }), prev);
    expect(state.transition.postureShift).toBe("soft");
  });

  it("transition postureShift is hard when posture changes with high arousal", () => {
    const prev = { ...ORCHESTRATION_DEFAULTS, orchestratedPosture: "companion" as const };
    const state = computeOrchestrationState(makeField({ arousal: 0.9 }), prev);
    expect(state.orchestratedPosture).toBe("sentinel");
    expect(state.transition.postureShift).toBe("hard");
  });

  it("continuityBlend reflects stability", () => {
    const state = computeOrchestrationState(makeField({ stability: 0.6 }));
    expect(state.transition.continuityBlend).toBe(0.6);
  });

  it("uses ORCHESTRATION_DEFAULTS as prev when none provided", () => {
    const state = computeOrchestrationState(makeField({ posture: "observer" }));
    expect(state.transition.postureShift).toBe("soft");
  });
});
