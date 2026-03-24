import { computeAdaptation } from "../../shared/daedalus/sceneAdaptationEngine";
import type { AnalyticsSnapshot } from "../../shared/daedalus/sceneAnalytics";
import { ANALYTICS_IDLE } from "../../shared/daedalus/sceneAnalytics";

function mkAnalytics(overrides: Partial<AnalyticsSnapshot> = {}): AnalyticsSnapshot {
  return { ...ANALYTICS_IDLE, timestamp: 1000, ...overrides };
}

describe("computeAdaptation", () => {
  // ── No adjustments when healthy ──

  it("returns only responsive adjustments when analytics are idle (health=1)", () => {
    const snap = computeAdaptation(mkAnalytics());
    expect(snap.reasons).toHaveLength(1);
    expect(snap.reasons[0].trigger).toBe("high-health");
  });

  it("returns no adjustments when expressiveHealth is moderate", () => {
    const snap = computeAdaptation(mkAnalytics({ expressiveHealth: 0.65 }));
    expect(snap.reasons).toHaveLength(0);
  });

  // ── High momentum volatility ──

  it("increases timeline smoothing when volatility > 0.5", () => {
    const snap = computeAdaptation(mkAnalytics({ momentumVolatility: 0.7 }));
    expect(snap.tuning.timelineMomentumHalfLifeMs).toBe(9000);
    expect(snap.reasons).toContainEqual(
      expect.objectContaining({ trigger: "high-volatility" }),
    );
  });

  it("does not adjust timeline when volatility <= 0.5", () => {
    const snap = computeAdaptation(mkAnalytics({ momentumVolatility: 0.5 }));
    expect(snap.tuning.timelineMomentumHalfLifeMs).toBeUndefined();
  });

  // ── Grammar rejections ──

  it("increases dwell when grammarRejectionRate > 0.3", () => {
    const snap = computeAdaptation(mkAnalytics({ grammarRejectionRate: 0.5 }));
    expect(snap.tuning.grammarDefaultDwellMs).toBe(1400);
    expect(snap.reasons).toContainEqual(
      expect.objectContaining({ trigger: "frequent-rejections" }),
    );
  });

  it("does not adjust dwell when rejections <= 0.3", () => {
    const snap = computeAdaptation(mkAnalytics({ grammarRejectionRate: 0.2 }));
    expect(snap.tuning.grammarDefaultDwellMs).toBeUndefined();
  });

  // ── Narrative density ──

  it("widens narrative interval when density > 3", () => {
    const snap = computeAdaptation(mkAnalytics({ narrativeDensity: 4.5 }));
    expect(snap.tuning.narrativeMinIntervalMs).toBe(5500);
    expect(snap.reasons).toContainEqual(
      expect.objectContaining({ trigger: "narrative-density" }),
    );
  });

  it("does not adjust narrative when density <= 3", () => {
    const snap = computeAdaptation(mkAnalytics({ narrativeDensity: 2 }));
    expect(snap.tuning.narrativeMinIntervalMs).toBeUndefined();
  });

  // ── Governor intervention rate ──

  it("widens governor cooldowns when rate > 1.5", () => {
    const snap = computeAdaptation(mkAnalytics({ governorInterventionRate: 2 }));
    expect(snap.tuning.governorCooldownMs).toBe(1400);
    expect(snap.tuning.governorEscalationLockMs).toBe(3500);
    expect(snap.reasons).toContainEqual(
      expect.objectContaining({ trigger: "governor-busy" }),
    );
  });

  it("does not adjust governor for rate alone when rate <= 1.5", () => {
    const snap = computeAdaptation(mkAnalytics({ governorInterventionRate: 1, expressiveHealth: 0.65 }));
    expect(snap.tuning.governorCooldownMs).toBeUndefined();
    expect(snap.reasons.every((r) => r.trigger !== "governor-busy")).toBe(true);
  });

  // ── Low expressive health ──

  it("shifts to calm preset when health < 0.4", () => {
    const snap = computeAdaptation(mkAnalytics({ expressiveHealth: 0.3 }));
    expect(snap.tuning.governorCooldownMs).toBeGreaterThanOrEqual(1600);
    expect(snap.tuning.governorEscalationLockMs).toBeGreaterThanOrEqual(4000);
    expect(snap.tuning.grammarDefaultBlendMs).toBe(700);
    expect(snap.tuning.grammarDefaultDwellMs).toBeGreaterThanOrEqual(1400);
    expect(snap.tuning.timelineMomentumHalfLifeMs).toBeGreaterThanOrEqual(10000);
    expect(snap.reasons).toContainEqual(
      expect.objectContaining({ trigger: "low-health" }),
    );
  });

  it("calm preset takes max of existing adjustments", () => {
    const snap = computeAdaptation(mkAnalytics({
      expressiveHealth: 0.2,
      governorInterventionRate: 3,
    }));
    // governor-busy sets cooldown to 1400; low-health raises to max(1400, 1600)=1600
    expect(snap.tuning.governorCooldownMs).toBe(1600);
    expect(snap.tuning.governorEscalationLockMs).toBe(4000);
  });

  // ── High expressive health ──

  it("shifts to responsive preset when health > 0.85", () => {
    const snap = computeAdaptation(mkAnalytics({ expressiveHealth: 0.95 }));
    expect(snap.tuning.governorCooldownMs).toBe(500);
    expect(snap.tuning.governorEscalationLockMs).toBe(1800);
    expect(snap.tuning.grammarDefaultBlendMs).toBe(400);
    expect(snap.reasons).toContainEqual(
      expect.objectContaining({ trigger: "high-health" }),
    );
  });

  it("responsive does not overwrite governor-busy adjustments", () => {
    const snap = computeAdaptation(mkAnalytics({
      expressiveHealth: 0.9,
      governorInterventionRate: 2,
    }));
    // governor-busy sets cooldown to 1400; high-health would set 500 but existing overrides win
    expect(snap.tuning.governorCooldownMs).toBe(1400);
    expect(snap.tuning.governorEscalationLockMs).toBe(3500);
  });

  // ── Multiple triggers ──

  it("accumulates reasons from multiple triggers", () => {
    const snap = computeAdaptation(mkAnalytics({
      momentumVolatility: 0.8,
      grammarRejectionRate: 1,
      narrativeDensity: 5,
    }));
    expect(snap.reasons.length).toBeGreaterThanOrEqual(3);
  });

  // ── Timestamp ──

  it("includes the provided timestamp", () => {
    const snap = computeAdaptation(mkAnalytics(), 42);
    expect(snap.timestamp).toBe(42);
  });
});
