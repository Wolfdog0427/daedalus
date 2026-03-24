import {
  blendScenes,
  snapScene,
  easeInOutCubic,
} from "../../shared/daedalus/sceneOrchestrationEngine";
import type { FusionScene } from "../../shared/daedalus/fusion";

function mkScene(overrides: Partial<FusionScene> = {}): FusionScene {
  return {
    sceneName: "idle",
    mode: "resting",
    tone: "neutral",
    posture: "companion",
    glow: 0.3,
    motion: 0.5,
    suppressAmbientPulse: false,
    continuityBadge: null,
    narrativeLine: null,
    ...overrides,
  };
}

describe("easeInOutCubic", () => {
  it("returns 0 at t=0", () => {
    expect(easeInOutCubic(0)).toBe(0);
  });

  it("returns 1 at t=1", () => {
    expect(easeInOutCubic(1)).toBe(1);
  });

  it("returns 0.5 at t=0.5", () => {
    expect(easeInOutCubic(0.5)).toBe(0.5);
  });

  it("is below 0.5 for t < 0.5", () => {
    expect(easeInOutCubic(0.25)).toBeLessThan(0.5);
  });

  it("is above 0.5 for t > 0.5", () => {
    expect(easeInOutCubic(0.75)).toBeGreaterThan(0.5);
  });

  it("is monotonically increasing", () => {
    const steps = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];
    for (let i = 1; i < steps.length; i++) {
      expect(easeInOutCubic(steps[i])).toBeGreaterThanOrEqual(
        easeInOutCubic(steps[i - 1]),
      );
    }
  });
});

describe("blendScenes", () => {
  const from = mkScene({ glow: 0.2, motion: 0.3, tone: "neutral", mode: "resting", posture: "companion" });
  const to = mkScene({
    sceneName: "focus",
    glow: 0.8,
    motion: 0.9,
    tone: "focused",
    mode: "attentive",
    posture: "sentinel",
    narrativeLine: "Attention is aligned.",
    continuityBadge: { kind: "threshold", label: "5 sessions" },
    suppressAmbientPulse: true,
  });

  describe("at progress 0", () => {
    const result = blendScenes(from, to, 0, 500, false);

    it("uses from glow and motion", () => {
      expect(result.glow).toBeCloseTo(0.2);
      expect(result.motion).toBeCloseTo(0.3);
    });

    it("uses from discrete values", () => {
      expect(result.tone).toBe("neutral");
      expect(result.mode).toBe("resting");
      expect(result.posture).toBe("companion");
      expect(result.suppressAmbientPulse).toBe(false);
      expect(result.continuityBadge).toBeNull();
    });

    it("uses from narrative line (no narrativeSync)", () => {
      expect(result.narrativeLine).toBeNull();
    });

    it("uses target sceneName", () => {
      expect(result.sceneName).toBe("focus");
    });

    it("sets progress to 0", () => {
      expect(result.progress).toBe(0);
    });
  });

  describe("at progress 1", () => {
    const result = blendScenes(from, to, 1, 500, false);

    it("uses to glow and motion", () => {
      expect(result.glow).toBeCloseTo(0.8);
      expect(result.motion).toBeCloseTo(0.9);
    });

    it("uses to discrete values", () => {
      expect(result.tone).toBe("focused");
      expect(result.mode).toBe("attentive");
      expect(result.posture).toBe("sentinel");
      expect(result.suppressAmbientPulse).toBe(true);
      expect(result.continuityBadge).toEqual({ kind: "threshold", label: "5 sessions" });
      expect(result.narrativeLine).toBe("Attention is aligned.");
    });

    it("sets progress to 1", () => {
      expect(result.progress).toBe(1);
    });
  });

  describe("at progress 0.5 (midpoint)", () => {
    const result = blendScenes(from, to, 0.5, 500, false);

    it("interpolates glow and motion", () => {
      expect(result.glow).toBeCloseTo(0.5, 1);
      expect(result.motion).toBeCloseTo(0.6, 1);
    });

    it("snaps discrete values to target at midpoint", () => {
      expect(result.tone).toBe("focused");
      expect(result.mode).toBe("attentive");
      expect(result.posture).toBe("sentinel");
    });
  });

  describe("before midpoint (t = 0.3)", () => {
    const result = blendScenes(from, to, 0.3, 500, false);

    it("keeps from discrete values", () => {
      expect(result.tone).toBe("neutral");
      expect(result.mode).toBe("resting");
      expect(result.posture).toBe("companion");
    });

    it("partially interpolates continuous values", () => {
      expect(result.glow).toBeGreaterThan(0.2);
      expect(result.glow).toBeLessThan(0.8);
    });
  });

  describe("narrative sync", () => {
    it("snaps narrative immediately when narrativeSync is true", () => {
      const result = blendScenes(from, to, 0.01, 500, true);
      expect(result.narrativeLine).toBe("Attention is aligned.");
    });

    it("holds narrative until midpoint when narrativeSync is false", () => {
      const result = blendScenes(from, to, 0.3, 500, false);
      expect(result.narrativeLine).toBeNull();
    });
  });

  describe("clamping", () => {
    it("clamps progress above 1", () => {
      const result = blendScenes(from, to, 1.5, 500, false);
      expect(result.progress).toBe(1);
      expect(result.glow).toBeCloseTo(0.8);
    });

    it("clamps progress below 0", () => {
      const result = blendScenes(from, to, -0.5, 500, false);
      expect(result.progress).toBe(0);
      expect(result.glow).toBeCloseTo(0.2);
    });

    it("clamps glow and motion to [0, 1]", () => {
      const high = mkScene({ glow: 0.95, motion: 0.95 });
      const higher = mkScene({ sceneName: "apex", glow: 1.2 as any, motion: 1.3 as any });
      const result = blendScenes(high, higher, 1, 500, false);
      expect(result.glow).toBeLessThanOrEqual(1);
      expect(result.motion).toBeLessThanOrEqual(1);
    });
  });

  describe("blendMs passthrough", () => {
    it("includes blendMs in the output", () => {
      const result = blendScenes(from, to, 0.5, 600, false);
      expect(result.blendMs).toBe(600);
    });
  });
});

describe("snapScene", () => {
  it("wraps a FusionScene with progress=1 and blendMs=0", () => {
    const fs = mkScene();
    const result = snapScene(fs);
    expect(result.progress).toBe(1);
    expect(result.blendMs).toBe(0);
    expect(result.sceneName).toBe(fs.sceneName);
    expect(result.glow).toBe(fs.glow);
  });

  it("accepts a custom blendMs", () => {
    const result = snapScene(mkScene(), 400);
    expect(result.blendMs).toBe(400);
  });
});
