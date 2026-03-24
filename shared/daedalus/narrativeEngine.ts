import type { NarrativeInput, NarrativeOutput, NarrativeConfig } from "./narrative";
import type { ConductorTone } from "./conductor";
import { NARRATIVE_ENABLED, NARRATIVE_DEFAULTS, NARRATIVE_SILENT } from "./narrative";

/**
 * Generates a single narrative line from expressive state.
 *
 * Priority:
 *   1. Timeline phase (arc transitions)
 *   2. Continuity badge (milestone acknowledgments)
 *   3. Posture (sentinel/observer signals)
 *   4. Affect (exploratory/focused whispers)
 *
 * Returns `{ line: null }` when:
 *   - Narrative is disabled
 *   - Rate-limit hasn't elapsed
 *   - Momentum is below threshold (no expressive energy)
 *   - No narrative condition is met
 */
export function generateNarrative(
  input: NarrativeInput,
  lastSpokenAt: number,
  config: NarrativeConfig = NARRATIVE_DEFAULTS,
  now: number = Date.now(),
): NarrativeOutput {
  if (!NARRATIVE_ENABLED) return NARRATIVE_SILENT;
  if ((now - lastSpokenAt) < config.minIntervalMs) return NARRATIVE_SILENT;
  if (input.momentum < config.momentumThreshold) return NARRATIVE_SILENT;

  let line: string | null = null;
  let tone: ConductorTone = "neutral";

  // ── 1. Timeline-driven arcs ───────────────────────────────────
  switch (input.timelinePhase) {
    case "rising":
      line = "The field is gathering.";
      tone = "focused";
      break;
    case "peak":
      line = "The field is at full height.";
      tone = "celebratory";
      break;
    case "cooldown":
      line = "The field is easing.";
      tone = "neutral";
      break;
    case "settling":
      line = "The field is settling.";
      tone = "neutral";
      break;
  }

  // ── 2. Continuity milestones ──────────────────────────────────
  if (!line && input.continuityBadgeLabel) {
    line = input.continuityBadgeLabel;
    tone = "celebratory";
  }

  // ── 3. Posture signals ────────────────────────────────────────
  if (!line) {
    if (input.posture === "sentinel") {
      line = "A threshold is guarded.";
      tone = "alert";
    } else if (input.posture === "observer") {
      line = "Attention holds steady.";
      tone = "focused";
    }
  }

  // ── 4. Affect whispers ────────────────────────────────────────
  if (!line) {
    if (input.affect === "exploratory") {
      line = "The field is open.";
      tone = "neutral";
    } else if (input.affect === "focused") {
      line = "The field narrows.";
      tone = "focused";
    }
  }

  if (!line) return NARRATIVE_SILENT;

  return { line, tone };
}
