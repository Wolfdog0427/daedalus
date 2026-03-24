import type { FusionSceneName } from "./fusion";
import type {
  SceneGrammarState,
  SceneGrammarConfig,
  GrammarResult,
} from "./sceneGrammar";
import {
  SCENE_GRAMMAR_ENABLED,
  SCENE_GRAMMAR_DEFAULTS,
  SCENE_TRANSITION_RULES,
} from "./sceneGrammar";

/**
 * Validates a proposed scene transition against the grammar rules.
 *
 * Returns the scene name that should be used (either the proposed one
 * if allowed, or the current one if blocked), plus blend and sync metadata.
 *
 * Three enforcement mechanisms:
 *   1. Explicit forbid — rule with `allowed: false` blocks the transition.
 *   2. Dwell time — the current scene must have been held for `minDwellMs`
 *      before the transition is allowed.
 *   3. Default allow — unlisted transitions are permitted with default blend.
 */
export function applySceneGrammar(
  proposed: FusionSceneName,
  prev: SceneGrammarState,
  config: SceneGrammarConfig = SCENE_GRAMMAR_DEFAULTS,
  now: number = Date.now(),
): { result: GrammarResult; nextState: SceneGrammarState } {
  if (!SCENE_GRAMMAR_ENABLED || proposed === prev.currentScene) {
    return {
      result: {
        sceneName: proposed,
        allowed: true,
        blendMs: 0,
        narrativeSync: false,
      },
      nextState: proposed === prev.currentScene
        ? prev
        : { currentScene: proposed, sceneEnteredAt: now },
    };
  }

  const rule = SCENE_TRANSITION_RULES.find(
    (r) => r.from === prev.currentScene && r.to === proposed,
  );

  // ── No explicit rule: allow with defaults ──
  if (!rule) {
    return {
      result: {
        sceneName: proposed,
        allowed: true,
        blendMs: config.defaultBlendMs,
        narrativeSync: false,
      },
      nextState: { currentScene: proposed, sceneEnteredAt: now },
    };
  }

  // ── Forbidden transition ──
  if (!rule.allowed) {
    return {
      result: {
        sceneName: prev.currentScene,
        allowed: false,
        blendMs: 0,
        narrativeSync: false,
      },
      nextState: prev,
    };
  }

  // ── Dwell time check ──
  const elapsed = now - prev.sceneEnteredAt;
  const minDwell = rule.minDwellMs ?? config.defaultDwellMs;
  if (elapsed < minDwell) {
    return {
      result: {
        sceneName: prev.currentScene,
        allowed: false,
        blendMs: 0,
        narrativeSync: false,
      },
      nextState: prev,
    };
  }

  // ── Allowed transition ──
  return {
    result: {
      sceneName: proposed,
      allowed: true,
      blendMs: rule.blendMs ?? config.defaultBlendMs,
      narrativeSync: rule.narrativeSync ?? false,
    },
    nextState: { currentScene: proposed, sceneEnteredAt: now },
  };
}
