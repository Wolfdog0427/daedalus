import type { OrchestratedScene } from "./sceneOrchestration";
import type { TimelineSnapshot } from "./timeline";
import type { PersistedScene, ScenePersistenceConfig } from "./scenePersistence";
import { SCENE_PERSISTENCE_ENABLED, PERSISTENCE_DEFAULTS } from "./scenePersistence";
import type { FusionScene } from "./fusion";
import { FUSION_SCENE_IDLE } from "./fusion";

/**
 * Extracts the persistable fields from a live scene + timeline snapshot.
 */
export function serializeScene(
  scene: OrchestratedScene,
  timeline: TimelineSnapshot,
  now: number = Date.now(),
): PersistedScene {
  return {
    timestamp: now,
    sceneName: scene.sceneName,
    mode: scene.mode,
    tone: scene.tone,
    posture: scene.posture,
    glow: scene.glow,
    motion: scene.motion,
    continuityBadge: scene.continuityBadge,
    narrativeLine: scene.narrativeLine,
    momentum: timeline.momentum,
    timelinePhase: timeline.phase,
  };
}

/**
 * Validates a persisted scene: returns null if disabled, expired,
 * or structurally invalid.
 */
export function validatePersistedScene(
  raw: unknown,
  config: ScenePersistenceConfig = PERSISTENCE_DEFAULTS,
  now: number = Date.now(),
): PersistedScene | null {
  if (!SCENE_PERSISTENCE_ENABLED) return null;
  if (!raw || typeof raw !== "object") return null;

  const p = raw as Record<string, unknown>;
  if (typeof p.timestamp !== "number") return null;
  if (typeof p.sceneName !== "string") return null;
  if (typeof p.glow !== "number") return null;
  if (typeof p.motion !== "number") return null;
  if (typeof p.tone !== "string") return null;
  if (typeof p.momentum !== "number") return null;

  const age = now - (p.timestamp as number);
  if (age > config.maxAgeMs || age < 0) return null;

  return p as unknown as PersistedScene;
}

/**
 * Converts a valid PersistedScene back into a FusionScene
 * suitable for injecting into the pipeline on startup.
 */
export function rehydrateScene(persisted: PersistedScene): FusionScene {
  return {
    sceneName: persisted.sceneName,
    mode: persisted.mode ?? FUSION_SCENE_IDLE.mode,
    tone: persisted.tone,
    posture: persisted.posture ?? FUSION_SCENE_IDLE.posture,
    glow: persisted.glow,
    motion: persisted.motion,
    suppressAmbientPulse: false,
    continuityBadge: persisted.continuityBadge ?? null,
    narrativeLine: persisted.narrativeLine ?? null,
  };
}
