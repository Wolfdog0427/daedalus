import {
  inferStrategy,
  recommendForStrategy,
  evolveStrategy,
  evaluateStrategy,
} from "../../shared/daedalus/expressiveStrategyEngine";
import type { AnalyticsSnapshot } from "../../shared/daedalus/sceneAnalytics";
import type { OperatorIntent } from "../../shared/daedalus/intentModel";
import { ANALYTICS_IDLE } from "../../shared/daedalus/sceneAnalytics";
import {
  STRATEGY_DEFAULTS,
  STRATEGY_EVAL_IDLE,
} from "../../shared/daedalus/expressiveStrategy";
import type { StrategyEvalState } from "../../shared/daedalus/expressiveStrategy";

const NOW = 100_000;

function mkAnalytics(overrides: Partial<AnalyticsSnapshot> = {}): AnalyticsSnapshot {
  return { ...ANALYTICS_IDLE, timestamp: NOW, ...overrides };
}

// ── inferStrategy ──────────────────────────────────────────────

describe("inferStrategy", () => {
  it("returns stability-first when smoothness is low and rejections high", () => {
    expect(
      inferStrategy("task", mkAnalytics({ transitionSmoothness: 0.3, grammarRejectionRate: 0.5 })),
    ).toBe("stability-first");
  });

  it("returns cooldown-arc when health is critically low", () => {
    expect(inferStrategy("task", mkAnalytics({ expressiveHealth: 0.3 }))).toBe("cooldown-arc");
  });

  it("returns sustained-focus for task intent with high stability", () => {
    expect(
      inferStrategy("task", mkAnalytics({ sceneStability: 0.9, expressiveHealth: 0.7 })),
    ).toBe("sustained-focus");
  });

  it("returns broad-exploration for exploration intent with low volatility", () => {
    expect(
      inferStrategy("exploration", mkAnalytics({ momentumVolatility: 0.2, expressiveHealth: 0.7 })),
    ).toBe("broad-exploration");
  });

  it("returns transition-arc for transition intent", () => {
    expect(inferStrategy("transition", mkAnalytics({ expressiveHealth: 0.7 }))).toBe(
      "transition-arc",
    );
  });

  it("returns cooldown-arc for idle intent with moderate health", () => {
    expect(inferStrategy("idle", mkAnalytics({ expressiveHealth: 0.55 }))).toBe("cooldown-arc");
  });

  it("returns responsiveness-first when health is high and no specific intent match", () => {
    expect(inferStrategy("idle", mkAnalytics({ expressiveHealth: 0.9 }))).toBe(
      "responsiveness-first",
    );
  });

  it("returns null when no intent and health is moderate", () => {
    expect(inferStrategy(null, mkAnalytics({ expressiveHealth: 0.7 }))).toBeNull();
  });

  it("stability-first takes priority over intent-specific strategies", () => {
    expect(
      inferStrategy(
        "task",
        mkAnalytics({
          sceneStability: 0.9,
          transitionSmoothness: 0.3,
          grammarRejectionRate: 0.5,
        }),
      ),
    ).toBe("stability-first");
  });

  it("cooldown-arc from low health takes priority over intent", () => {
    expect(
      inferStrategy(
        "exploration",
        mkAnalytics({ expressiveHealth: 0.3, momentumVolatility: 0.1 }),
      ),
    ).toBe("cooldown-arc");
  });
});

// ── recommendForStrategy ───────────────────────────────────────

describe("recommendForStrategy", () => {
  it("sustained-focus recommends responsive governor + fast blend", () => {
    const rec = recommendForStrategy("sustained-focus");
    expect(rec.governorCooldownMs).toBe(600);
    expect(rec.grammarDefaultBlendMs).toBe(300);
  });

  it("broad-exploration recommends responsive timeline + narrative", () => {
    const rec = recommendForStrategy("broad-exploration");
    expect(rec.timelineMomentumHalfLifeMs).toBe(4500);
    expect(rec.narrativeMinIntervalMs).toBe(2200);
  });

  it("cooldown-arc recommends wide cooldowns + slow narrative", () => {
    const rec = recommendForStrategy("cooldown-arc");
    expect(rec.governorCooldownMs).toBe(1600);
    expect(rec.narrativeMinIntervalMs).toBe(6500);
  });

  it("transition-arc recommends moderate blend", () => {
    const rec = recommendForStrategy("transition-arc");
    expect(rec.grammarDefaultBlendMs).toBe(450);
  });

  it("stability-first recommends high smoothing + slow blend", () => {
    const rec = recommendForStrategy("stability-first");
    expect(rec.timelineMomentumHalfLifeMs).toBe(10000);
    expect(rec.grammarDefaultBlendMs).toBe(700);
  });

  it("responsiveness-first recommends fast governor + blend", () => {
    const rec = recommendForStrategy("responsiveness-first");
    expect(rec.governorCooldownMs).toBe(650);
    expect(rec.grammarDefaultBlendMs).toBe(350);
  });
});

// ── evolveStrategy ─────────────────────────────────────────────

describe("evolveStrategy", () => {
  it("starts from idle with reinforceStep confidence on first inference", () => {
    const next = evolveStrategy(
      STRATEGY_EVAL_IDLE,
      "task",
      mkAnalytics({ sceneStability: 0.9, expressiveHealth: 0.7 }),
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(next.candidate).toBe("sustained-focus");
    expect(next.confidence).toBe(STRATEGY_DEFAULTS.reinforceStep);
    expect(next.lastEvalAt).toBe(NOW);
  });

  it("reinforces confidence when candidate matches", () => {
    const prev: StrategyEvalState = {
      candidate: "sustained-focus",
      confidence: 0.3,
      lastEvalAt: NOW - 1000,
    };
    const next = evolveStrategy(
      prev,
      "task",
      mkAnalytics({ sceneStability: 0.9, expressiveHealth: 0.7 }),
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(next.candidate).toBe("sustained-focus");
    expect(next.confidence).toBe(0.3 + STRATEGY_DEFAULTS.reinforceStep);
  });

  it("caps confidence at 1", () => {
    const prev: StrategyEvalState = {
      candidate: "sustained-focus",
      confidence: 0.95,
      lastEvalAt: NOW - 1000,
    };
    const next = evolveStrategy(
      prev,
      "task",
      mkAnalytics({ sceneStability: 0.9, expressiveHealth: 0.7 }),
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(next.confidence).toBe(1);
  });

  it("resets to new candidate with base confidence when inference changes", () => {
    const prev: StrategyEvalState = {
      candidate: "sustained-focus",
      confidence: 0.8,
      lastEvalAt: NOW - 1000,
    };
    const next = evolveStrategy(
      prev,
      "exploration",
      mkAnalytics({ momentumVolatility: 0.2, expressiveHealth: 0.7 }),
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(next.candidate).toBe("broad-exploration");
    expect(next.confidence).toBe(STRATEGY_DEFAULTS.reinforceStep);
  });

  it("weakens confidence when inference returns null", () => {
    const prev: StrategyEvalState = {
      candidate: "sustained-focus",
      confidence: 0.5,
      lastEvalAt: NOW - 1000,
    };
    const next = evolveStrategy(prev, null, mkAnalytics({ expressiveHealth: 0.7 }), STRATEGY_DEFAULTS, NOW);
    expect(next.candidate).toBe("sustained-focus");
    expect(next.confidence).toBe(0.5 - STRATEGY_DEFAULTS.weakenStep);
  });

  it("applies time-based decay when lastEvalAt exceeds decayAfterMs", () => {
    const prev: StrategyEvalState = {
      candidate: "sustained-focus",
      confidence: 0.8,
      lastEvalAt: NOW - 30_000, // well past decayAfterMs (20s)
    };
    const next = evolveStrategy(
      prev,
      "task",
      mkAnalytics({ sceneStability: 0.9, expressiveHealth: 0.7 }),
      STRATEGY_DEFAULTS,
      NOW,
    );
    // decay reduces by decayStep, then reinforce adds reinforceStep
    expect(next.confidence).toBe(0.8 - STRATEGY_DEFAULTS.decayStep + STRATEGY_DEFAULTS.reinforceStep);
  });

  it("clamps confidence to 0 on decay", () => {
    const prev: StrategyEvalState = {
      candidate: "sustained-focus",
      confidence: 0.05,
      lastEvalAt: NOW - 1000,
    };
    const next = evolveStrategy(prev, null, mkAnalytics({ expressiveHealth: 0.7 }), STRATEGY_DEFAULTS, NOW);
    expect(next.confidence).toBe(0);
  });

  it("does not apply time-decay when lastEvalAt is 0 (first run)", () => {
    const next = evolveStrategy(
      STRATEGY_EVAL_IDLE,
      "task",
      mkAnalytics({ sceneStability: 0.9, expressiveHealth: 0.7 }),
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(next.confidence).toBe(STRATEGY_DEFAULTS.reinforceStep);
  });
});

// ── evaluateStrategy ───────────────────────────────────────────

describe("evaluateStrategy", () => {
  it("returns no proposal when confidence is below threshold", () => {
    const result = evaluateStrategy(
      STRATEGY_EVAL_IDLE,
      "task",
      mkAnalytics({ sceneStability: 0.9, expressiveHealth: 0.7 }),
      0,
      1,
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(result.proposal).toBeNull();
    expect(result.state.candidate).toBe("sustained-focus");
  });

  it("returns no proposal when within proposalIntervalMs", () => {
    const highConfidence: StrategyEvalState = {
      candidate: "sustained-focus",
      confidence: 0.8,
      lastEvalAt: NOW - 1000,
    };
    const result = evaluateStrategy(
      highConfidence,
      "task",
      mkAnalytics({ sceneStability: 0.9, expressiveHealth: 0.7 }),
      NOW - 5000, // too recent
      1,
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(result.proposal).toBeNull();
  });

  it("produces a proposal when confidence exceeds threshold and interval has elapsed", () => {
    const highConfidence: StrategyEvalState = {
      candidate: "sustained-focus",
      confidence: 0.8,
      lastEvalAt: NOW - 1000,
    };
    const result = evaluateStrategy(
      highConfidence,
      "task",
      mkAnalytics({ sceneStability: 0.9, expressiveHealth: 0.7 }),
      0, // no previous proposal
      42,
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(result.proposal).not.toBeNull();
    expect(result.proposal!.id).toBe(42);
    expect(result.proposal!.reason).toContain("sustained-focus");
    expect(result.proposal!.recommended.governorCooldownMs).toBe(600);
  });

  it("returns no proposal when candidate is null", () => {
    const noCandidate: StrategyEvalState = {
      candidate: null,
      confidence: 0,
      lastEvalAt: NOW - 1000,
    };
    const result = evaluateStrategy(
      noCandidate,
      null,
      mkAnalytics({ expressiveHealth: 0.7 }),
      0,
      1,
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(result.proposal).toBeNull();
  });

  it("includes confidence in proposal reason", () => {
    const highConfidence: StrategyEvalState = {
      candidate: "broad-exploration",
      confidence: 0.75,
      lastEvalAt: NOW - 1000,
    };
    const result = evaluateStrategy(
      highConfidence,
      "exploration",
      mkAnalytics({ momentumVolatility: 0.2, expressiveHealth: 0.7 }),
      0,
      1,
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(result.proposal!.reason).toContain("broad-exploration");
    expect(result.proposal!.reason).toMatch(/\d+%/);
  });

  it("updates state even when no proposal is produced", () => {
    const result = evaluateStrategy(
      STRATEGY_EVAL_IDLE,
      "transition",
      mkAnalytics({ expressiveHealth: 0.7 }),
      0,
      1,
      STRATEGY_DEFAULTS,
      NOW,
    );
    expect(result.state.candidate).toBe("transition-arc");
    expect(result.state.lastEvalAt).toBe(NOW);
    expect(result.proposal).toBeNull();
  });
});
