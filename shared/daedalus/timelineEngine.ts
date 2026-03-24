import type { ConductorOutput } from "./conductor";
import type {
  TimelineEvent,
  TimelineSnapshot,
  TimelineConfig,
  TimelinePhase,
} from "./timeline";
import { TIMELINE_ENABLED, TIMELINE_DEFAULTS, TIMELINE_SNAPSHOT_IDLE } from "./timeline";

function clamp(v: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, v));
}

function derivePhase(
  momentum: number,
  prevMomentum: number,
  config: TimelineConfig,
): TimelinePhase {
  if (momentum >= config.peakThreshold) return "peak";
  if (momentum < 0.1) return "idle";

  const rising = momentum >= prevMomentum;
  if (momentum >= config.cooldownThreshold) {
    return rising ? "rising" : "cooldown";
  }
  return "settling";
}

/**
 * Computes a timeline snapshot from a list of discrete transition events.
 *
 * Momentum is a decay-weighted sum of recent events, smoothed with the
 * previous value. Phase is derived from momentum magnitude and direction.
 */
export function computeTimelineSnapshot(
  events: TimelineEvent[],
  prevMomentum: number,
  config: TimelineConfig = TIMELINE_DEFAULTS,
  now: number = Date.now(),
): TimelineSnapshot {
  if (!TIMELINE_ENABLED) return TIMELINE_SNAPSHOT_IDLE;

  const cutoff = now - config.windowMs;
  const windowed = events.filter((e) => e.timestamp >= cutoff);

  let rawMomentum = 0;
  for (const e of windowed) {
    const age = now - e.timestamp;
    rawMomentum += Math.exp(-age / config.momentumHalfLifeMs);
  }
  rawMomentum = Math.min(1, rawMomentum);

  const momentum = (rawMomentum + prevMomentum) / 2;
  const phase = derivePhase(momentum, prevMomentum, config);

  return {
    phase,
    momentum,
    eventCount: windowed.length,
  };
}

/**
 * Modulates the conductor's continuous values based on timeline momentum.
 *
 * Momentum amplifies glow (0.9–1.2x) and motion (0.8–1.2x), creating
 * organic intensity curves tied to recent expressive activity.
 *
 * Discrete values (mode, tone, posture) pass through unchanged — those
 * are the conductor's and governor's responsibility.
 */
export function applyTimeline(
  output: ConductorOutput,
  snapshot: TimelineSnapshot,
): ConductorOutput {
  if (!TIMELINE_ENABLED || snapshot.phase === "idle") return output;

  const m = snapshot.momentum;
  return {
    ...output,
    glowIntensity: clamp(output.glowIntensity * (0.9 + m * 0.3)),
    motionIntensity: clamp(output.motionIntensity * (0.8 + m * 0.4)),
  };
}
