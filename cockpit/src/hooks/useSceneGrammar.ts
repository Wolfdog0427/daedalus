import { useMemo, useRef } from "react";
import type { FusionScene } from "../shared/daedalus/fusion";
import type { SceneGrammarState, SceneGrammarConfig, GrammarResult } from "../shared/daedalus/sceneGrammar";
import { makeInitialGrammarState, SCENE_GRAMMAR_DEFAULTS } from "../shared/daedalus/sceneGrammar";
import { applySceneGrammar } from "../shared/daedalus/sceneGrammarEngine";

export interface GrammarOutput {
  scene: FusionScene;
  grammar: GrammarResult;
}

/**
 * Validates fusion scene transitions against the declarative grammar.
 * Blocks forbidden transitions and enforces dwell times.
 * Returns the grammar-approved scene plus blend/sync metadata.
 */
export function useSceneGrammar(
  proposed: FusionScene,
  config: SceneGrammarConfig = SCENE_GRAMMAR_DEFAULTS,
): GrammarOutput {
  const stateRef = useRef<SceneGrammarState>(makeInitialGrammarState());
  const prevSceneRef = useRef<FusionScene>(proposed);

  return useMemo(() => {
    const now = Date.now();
    const { result, nextState } = applySceneGrammar(
      proposed.sceneName,
      stateRef.current,
      config,
      now,
    );
    stateRef.current = nextState;

    let scene: FusionScene;
    if (result.sceneName === proposed.sceneName) {
      scene = proposed;
      prevSceneRef.current = proposed;
    } else {
      scene = { ...prevSceneRef.current, sceneName: result.sceneName };
    }

    return { scene, grammar: result };
  }, [proposed, config]);
}
