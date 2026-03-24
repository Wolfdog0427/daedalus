import { composeSceneFrame } from "../../shared/daedalus/sceneSyncEngine";
import { GLOW_COLORS, SCENE_GRADIENTS } from "../../shared/daedalus/sceneSurfaces";
import type { OrchestratedScene } from "../../shared/daedalus/sceneOrchestration";

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

describe("composeSceneFrame", () => {
  it("bundles scene and surfaces into a single frame", () => {
    const scene = mkScene({ tone: "focused", glow: 0.8 });
    const frame = composeSceneFrame(scene, 1);

    expect(frame.scene).toBe(scene);
    expect(frame.surfaces.glowColor).toBe(GLOW_COLORS.focused);
    expect(frame.surfaces.glowStrength).toBe(0.8);
    expect(frame.cssVars["--surface-glow-color"]).toBe(GLOW_COLORS.focused);
  });

  it("assigns the provided frameId", () => {
    const frame = composeSceneFrame(mkScene(), 42);
    expect(frame.frameId).toBe(42);
  });

  it("uses the provided timestamp", () => {
    const frame = composeSceneFrame(mkScene(), 1, 99999);
    expect(frame.timestamp).toBe(99999);
  });

  it("defaults timestamp to Date.now()", () => {
    const before = Date.now();
    const frame = composeSceneFrame(mkScene(), 1);
    const after = Date.now();
    expect(frame.timestamp).toBeGreaterThanOrEqual(before);
    expect(frame.timestamp).toBeLessThanOrEqual(after);
  });

  it("surfaces gradient matches the scene name", () => {
    const frame = composeSceneFrame(mkScene({ sceneName: "apex" }), 1);
    expect(frame.surfaces.backgroundGradient).toBe(SCENE_GRADIENTS.apex);
    expect(frame.cssVars["--surface-background"]).toBe(SCENE_GRADIENTS.apex);
  });

  it("surfaces ribbonTone matches scene tone", () => {
    const frame = composeSceneFrame(mkScene({ tone: "alert" }), 1);
    expect(frame.surfaces.ribbonTone).toBe("alert");
  });

  it("passes narrativeLine from scene to surfaces", () => {
    const frame = composeSceneFrame(
      mkScene({ narrativeLine: "The field gathers." }),
      1,
    );
    expect(frame.surfaces.narrativeLine).toBe("The field gathers.");
  });

  it("passes continuityBadge from scene to surfaces", () => {
    const badge = { kind: "threshold" as const, label: "10 sessions" };
    const frame = composeSceneFrame(mkScene({ continuityBadge: badge }), 1);
    expect(frame.surfaces.continuityBadge).toEqual(badge);
  });

  it("passes progress from scene to surfaces as blendProgress", () => {
    const frame = composeSceneFrame(mkScene({ progress: 0.65 }), 1);
    expect(frame.surfaces.blendProgress).toBe(0.65);
  });

  it("produces consistent scene and surfaces for all scene names", () => {
    const names = [
      "idle", "focus", "rising", "apex", "waning",
      "settling", "alert", "celebrating", "exploring",
    ] as const;

    for (const sceneName of names) {
      const frame = composeSceneFrame(mkScene({ sceneName }), 1);
      expect(frame.scene.sceneName).toBe(sceneName);
      expect(frame.surfaces.backgroundGradient).toBe(SCENE_GRADIENTS[sceneName]);
    }
  });

  it("produces consistent scene and surfaces for all tones", () => {
    const tones = ["neutral", "focused", "celebratory", "alert"] as const;

    for (const tone of tones) {
      const frame = composeSceneFrame(mkScene({ tone }), 1);
      expect(frame.scene.tone).toBe(tone);
      expect(frame.surfaces.glowColor).toBe(GLOW_COLORS[tone]);
      expect(frame.surfaces.ribbonTone).toBe(tone);
    }
  });

  it("all cssVars keys start with --surface-", () => {
    const frame = composeSceneFrame(mkScene(), 1);
    for (const key of Object.keys(frame.cssVars)) {
      expect(key).toMatch(/^--surface-/);
    }
  });
});
