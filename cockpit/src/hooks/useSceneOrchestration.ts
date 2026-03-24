import { useState, useEffect, useRef } from "react";
import type { FusionScene } from "../shared/daedalus/fusion";
import type { GrammarResult } from "../shared/daedalus/sceneGrammar";
import type { OrchestratedScene } from "../shared/daedalus/sceneOrchestration";
import { SCENE_ORCHESTRATION_ENABLED } from "../shared/daedalus/sceneOrchestration";
import { blendScenes, snapScene } from "../shared/daedalus/sceneOrchestrationEngine";

/**
 * Smoothly blends between grammar-approved FusionScenes using
 * requestAnimationFrame. Continuous values (glow, motion) interpolate;
 * discrete values snap at the blend midpoint. When narrativeSync is
 * true, the narrative line snaps immediately.
 *
 * When SCENE_ORCHESTRATION_ENABLED is false, returns the scene as-is.
 */
export function useSceneOrchestration(
  scene: FusionScene,
  grammar: GrammarResult,
): OrchestratedScene {
  const [output, setOutput] = useState<OrchestratedScene>(
    () => snapScene(scene),
  );

  const lastOutputRef = useRef<FusionScene>(scene);
  const latestSceneRef = useRef<FusionScene>(scene);
  const prevNameRef = useRef(scene.sceneName);
  const rafRef = useRef(0);
  const blendingRef = useRef(false);

  latestSceneRef.current = scene;

  // ── Scene name change → start blend ───────────────────────────
  useEffect(() => {
    const nameChanged = scene.sceneName !== prevNameRef.current;
    prevNameRef.current = scene.sceneName;

    if (!nameChanged) return;

    if (!SCENE_ORCHESTRATION_ENABLED || grammar.blendMs <= 0) {
      const snapped = snapScene(scene, grammar.blendMs);
      lastOutputRef.current = scene;
      blendingRef.current = false;
      setOutput(snapped);
      return;
    }

    const from: FusionScene = { ...lastOutputRef.current };
    const startTime = performance.now();
    const { blendMs, narrativeSync } = grammar;
    blendingRef.current = true;

    const animate = () => {
      const t = Math.min(1, (performance.now() - startTime) / blendMs);
      const blended = blendScenes(
        from,
        latestSceneRef.current,
        t,
        blendMs,
        narrativeSync,
      );
      lastOutputRef.current = blended;
      setOutput(blended);

      if (t < 1) {
        rafRef.current = requestAnimationFrame(animate);
      } else {
        blendingRef.current = false;
      }
    };

    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(rafRef.current);
      blendingRef.current = false;
    };
  }, [scene.sceneName, grammar.blendMs, grammar.narrativeSync]);

  // ── Same-scene value updates → pass through when not blending ──
  useEffect(() => {
    if (blendingRef.current) return;
    const snapped = snapScene(scene);
    lastOutputRef.current = scene;
    setOutput(snapped);
  }, [scene]);

  return output;
}
