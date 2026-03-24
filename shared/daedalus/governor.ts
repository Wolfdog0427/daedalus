import type { ConductorMode, ConductorTone, ConductorOutput } from "./conductor";
import type { DaedalusPosture } from "./contracts";

/** Minimum time between discrete mode/tone transitions. */
export const GOVERNOR_COOLDOWN_MS = 900;

/** Once escalated, mode is held for at least this long. */
export const ESCALATION_LOCK_MS = 2500;

export type GovernorPresetName = "default" | "calm" | "responsive";

export interface GovernorConfig {
  enabled: boolean;
  cooldownMs: number;
  escalationLockMs: number;
}

export const GOVERNOR_PRESETS: Record<GovernorPresetName, GovernorConfig> = {
  default: { enabled: true, cooldownMs: GOVERNOR_COOLDOWN_MS, escalationLockMs: ESCALATION_LOCK_MS },
  calm: { enabled: true, cooldownMs: 1500, escalationLockMs: 4000 },
  responsive: { enabled: true, cooldownMs: 400, escalationLockMs: 1500 },
};

export interface GovernorDisplayInfo {
  enabled: boolean;
  escalationLocked: boolean;
  modeCooldownActive: boolean;
  toneCooldownActive: boolean;
}

export interface GovernorState {
  mode: ConductorMode;
  tone: ConductorTone;
  posture: DaedalusPosture;
  lastModeChangeAt: number;
  lastToneChangeAt: number;
  escalationLockedUntil: number;
}

export function makeInitialGovernorState(seed: ConductorOutput): GovernorState {
  return {
    mode: seed.mode,
    tone: seed.tone,
    posture: seed.posture,
    lastModeChangeAt: 0,
    lastToneChangeAt: 0,
    escalationLockedUntil: 0,
  };
}
