import { evaluateAutonomy, mergeAutonomyTuning } from "../../shared/daedalus/sceneAutonomyEngine";
import type { AnalyticsSnapshot } from "../../shared/daedalus/sceneAnalytics";
import type { AdaptationTuning } from "../../shared/daedalus/sceneAdaptation";
import { ANALYTICS_IDLE } from "../../shared/daedalus/sceneAnalytics";
import { AUTONOMY_DEFAULTS } from "../../shared/daedalus/sceneAutonomy";

const NOW = 100_000;

function mkAnalytics(overrides: Partial<AnalyticsSnapshot> = {}): AnalyticsSnapshot {
  return { ...ANALYTICS_IDLE, timestamp: NOW, ...overrides };
}

describe("evaluateAutonomy", () => {
  // ── Rate limiting ──

  it("returns null when within minIntervalMs", () => {
    const result = evaluateAutonomy(
      mkAnalytics({ momentumVolatility: 0.9 }),
      NOW - 1000,
      1,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    expect(result).toBeNull();
  });

  it("allows proposal after minIntervalMs elapses", () => {
    const result = evaluateAutonomy(
      mkAnalytics({ momentumVolatility: 0.9 }),
      NOW - 10_000,
      1,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    expect(result).not.toBeNull();
  });

  // ── No proposal when healthy ──

  it("returns null when all metrics are within thresholds", () => {
    const result = evaluateAutonomy(
      mkAnalytics({ expressiveHealth: 0.8, momentumVolatility: 0.1 }),
      0,
      1,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    expect(result).toBeNull();
  });

  // ── High volatility ──

  it("proposes timeline smoothing when volatility exceeds threshold", () => {
    const result = evaluateAutonomy(
      mkAnalytics({ momentumVolatility: 0.7 }),
      0,
      5,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    expect(result).not.toBeNull();
    expect(result!.id).toBe(5);
    expect(result!.reason).toContain("volatility");
    expect(result!.recommended.timelineMomentumHalfLifeMs).toBe(10000);
  });

  it("does not propose for volatility below threshold", () => {
    const result = evaluateAutonomy(
      mkAnalytics({ momentumVolatility: 0.5 }),
      0,
      1,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    expect(result).toBeNull();
  });

  // ── Frequent rejections ──

  it("proposes increased dwell when rejection rate exceeds threshold", () => {
    const result = evaluateAutonomy(
      mkAnalytics({ grammarRejectionRate: 1.0 }),
      0,
      1,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    expect(result).not.toBeNull();
    expect(result!.reason).toContain("rejection");
    expect(result!.recommended.grammarDefaultDwellMs).toBe(1500);
  });

  // ── Governor overactive ──

  it("proposes widened cooldowns when governor rate exceeds threshold", () => {
    const result = evaluateAutonomy(
      mkAnalytics({ governorInterventionRate: 3 }),
      0,
      1,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    expect(result).not.toBeNull();
    expect(result!.reason).toContain("Governor");
    expect(result!.recommended.governorCooldownMs).toBe(1600);
    expect(result!.recommended.governorEscalationLockMs).toBe(4000);
  });

  // ── Low expressive health ──

  it("proposes comprehensive calm shift when health is low", () => {
    const result = evaluateAutonomy(
      mkAnalytics({ expressiveHealth: 0.3 }),
      0,
      1,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    expect(result).not.toBeNull();
    expect(result!.reason).toContain("health");
    expect(result!.recommended.governorCooldownMs).toBeGreaterThanOrEqual(1800);
    expect(result!.recommended.grammarDefaultBlendMs).toBe(800);
    expect(result!.recommended.narrativeMinIntervalMs).toBe(6000);
    expect(result!.recommended.timelineMomentumHalfLifeMs).toBeGreaterThanOrEqual(12000);
  });

  // ── Multiple triggers ──

  it("combines reasons from multiple triggers", () => {
    const result = evaluateAutonomy(
      mkAnalytics({
        momentumVolatility: 0.8,
        grammarRejectionRate: 1.5,
        expressiveHealth: 0.3,
      }),
      0,
      1,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    expect(result).not.toBeNull();
    const reasons = result!.reason.split("; ");
    expect(reasons.length).toBeGreaterThanOrEqual(3);
  });

  it("takes max of overlapping adjustments", () => {
    const result = evaluateAutonomy(
      mkAnalytics({
        momentumVolatility: 0.8,
        expressiveHealth: 0.3,
      }),
      0,
      1,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    // volatility sets half-life to 10000; low-health raises to max(10000,12000)=12000
    expect(result!.recommended.timelineMomentumHalfLifeMs).toBe(12000);
  });

  // ── Custom config ──

  it("respects custom thresholds", () => {
    const result = evaluateAutonomy(
      mkAnalytics({ momentumVolatility: 0.3 }),
      0,
      1,
      { ...AUTONOMY_DEFAULTS, volatilityThreshold: 0.2 },
      NOW,
    );
    expect(result).not.toBeNull();
  });

  // ── Timestamp and ID ──

  it("includes the provided timestamp and ID", () => {
    const result = evaluateAutonomy(
      mkAnalytics({ momentumVolatility: 0.9 }),
      0,
      42,
      AUTONOMY_DEFAULTS,
      NOW,
    );
    expect(result!.timestamp).toBe(NOW);
    expect(result!.id).toBe(42);
  });
});

describe("mergeAutonomyTuning", () => {
  it("returns adaptation tuning when autonomy is empty", () => {
    const adapt: AdaptationTuning = { governorCooldownMs: 1000 };
    expect(mergeAutonomyTuning(adapt, {})).toEqual(adapt);
  });

  it("returns autonomy tuning when adaptation is empty", () => {
    const approved: AdaptationTuning = { narrativeMinIntervalMs: 5000 };
    expect(mergeAutonomyTuning({}, approved)).toEqual(approved);
  });

  it("autonomy overrides adaptation for overlapping keys", () => {
    const adapt: AdaptationTuning = { governorCooldownMs: 1000, grammarDefaultBlendMs: 500 };
    const approved: AdaptationTuning = { governorCooldownMs: 1800 };
    const merged = mergeAutonomyTuning(adapt, approved);
    expect(merged.governorCooldownMs).toBe(1800);
    expect(merged.grammarDefaultBlendMs).toBe(500);
  });

  it("preserves non-overlapping keys from both", () => {
    const adapt: AdaptationTuning = { timelineMomentumHalfLifeMs: 9000 };
    const approved: AdaptationTuning = { narrativeMinIntervalMs: 6000 };
    const merged = mergeAutonomyTuning(adapt, approved);
    expect(merged.timelineMomentumHalfLifeMs).toBe(9000);
    expect(merged.narrativeMinIntervalMs).toBe(6000);
  });
});
