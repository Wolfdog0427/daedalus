import type { OrchestratedScene } from "./sceneOrchestration";
import type { SceneSurfaceProps } from "./sceneSurfaces";

/** Feature toggle: set to false to bypass frame synchronization. */
export const SCENE_SYNC_ENABLED = true;

/**
 * A single synchronized expressive frame — the authoritative snapshot
 * consumed by all UI surfaces in the same render pass.
 *
 * Guarantees:
 * - `scene` and `surfaces` are derived from the same orchestrated state.
 * - `frameId` is monotonically increasing.
 * - No partial updates: every consumer reads from the same frame.
 */
export interface SceneFrame {
  timestamp: number;
  frameId: number;
  scene: OrchestratedScene;
  surfaces: SceneSurfaceProps;
  cssVars: Record<string, string>;
}
