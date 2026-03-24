import type { FusionSceneName } from "./fusion";
import type { ConductorMode, ConductorTone, ConductorBadge } from "./conductor";
import type { DaedalusPosture } from "./contracts";
import type { TimelinePhase } from "./timeline";

/** Feature toggle: set to false to disable persistence entirely. */
export const SCENE_PERSISTENCE_ENABLED = true;

export interface PersistedScene {
  timestamp: number;
  sceneName: FusionSceneName;
  mode: ConductorMode;
  tone: ConductorTone;
  posture: DaedalusPosture;
  glow: number;
  motion: number;
  continuityBadge: ConductorBadge | null;
  narrativeLine: string | null;
  momentum: number;
  timelinePhase: TimelinePhase;
}

export interface ScenePersistenceConfig {
  storageKey: string;
  maxAgeMs: number;
  saveIntervalMs: number;
}

export const PERSISTENCE_DEFAULTS: ScenePersistenceConfig = {
  storageKey: "daedalus.expressive.scene",
  maxAgeMs: 6 * 60 * 60 * 1000, // 6 hours
  saveIntervalMs: 2000, // debounce: save at most every 2s
};
