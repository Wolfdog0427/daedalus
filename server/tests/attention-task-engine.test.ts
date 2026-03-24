import {
  deriveAttentionTier,
  computeAttentionLevel,
  computeCognitiveLoad,
  deriveActiveTask,
  computeTaskLoad,
  computeAttentionTask,
  type AttentionTaskInput,
} from "../../shared/daedalus/attentionTaskEngine";
import { ATTENTION_TASK_IDLE } from "../../shared/daedalus/attentionTask";

describe("deriveAttentionTier", () => {
  it("maps known levels", () => {
    expect(deriveAttentionTier("locked")).toBe("locked");
    expect(deriveAttentionTier("focused")).toBe("focused");
    expect(deriveAttentionTier("aware")).toBe("aware");
    expect(deriveAttentionTier("unfocused")).toBe("unfocused");
  });

  it("defaults unknown levels to unfocused", () => {
    expect(deriveAttentionTier("something")).toBe("unfocused");
    expect(deriveAttentionTier("")).toBe("unfocused");
  });
});

describe("computeAttentionLevel", () => {
  it("locked tier with full focus approaches 1", () => {
    const level = computeAttentionLevel("locked", 1);
    expect(level).toBeCloseTo(0.9 * 0.6 + 1 * 0.4);
  });

  it("unfocused tier with zero focus is near 0", () => {
    const level = computeAttentionLevel("unfocused", 0);
    expect(level).toBeCloseTo(0.1 * 0.6);
  });

  it("blends tier base (60%) with focus (40%)", () => {
    const focused = computeAttentionLevel("focused", 0.5);
    expect(focused).toBeCloseTo(0.7 * 0.6 + 0.5 * 0.4);
  });

  it("clamps to [0,1]", () => {
    expect(computeAttentionLevel("locked", 2)).toBeLessThanOrEqual(1);
  });
});

describe("computeCognitiveLoad", () => {
  it("returns 0 when all inputs are zero/stable", () => {
    expect(computeCognitiveLoad(0, 0, 1)).toBeCloseTo(0);
  });

  it("increases with arousal", () => {
    const low = computeCognitiveLoad(0.2, 0, 1);
    const high = computeCognitiveLoad(0.8, 0, 1);
    expect(high).toBeGreaterThan(low);
  });

  it("increases with pending proposals", () => {
    const none = computeCognitiveLoad(0.5, 0, 1);
    const many = computeCognitiveLoad(0.5, 4, 1);
    expect(many).toBeGreaterThan(none);
  });

  it("increases when stability drops", () => {
    const stable = computeCognitiveLoad(0.5, 1, 0.9);
    const fragile = computeCognitiveLoad(0.5, 1, 0.2);
    expect(fragile).toBeGreaterThan(stable);
  });

  it("clamps proposals to [0,1] contribution", () => {
    const huge = computeCognitiveLoad(0, 20, 1);
    expect(huge).toBeLessThanOrEqual(1);
  });
});

describe("deriveActiveTask", () => {
  it("returns operator-task when operatorIntent is task", () => {
    expect(deriveActiveTask("idle", "task")).toBe("operator-task");
  });

  it("returns exploration when operatorIntent is exploration", () => {
    expect(deriveActiveTask("idle", "exploration")).toBe("exploration");
  });

  it("returns guided-task for guiding orchestration", () => {
    expect(deriveActiveTask("guiding", null)).toBe("guided-task");
  });

  it("returns support-task for supporting orchestration", () => {
    expect(deriveActiveTask("supporting", null)).toBe("support-task");
  });

  it("returns alert-response for alert orchestration", () => {
    expect(deriveActiveTask("alert", null)).toBe("alert-response");
    expect(deriveActiveTask("escalating", null)).toBe("alert-response");
  });

  it("returns null when idle and no operator intent", () => {
    expect(deriveActiveTask("idle", null)).toBeNull();
    expect(deriveActiveTask("idle", "idle")).toBeNull();
  });

  it("prioritizes operator intent over orchestration", () => {
    expect(deriveActiveTask("guiding", "task")).toBe("operator-task");
  });
});

describe("computeTaskLoad", () => {
  it("returns 0 when no active task", () => {
    expect(computeTaskLoad(0.8, false)).toBe(0);
  });

  it("starts at 0.2 base with active task", () => {
    expect(computeTaskLoad(0, true)).toBeCloseTo(0.2);
  });

  it("scales with arousal when task is active", () => {
    const low = computeTaskLoad(0.2, true);
    const high = computeTaskLoad(0.8, true);
    expect(high).toBeGreaterThan(low);
  });

  it("clamps to [0,1]", () => {
    expect(computeTaskLoad(2, true)).toBeLessThanOrEqual(1);
  });
});

describe("computeAttentionTask", () => {
  const base: AttentionTaskInput = {
    expressiveAttentionLevel: "focused",
    expressiveFocus: 0.7,
    expressiveArousal: 0.5,
    expressiveStability: 0.8,
    orchestrationIntent: "guiding",
    activePanel: "topology",
    operatorIntent: "task",
    pendingProposals: 1,
  };

  it("produces a frozen snapshot", () => {
    const snap = computeAttentionTask(base);
    expect(Object.isFrozen(snap)).toBe(true);
  });

  it("derives attentionTier from expressiveAttentionLevel", () => {
    const snap = computeAttentionTask(base);
    expect(snap.attentionTier).toBe("focused");
  });

  it("computes attentionLevel from tier and focus", () => {
    const snap = computeAttentionTask(base);
    expect(snap.attentionLevel).toBeCloseTo(0.7 * 0.6 + 0.7 * 0.4);
  });

  it("uses activePanel as focusTarget", () => {
    const snap = computeAttentionTask(base);
    expect(snap.focusTarget).toBe("topology");
  });

  it("uses stability as continuity signals", () => {
    const snap = computeAttentionTask(base);
    expect(snap.attentionContinuity).toBe(0.8);
    expect(snap.taskContinuity).toBe(0.8);
  });

  it("derives activeTask from operator intent first", () => {
    const snap = computeAttentionTask(base);
    expect(snap.activeTask).toBe("operator-task");
  });

  it("derives activeTask from orchestration when no operator intent", () => {
    const snap = computeAttentionTask({ ...base, operatorIntent: null });
    expect(snap.activeTask).toBe("guided-task");
  });

  it("returns null activeTask when everything idle", () => {
    const snap = computeAttentionTask({
      ...base,
      orchestrationIntent: "idle",
      operatorIntent: null,
    });
    expect(snap.activeTask).toBeNull();
  });

  it("computes taskLoad only when task is active", () => {
    const active = computeAttentionTask(base);
    const idle = computeAttentionTask({
      ...base,
      orchestrationIntent: "idle",
      operatorIntent: null,
    });
    expect(active.taskLoad).toBeGreaterThan(0);
    expect(idle.taskLoad).toBe(0);
  });
});

describe("ATTENTION_TASK_IDLE", () => {
  it("is frozen", () => {
    expect(Object.isFrozen(ATTENTION_TASK_IDLE)).toBe(true);
  });

  it("has zero-energy defaults", () => {
    expect(ATTENTION_TASK_IDLE.attentionLevel).toBe(0);
    expect(ATTENTION_TASK_IDLE.attentionTier).toBe("unfocused");
    expect(ATTENTION_TASK_IDLE.cognitiveLoad).toBe(0);
    expect(ATTENTION_TASK_IDLE.activeTask).toBeNull();
    expect(ATTENTION_TASK_IDLE.taskLoad).toBe(0);
  });
});
