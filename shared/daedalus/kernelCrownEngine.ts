import type { KernelHaloSnapshot } from "./kernelHalo";
import type { CrownState, CrownSymbol } from "./kernelCrown";

function clamp(v: number, lo = 0, hi = 1): number {
  return Math.min(hi, Math.max(lo, v));
}

/**
 * Derives the crown's expressive state from the halo snapshot.
 *
 * - glow:      kernel warmth/activity (0–1)
 * - pulse:     urgency from pending proposals (0–1)
 * - stability: system coherence (1 = fully coherent, 0 = under stress)
 * - symbol:    one-word identity for the current governance mood
 */
export function computeCrownState(halo: KernelHaloSnapshot): CrownState {
  // ── symbol ──
  let symbol: CrownSymbol;
  if (halo.shellStatus === "degraded") {
    symbol = "shielded";
  } else if (halo.kernelStatus === "escalated" || halo.pendingCount > 0) {
    symbol = "vigilant";
  } else if (halo.kernelStatus === "tuned") {
    symbol = "attentive";
  } else {
    symbol = "serene";
  }

  // ── glow ──
  let glow: number;
  switch (symbol) {
    case "shielded":  glow = 0.15; break;
    case "vigilant":  glow = 0.9;  break;
    case "attentive": glow = 0.6;  break;
    default:          glow = 0.3;
  }

  // ── pulse ──
  let pulse: number;
  if (halo.shellStatus === "degraded") {
    pulse = 0.5;
  } else {
    pulse = clamp(halo.pendingCount * 0.3);
  }

  // ── stability ──
  const overridePenalty = halo.overrideCount * 0.08;
  const invariantPenalty = halo.failedInvariants.length * 0.15;
  const capPenalty = halo.cappingApplied ? 0.1 : 0;
  const stability = clamp(1 - overridePenalty - invariantPenalty - capPenalty);

  return Object.freeze({ symbol, glow, pulse, stability });
}
