import type { BeingPresenceDetail } from "./contracts";

export type ContinuitySignalKind = "recency" | "streak" | "threshold" | "drift-recovery" | "anchor";

export interface ContinuitySignal {
  kind: ContinuitySignalKind;
  beingId: string;
  beingName: string;
  label: string;
  detail?: string;
}

/** Feature toggle: set to false to suppress all continuity signals. */
export const CONTINUITY_NARRATOR_ENABLED = true;

const STREAK_THRESHOLDS = [5, 10, 25, 50, 100];

function formatRecency(lastCheckIn: string, now: number): string {
  const delta = now - new Date(lastCheckIn).getTime();
  if (delta < 0) return "just now";
  const seconds = Math.floor(delta / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function isReturningAfterAbsence(lastCheckIn: string, now: number): boolean {
  const delta = now - new Date(lastCheckIn).getTime();
  return delta > 3_600_000;
}

function crossedThreshold(streak: number): number | null {
  for (let i = STREAK_THRESHOLDS.length - 1; i >= 0; i--) {
    if (streak === STREAK_THRESHOLDS[i]) return STREAK_THRESHOLDS[i];
  }
  return null;
}

export function narrateContinuity(
  beings: Record<string, BeingPresenceDetail>,
  prevHealthMap?: Record<string, boolean>,
  now: number = Date.now(),
): ContinuitySignal[] {
  if (!CONTINUITY_NARRATOR_ENABLED) return [];

  const list = Object.values(beings);
  if (list.length === 0) return [];

  const signals: ContinuitySignal[] = [];

  let anchorBeing: BeingPresenceDetail | null = null;
  let maxStreak = -1;

  for (const b of list) {
    const recencyText = formatRecency(b.continuity.lastCheckIn, now);
    const returning = isReturningAfterAbsence(b.continuity.lastCheckIn, now);

    if (returning) {
      signals.push({
        kind: "recency",
        beingId: b.id,
        beingName: b.name,
        label: "Returning after a while",
        detail: `Last seen ${recencyText}`,
      });
    }

    if (b.continuity.streak <= 1) {
      signals.push({
        kind: "streak",
        beingId: b.id,
        beingName: b.name,
        label: "Newly joined",
      });
    } else {
      const threshold = crossedThreshold(b.continuity.streak);
      if (threshold !== null) {
        signals.push({
          kind: "threshold",
          beingId: b.id,
          beingName: b.name,
          label: `Crossed ${threshold} consecutive check-ins`,
        });
      }
    }

    if (prevHealthMap && prevHealthMap[b.id] === false && b.continuity.healthy) {
      signals.push({
        kind: "drift-recovery",
        beingId: b.id,
        beingName: b.name,
        label: "Recovered",
        detail: "Was drifting, now healthy",
      });
    }

    if (b.continuity.streak > maxStreak) {
      maxStreak = b.continuity.streak;
      anchorBeing = b;
    }
  }

  if (anchorBeing && list.length > 1 && maxStreak > 3) {
    signals.push({
      kind: "anchor",
      beingId: anchorBeing.id,
      beingName: anchorBeing.name,
      label: "Longest-running presence",
      detail: `Stable for ${maxStreak} check-ins`,
    });
  }

  return signals;
}

export { STREAK_THRESHOLDS, formatRecency };
