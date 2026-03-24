import { computeFusionScene } from "../../shared/daedalus/fusionEngine";
import type { FusionInputs } from "../../shared/daedalus/fusionEngine";
import { CONDUCTOR_DEFAULTS } from "../../shared/daedalus/conductor";

function makeInputs(overrides: Partial<FusionInputs> = {}): FusionInputs {
  return {
    conductor: { ...CONDUCTOR_DEFAULTS, updatedAt: Date.now() },
    narrative: { line: null, tone: "neutral" },
    timelinePhase: "idle",
    affect: "settled",
    ...overrides,
  };
}

describe("computeFusionScene", () => {
  // ── Scene naming: timeline takes priority ──

  it("names scene 'apex' when timeline phase is peak", () => {
    const scene = computeFusionScene(makeInputs({ timelinePhase: "peak" }));
    expect(scene.sceneName).toBe("apex");
  });

  it("names scene 'rising' when timeline phase is rising", () => {
    const scene = computeFusionScene(makeInputs({ timelinePhase: "rising" }));
    expect(scene.sceneName).toBe("rising");
  });

  it("names scene 'waning' when timeline phase is cooldown", () => {
    const scene = computeFusionScene(makeInputs({ timelinePhase: "cooldown" }));
    expect(scene.sceneName).toBe("waning");
  });

  it("names scene 'settling' when timeline phase is settling", () => {
    const scene = computeFusionScene(makeInputs({ timelinePhase: "settling" }));
    expect(scene.sceneName).toBe("settling");
  });

  // ── Scene naming: conductor mode ──

  it("names scene 'alert' when conductor mode is escalated", () => {
    const scene = computeFusionScene(makeInputs({
      conductor: { ...CONDUCTOR_DEFAULTS, mode: "escalated", updatedAt: Date.now() },
    }));
    expect(scene.sceneName).toBe("alert");
  });

  it("names scene 'celebrating' when conductor mode is celebrating", () => {
    const scene = computeFusionScene(makeInputs({
      conductor: { ...CONDUCTOR_DEFAULTS, mode: "celebrating", updatedAt: Date.now() },
    }));
    expect(scene.sceneName).toBe("celebrating");
  });

  // ── Scene naming: affect ──

  it("names scene 'focus' when affect is focused", () => {
    const scene = computeFusionScene(makeInputs({ affect: "focused" }));
    expect(scene.sceneName).toBe("focus");
  });

  it("names scene 'exploring' when affect is exploratory", () => {
    const scene = computeFusionScene(makeInputs({ affect: "exploratory" }));
    expect(scene.sceneName).toBe("exploring");
  });

  // ── Scene naming: fallback ──

  it("names scene 'idle' when no condition matches", () => {
    const scene = computeFusionScene(makeInputs());
    expect(scene.sceneName).toBe("idle");
  });

  // ── Scene naming: priority ──

  it("timeline phase takes priority over conductor mode", () => {
    const scene = computeFusionScene(makeInputs({
      timelinePhase: "peak",
      conductor: { ...CONDUCTOR_DEFAULTS, mode: "escalated", updatedAt: Date.now() },
    }));
    expect(scene.sceneName).toBe("apex");
  });

  it("conductor mode takes priority over affect", () => {
    const scene = computeFusionScene(makeInputs({
      conductor: { ...CONDUCTOR_DEFAULTS, mode: "escalated", updatedAt: Date.now() },
      affect: "focused",
    }));
    expect(scene.sceneName).toBe("alert");
  });

  // ── Tone resolution ──

  it("uses narrative tone when narrative line is present", () => {
    const scene = computeFusionScene(makeInputs({
      conductor: { ...CONDUCTOR_DEFAULTS, tone: "neutral", updatedAt: Date.now() },
      narrative: { line: "The field is gathering.", tone: "focused" },
    }));
    expect(scene.tone).toBe("focused");
  });

  it("uses conductor tone when narrative line is null", () => {
    const scene = computeFusionScene(makeInputs({
      conductor: { ...CONDUCTOR_DEFAULTS, tone: "alert", updatedAt: Date.now() },
      narrative: { line: null, tone: "neutral" },
    }));
    expect(scene.tone).toBe("alert");
  });

  // ── Field passthrough ──

  it("passes through conductor glow and motion", () => {
    const scene = computeFusionScene(makeInputs({
      conductor: { ...CONDUCTOR_DEFAULTS, glowIntensity: 0.77, motionIntensity: 0.33, updatedAt: Date.now() },
    }));
    expect(scene.glow).toBe(0.77);
    expect(scene.motion).toBe(0.33);
  });

  it("passes through conductor posture", () => {
    const scene = computeFusionScene(makeInputs({
      conductor: { ...CONDUCTOR_DEFAULTS, posture: "sentinel", updatedAt: Date.now() },
    }));
    expect(scene.posture).toBe("sentinel");
  });

  it("passes through continuity badge", () => {
    const scene = computeFusionScene(makeInputs({
      conductor: {
        ...CONDUCTOR_DEFAULTS,
        continuityBadge: { kind: "threshold", label: "10 check-ins" },
        updatedAt: Date.now(),
      },
    }));
    expect(scene.continuityBadge).toEqual({ kind: "threshold", label: "10 check-ins" });
  });

  it("passes through narrative line", () => {
    const scene = computeFusionScene(makeInputs({
      narrative: { line: "A threshold is guarded.", tone: "alert" },
    }));
    expect(scene.narrativeLine).toBe("A threshold is guarded.");
  });

  it("passes through suppressAmbientPulse", () => {
    const scene = computeFusionScene(makeInputs({
      conductor: { ...CONDUCTOR_DEFAULTS, suppressAmbientPulse: true, updatedAt: Date.now() },
    }));
    expect(scene.suppressAmbientPulse).toBe(true);
  });
});
