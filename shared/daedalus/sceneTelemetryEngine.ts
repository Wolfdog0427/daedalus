import type {
  TelemetryEvent,
  TelemetryEventType,
  TelemetryConfig,
} from "./sceneTelemetry";
import { TELEMETRY_DEFAULTS } from "./sceneTelemetry";

/**
 * Creates a telemetry event with a given sequential ID.
 */
export function createTelemetryEvent(
  type: TelemetryEventType,
  payload: Record<string, unknown>,
  id: number,
  now: number = Date.now(),
): TelemetryEvent {
  return { id, timestamp: now, type, payload };
}

/**
 * Appends events to a buffer, trimming to maxEvents from the end.
 */
export function appendToBuffer(
  buffer: TelemetryEvent[],
  incoming: TelemetryEvent[],
  config: TelemetryConfig = TELEMETRY_DEFAULTS,
): TelemetryEvent[] {
  if (incoming.length === 0) return buffer;
  const merged = [...buffer, ...incoming];
  return merged.length > config.maxEvents
    ? merged.slice(merged.length - config.maxEvents)
    : merged;
}

/**
 * Formats a telemetry event's payload into a short summary string
 * for HUD display.
 */
export function summarizePayload(event: TelemetryEvent): string {
  switch (event.type) {
    case "scene-transition":
      return `${event.payload.from} → ${event.payload.to}`;
    case "scene-rejected":
      return `held at ${event.payload.held}`;
    case "blend-start":
      return `${event.payload.scene} (${event.payload.blendMs}ms)`;
    case "blend-complete":
      return `${event.payload.scene}`;
    case "momentum":
      return `${event.payload.prevPhase} → ${event.payload.phase}`;
    case "narrative":
      return String(event.payload.line).slice(0, 40);
    case "governor-lock":
      return "escalation";
    case "governor-cooldown": {
      const parts: string[] = [];
      if (event.payload.mode) parts.push("mode");
      if (event.payload.tone) parts.push("tone");
      return parts.join("+") || "active";
    }
    case "persistence-restore":
      return `${event.payload.scene}`;
    default:
      return "";
  }
}
