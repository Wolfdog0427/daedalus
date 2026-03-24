import {
  computeMotionGrammar,
  unifyGlow,
  computeEmbodiment,
  computeNodeGlows,
  computeEmbodiedPresence,
  type EmbodiedPresenceInput,
} from "../../shared/daedalus/embodiedPresenceEngine";
import { EMBODIED_IDLE } from "../../shared/daedalus/embodiedPresence";

describe("computeMotionGrammar", () => {
  it("blends arousal (60%) and stability (40%)", () => {
    expect(computeMotionGrammar(1, 1)).toBeCloseTo(1);
    expect(computeMotionGrammar(0, 0)).toBeCloseTo(0);
    expect(computeMotionGrammar(0.5, 0.5)).toBeCloseTo(0.5);
  });

  it("clamps to [0,1]", () => {
    expect(computeMotionGrammar(2, 2)).toBe(1);
    expect(computeMotionGrammar(-1, -1)).toBe(0);
  });

  it("weights arousal more heavily", () => {
    const highArousal = computeMotionGrammar(0.8, 0.2);
    const highStability = computeMotionGrammar(0.2, 0.8);
    expect(highArousal).toBeGreaterThan(highStability);
  });
});

describe("unifyGlow", () => {
  it("blends scene glow (70%) with motion grammar (30%)", () => {
    expect(unifyGlow(1, 1)).toBeCloseTo(1);
    expect(unifyGlow(0, 0)).toBeCloseTo(0);
    expect(unifyGlow(0.5, 0.5)).toBeCloseTo(0.5);
  });

  it("weights scene glow more heavily", () => {
    const highScene = unifyGlow(0.8, 0.2);
    const highMotion = unifyGlow(0.2, 0.8);
    expect(highScene).toBeGreaterThan(highMotion);
  });

  it("clamps to [0,1]", () => {
    expect(unifyGlow(2, 2)).toBe(1);
  });
});

describe("computeEmbodiment", () => {
  it("returns 0 when no beings", () => {
    expect(computeEmbodiment(0, 0.5, 0.5)).toBe(0);
  });

  it("increases with more beings up to a cap", () => {
    const one = computeEmbodiment(1, 0.5, 0.5);
    const four = computeEmbodiment(4, 0.5, 0.5);
    expect(four).toBeGreaterThan(one);
  });

  it("clamps at 1", () => {
    expect(computeEmbodiment(10, 1, 1)).toBeLessThanOrEqual(1);
  });

  it("responds to focus and arousal", () => {
    const lowFocus = computeEmbodiment(2, 0.2, 0.5);
    const highFocus = computeEmbodiment(2, 0.8, 0.5);
    expect(highFocus).toBeGreaterThan(lowFocus);
  });
});

describe("computeNodeGlows", () => {
  it("returns empty array for empty nodes", () => {
    expect(computeNodeGlows([])).toEqual([]);
  });

  it("computes glow from health and trust", () => {
    const glows = computeNodeGlows([
      { id: "a", health: 1, trusted: true },
      { id: "b", health: 0.5, trusted: false },
    ]);
    expect(glows).toHaveLength(2);
    expect(glows[0].glow).toBeCloseTo(1);
    expect(glows[1].glow).toBeCloseTo(0.4);
  });

  it("adds trust bonus", () => {
    const trusted = computeNodeGlows([{ id: "a", health: 0.5, trusted: true }]);
    const untrusted = computeNodeGlows([{ id: "a", health: 0.5, trusted: false }]);
    expect(trusted[0].glow).toBeGreaterThan(untrusted[0].glow);
  });

  it("clamps glow to 1", () => {
    const glows = computeNodeGlows([{ id: "a", health: 1.5, trusted: true }]);
    expect(glows[0].glow).toBe(1);
  });

  it("returns frozen objects", () => {
    const glows = computeNodeGlows([{ id: "a", health: 0.5, trusted: true }]);
    expect(Object.isFrozen(glows[0])).toBe(true);
  });
});

describe("computeEmbodiedPresence", () => {
  const base: EmbodiedPresenceInput = {
    beingCount: 2,
    dominantBeingId: "alpha",
    posture: "companion",
    arousal: 0.6,
    focus: 0.7,
    stability: 0.8,
    sceneGlow: 0.5,
    sceneMotion: 0.4,
    connectivityNodes: [
      { id: "n1", health: 0.9, trusted: true },
      { id: "n2", health: 0.6, trusted: false },
    ],
  };

  it("produces a frozen snapshot", () => {
    const snap = computeEmbodiedPresence(base);
    expect(Object.isFrozen(snap)).toBe(true);
    expect(Object.isFrozen(snap.nodeGlows)).toBe(true);
  });

  it("forwards posture, beingCount, dominantBeingId", () => {
    const snap = computeEmbodiedPresence(base);
    expect(snap.posture).toBe("companion");
    expect(snap.beingCount).toBe(2);
    expect(snap.dominantBeingId).toBe("alpha");
  });

  it("computes motionGrammar from arousal and stability", () => {
    const snap = computeEmbodiedPresence(base);
    expect(snap.motionGrammar).toBeCloseTo(0.6 * 0.6 + 0.8 * 0.4);
  });

  it("computes unifiedGlow from sceneGlow and motionGrammar", () => {
    const snap = computeEmbodiedPresence(base);
    const expectedMotion = 0.6 * 0.6 + 0.8 * 0.4;
    const expectedGlow = 0.5 * 0.7 + expectedMotion * 0.3;
    expect(snap.unifiedGlow).toBeCloseTo(expectedGlow);
  });

  it("uses stability as continuity", () => {
    const snap = computeEmbodiedPresence(base);
    expect(snap.continuity).toBe(0.8);
  });

  it("produces nodeGlows for each connectivity node", () => {
    const snap = computeEmbodiedPresence(base);
    expect(snap.nodeGlows).toHaveLength(2);
    expect(snap.nodeGlows[0].id).toBe("n1");
    expect(snap.nodeGlows[1].id).toBe("n2");
  });

  it("returns idle-like values when no beings and no nodes", () => {
    const snap = computeEmbodiedPresence({
      ...base,
      beingCount: 0,
      dominantBeingId: null,
      arousal: 0,
      focus: 0,
      stability: 1,
      sceneGlow: 0,
      sceneMotion: 0,
      connectivityNodes: [],
    });
    expect(snap.embodiment).toBe(0);
    expect(snap.nodeGlows).toHaveLength(0);
  });
});

describe("EMBODIED_IDLE", () => {
  it("is frozen", () => {
    expect(Object.isFrozen(EMBODIED_IDLE)).toBe(true);
    expect(Object.isFrozen(EMBODIED_IDLE.nodeGlows)).toBe(true);
  });

  it("has zero-energy defaults", () => {
    expect(EMBODIED_IDLE.embodiment).toBe(0);
    expect(EMBODIED_IDLE.motionGrammar).toBe(0);
    expect(EMBODIED_IDLE.unifiedGlow).toBe(0);
    expect(EMBODIED_IDLE.beingCount).toBe(0);
  });
});
