import {
  createTelemetryEvent,
  appendToBuffer,
  summarizePayload,
} from "../../shared/daedalus/sceneTelemetryEngine";
import type { TelemetryEvent, TelemetryConfig } from "../../shared/daedalus/sceneTelemetry";
import { TELEMETRY_DEFAULTS } from "../../shared/daedalus/sceneTelemetry";

describe("sceneTelemetryEngine", () => {
  // ── createTelemetryEvent ──

  describe("createTelemetryEvent", () => {
    it("creates an event with the given fields", () => {
      const ev = createTelemetryEvent("scene-transition", { from: "idle", to: "rising" }, 1, 1000);
      expect(ev).toEqual({
        id: 1,
        timestamp: 1000,
        type: "scene-transition",
        payload: { from: "idle", to: "rising" },
      });
    });

    it("defaults timestamp to Date.now()", () => {
      const before = Date.now();
      const ev = createTelemetryEvent("narrative", { line: "test" }, 42);
      expect(ev.timestamp).toBeGreaterThanOrEqual(before);
      expect(ev.timestamp).toBeLessThanOrEqual(Date.now());
      expect(ev.id).toBe(42);
    });

    it("preserves arbitrary payload keys", () => {
      const ev = createTelemetryEvent("momentum", { phase: "peak", momentum: 0.85, custom: true }, 5, 500);
      expect(ev.payload).toEqual({ phase: "peak", momentum: 0.85, custom: true });
    });
  });

  // ── appendToBuffer ──

  describe("appendToBuffer", () => {
    const mkEvent = (id: number): TelemetryEvent => ({
      id,
      timestamp: id * 1000,
      type: "narrative",
      payload: {},
    });

    it("appends events to an empty buffer", () => {
      const result = appendToBuffer([], [mkEvent(1), mkEvent(2)]);
      expect(result).toHaveLength(2);
      expect(result[0].id).toBe(1);
      expect(result[1].id).toBe(2);
    });

    it("appends events to an existing buffer", () => {
      const existing = [mkEvent(1)];
      const result = appendToBuffer(existing, [mkEvent(2)]);
      expect(result).toHaveLength(2);
    });

    it("returns the same buffer when incoming is empty", () => {
      const existing = [mkEvent(1)];
      const result = appendToBuffer(existing, []);
      expect(result).toBe(existing);
    });

    it("trims to maxEvents, keeping most recent", () => {
      const config: TelemetryConfig = { maxEvents: 3 };
      const existing = [mkEvent(1), mkEvent(2)];
      const result = appendToBuffer(existing, [mkEvent(3), mkEvent(4)], config);
      expect(result).toHaveLength(3);
      expect(result[0].id).toBe(2);
      expect(result[1].id).toBe(3);
      expect(result[2].id).toBe(4);
    });

    it("does not trim below maxEvents", () => {
      const config: TelemetryConfig = { maxEvents: 10 };
      const result = appendToBuffer([], [mkEvent(1), mkEvent(2)], config);
      expect(result).toHaveLength(2);
    });

    it("uses default config when not provided", () => {
      const events = Array.from({ length: TELEMETRY_DEFAULTS.maxEvents + 5 }, (_, i) => mkEvent(i));
      const result = appendToBuffer([], events);
      expect(result).toHaveLength(TELEMETRY_DEFAULTS.maxEvents);
      expect(result[0].id).toBe(5);
    });
  });

  // ── summarizePayload ──

  describe("summarizePayload", () => {
    it("summarizes scene-transition", () => {
      const ev = createTelemetryEvent("scene-transition", { from: "idle", to: "rising" }, 1, 0);
      expect(summarizePayload(ev)).toBe("idle → rising");
    });

    it("summarizes scene-rejected", () => {
      const ev = createTelemetryEvent("scene-rejected", { held: "apex" }, 1, 0);
      expect(summarizePayload(ev)).toBe("held at apex");
    });

    it("summarizes blend-start", () => {
      const ev = createTelemetryEvent("blend-start", { scene: "rising", blendMs: 600 }, 1, 0);
      expect(summarizePayload(ev)).toBe("rising (600ms)");
    });

    it("summarizes blend-complete", () => {
      const ev = createTelemetryEvent("blend-complete", { scene: "apex" }, 1, 0);
      expect(summarizePayload(ev)).toBe("apex");
    });

    it("summarizes momentum", () => {
      const ev = createTelemetryEvent("momentum", { prevPhase: "idle", phase: "rising" }, 1, 0);
      expect(summarizePayload(ev)).toBe("idle → rising");
    });

    it("summarizes narrative (truncates long lines)", () => {
      const long = "A".repeat(60);
      const ev = createTelemetryEvent("narrative", { line: long }, 1, 0);
      expect(summarizePayload(ev).length).toBe(40);
    });

    it("summarizes governor-lock", () => {
      const ev = createTelemetryEvent("governor-lock", {}, 1, 0);
      expect(summarizePayload(ev)).toBe("escalation");
    });

    it("summarizes governor-cooldown with mode+tone", () => {
      const ev = createTelemetryEvent("governor-cooldown", { mode: true, tone: true }, 1, 0);
      expect(summarizePayload(ev)).toBe("mode+tone");
    });

    it("summarizes governor-cooldown with mode only", () => {
      const ev = createTelemetryEvent("governor-cooldown", { mode: true, tone: false }, 1, 0);
      expect(summarizePayload(ev)).toBe("mode");
    });

    it("summarizes persistence-restore", () => {
      const ev = createTelemetryEvent("persistence-restore", { scene: "focus" }, 1, 0);
      expect(summarizePayload(ev)).toBe("focus");
    });
  });
});
