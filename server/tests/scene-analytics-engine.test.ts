import { computeAnalytics } from "../../shared/daedalus/sceneAnalyticsEngine";
import type { TelemetryEvent } from "../../shared/daedalus/sceneTelemetry";
import type { AnalyticsConfig } from "../../shared/daedalus/sceneAnalytics";

function mkEvent(
  type: TelemetryEvent["type"],
  payload: Record<string, unknown> = {},
  timestamp = 1000,
): TelemetryEvent {
  return { id: Math.random(), timestamp, type, payload };
}

const NOW = 10_000;
const WINDOW: AnalyticsConfig = { windowMs: 20_000 };

describe("computeAnalytics", () => {
  // ── Empty / idle ──

  it("returns idle snapshot when no events exist", () => {
    const snap = computeAnalytics([], WINDOW, NOW);
    expect(snap.sceneStability).toBe(1);
    expect(snap.transitionSmoothness).toBe(1);
    expect(snap.momentumVolatility).toBe(0);
    expect(snap.narrativeDensity).toBe(0);
    expect(snap.governorInterventionRate).toBe(0);
    expect(snap.grammarRejectionRate).toBe(0);
    expect(snap.expressiveHealth).toBe(1);
    expect(snap.timestamp).toBe(NOW);
  });

  it("filters events outside the time window", () => {
    const ancient = mkEvent("scene-transition", {}, 1);
    const snap = computeAnalytics([ancient], { windowMs: 5_000 }, NOW);
    expect(snap.sceneStability).toBe(1);
  });

  // ── Scene stability ──

  it("computes full stability when all transitions succeed", () => {
    const events = [
      mkEvent("scene-transition", {}, NOW - 100),
      mkEvent("scene-transition", {}, NOW - 200),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.sceneStability).toBe(1);
  });

  it("computes reduced stability when rejections occur", () => {
    const events = [
      mkEvent("scene-transition", {}, NOW - 100),
      mkEvent("scene-rejected", {}, NOW - 200),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.sceneStability).toBe(0.5);
  });

  it("computes zero stability when all attempts are rejected", () => {
    const events = [
      mkEvent("scene-rejected", {}, NOW - 100),
      mkEvent("scene-rejected", {}, NOW - 200),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.sceneStability).toBe(0);
  });

  // ── Transition smoothness ──

  it("computes full smoothness when all blends complete", () => {
    const events = [
      mkEvent("blend-start", {}, NOW - 300),
      mkEvent("blend-complete", {}, NOW - 100),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.transitionSmoothness).toBe(1);
  });

  it("computes reduced smoothness when blends don't complete", () => {
    const events = [
      mkEvent("blend-start", {}, NOW - 300),
      mkEvent("blend-start", {}, NOW - 200),
      mkEvent("blend-complete", {}, NOW - 100),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.transitionSmoothness).toBe(0.5);
  });

  it("returns full smoothness when no blends occurred", () => {
    const snap = computeAnalytics(
      [mkEvent("narrative", {}, NOW - 100)],
      WINDOW,
      NOW,
    );
    expect(snap.transitionSmoothness).toBe(1);
  });

  // ── Momentum volatility ──

  it("returns zero volatility with fewer than 2 momentum events", () => {
    const events = [
      mkEvent("momentum", { momentum: 0.5 }, NOW - 100),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.momentumVolatility).toBe(0);
  });

  it("returns zero volatility when all momentum values are identical", () => {
    const events = [
      mkEvent("momentum", { momentum: 0.5 }, NOW - 200),
      mkEvent("momentum", { momentum: 0.5 }, NOW - 100),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.momentumVolatility).toBe(0);
  });

  it("returns non-zero volatility when momentum values vary", () => {
    const events = [
      mkEvent("momentum", { momentum: 0.0 }, NOW - 300),
      mkEvent("momentum", { momentum: 1.0 }, NOW - 200),
      mkEvent("momentum", { momentum: 0.0 }, NOW - 100),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.momentumVolatility).toBeGreaterThan(0.5);
  });

  it("clamps volatility to 1", () => {
    const events = [
      mkEvent("momentum", { momentum: 0.0 }, NOW - 200),
      mkEvent("momentum", { momentum: 1.0 }, NOW - 100),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.momentumVolatility).toBeLessThanOrEqual(1);
  });

  it("treats non-numeric momentum as 0", () => {
    const events = [
      mkEvent("momentum", { momentum: "bad" }, NOW - 200),
      mkEvent("momentum", { momentum: 0.5 }, NOW - 100),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.momentumVolatility).toBeGreaterThan(0);
  });

  // ── Rates ──

  it("computes narrative density as events per minute", () => {
    const config: AnalyticsConfig = { windowMs: 60_000 };
    const events = [
      mkEvent("narrative", {}, NOW - 100),
      mkEvent("narrative", {}, NOW - 200),
      mkEvent("narrative", {}, NOW - 300),
    ];
    const snap = computeAnalytics(events, config, NOW);
    expect(snap.narrativeDensity).toBe(3);
  });

  it("computes governor intervention rate", () => {
    const config: AnalyticsConfig = { windowMs: 60_000 };
    const events = [
      mkEvent("governor-lock", {}, NOW - 100),
      mkEvent("governor-cooldown", {}, NOW - 200),
    ];
    const snap = computeAnalytics(events, config, NOW);
    expect(snap.governorInterventionRate).toBe(2);
  });

  it("computes grammar rejection rate", () => {
    const config: AnalyticsConfig = { windowMs: 60_000 };
    const events = [
      mkEvent("scene-rejected", {}, NOW - 100),
    ];
    const snap = computeAnalytics(events, config, NOW);
    expect(snap.grammarRejectionRate).toBe(1);
  });

  // ── Expressive health ──

  it("returns high health when everything is stable", () => {
    const events = [
      mkEvent("scene-transition", {}, NOW - 100),
      mkEvent("blend-start", {}, NOW - 90),
      mkEvent("blend-complete", {}, NOW - 50),
    ];
    const snap = computeAnalytics(events, WINDOW, NOW);
    expect(snap.expressiveHealth).toBeGreaterThan(0.85);
  });

  it("returns reduced health when rejections and cooldowns are high", () => {
    const config: AnalyticsConfig = { windowMs: 60_000 };
    const events: TelemetryEvent[] = [];
    for (let i = 0; i < 20; i++) {
      events.push(mkEvent("scene-rejected", {}, NOW - i * 100));
      events.push(mkEvent("governor-cooldown", {}, NOW - i * 100));
    }
    const snap = computeAnalytics(events, config, NOW);
    expect(snap.expressiveHealth).toBeLessThan(0.7);
  });

  it("clamps health to [0, 1]", () => {
    const snap = computeAnalytics([], WINDOW, NOW);
    expect(snap.expressiveHealth).toBeGreaterThanOrEqual(0);
    expect(snap.expressiveHealth).toBeLessThanOrEqual(1);
  });

  // ── Timestamp ──

  it("includes the provided timestamp", () => {
    const snap = computeAnalytics([], WINDOW, 42);
    expect(snap.timestamp).toBe(42);
  });
});
