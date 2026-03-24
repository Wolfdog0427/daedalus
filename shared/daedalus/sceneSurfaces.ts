import type { FusionSceneName } from "./fusion";
import type { ConductorTone, ConductorBadge } from "./conductor";

/** Feature toggle: set to false to bypass surface mapping. */
export const SCENE_SURFACES_ENABLED = true;

export interface SceneSurfaceProps {
  glowColor: string;
  glowStrength: number;
  motionStrength: number;
  backgroundGradient: string;
  ribbonTone: ConductorTone;
  continuityBadge: ConductorBadge | null;
  narrativeLine: string | null;
  blendProgress: number;
}

export const GLOW_COLORS: Record<ConductorTone, string> = {
  neutral: "#7a8a9a",
  focused: "#4da3ff",
  celebratory: "#ffd86b",
  alert: "#ff4d4d",
};

export const SCENE_GRADIENTS: Record<FusionSceneName, string> = {
  idle: "linear-gradient(180deg, #0a0a0a 0%, #000 100%)",
  focus: "linear-gradient(180deg, #0a1a2a 0%, #000 100%)",
  rising: "linear-gradient(180deg, #0f2238 0%, #000 100%)",
  apex: "linear-gradient(180deg, #1a2f4f 0%, #000 100%)",
  waning: "linear-gradient(180deg, #12203a 0%, #000 100%)",
  settling: "linear-gradient(180deg, #0d1824 0%, #000 100%)",
  alert: "linear-gradient(180deg, #2a0a0a 0%, #000 100%)",
  celebrating: "linear-gradient(180deg, #2a2200 0%, #000 100%)",
  exploring: "linear-gradient(180deg, #0a2a1a 0%, #000 100%)",
};

export const SURFACE_DEFAULTS: SceneSurfaceProps = {
  glowColor: "#7a8a9a",
  glowStrength: 0.3,
  motionStrength: 0.5,
  backgroundGradient: SCENE_GRADIENTS.idle,
  ribbonTone: "neutral",
  continuityBadge: null,
  narrativeLine: null,
  blendProgress: 1,
};
