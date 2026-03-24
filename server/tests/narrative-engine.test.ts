import { generateNarrative } from "../../shared/daedalus/narrativeEngine";
import type { NarrativeInput, NarrativeConfig } from "../../shared/daedalus/narrative";
import { NARRATIVE_DEFAULTS } from "../../shared/daedalus/narrative";

function makeInput(overrides: Partial<NarrativeInput> = {}): NarrativeInput {
  return {
    posture: "companion",
    conductorTone: "neutral",
    affect: "settled",
    timelinePhase: "idle",
    momentum: 0.5,
    continuityBadgeLabel: null,
    ...overrides,
  };
}

describe("generateNarrative", () => {
  // ── Silence conditions ──

  it("returns null when momentum is below threshold", () => {
    const input = makeInput({ momentum: 0.05 });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBeNull();
  });

  it("returns null when rate-limited", () => {
    const now = 10000;
    const lastSpokenAt = now - 1000;
    const input = makeInput({ timelinePhase: "rising" });
    const result = generateNarrative(input, lastSpokenAt, NARRATIVE_DEFAULTS, now);
    expect(result.line).toBeNull();
  });

  it("speaks when rate-limit has elapsed", () => {
    const now = 10000;
    const lastSpokenAt = now - NARRATIVE_DEFAULTS.minIntervalMs - 1;
    const input = makeInput({ timelinePhase: "rising" });
    const result = generateNarrative(input, lastSpokenAt, NARRATIVE_DEFAULTS, now);
    expect(result.line).not.toBeNull();
  });

  it("returns null when no narrative condition is met", () => {
    const input = makeInput({
      timelinePhase: "idle",
      posture: "companion",
      affect: "settled",
      continuityBadgeLabel: null,
    });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBeNull();
  });

  // ── Timeline-driven ──

  it("narrates rising phase", () => {
    const input = makeInput({ timelinePhase: "rising" });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("The field is gathering.");
    expect(result.tone).toBe("focused");
  });

  it("narrates peak phase", () => {
    const input = makeInput({ timelinePhase: "peak" });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("The field is at full height.");
    expect(result.tone).toBe("celebratory");
  });

  it("narrates cooldown phase", () => {
    const input = makeInput({ timelinePhase: "cooldown" });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("The field is easing.");
    expect(result.tone).toBe("neutral");
  });

  it("narrates settling phase", () => {
    const input = makeInput({ timelinePhase: "settling" });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("The field is settling.");
    expect(result.tone).toBe("neutral");
  });

  // ── Continuity-driven ──

  it("narrates continuity badge when no timeline signal", () => {
    const input = makeInput({
      timelinePhase: "idle",
      continuityBadgeLabel: "Crossed 10 check-ins",
    });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("Crossed 10 check-ins");
    expect(result.tone).toBe("celebratory");
  });

  // ── Posture-driven ──

  it("narrates sentinel posture when no higher-priority signal", () => {
    const input = makeInput({ timelinePhase: "idle", posture: "sentinel" });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("A threshold is guarded.");
    expect(result.tone).toBe("alert");
  });

  it("narrates observer posture", () => {
    const input = makeInput({ timelinePhase: "idle", posture: "observer" });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("Attention holds steady.");
    expect(result.tone).toBe("focused");
  });

  // ── Affect-driven ──

  it("narrates exploratory affect when no higher-priority signal", () => {
    const input = makeInput({ timelinePhase: "idle", posture: "companion", affect: "exploratory" });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("The field is open.");
    expect(result.tone).toBe("neutral");
  });

  it("narrates focused affect", () => {
    const input = makeInput({ timelinePhase: "idle", posture: "companion", affect: "focused" });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("The field narrows.");
    expect(result.tone).toBe("focused");
  });

  // ── Priority ──

  it("timeline takes priority over posture", () => {
    const input = makeInput({ timelinePhase: "peak", posture: "sentinel" });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("The field is at full height.");
  });

  it("continuity takes priority over posture", () => {
    const input = makeInput({
      timelinePhase: "idle",
      posture: "sentinel",
      continuityBadgeLabel: "Recovered",
    });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("Recovered");
  });

  it("posture takes priority over affect", () => {
    const input = makeInput({
      timelinePhase: "idle",
      posture: "sentinel",
      affect: "exploratory",
    });
    const result = generateNarrative(input, 0, NARRATIVE_DEFAULTS, 100000);
    expect(result.line).toBe("A threshold is guarded.");
  });

  // ── Custom config ──

  it("respects custom momentum threshold", () => {
    const config: NarrativeConfig = { minIntervalMs: 0, momentumThreshold: 0.8 };
    const input = makeInput({ timelinePhase: "rising", momentum: 0.5 });
    const result = generateNarrative(input, 0, config, 100000);
    expect(result.line).toBeNull();
  });

  it("respects custom rate-limit interval", () => {
    const config: NarrativeConfig = { minIntervalMs: 10000, momentumThreshold: 0 };
    const now = 15000;
    const input = makeInput({ timelinePhase: "rising" });
    const result = generateNarrative(input, now - 5000, config, now);
    expect(result.line).toBeNull();
  });
});
