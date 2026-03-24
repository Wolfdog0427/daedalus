import {
  trimHistory,
  recordStrategy,
  inferMetaStrategy,
  recommendForMetaStrategy,
  evolveMetaStrategy,
  evaluateMetaStrategy,
} from "../../shared/daedalus/metaStrategyEngine";
import type { AnalyticsSnapshot } from "../../shared/daedalus/sceneAnalytics";
import type { StrategyHistoryEntry } from "../../shared/daedalus/metaStrategy";
import { ANALYTICS_IDLE } from "../../shared/daedalus/sceneAnalytics";
import {
  META_STRATEGY_DEFAULTS,
  META_STRATEGY_EVAL_IDLE,
} from "../../shared/daedalus/metaStrategy";
import type { MetaStrategyEvalState } from "../../shared/daedalus/metaStrategy";
import type { ExpressiveStrategy } from "../../shared/daedalus/expressiveStrategy";

const NOW = 200_000;

function mkAnalytics(overrides: Partial<AnalyticsSnapshot> = {}): AnalyticsSnapshot {
  return { ...ANALYTICS_IDLE, timestamp: NOW, expressiveHealth: 0.7, ...overrides };
}

function mkHistory(
  strategies: ExpressiveStrategy[],
  baseTime: number = NOW - 5000,
): StrategyHistoryEntry[] {
  return strategies.map((strategy, i) => ({ strategy, timestamp: baseTime + i * 1000 }));
}

// ── trimHistory ────────────────────────────────────────────────

describe("trimHistory", () => {
  it("keeps entries within the window", () => {
    const history = mkHistory(["sustained-focus", "sustained-focus"], NOW - 2000);
    expect(trimHistory(history, 60000, NOW)).toHaveLength(2);
  });

  it("removes entries older than the window", () => {
    const history = [
      { strategy: "sustained-focus" as const, timestamp: NOW - 90000 },
      { strategy: "broad-exploration" as const, timestamp: NOW - 1000 },
    ];
    expect(trimHistory(history, 60000, NOW)).toHaveLength(1);
  });
});

// ── recordStrategy ─────────────────────────────────────────────

describe("recordStrategy", () => {
  it("appends and trims in one call", () => {
    const history = mkHistory(["sustained-focus"], NOW - 90000);
    const result = recordStrategy(history, "broad-exploration", 60000, NOW);
    expect(result).toHaveLength(1);
    expect(result[0].strategy).toBe("broad-exploration");
  });
});

// ── inferMetaStrategy ──────────────────────────────────────────

describe("inferMetaStrategy", () => {
  it("returns null with fewer than minHistoryEntries", () => {
    expect(inferMetaStrategy(mkHistory(["sustained-focus"]), mkAnalytics())).toBeNull();
  });

  it("returns stability-cycle when sustained-focus dominates", () => {
    const history = mkHistory([
      "sustained-focus",
      "sustained-focus",
      "sustained-focus",
      "broad-exploration",
    ]);
    expect(inferMetaStrategy(history, mkAnalytics())).toBe("stability-cycle");
  });

  it("returns stability-cycle when stability-first dominates", () => {
    const history = mkHistory([
      "stability-first",
      "stability-first",
      "stability-first",
      "cooldown-arc",
    ]);
    expect(inferMetaStrategy(history, mkAnalytics())).toBe("stability-cycle");
  });

  it("returns exploration-cycle when broad-exploration dominates", () => {
    const history = mkHistory([
      "broad-exploration",
      "broad-exploration",
      "broad-exploration",
      "transition-arc",
    ]);
    expect(inferMetaStrategy(history, mkAnalytics())).toBe("exploration-cycle");
  });

  it("returns cooldown-cycle when cooldown-arc dominates", () => {
    const history = mkHistory([
      "cooldown-arc",
      "cooldown-arc",
      "cooldown-arc",
    ]);
    expect(inferMetaStrategy(history, mkAnalytics())).toBe("cooldown-cycle");
  });

  it("returns responsiveness-cycle when responsiveness-first dominates", () => {
    const history = mkHistory([
      "responsiveness-first",
      "responsiveness-first",
      "responsiveness-first",
    ]);
    expect(inferMetaStrategy(history, mkAnalytics())).toBe("responsiveness-cycle");
  });

  it("returns responsiveness-cycle from analytics when health is high and no dominant", () => {
    const history = mkHistory([
      "sustained-focus",
      "broad-exploration",
      "cooldown-arc",
    ]);
    expect(inferMetaStrategy(history, mkAnalytics({ expressiveHealth: 0.9 }))).toBe(
      "responsiveness-cycle",
    );
  });

  it("returns cooldown-cycle from analytics when health is low and no dominant", () => {
    const history = mkHistory([
      "sustained-focus",
      "broad-exploration",
      "transition-arc",
    ]);
    expect(inferMetaStrategy(history, mkAnalytics({ expressiveHealth: 0.3 }))).toBe(
      "cooldown-cycle",
    );
  });

  it("returns mixed-cycle when no dominant and moderate health", () => {
    const history = mkHistory([
      "sustained-focus",
      "broad-exploration",
      "cooldown-arc",
    ]);
    expect(inferMetaStrategy(history, mkAnalytics({ expressiveHealth: 0.6 }))).toBe(
      "mixed-cycle",
    );
  });
});

// ── recommendForMetaStrategy ───────────────────────────────────

describe("recommendForMetaStrategy", () => {
  it("stability-cycle recommends high smoothing + slow blend", () => {
    const rec = recommendForMetaStrategy("stability-cycle");
    expect(rec.timelineMomentumHalfLifeMs).toBe(11000);
    expect(rec.grammarDefaultBlendMs).toBe(750);
  });

  it("exploration-cycle recommends responsive timeline + narrative", () => {
    const rec = recommendForMetaStrategy("exploration-cycle");
    expect(rec.timelineMomentumHalfLifeMs).toBe(4500);
    expect(rec.narrativeMinIntervalMs).toBe(2400);
  });

  it("cooldown-cycle recommends wide cooldowns", () => {
    const rec = recommendForMetaStrategy("cooldown-cycle");
    expect(rec.governorCooldownMs).toBe(1700);
    expect(rec.narrativeMinIntervalMs).toBe(7000);
  });

  it("responsiveness-cycle recommends fast governor + blend", () => {
    const rec = recommendForMetaStrategy("responsiveness-cycle");
    expect(rec.governorCooldownMs).toBe(600);
    expect(rec.grammarDefaultBlendMs).toBe(320);
  });

  it("mixed-cycle recommends moderate blend", () => {
    const rec = recommendForMetaStrategy("mixed-cycle");
    expect(rec.grammarDefaultBlendMs).toBe(500);
  });
});

// ── evolveMetaStrategy ─────────────────────────────────────────

describe("evolveMetaStrategy", () => {
  const withHistory = (
    candidate: MetaStrategyEvalState["candidate"],
    confidence: number,
    history: StrategyHistoryEntry[],
  ): MetaStrategyEvalState => ({
    candidate,
    confidence,
    lastEvalAt: NOW - 1000,
    history,
  });

  it("starts from idle with reinforceStep on first inference", () => {
    const state: MetaStrategyEvalState = {
      ...META_STRATEGY_EVAL_IDLE,
      history: mkHistory(["sustained-focus", "sustained-focus", "sustained-focus"]),
    };
    const next = evolveMetaStrategy(state, mkAnalytics(), META_STRATEGY_DEFAULTS, NOW);
    expect(next.candidate).toBe("stability-cycle");
    expect(next.confidence).toBe(META_STRATEGY_DEFAULTS.reinforceStep);
  });

  it("reinforces confidence when candidate matches", () => {
    const state = withHistory(
      "stability-cycle",
      0.4,
      mkHistory(["sustained-focus", "sustained-focus", "sustained-focus"]),
    );
    const next = evolveMetaStrategy(state, mkAnalytics(), META_STRATEGY_DEFAULTS, NOW);
    expect(next.confidence).toBe(0.4 + META_STRATEGY_DEFAULTS.reinforceStep);
  });

  it("caps confidence at 1", () => {
    const state = withHistory(
      "stability-cycle",
      0.95,
      mkHistory(["sustained-focus", "sustained-focus", "sustained-focus"]),
    );
    const next = evolveMetaStrategy(state, mkAnalytics(), META_STRATEGY_DEFAULTS, NOW);
    expect(next.confidence).toBe(1);
  });

  it("resets to new candidate when inference changes", () => {
    const state = withHistory(
      "stability-cycle",
      0.8,
      mkHistory(["broad-exploration", "broad-exploration", "broad-exploration"]),
    );
    const next = evolveMetaStrategy(state, mkAnalytics(), META_STRATEGY_DEFAULTS, NOW);
    expect(next.candidate).toBe("exploration-cycle");
    expect(next.confidence).toBe(META_STRATEGY_DEFAULTS.reinforceStep);
  });

  it("weakens confidence when inference returns null (too few entries)", () => {
    const state: MetaStrategyEvalState = {
      candidate: "stability-cycle",
      confidence: 0.5,
      lastEvalAt: NOW - 1000,
      history: mkHistory(["sustained-focus"]),
    };
    const next = evolveMetaStrategy(state, mkAnalytics(), META_STRATEGY_DEFAULTS, NOW);
    expect(next.confidence).toBe(0.5 - META_STRATEGY_DEFAULTS.weakenStep);
  });

  it("applies time-based decay", () => {
    const state: MetaStrategyEvalState = {
      candidate: "stability-cycle",
      confidence: 0.8,
      lastEvalAt: NOW - 40000,
      history: mkHistory(["sustained-focus", "sustained-focus", "sustained-focus"]),
    };
    const next = evolveMetaStrategy(state, mkAnalytics(), META_STRATEGY_DEFAULTS, NOW);
    expect(next.confidence).toBe(
      0.8 - META_STRATEGY_DEFAULTS.decayStep + META_STRATEGY_DEFAULTS.reinforceStep,
    );
  });

  it("trims history during evolution", () => {
    const state: MetaStrategyEvalState = {
      candidate: null,
      confidence: 0,
      lastEvalAt: 0,
      history: [
        { strategy: "sustained-focus", timestamp: NOW - 120000 },
        ...mkHistory(["sustained-focus", "sustained-focus", "sustained-focus"]),
      ],
    };
    const next = evolveMetaStrategy(state, mkAnalytics(), META_STRATEGY_DEFAULTS, NOW);
    expect(next.history).toHaveLength(3);
  });
});

// ── evaluateMetaStrategy ───────────────────────────────────────

describe("evaluateMetaStrategy", () => {
  it("returns no proposal when confidence is below threshold", () => {
    const state: MetaStrategyEvalState = {
      ...META_STRATEGY_EVAL_IDLE,
      history: mkHistory(["sustained-focus", "sustained-focus", "sustained-focus"]),
    };
    const result = evaluateMetaStrategy(state, mkAnalytics(), 0, 1, META_STRATEGY_DEFAULTS, NOW);
    expect(result.proposal).toBeNull();
    expect(result.state.candidate).toBe("stability-cycle");
  });

  it("returns no proposal when within proposalIntervalMs", () => {
    const state: MetaStrategyEvalState = {
      candidate: "stability-cycle",
      confidence: 0.8,
      lastEvalAt: NOW - 1000,
      history: mkHistory(["sustained-focus", "sustained-focus", "sustained-focus"]),
    };
    const result = evaluateMetaStrategy(
      state,
      mkAnalytics(),
      NOW - 5000,
      1,
      META_STRATEGY_DEFAULTS,
      NOW,
    );
    expect(result.proposal).toBeNull();
  });

  it("produces a proposal when confidence exceeds threshold and interval elapsed", () => {
    const state: MetaStrategyEvalState = {
      candidate: "stability-cycle",
      confidence: 0.8,
      lastEvalAt: NOW - 1000,
      history: mkHistory(["sustained-focus", "sustained-focus", "sustained-focus"]),
    };
    const result = evaluateMetaStrategy(state, mkAnalytics(), 0, 77, META_STRATEGY_DEFAULTS, NOW);
    expect(result.proposal).not.toBeNull();
    expect(result.proposal!.id).toBe(77);
    expect(result.proposal!.reason).toContain("stability-cycle");
    expect(result.proposal!.recommended.timelineMomentumHalfLifeMs).toBe(11000);
  });

  it("includes confidence in proposal reason", () => {
    const state: MetaStrategyEvalState = {
      candidate: "exploration-cycle",
      confidence: 0.75,
      lastEvalAt: NOW - 1000,
      history: mkHistory(["broad-exploration", "broad-exploration", "broad-exploration"]),
    };
    const result = evaluateMetaStrategy(state, mkAnalytics(), 0, 1, META_STRATEGY_DEFAULTS, NOW);
    expect(result.proposal!.reason).toMatch(/\d+%/);
  });

  it("updates state even when no proposal is produced", () => {
    const state: MetaStrategyEvalState = {
      ...META_STRATEGY_EVAL_IDLE,
      history: mkHistory(["cooldown-arc", "cooldown-arc", "cooldown-arc"]),
    };
    const result = evaluateMetaStrategy(state, mkAnalytics(), 0, 1, META_STRATEGY_DEFAULTS, NOW);
    expect(result.state.candidate).toBe("cooldown-cycle");
    expect(result.state.lastEvalAt).toBe(NOW);
    expect(result.proposal).toBeNull();
  });
});
