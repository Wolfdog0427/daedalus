import type { FusionSceneName } from "./fusion";

/** Feature toggle: set to false to bypass all grammar rules. */
export const SCENE_GRAMMAR_ENABLED = true;

export interface SceneTransitionRule {
  from: FusionSceneName;
  to: FusionSceneName;
  allowed: boolean;
  minDwellMs?: number;
  blendMs?: number;
  narrativeSync?: boolean;
}

export interface SceneGrammarConfig {
  defaultBlendMs: number;
  defaultDwellMs: number;
}

export const SCENE_GRAMMAR_DEFAULTS: SceneGrammarConfig = {
  defaultBlendMs: 500,
  defaultDwellMs: 900,
};

/**
 * Declarative transition rules. Unlisted transitions default to allowed
 * with config-level blend/dwell.
 */
export const SCENE_TRANSITION_RULES: SceneTransitionRule[] = [
  // ── Natural arc: idle → focus → rising → apex → waning → settling → idle ──
  { from: "idle",      to: "focus",       allowed: true, blendMs: 400 },
  { from: "focus",     to: "rising",      allowed: true, blendMs: 500 },
  { from: "rising",    to: "apex",        allowed: true, blendMs: 600, narrativeSync: true },
  { from: "apex",      to: "waning",      allowed: true, blendMs: 700, minDwellMs: 1200 },
  { from: "waning",    to: "settling",    allowed: true, blendMs: 600 },
  { from: "settling",  to: "idle",        allowed: true, blendMs: 500 },

  // ── Celebrating branches off settling/idle ──
  { from: "idle",      to: "celebrating", allowed: true, blendMs: 500, narrativeSync: true },
  { from: "settling",  to: "celebrating", allowed: true, blendMs: 500, narrativeSync: true },
  { from: "celebrating", to: "idle",      allowed: true, blendMs: 600, minDwellMs: 1000 },
  { from: "celebrating", to: "settling",  allowed: true, blendMs: 600, minDwellMs: 1000 },

  // ── Exploring branches off idle/focus ──
  { from: "idle",      to: "exploring",   allowed: true, blendMs: 400 },
  { from: "focus",     to: "exploring",   allowed: true, blendMs: 400 },
  { from: "exploring", to: "idle",        allowed: true, blendMs: 500 },
  { from: "exploring", to: "focus",       allowed: true, blendMs: 400 },

  // ── Alert overrides: any scene can escalate to alert instantly ──
  { from: "idle",        to: "alert", allowed: true, blendMs: 200 },
  { from: "focus",       to: "alert", allowed: true, blendMs: 200 },
  { from: "rising",      to: "alert", allowed: true, blendMs: 200 },
  { from: "apex",        to: "alert", allowed: true, blendMs: 200 },
  { from: "waning",      to: "alert", allowed: true, blendMs: 200 },
  { from: "settling",    to: "alert", allowed: true, blendMs: 200 },
  { from: "celebrating", to: "alert", allowed: true, blendMs: 200 },
  { from: "exploring",   to: "alert", allowed: true, blendMs: 200 },

  // ── Alert recovery goes through settling, not directly to active scenes ──
  { from: "alert",     to: "settling",  allowed: true, blendMs: 600, minDwellMs: 1500 },
  { from: "alert",     to: "idle",      allowed: true, blendMs: 500, minDwellMs: 1500 },

  // ── Forbidden: no skipping arcs ──
  { from: "apex",      to: "focus",     allowed: false },
  { from: "apex",      to: "idle",      allowed: false },
  { from: "alert",     to: "apex",      allowed: false },
  { from: "alert",     to: "rising",    allowed: false },
  { from: "alert",     to: "celebrating", allowed: false },
  { from: "alert",     to: "exploring", allowed: false },
];

export interface SceneGrammarState {
  currentScene: FusionSceneName;
  sceneEnteredAt: number;
}

export interface GrammarResult {
  sceneName: FusionSceneName;
  allowed: boolean;
  blendMs: number;
  narrativeSync: boolean;
}

export function makeInitialGrammarState(): SceneGrammarState {
  return { currentScene: "idle", sceneEnteredAt: 0 };
}
