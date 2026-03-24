import { computeTimelineSnapshot, applyTimeline } from "../../shared/daedalus/timelineEngine";
import type { TimelineEvent, TimelineConfig } from "../../shared/daedalus/timeline";
import { TIMELINE_DEFAULTS, TIMELINE_SNAPSHOT_IDLE } from "../../shared/daedalus/timeline";
import type { ConductorOutput } from "../../shared/daedalus/conductor";
import { CONDUCTOR_DEFAULTS } from "../../shared/daedalus/conductor";

function makeEvents(count: number, now: number, spacingMs = 500): TimelineEvent[] {
  return Array.from({ length: count }, (_, i) => ({
    timestamp: now - i * spacingMs,
    kind: "mode" as const,
  }));
}

function makeOutput(overrides: Partial<ConductorOutput> = {}): ConductorOutput {
  return { ...CONDUCTOR_DEFAULTS, updatedAt: Date.now(), ...overrides };
}

describe("computeTimelineSnapshot", () => {
  it("returns idle with no events", () => {
    const snap = computeTimelineSnapshot([], 0, TIMELINE_DEFAULTS, 10000);
    expect(snap.phase).toBe("idle");
    expect(snap.momentum).toBe(0);
    expect(snap.eventCount).toBe(0);
  });

  it("produces positive momentum from recent events", () => {
    const now = 10000;
    const events = makeEvents(3, now, 500);
    const snap = computeTimelineSnapshot(events, 0, TIMELINE_DEFAULTS, now);
    expect(snap.momentum).toBeGreaterThan(0);
    expect(snap.eventCount).toBe(3);
  });

  it("caps momentum at 1", () => {
    const now = 10000;
    const events = makeEvents(20, now, 100);
    const snap = computeTimelineSnapshot(events, 0.9, TIMELINE_DEFAULTS, now);
    expect(snap.momentum).toBeLessThanOrEqual(1);
  });

  it("smooths momentum with previous value", () => {
    const now = 10000;
    const events = makeEvents(1, now);
    const withZeroPrev = computeTimelineSnapshot(events, 0, TIMELINE_DEFAULTS, now);
    const withHighPrev = computeTimelineSnapshot(events, 0.8, TIMELINE_DEFAULTS, now);
    expect(withHighPrev.momentum).toBeGreaterThan(withZeroPrev.momentum);
  });

  it("filters events outside the window", () => {
    const now = 20000;
    const oldEvent: TimelineEvent = { timestamp: now - TIMELINE_DEFAULTS.windowMs - 1000, kind: "mode" };
    const recentEvent: TimelineEvent = { timestamp: now - 100, kind: "tone" };
    const snap = computeTimelineSnapshot([oldEvent, recentEvent], 0, TIMELINE_DEFAULTS, now);
    expect(snap.eventCount).toBe(1);
  });

  it("decays momentum for older events", () => {
    const now = 10000;
    const recent: TimelineEvent[] = [{ timestamp: now, kind: "mode" }];
    const old: TimelineEvent[] = [{ timestamp: now - 5000, kind: "mode" }];

    const snapRecent = computeTimelineSnapshot(recent, 0, TIMELINE_DEFAULTS, now);
    const snapOld = computeTimelineSnapshot(old, 0, TIMELINE_DEFAULTS, now);
    expect(snapRecent.momentum).toBeGreaterThan(snapOld.momentum);
  });

  // ── Phase derivation ──

  it("returns peak when momentum exceeds peakThreshold", () => {
    const snap = computeTimelineSnapshot([], 0.9, TIMELINE_DEFAULTS, 10000);
    // prevMomentum=0.9, rawMomentum=0 → momentum = 0.45
    // That's below peak. Let's use high prevMomentum + events.
    const now = 10000;
    const events = makeEvents(5, now, 200);
    const snap2 = computeTimelineSnapshot(events, 0.8, TIMELINE_DEFAULTS, now);
    expect(snap2.momentum).toBeGreaterThan(TIMELINE_DEFAULTS.peakThreshold);
    expect(snap2.phase).toBe("peak");
  });

  it("returns rising when momentum increases above cooldownThreshold", () => {
    const now = 10000;
    const events = makeEvents(2, now, 300);
    const prevMomentum = 0.2;
    const snap = computeTimelineSnapshot(events, prevMomentum, TIMELINE_DEFAULTS, now);
    if (snap.momentum >= TIMELINE_DEFAULTS.cooldownThreshold && snap.momentum > prevMomentum) {
      expect(snap.phase).toBe("rising");
    }
  });

  it("returns cooldown when momentum decreases above cooldownThreshold", () => {
    const now = 10000;
    const events: TimelineEvent[] = [{ timestamp: now - 4000, kind: "mode" }];
    const prevMomentum = 0.6;
    const snap = computeTimelineSnapshot(events, prevMomentum, TIMELINE_DEFAULTS, now);
    if (snap.momentum >= TIMELINE_DEFAULTS.cooldownThreshold && snap.momentum < prevMomentum) {
      expect(snap.phase).toBe("cooldown");
    }
  });

  it("returns settling when momentum is between 0.1 and cooldownThreshold", () => {
    const now = 10000;
    const events: TimelineEvent[] = [{ timestamp: now - 5000, kind: "mode" }];
    const snap = computeTimelineSnapshot(events, 0.15, TIMELINE_DEFAULTS, now);
    if (snap.momentum >= 0.1 && snap.momentum < TIMELINE_DEFAULTS.cooldownThreshold) {
      expect(snap.phase).toBe("settling");
    }
  });

  it("returns idle when momentum drops below 0.1", () => {
    const now = 20000;
    // All events outside the window → filtered out. prevMomentum is low.
    const events: TimelineEvent[] = [{ timestamp: now - TIMELINE_DEFAULTS.windowMs - 100, kind: "mode" }];
    const snap = computeTimelineSnapshot(events, 0.05, TIMELINE_DEFAULTS, now);
    // rawMomentum = 0 (no windowed events), smoothed = (0 + 0.05) / 2 = 0.025
    expect(snap.momentum).toBeLessThan(0.1);
    expect(snap.phase).toBe("idle");
  });
});

describe("applyTimeline", () => {
  it("returns output unchanged when phase is idle", () => {
    const output = makeOutput({ glowIntensity: 0.5, motionIntensity: 0.5 });
    const result = applyTimeline(output, TIMELINE_SNAPSHOT_IDLE);
    expect(result.glowIntensity).toBe(0.5);
    expect(result.motionIntensity).toBe(0.5);
  });

  it("dampens values at low momentum", () => {
    const output = makeOutput({ glowIntensity: 0.5, motionIntensity: 0.5 });
    const snap = { phase: "settling" as const, momentum: 0.15, eventCount: 1 };
    const result = applyTimeline(output, snap);
    expect(result.glowIntensity).toBeLessThan(0.5);
    expect(result.motionIntensity).toBeLessThan(0.5);
  });

  it("amplifies values at high momentum", () => {
    const output = makeOutput({ glowIntensity: 0.5, motionIntensity: 0.5 });
    const snap = { phase: "peak" as const, momentum: 0.95, eventCount: 5 };
    const result = applyTimeline(output, snap);
    expect(result.glowIntensity).toBeGreaterThan(0.5);
    expect(result.motionIntensity).toBeGreaterThan(0.5);
  });

  it("clamps values to [0, 1]", () => {
    const output = makeOutput({ glowIntensity: 0.95, motionIntensity: 0.95 });
    const snap = { phase: "peak" as const, momentum: 1.0, eventCount: 10 };
    const result = applyTimeline(output, snap);
    expect(result.glowIntensity).toBeLessThanOrEqual(1);
    expect(result.motionIntensity).toBeLessThanOrEqual(1);
  });

  it("preserves discrete values (mode, tone, posture)", () => {
    const output = makeOutput({ mode: "attentive", tone: "focused", posture: "sentinel" });
    const snap = { phase: "rising" as const, momentum: 0.6, eventCount: 3 };
    const result = applyTimeline(output, snap);
    expect(result.mode).toBe("attentive");
    expect(result.tone).toBe("focused");
    expect(result.posture).toBe("sentinel");
  });
});
