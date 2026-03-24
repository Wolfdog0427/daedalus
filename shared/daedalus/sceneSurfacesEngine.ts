import type { OrchestratedScene } from "./sceneOrchestration";
import type { SceneSurfaceProps } from "./sceneSurfaces";
import {
  SCENE_SURFACES_ENABLED,
  SURFACE_DEFAULTS,
  GLOW_COLORS,
  SCENE_GRADIENTS,
} from "./sceneSurfaces";

/**
 * Maps an OrchestratedScene to concrete CSS-ready surface properties.
 *
 * Pure function — no side effects, no singletons.
 */
export function mapSceneToSurfaces(scene: OrchestratedScene): SceneSurfaceProps {
  if (!SCENE_SURFACES_ENABLED) return SURFACE_DEFAULTS;

  return {
    glowColor: GLOW_COLORS[scene.tone],
    glowStrength: scene.glow,
    motionStrength: scene.motion,
    backgroundGradient: SCENE_GRADIENTS[scene.sceneName] ?? SCENE_GRADIENTS.idle,
    ribbonTone: scene.tone,
    continuityBadge: scene.continuityBadge,
    narrativeLine: scene.narrativeLine,
    blendProgress: scene.progress,
  };
}

/**
 * Converts surface props into a CSS custom-property record suitable for
 * use as a React `style` object on the cockpit root element.
 */
export function surfacesToCssVars(s: SceneSurfaceProps): Record<string, string> {
  return {
    "--surface-glow-color": s.glowColor,
    "--surface-glow-strength": String(s.glowStrength),
    "--surface-motion-strength": String(s.motionStrength),
    "--surface-background": s.backgroundGradient,
    "--surface-blend-progress": String(s.blendProgress),
  };
}
