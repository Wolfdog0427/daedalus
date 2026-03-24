import { useMemo, useRef } from "react";
import type { FusionScene } from "../shared/daedalus/fusion";
import type { GrammarResult } from "../shared/daedalus/sceneGrammar";
import type { SceneFrame } from "../shared/daedalus/sceneSync";
import { useSceneOrchestration } from "./useSceneOrchestration";
import { composeSceneFrame } from "../shared/daedalus/sceneSyncEngine";

/**
 * Single entry point that fuses scene orchestration (blending) and
 * surface mapping into one synchronized SceneFrame per render pass.
 *
 * Guarantees:
 *  - scene + surfaces are derived from the same OrchestratedScene
 *  - frameId is monotonically increasing
 *  - all downstream consumers read from one consistent frame
 */
export function useSceneSync(
  grammarScene: FusionScene,
  sceneGrammar: GrammarResult,
): SceneFrame {
  const scene = useSceneOrchestration(grammarScene, sceneGrammar);
  const frameIdRef = useRef(0);

  return useMemo(() => {
    frameIdRef.current += 1;
    return composeSceneFrame(scene, frameIdRef.current);
  }, [scene]);
}
