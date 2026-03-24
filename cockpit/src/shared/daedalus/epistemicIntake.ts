/**
 * Epistemic Intake — source quality scoring and verification gating.
 *
 * Evaluates the trustworthiness of data entering the system based on
 * connectivity state (node trust, quarantine rate, network quality).
 * Read-only diagnostic — never feeds back into governance logic.
 */

export interface EpistemicReport {
  readonly overallQuality: number;
  readonly trustedRatio: number;
  readonly quarantinedRatio: number;
  readonly connectivityPenalty: number;
  readonly healthy: boolean;

  readonly freshness: number;
  readonly unverifiedCount: number;
  readonly unverifiedWarning: boolean;
}

export const EPISTEMIC_IDLE: EpistemicReport = Object.freeze({
  overallQuality: 1,
  trustedRatio: 1,
  quarantinedRatio: 0,
  connectivityPenalty: 0,
  healthy: true,

  freshness: 1,
  unverifiedCount: 0,
  unverifiedWarning: false,
});
