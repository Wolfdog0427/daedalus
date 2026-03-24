import {
  trimSignals,
  inferIntent,
  recommendForIntent,
  evaluateIntent,
} from "../../shared/daedalus/intentModelEngine";
import type { IntentSignal, IntentModelConfig } from "../../shared/daedalus/intentModel";
import { INTENT_MODEL_DEFAULTS } from "../../shared/daedalus/intentModel";

const NOW = 100_000;

function mkSignals(
  types: IntentSignal["type"][],
  baseTime: number = NOW - 1000,
): IntentSignal[] {
  return types.map((type, i) => ({ type, timestamp: baseTime + i * 100 }));
}

describe("trimSignals", () => {
  it("keeps signals within the window", () => {
    const signals = mkSignals(["input", "input", "input"], NOW - 500);
    expect(trimSignals(signals, 8000, NOW)).toHaveLength(3);
  });

  it("removes signals older than the window", () => {
    const signals = [
      { type: "input" as const, timestamp: NOW - 20_000 },
      { type: "input" as const, timestamp: NOW - 500 },
    ];
    expect(trimSignals(signals, 8000, NOW)).toHaveLength(1);
  });

  it("returns empty array when all are too old", () => {
    const signals = mkSignals(["input"], NOW - 20_000);
    expect(trimSignals(signals, 8000, NOW)).toHaveLength(0);
  });
});

describe("inferIntent", () => {
  it("returns null with fewer signals than minSignals", () => {
    expect(inferIntent(mkSignals(["input", "input"]), INTENT_MODEL_DEFAULTS)).toBeNull();
  });

  it("returns task when input+focus dominate", () => {
    const signals = mkSignals(["input", "input", "focus", "input", "focus"]);
    expect(inferIntent(signals, INTENT_MODEL_DEFAULTS)).toBe("task");
  });

  it("returns exploration when navigation dominates", () => {
    const signals = mkSignals(["navigation", "navigation", "navigation", "navigation", "input"]);
    expect(inferIntent(signals, INTENT_MODEL_DEFAULTS)).toBe("exploration");
  });

  it("returns idle when idle signals exceed 60%", () => {
    const signals = mkSignals(["idle", "idle", "idle", "idle", "input"]);
    expect(inferIntent(signals, INTENT_MODEL_DEFAULTS)).toBe("idle");
  });

  it("returns transition when no clear pattern", () => {
    const signals = mkSignals(["input", "navigation", "focus", "idle"]);
    expect(inferIntent(signals, INTENT_MODEL_DEFAULTS)).toBe("transition");
  });

  it("idle takes priority over task", () => {
    const signals = mkSignals(["idle", "idle", "idle", "idle", "input", "focus"]);
    expect(inferIntent(signals, INTENT_MODEL_DEFAULTS)).toBe("idle");
  });

  it("task takes priority over exploration when input+focus > navigation*2", () => {
    const signals = mkSignals(["input", "input", "focus", "navigation", "input"]);
    expect(inferIntent(signals, INTENT_MODEL_DEFAULTS)).toBe("task");
  });

  it("respects custom minSignals", () => {
    const signals = mkSignals(["input", "input"]);
    const config: IntentModelConfig = { ...INTENT_MODEL_DEFAULTS, minSignals: 2 };
    expect(inferIntent(signals, config)).toBe("task");
  });
});

describe("recommendForIntent", () => {
  it("recommends responsive tuning for task mode", () => {
    const rec = recommendForIntent("task");
    expect(rec.governorCooldownMs).toBe(700);
    expect(rec.grammarDefaultBlendMs).toBe(350);
  });

  it("recommends responsive timeline for exploration mode", () => {
    const rec = recommendForIntent("exploration");
    expect(rec.timelineMomentumHalfLifeMs).toBe(5000);
    expect(rec.narrativeMinIntervalMs).toBe(2500);
  });

  it("recommends calm tuning for idle mode", () => {
    const rec = recommendForIntent("idle");
    expect(rec.governorCooldownMs).toBe(1500);
    expect(rec.narrativeMinIntervalMs).toBe(6000);
    expect(rec.grammarDefaultBlendMs).toBe(700);
  });

  it("recommends moderate blend for transition mode", () => {
    const rec = recommendForIntent("transition");
    expect(rec.grammarDefaultBlendMs).toBe(500);
  });
});

describe("evaluateIntent", () => {
  it("returns null when within proposalIntervalMs", () => {
    const signals = mkSignals(["input", "input", "input", "input"]);
    const result = evaluateIntent(signals, NOW - 1000, 1, INTENT_MODEL_DEFAULTS, NOW);
    expect(result).toBeNull();
  });

  it("returns null when not enough signals", () => {
    const signals = mkSignals(["input", "input"]);
    const result = evaluateIntent(signals, 0, 1, INTENT_MODEL_DEFAULTS, NOW);
    expect(result).toBeNull();
  });

  it("produces a proposal when intent is clear and interval has elapsed", () => {
    const signals = mkSignals(["input", "input", "focus", "input", "input"]);
    const result = evaluateIntent(signals, 0, 5, INTENT_MODEL_DEFAULTS, NOW);
    expect(result).not.toBeNull();
    expect(result!.intent).toBe("task");
    expect(result!.proposal.id).toBe(5);
    expect(result!.proposal.reason).toContain("task");
    expect(result!.proposal.recommended.governorCooldownMs).toBe(700);
  });

  it("includes the correct timestamp", () => {
    const signals = mkSignals(["navigation", "navigation", "navigation", "navigation"]);
    const result = evaluateIntent(signals, 0, 1, INTENT_MODEL_DEFAULTS, NOW);
    expect(result!.proposal.timestamp).toBe(NOW);
  });

  it("trims old signals before inferring", () => {
    const signals = [
      ...mkSignals(["idle", "idle", "idle", "idle"], NOW - 20_000),
      ...mkSignals(["input", "input", "input", "input"], NOW - 500),
    ];
    const result = evaluateIntent(signals, 0, 1, INTENT_MODEL_DEFAULTS, NOW);
    expect(result).not.toBeNull();
    expect(result!.intent).toBe("task");
  });

  it("returns exploration when navigation dominates", () => {
    const signals = mkSignals([
      "navigation",
      "navigation",
      "navigation",
      "navigation",
      "input",
    ]);
    const result = evaluateIntent(signals, 0, 1, INTENT_MODEL_DEFAULTS, NOW);
    expect(result!.intent).toBe("exploration");
    expect(result!.proposal.recommended.timelineMomentumHalfLifeMs).toBe(5000);
  });

  it("returns idle when dominated by idle signals", () => {
    const signals = mkSignals(["idle", "idle", "idle", "idle", "input"]);
    const result = evaluateIntent(signals, 0, 1, INTENT_MODEL_DEFAULTS, NOW);
    expect(result!.intent).toBe("idle");
  });
});
