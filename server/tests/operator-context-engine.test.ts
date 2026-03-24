import {
  deriveMode,
  countOverrides,
  computeSovereignty,
  computeOperatorContext,
  type OperatorContextInput,
} from "../../shared/daedalus/operatorContextEngine";

function mkInput(overrides: Partial<OperatorContextInput> = {}): OperatorContextInput {
  return {
    activePanel: "topology",
    affectEffective: "settled",
    affectPinned: false,
    currentIntent: null,
    postureNudge: null,
    governorEnabled: true,
    governorPreset: "default",
    pendingProposals: 0,
    ...overrides,
  };
}

describe("deriveMode", () => {
  it("returns focus by default", () => {
    expect(deriveMode(mkInput())).toBe("focus");
  });

  it("returns override when affect is pinned", () => {
    expect(deriveMode(mkInput({ affectPinned: true }))).toBe("override");
  });

  it("returns override when posture is nudged", () => {
    expect(deriveMode(mkInput({ postureNudge: "sentinel" }))).toBe("override");
  });

  it("returns override when governor is disabled", () => {
    expect(deriveMode(mkInput({ governorEnabled: false }))).toBe("override");
  });

  it("returns explore for exploration intent", () => {
    expect(deriveMode(mkInput({ currentIntent: "exploration" }))).toBe("explore");
  });

  it("returns explore for exploratory affect", () => {
    expect(deriveMode(mkInput({ affectEffective: "exploratory" }))).toBe("explore");
  });

  it("returns review when governance panel is active", () => {
    expect(deriveMode(mkInput({ activePanel: "governance" }))).toBe("review");
  });

  it("override takes priority over explore", () => {
    expect(deriveMode(mkInput({ affectPinned: true, currentIntent: "exploration" }))).toBe("override");
  });

  it("explore takes priority over review", () => {
    expect(deriveMode(mkInput({ currentIntent: "exploration", activePanel: "governance" }))).toBe("explore");
  });
});

describe("countOverrides", () => {
  it("returns 0 with no overrides", () => {
    expect(countOverrides(mkInput())).toBe(0);
  });

  it("counts affect pin", () => {
    expect(countOverrides(mkInput({ affectPinned: true }))).toBe(1);
  });

  it("counts posture nudge", () => {
    expect(countOverrides(mkInput({ postureNudge: "sentinel" }))).toBe(1);
  });

  it("counts governor disabled", () => {
    expect(countOverrides(mkInput({ governorEnabled: false }))).toBe(1);
  });

  it("counts non-default preset", () => {
    expect(countOverrides(mkInput({ governorPreset: "calm" }))).toBe(1);
  });

  it("accumulates all overrides", () => {
    expect(countOverrides(mkInput({
      affectPinned: true,
      postureNudge: "companion",
      governorEnabled: false,
      governorPreset: "responsive",
    }))).toBe(4);
  });
});

describe("computeSovereignty", () => {
  it("returns 1 with no overrides or pending", () => {
    expect(computeSovereignty(0, 0)).toBe(1);
  });

  it("decreases with pending proposals", () => {
    expect(computeSovereignty(0, 3)).toBe(0.7);
  });

  it("increases slightly with overrides", () => {
    expect(computeSovereignty(2, 0)).toBe(1);
  });

  it("override boost partially offsets pending penalty", () => {
    const withOverrides = computeSovereignty(2, 2);
    const without = computeSovereignty(0, 2);
    expect(withOverrides).toBeGreaterThan(without);
  });

  it("clamps to 0", () => {
    expect(computeSovereignty(0, 15)).toBe(0);
  });

  it("clamps to 1", () => {
    expect(computeSovereignty(4, 0)).toBe(1);
  });
});

describe("computeOperatorContext", () => {
  it("returns idle-like snapshot for default input", () => {
    const ctx = computeOperatorContext(mkInput());
    expect(ctx.mode).toBe("focus");
    expect(ctx.focus).toBe("topology");
    expect(ctx.intent).toBeNull();
    expect(ctx.affect).toBe("settled");
    expect(ctx.affectPinned).toBe(false);
    expect(ctx.postureNudged).toBe(false);
    expect(ctx.governorOverridden).toBe(false);
    expect(ctx.overrideCount).toBe(0);
    expect(ctx.pendingProposals).toBe(0);
    expect(ctx.sovereignty).toBe(1);
  });

  it("reflects override mode and sovereignty when affect is pinned", () => {
    const ctx = computeOperatorContext(mkInput({ affectPinned: true }));
    expect(ctx.mode).toBe("override");
    expect(ctx.affectPinned).toBe(true);
    expect(ctx.overrideCount).toBe(1);
    expect(ctx.sovereignty).toBeGreaterThan(1 - 0.01);
  });

  it("reflects explore mode from intent", () => {
    const ctx = computeOperatorContext(mkInput({ currentIntent: "exploration" }));
    expect(ctx.mode).toBe("explore");
    expect(ctx.intent).toBe("exploration");
  });

  it("reflects review mode from governance panel", () => {
    const ctx = computeOperatorContext(mkInput({ activePanel: "governance" }));
    expect(ctx.mode).toBe("review");
    expect(ctx.focus).toBe("governance");
  });

  it("reflects pending proposals in sovereignty", () => {
    const ctx = computeOperatorContext(mkInput({ pendingProposals: 5 }));
    expect(ctx.pendingProposals).toBe(5);
    expect(ctx.sovereignty).toBe(0.5);
  });

  it("produces a frozen object", () => {
    const ctx = computeOperatorContext(mkInput());
    expect(Object.isFrozen(ctx)).toBe(true);
  });

  it("handles full override scenario", () => {
    const ctx = computeOperatorContext(mkInput({
      affectPinned: true,
      postureNudge: "sentinel",
      governorEnabled: false,
      governorPreset: "calm",
      pendingProposals: 2,
    }));
    expect(ctx.mode).toBe("override");
    expect(ctx.overrideCount).toBe(4);
    expect(ctx.postureNudged).toBe(true);
    expect(ctx.governorOverridden).toBe(true);
    expect(ctx.sovereignty).toBeGreaterThan(0.7);
  });
});
