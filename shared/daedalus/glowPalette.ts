/**
 * Glow Palette — the canonical color field for Daedalus.
 *
 * Maps GlowLevel to hex colors and motion patterns. Every UI surface
 * that renders glow (cockpit, mobile, node fabric) should import
 * from here instead of defining ad-hoc colors.
 *
 * The palette is intentionally cool-blue-dominant: Daedalus's natural
 * color field is blue, shifting toward warmth only under alert/defense.
 */

import type { GlowLevel } from "./contracts";

export interface GlowColor {
  readonly hex: string;
  readonly shadow: string;
  readonly motionPattern: "none" | "steady" | "breathe" | "pulse";
}

export const GLOW_PALETTE: Readonly<Record<GlowLevel, GlowColor>> = Object.freeze({
  none: Object.freeze({
    hex: "#444444",
    shadow: "transparent",
    motionPattern: "none" as const,
  }),
  low: Object.freeze({
    hex: "#4da3ff",
    shadow: "#4da3ff33",
    motionPattern: "steady" as const,
  }),
  medium: Object.freeze({
    hex: "#58a6ff",
    shadow: "#58a6ff55",
    motionPattern: "breathe" as const,
  }),
  high: Object.freeze({
    hex: "#79c0ff",
    shadow: "#79c0ff77",
    motionPattern: "pulse" as const,
  }),
});

/**
 * Posture-to-color overrides: when a node or being is in a
 * non-standard posture, the glow shifts from the default blue
 * palette to the posture color.
 */
export const POSTURE_GLOW_OVERRIDES = Object.freeze({
  sentinel: Object.freeze({ hex: "#f85149", shadow: "#f8514966" }),
  companion: Object.freeze({ hex: "#58a6ff", shadow: "#58a6ff55" }),
  observer: Object.freeze({ hex: "#7a8a9a", shadow: "#7a8a9a44" }),
  dormant: Object.freeze({ hex: "#444444", shadow: "transparent" }),
});

export function glowLevelToHex(level: GlowLevel): string {
  return GLOW_PALETTE[level].hex;
}

export function glowLevelToShadow(level: GlowLevel): string {
  return GLOW_PALETTE[level].shadow;
}

/**
 * Generate CSS custom properties for the current glow level.
 * Useful for injecting into component style attributes.
 */
export function glowToCssVars(level: GlowLevel): Record<string, string> {
  const color = GLOW_PALETTE[level];
  return {
    "--glow-hex": color.hex,
    "--glow-shadow": color.shadow,
    "--glow-motion": color.motionPattern,
  };
}
