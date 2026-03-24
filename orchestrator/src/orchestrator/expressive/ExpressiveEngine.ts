import type { Logger } from '../../infrastructure/logging.js';
import type { PostureSnapshot } from '../posture/PostureEngine.js';

export interface GlowSnapshot {
  hue: string;
  intensity: number;
  label: string;
}

export interface ExpressiveEngineDeps {
  logger: Logger;
}

const POSTURE_HUE: Record<string, string> = {
  idle: '#58a6ff',
  normal: '#3fb950',
  elevated: '#d29922',
  defensive: '#f85149',
};

const POSTURE_INTENSITY: Record<string, number> = {
  idle: 0.2,
  normal: 0.4,
  elevated: 0.7,
  defensive: 1.0,
};

export class ExpressiveEngine {
  private readonly logger: Logger;
  private glow: GlowSnapshot = { hue: '#3fb950', intensity: 0.4, label: 'calm' };

  constructor(deps: ExpressiveEngineDeps) {
    this.logger = deps.logger;
  }

  public computeGlow(posture: PostureSnapshot, nodeCount: number): void {
    const mode = posture.mode;
    const hue = POSTURE_HUE[mode] ?? '#3fb950';
    const baseIntensity = POSTURE_INTENSITY[mode] ?? 0.4;
    const nodeBoost = Math.min(nodeCount * 0.05, 0.2);
    const intensity = Math.min(baseIntensity + nodeBoost, 1.0);

    const label =
      mode === 'defensive' ? 'alert' :
      mode === 'elevated' ? 'watchful' :
      mode === 'idle' ? 'resting' : 'calm';

    if (this.glow.label !== label) {
      this.logger.info('[expressive] glow changed', { label, hue, intensity });
    }

    this.glow = { hue, intensity, label };
  }

  public getSnapshot(): GlowSnapshot {
    return { ...this.glow };
  }
}

export function createExpressiveEngine(
  deps: ExpressiveEngineDeps,
): ExpressiveEngine {
  return new ExpressiveEngine(deps);
}
