/**
 * Identity Continuity Checks
 *
 * Tracks drift between successive identity snapshots. Each tick,
 * the current identity state (posture, mode, governance tier) is
 * compared against the previous. Drift is scored:
 *
 *   posture change     → 10 pts
 *   mode change        → 15 pts
 *   governance tier Δ  → 20 pts
 *
 * Continuity = max(0, 100 - driftScore). This score is blended
 * into the identity axis of the alignment breakdown.
 */

export interface IdentitySnapshot {
  posture?: string;
  mode?: string;
  governanceTier?: string;
}

let lastIdentitySnapshot: IdentitySnapshot | null = null;

export function computeIdentityContinuity(current: IdentitySnapshot): number {
  if (!lastIdentitySnapshot) {
    lastIdentitySnapshot = { ...current };
    return 100;
  }

  let driftScore = 0;

  if (current.posture !== lastIdentitySnapshot.posture) {
    driftScore += 10;
  }

  if (current.mode !== lastIdentitySnapshot.mode) {
    driftScore += 15;
  }

  if (current.governanceTier !== lastIdentitySnapshot.governanceTier) {
    driftScore += 20;
  }

  lastIdentitySnapshot = { ...current };

  return Math.max(0, 100 - driftScore);
}

export function getLastIdentitySnapshot(): IdentitySnapshot | null {
  return lastIdentitySnapshot ? { ...lastIdentitySnapshot } : null;
}

export function resetIdentityState(): void {
  lastIdentitySnapshot = null;
}
