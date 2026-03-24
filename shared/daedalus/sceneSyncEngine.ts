import type { OrchestratedScene } from "./sceneOrchestration";
import type { SceneSurfaceProps } from "./sceneSurfaces";
import type { SceneFrame } from "./sceneSync";
import { SCENE_SYNC_ENABLED } from "./sceneSync";
import { mapSceneToSurfaces, surfacesToCssVars } from "./sceneSurfacesEngine";
import { SURFACE_DEFAULTS } from "./sceneSurfaces";

/**
 * Composes a synchronized SceneFrame from an OrchestratedScene.
 *
 * When SCENE_SYNC_ENABLED is false, surfaces fall back to defaults
 * but the scene is still passed through for UI consumption.
 */
export function composeSceneFrame(
  scene: OrchestratedScene,
  frameId: number,
  now: number = Date.now(),
): SceneFrame {
  const surfaces = SCENE_SYNC_ENABLED
    ? mapSceneToSurfaces(scene)
    : SURFACE_DEFAULTS;
  const cssVars = surfacesToCssVars(surfaces);

  return {
    timestamp: now,
    frameId,
    scene,
    surfaces,
    cssVars,
  };
}
