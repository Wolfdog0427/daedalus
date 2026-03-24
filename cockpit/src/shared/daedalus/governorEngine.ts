import type { ConductorOutput, ConductorMode, ConductorTone } from "./conductor";
import type { GovernorState, GovernorConfig, GovernorDisplayInfo } from "./governor";
import { GOVERNOR_PRESETS } from "./governor";

/**
 * Applies temporal stability to the conductor's output.
 *
 * Three mechanisms:
 *   1. Escalation lock — entering "escalated" mode starts a mandatory hold;
 *      the mode cannot drop until the lock expires.
 *   2. Mode hysteresis — mode transitions are blocked during the cooldown window.
 *   3. Tone hysteresis — tone transitions are blocked during the cooldown window.
 *
 * Continuous values (glowIntensity, motionIntensity) pass through unchanged;
 * CSS transitions handle their smoothing.
 */
export function governOutput(
  raw: ConductorOutput,
  prev: GovernorState,
  now: number = Date.now(),
  config: GovernorConfig = GOVERNOR_PRESETS.default,
): { governed: ConductorOutput; nextState: GovernorState } {
  if (!config.enabled) {
    return {
      governed: raw,
      nextState: { ...prev, mode: raw.mode, tone: raw.tone, posture: raw.posture },
    };
  }

  let { lastModeChangeAt, lastToneChangeAt, escalationLockedUntil } = prev;

  // ── 1. Escalation lock ────────────────────────────────────────
  // Entering or staying in escalation resets the lock timer.
  if (raw.mode === "escalated") {
    escalationLockedUntil = now + config.escalationLockMs;
  }

  let mode: ConductorMode;
  let tone: ConductorTone;

  const inEscalationLock = now < escalationLockedUntil;

  if (inEscalationLock) {
    mode = "escalated";
    tone = "alert";
  } else {
    // ── 2. Mode hysteresis ────────────────────────────────────
    if (raw.mode !== prev.mode && (now - lastModeChangeAt) < config.cooldownMs) {
      mode = prev.mode;
    } else {
      mode = raw.mode;
    }

    // ── 3. Tone hysteresis ────────────────────────────────────
    if (raw.tone !== prev.tone && (now - lastToneChangeAt) < config.cooldownMs) {
      tone = prev.tone;
    } else {
      tone = raw.tone;
    }
  }

  // Track when governed values actually change
  if (mode !== prev.mode) lastModeChangeAt = now;
  if (tone !== prev.tone) lastToneChangeAt = now;

  // Posture follows mode: if mode was held back, hold posture too
  const posture = mode !== raw.mode ? prev.posture : raw.posture;

  // Suppress ambient pulse whenever escalated; otherwise use conductor's decision
  const suppressAmbientPulse = mode === "escalated" || raw.suppressAmbientPulse;

  // Suppress continuity badge during escalation lock
  const continuityBadge = inEscalationLock ? null : raw.continuityBadge;

  const governed: ConductorOutput = {
    ...raw,
    mode,
    tone,
    posture,
    suppressAmbientPulse,
    continuityBadge,
  };

  const nextState: GovernorState = {
    mode,
    tone,
    posture,
    lastModeChangeAt,
    lastToneChangeAt,
    escalationLockedUntil,
  };

  return { governed, nextState };
}

/** Derives operator-facing display info from the governor's internal state. */
export function computeGovernorDisplay(
  state: GovernorState,
  config: GovernorConfig,
  now: number = Date.now(),
): GovernorDisplayInfo {
  return {
    enabled: config.enabled,
    escalationLocked: now < state.escalationLockedUntil,
    modeCooldownActive: (now - state.lastModeChangeAt) < config.cooldownMs,
    toneCooldownActive: (now - state.lastToneChangeAt) < config.cooldownMs,
  };
}
