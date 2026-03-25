/**
 * Expressive Overlays
 *
 * Temporary expressive modifiers that layer on top of the constitutional
 * posture without overriding it. Each overlay has a tick-based lifetime
 * (3–10 ticks) and decays automatically unless renewed.
 *
 * Safety: Overlays NEVER override constitutional posture bands, bypass
 * safe mode, or reduce caution during low alignment.
 */

import type { KernelPosture, SafeModeState } from "./types";
import { ExpressiveOverlay } from "./types";

interface OverlayState {
  current: ExpressiveOverlay;
  ticksRemaining: number;
}

let overlayState: OverlayState = { current: ExpressiveOverlay.NONE, ticksRemaining: 0 };
let previousPosture: KernelPosture | null = null;

const OVERLAY_DURATIONS: Record<ExpressiveOverlay, number> = {
  [ExpressiveOverlay.NONE]: 0,
  [ExpressiveOverlay.FOCUS]: 8,
  [ExpressiveOverlay.CALM]: 10,
  [ExpressiveOverlay.ALERT]: 5,
  [ExpressiveOverlay.RECOVERY]: 6,
  [ExpressiveOverlay.TRANSITION]: 3,
};

export interface OverlayContext {
  safeMode: SafeModeState;
  previousSafeModeActive: boolean;
  postureChanged: boolean;
  highFocusTask: boolean;
  lowStress: boolean;
}

export function selectOverlay(
  context: OverlayContext,
  posture: KernelPosture,
): ExpressiveOverlay {
  if (context.safeMode.active && !context.previousSafeModeActive) {
    setOverlay(ExpressiveOverlay.ALERT);
    return ExpressiveOverlay.ALERT;
  }
  if (!context.safeMode.active && context.previousSafeModeActive) {
    setOverlay(ExpressiveOverlay.RECOVERY);
    return ExpressiveOverlay.RECOVERY;
  }
  if (context.postureChanged) {
    setOverlay(ExpressiveOverlay.TRANSITION);
    return ExpressiveOverlay.TRANSITION;
  }
  if (context.highFocusTask) {
    setOverlay(ExpressiveOverlay.FOCUS);
    return ExpressiveOverlay.FOCUS;
  }
  if (context.lowStress && posture.caution < 0.3) {
    setOverlay(ExpressiveOverlay.CALM);
    return ExpressiveOverlay.CALM;
  }

  return overlayState.current;
}

export function tickOverlay(): { overlay: ExpressiveOverlay; ticksRemaining: number } {
  if (overlayState.ticksRemaining > 0) {
    overlayState.ticksRemaining--;
    if (overlayState.ticksRemaining === 0) {
      overlayState.current = ExpressiveOverlay.NONE;
    }
  }
  return { overlay: overlayState.current, ticksRemaining: overlayState.ticksRemaining };
}

export function setOverlay(overlay: ExpressiveOverlay): void {
  overlayState.current = overlay;
  overlayState.ticksRemaining = OVERLAY_DURATIONS[overlay];
}

export function forceOverlay(overlay: ExpressiveOverlay): void {
  setOverlay(overlay);
}

export function getOverlayState(): OverlayState {
  return { ...overlayState };
}

export function setPreviousPosture(posture: KernelPosture): void {
  previousPosture = posture ? { ...posture } : null;
}

export function getPreviousPosture(): KernelPosture | null {
  return previousPosture;
}

export function resetOverlayState(): void {
  overlayState = { current: ExpressiveOverlay.NONE, ticksRemaining: 0 };
  previousPosture = null;
}
