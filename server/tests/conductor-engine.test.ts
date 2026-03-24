import { computeConductorOutput } from "../../shared/daedalus/conductorEngine";
import type { ConductorInputs } from "../../shared/daedalus/conductor";

function makeInputs(overrides: Partial<ConductorInputs> = {}): ConductorInputs {
  return {
    orchestrationIntent: "idle",
    orchestratedPosture: "companion",
    arousal: 0,
    focus: 0,
    stability: 1,
    operatorAffect: "settled",
    continuitySignals: [],
    glowIntensity: 0.5,
    ...overrides,
  };
}

describe("computeConductorOutput", () => {
  // ── Layer 1: Orchestration intent ──

  it("defaults to resting mode with neutral tone", () => {
    const out = computeConductorOutput(makeInputs());
    expect(out.mode).toBe("resting");
    expect(out.tone).toBe("neutral");
  });

  it("escalates to escalated mode when intent is alert", () => {
    const out = computeConductorOutput(makeInputs({ orchestrationIntent: "alert" }));
    expect(out.mode).toBe("escalated");
    expect(out.tone).toBe("alert");
    expect(out.suppressAmbientPulse).toBe(true);
  });

  it("escalates to escalated mode when intent is escalating", () => {
    const out = computeConductorOutput(makeInputs({ orchestrationIntent: "escalating" }));
    expect(out.mode).toBe("escalated");
    expect(out.tone).toBe("alert");
  });

  it("goes attentive with focused tone when intent is guiding", () => {
    const out = computeConductorOutput(makeInputs({ orchestrationIntent: "guiding" }));
    expect(out.mode).toBe("attentive");
    expect(out.tone).toBe("focused");
  });

  it("goes attentive with neutral tone when intent is supporting", () => {
    const out = computeConductorOutput(makeInputs({ orchestrationIntent: "supporting" }));
    expect(out.mode).toBe("attentive");
    expect(out.tone).toBe("neutral");
  });

  it("amplifies glow when escalated", () => {
    const base = computeConductorOutput(makeInputs({ glowIntensity: 0.5 }));
    const escalated = computeConductorOutput(makeInputs({ orchestrationIntent: "alert", glowIntensity: 0.5 }));
    expect(escalated.glowIntensity).toBeGreaterThan(base.glowIntensity);
  });

  // ── Layer 2: Operator affect ──

  it("dampens motion when affect is focused", () => {
    const settled = computeConductorOutput(makeInputs());
    const focused = computeConductorOutput(makeInputs({ operatorAffect: "focused" }));
    expect(focused.motionIntensity).toBeLessThan(settled.motionIntensity);
    expect(focused.suppressAmbientPulse).toBe(true);
  });

  it("sets focused tone when affect is focused (non-escalated)", () => {
    const out = computeConductorOutput(makeInputs({ operatorAffect: "focused" }));
    expect(out.tone).toBe("focused");
  });

  it("does not override alert tone when affect is focused during escalation", () => {
    const out = computeConductorOutput(makeInputs({
      orchestrationIntent: "alert",
      operatorAffect: "focused",
    }));
    expect(out.tone).toBe("alert");
  });

  it("brightens glow when affect is exploratory", () => {
    const settled = computeConductorOutput(makeInputs({ glowIntensity: 0.5 }));
    const exploratory = computeConductorOutput(makeInputs({ operatorAffect: "exploratory", glowIntensity: 0.5 }));
    expect(exploratory.glowIntensity).toBeGreaterThan(settled.glowIntensity);
  });

  it("escalates mode when affect is under-load (non-escalated intent)", () => {
    const out = computeConductorOutput(makeInputs({ operatorAffect: "under-load" }));
    expect(out.mode).toBe("escalated");
    expect(out.tone).toBe("alert");
  });

  // ── Layer 3: Continuity ──

  it("shows threshold badge and celebrates when neutral", () => {
    const out = computeConductorOutput(makeInputs({
      continuitySignals: [{ kind: "threshold", label: "Crossed 10 check-ins" }],
    }));
    expect(out.continuityBadge).toEqual({ kind: "threshold", label: "Crossed 10 check-ins" });
    expect(out.mode).toBe("celebrating");
    expect(out.tone).toBe("celebratory");
  });

  it("shows recovery badge when neutral", () => {
    const out = computeConductorOutput(makeInputs({
      continuitySignals: [{ kind: "drift-recovery", label: "Recovered" }],
    }));
    expect(out.continuityBadge).toEqual({ kind: "drift-recovery", label: "Recovered" });
    expect(out.tone).toBe("celebratory");
  });

  it("suppresses continuity badge during escalation", () => {
    const out = computeConductorOutput(makeInputs({
      orchestrationIntent: "alert",
      continuitySignals: [{ kind: "threshold", label: "Crossed 10 check-ins" }],
    }));
    expect(out.continuityBadge).toBeNull();
    expect(out.mode).toBe("escalated");
  });

  it("suppresses continuity badge when under-load", () => {
    const out = computeConductorOutput(makeInputs({
      operatorAffect: "under-load",
      continuitySignals: [{ kind: "threshold", label: "Crossed 10 check-ins" }],
    }));
    expect(out.continuityBadge).toBeNull();
  });

  it("does not celebrate when tone is already focused", () => {
    const out = computeConductorOutput(makeInputs({
      operatorAffect: "focused",
      continuitySignals: [{ kind: "threshold", label: "Crossed 10 check-ins" }],
    }));
    expect(out.tone).toBe("focused");
    expect(out.mode).not.toBe("celebrating");
  });

  // ── Passthrough ──

  it("passes posture through from orchestration", () => {
    const out = computeConductorOutput(makeInputs({ orchestratedPosture: "sentinel" }));
    expect(out.posture).toBe("sentinel");
  });

  it("clamps glow and motion to [0, 1]", () => {
    const out = computeConductorOutput(makeInputs({
      orchestrationIntent: "alert",
      glowIntensity: 0.9,
      arousal: 1,
    }));
    expect(out.glowIntensity).toBeLessThanOrEqual(1);
    expect(out.motionIntensity).toBeLessThanOrEqual(1);
  });
});
