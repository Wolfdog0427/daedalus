import { narrateContinuity, formatRecency } from "../../shared/daedalus/continuityNarrator";
import type { BeingPresenceDetail } from "../../shared/daedalus/contracts";

function makeBeing(overrides: Partial<BeingPresenceDetail> = {}): BeingPresenceDetail {
  return {
    id: "a",
    name: "Alpha",
    posture: "companion",
    glow: { level: "medium", intensity: 0.5 },
    attention: { level: "focused" },
    heartbeat: 1,
    influenceLevel: 0.8,
    presenceMode: "active",
    isSpeaking: false,
    isGuiding: false,
    continuity: { streak: 5, lastCheckIn: new Date().toISOString(), healthy: true },
    autopilot: { enabled: false, scope: "none" },
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe("formatRecency", () => {
  it("returns 'just now' for recent timestamps", () => {
    const now = Date.now();
    expect(formatRecency(new Date(now - 10_000).toISOString(), now)).toBe("just now");
  });

  it("returns minutes for short deltas", () => {
    const now = Date.now();
    expect(formatRecency(new Date(now - 5 * 60_000).toISOString(), now)).toBe("5m ago");
  });

  it("returns hours for medium deltas", () => {
    const now = Date.now();
    expect(formatRecency(new Date(now - 3 * 3_600_000).toISOString(), now)).toBe("3h ago");
  });

  it("returns days for long deltas", () => {
    const now = Date.now();
    expect(formatRecency(new Date(now - 2 * 86_400_000).toISOString(), now)).toBe("2d ago");
  });
});

describe("narrateContinuity", () => {
  it("returns empty for no beings", () => {
    expect(narrateContinuity({})).toEqual([]);
  });

  it("emits threshold signal when streak equals a threshold", () => {
    const beings = { a: makeBeing({ continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true } }) };
    const signals = narrateContinuity(beings);
    expect(signals.some((s) => s.kind === "threshold" && s.label.includes("10"))).toBe(true);
  });

  it("emits newly-joined signal when streak is 0 or 1", () => {
    const beings = { a: makeBeing({ continuity: { streak: 1, lastCheckIn: new Date().toISOString(), healthy: true } }) };
    const signals = narrateContinuity(beings);
    expect(signals.some((s) => s.kind === "streak" && s.label === "Newly joined")).toBe(true);
  });

  it("emits recency signal when lastCheckIn is over 1 hour ago", () => {
    const now = Date.now();
    const oldCheckIn = new Date(now - 2 * 3_600_000).toISOString();
    const beings = { a: makeBeing({ continuity: { streak: 5, lastCheckIn: oldCheckIn, healthy: true } }) };
    const signals = narrateContinuity(beings, {}, now);
    expect(signals.some((s) => s.kind === "recency" && s.label === "Returning after a while")).toBe(true);
  });

  it("does not emit recency signal when lastCheckIn is recent", () => {
    const now = Date.now();
    const recentCheckIn = new Date(now - 60_000).toISOString();
    const beings = { a: makeBeing({ continuity: { streak: 5, lastCheckIn: recentCheckIn, healthy: true } }) };
    const signals = narrateContinuity(beings, {}, now);
    expect(signals.some((s) => s.kind === "recency")).toBe(false);
  });

  it("emits drift-recovery when being was unhealthy and is now healthy", () => {
    const beings = { a: makeBeing({ continuity: { streak: 5, lastCheckIn: new Date().toISOString(), healthy: true } }) };
    const prevHealth = { a: false };
    const signals = narrateContinuity(beings, prevHealth);
    expect(signals.some((s) => s.kind === "drift-recovery" && s.label === "Recovered")).toBe(true);
  });

  it("does not emit drift-recovery when being was already healthy", () => {
    const beings = { a: makeBeing({ continuity: { streak: 5, lastCheckIn: new Date().toISOString(), healthy: true } }) };
    const prevHealth = { a: true };
    const signals = narrateContinuity(beings, prevHealth);
    expect(signals.some((s) => s.kind === "drift-recovery")).toBe(false);
  });

  it("emits anchor signal when multiple beings and one has highest streak", () => {
    const now = Date.now();
    const beings = {
      a: makeBeing({ id: "a", name: "Alpha", continuity: { streak: 12, lastCheckIn: new Date(now).toISOString(), healthy: true } }),
      b: makeBeing({ id: "b", name: "Beta", continuity: { streak: 3, lastCheckIn: new Date(now).toISOString(), healthy: true } }),
    };
    const signals = narrateContinuity(beings, {}, now);
    expect(signals.some((s) => s.kind === "anchor" && s.beingName === "Alpha")).toBe(true);
  });

  it("does not emit anchor signal for a single being", () => {
    const beings = { a: makeBeing({ continuity: { streak: 20, lastCheckIn: new Date().toISOString(), healthy: true } }) };
    const signals = narrateContinuity(beings);
    expect(signals.some((s) => s.kind === "anchor")).toBe(false);
  });

  it("does not emit anchor signal when max streak is <=3", () => {
    const now = Date.now();
    const beings = {
      a: makeBeing({ id: "a", name: "Alpha", continuity: { streak: 2, lastCheckIn: new Date(now).toISOString(), healthy: true } }),
      b: makeBeing({ id: "b", name: "Beta", continuity: { streak: 3, lastCheckIn: new Date(now).toISOString(), healthy: true } }),
    };
    const signals = narrateContinuity(beings, {}, now);
    expect(signals.some((s) => s.kind === "anchor")).toBe(false);
  });
});
