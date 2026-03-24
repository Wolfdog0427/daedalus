import { mapSceneToSurfaces, surfacesToCssVars } from "../../shared/daedalus/sceneSurfacesEngine";
import { GLOW_COLORS, SCENE_GRADIENTS, SURFACE_DEFAULTS } from "../../shared/daedalus/sceneSurfaces";
import type { OrchestratedScene } from "../../shared/daedalus/sceneOrchestration";
import type { FusionSceneName } from "../../shared/daedalus/fusion";
import type { ConductorTone } from "../../shared/daedalus/conductor";

function mkScene(overrides: Partial<OrchestratedScene> = {}): OrchestratedScene {
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
    progress: 1,
    blendMs: 0,
    ...overrides,
  };
}

describe("mapSceneToSurfaces", () => {
  describe("glow color mapping", () => {
    const tones: ConductorTone[] = ["neutral", "focused", "celebratory", "alert"];
    for (const tone of tones) {
      it(`maps tone '${tone}' to its glow color`, () => {
        const result = mapSceneToSurfaces(mkScene({ tone }));
        expect(result.glowColor).toBe(GLOW_COLORS[tone]);
      });
    }
  });

  describe("background gradient mapping", () => {
    const scenes: FusionSceneName[] = [
      "idle", "focus", "rising", "apex", "waning",
      "settling", "alert", "celebrating", "exploring",
    ];
    for (const sceneName of scenes) {
      it(`maps sceneName '${sceneName}' to its gradient`, () => {
        const result = mapSceneToSurfaces(mkScene({ sceneName }));
        expect(result.backgroundGradient).toBe(SCENE_GRADIENTS[sceneName]);
      });
    }
  });

  describe("passthrough values", () => {
    it("passes glow as glowStrength", () => {
      const result = mapSceneToSurfaces(mkScene({ glow: 0.75 }));
      expect(result.glowStrength).toBe(0.75);
    });

    it("passes motion as motionStrength", () => {
      const result = mapSceneToSurfaces(mkScene({ motion: 0.6 }));
      expect(result.motionStrength).toBe(0.6);
    });

    it("passes tone as ribbonTone", () => {
      const result = mapSceneToSurfaces(mkScene({ tone: "focused" }));
      expect(result.ribbonTone).toBe("focused");
    });

    it("passes continuityBadge through", () => {
      const badge = { kind: "threshold" as const, label: "5 sessions" };
      const result = mapSceneToSurfaces(mkScene({ continuityBadge: badge }));
      expect(result.continuityBadge).toEqual(badge);
    });

    it("passes null continuityBadge through", () => {
      const result = mapSceneToSurfaces(mkScene({ continuityBadge: null }));
      expect(result.continuityBadge).toBeNull();
    });

    it("passes narrativeLine through", () => {
      const result = mapSceneToSurfaces(mkScene({ narrativeLine: "The field gathers." }));
      expect(result.narrativeLine).toBe("The field gathers.");
    });

    it("passes null narrativeLine through", () => {
      const result = mapSceneToSurfaces(mkScene());
      expect(result.narrativeLine).toBeNull();
    });

    it("passes progress as blendProgress", () => {
      const result = mapSceneToSurfaces(mkScene({ progress: 0.42 }));
      expect(result.blendProgress).toBe(0.42);
    });
  });
});

describe("surfacesToCssVars", () => {
  it("produces all expected CSS custom properties", () => {
    const props = mapSceneToSurfaces(mkScene({ tone: "focused", glow: 0.8, motion: 0.6, progress: 0.5 }));
    const vars = surfacesToCssVars(props);

    expect(vars["--surface-glow-color"]).toBe(GLOW_COLORS.focused);
    expect(vars["--surface-glow-strength"]).toBe("0.8");
    expect(vars["--surface-motion-strength"]).toBe("0.6");
    expect(vars["--surface-background"]).toBe(SCENE_GRADIENTS.idle);
    expect(vars["--surface-blend-progress"]).toBe("0.5");
  });

  it("produces string values for numeric properties", () => {
    const vars = surfacesToCssVars(SURFACE_DEFAULTS);
    expect(typeof vars["--surface-glow-strength"]).toBe("string");
    expect(typeof vars["--surface-motion-strength"]).toBe("string");
    expect(typeof vars["--surface-blend-progress"]).toBe("string");
  });
});
