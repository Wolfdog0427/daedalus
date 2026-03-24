import { suggestAffect, resolveAffect, FOCUSED_DWELL_MS, EXPLORATORY_SWITCHES } from "../../shared/daedalus/affectEngine";
import type { AffectSuggestionInput } from "../../shared/daedalus/operatorAffect";

function makeInput(overrides: Partial<AffectSuggestionInput> = {}): AffectSuggestionInput {
  return {
    orchestrationIntent: "idle",
    governancePosture: "OPEN",
    panelSwitchCount: 0,
    panelStableSince: Date.now(),
    now: Date.now(),
    ...overrides,
  };
}

describe("suggestAffect", () => {
  it("defaults to settled", () => {
    expect(suggestAffect(makeInput())).toBe("settled");
  });

  it("suggests under-load when alert + GUARDED", () => {
    expect(suggestAffect(makeInput({
      orchestrationIntent: "alert",
      governancePosture: "GUARDED",
    }))).toBe("under-load");
  });

  it("suggests under-load when escalating + LOCKDOWN", () => {
    expect(suggestAffect(makeInput({
      orchestrationIntent: "escalating",
      governancePosture: "LOCKDOWN",
    }))).toBe("under-load");
  });

  it("does NOT suggest under-load when alert but posture is OPEN", () => {
    expect(suggestAffect(makeInput({
      orchestrationIntent: "alert",
      governancePosture: "OPEN",
    }))).not.toBe("under-load");
  });

  it("suggests focused after long dwell", () => {
    const now = Date.now();
    expect(suggestAffect(makeInput({
      panelStableSince: now - FOCUSED_DWELL_MS - 1000,
      now,
    }))).toBe("focused");
  });

  it("suggests exploratory on rapid panel switches", () => {
    const now = Date.now();
    expect(suggestAffect(makeInput({
      panelSwitchCount: EXPLORATORY_SWITCHES,
      panelStableSince: now - 5000,
      now,
    }))).toBe("exploratory");
  });

  it("does NOT suggest exploratory if dwell is too long", () => {
    const now = Date.now();
    expect(suggestAffect(makeInput({
      panelSwitchCount: EXPLORATORY_SWITCHES + 5,
      panelStableSince: now - FOCUSED_DWELL_MS - 1000,
      now,
    }))).toBe("focused");
  });

  it("under-load takes priority over focused", () => {
    const now = Date.now();
    expect(suggestAffect(makeInput({
      orchestrationIntent: "escalating",
      governancePosture: "GUARDED",
      panelStableSince: now - FOCUSED_DWELL_MS - 1000,
      now,
    }))).toBe("under-load");
  });
});

describe("resolveAffect", () => {
  it("returns suggested when no pin", () => {
    expect(resolveAffect(null, "exploratory")).toBe("exploratory");
  });

  it("returns pinned over suggested", () => {
    expect(resolveAffect("focused", "exploratory")).toBe("focused");
  });

  it("returns pinned even when suggested matches", () => {
    expect(resolveAffect("settled", "settled")).toBe("settled");
  });
});
