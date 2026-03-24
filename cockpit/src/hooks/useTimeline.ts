import { useMemo, useRef } from "react";
import type { ConductorOutput } from "../shared/daedalus/conductor";
import type { TimelineEvent, TimelineSnapshot, TimelineConfig } from "../shared/daedalus/timeline";
import { TIMELINE_DEFAULTS, TIMELINE_SNAPSHOT_IDLE } from "../shared/daedalus/timeline";
import { computeTimelineSnapshot, applyTimeline } from "../shared/daedalus/timelineEngine";

interface PrevValues {
  mode: string;
  tone: string;
  posture: string;
  hasBadge: boolean;
}

export interface TimelineResult {
  output: ConductorOutput;
  snapshot: TimelineSnapshot;
}

/**
 * Observes discrete transitions in the governed output, records them as
 * timeline events, and applies momentum-based modulation to glow/motion.
 */
export function useTimeline(
  governed: ConductorOutput,
  config: TimelineConfig = TIMELINE_DEFAULTS,
): TimelineResult {
  const eventsRef = useRef<TimelineEvent[]>([]);
  const prevRef = useRef<PrevValues | null>(null);
  const prevMomentumRef = useRef(0);

  return useMemo(() => {
    const now = Date.now();

    if (prevRef.current) {
      const prev = prevRef.current;
      if (governed.mode !== prev.mode) {
        eventsRef.current.push({ timestamp: now, kind: "mode" });
      }
      if (governed.tone !== prev.tone) {
        eventsRef.current.push({ timestamp: now, kind: "tone" });
      }
      if (governed.posture !== prev.posture) {
        eventsRef.current.push({ timestamp: now, kind: "posture" });
      }
      const hasBadge = governed.continuityBadge !== null;
      if (hasBadge && !prev.hasBadge) {
        eventsRef.current.push({ timestamp: now, kind: "badge" });
      }
    }

    prevRef.current = {
      mode: governed.mode,
      tone: governed.tone,
      posture: governed.posture,
      hasBadge: governed.continuityBadge !== null,
    };

    const snapshot = computeTimelineSnapshot(
      eventsRef.current,
      prevMomentumRef.current,
      config,
      now,
    );
    prevMomentumRef.current = snapshot.momentum;

    const cutoff = now - config.windowMs;
    eventsRef.current = eventsRef.current.filter((e) => e.timestamp >= cutoff);

    const output = applyTimeline(governed, snapshot);

    return { output, snapshot };
  }, [governed, config]);
}
