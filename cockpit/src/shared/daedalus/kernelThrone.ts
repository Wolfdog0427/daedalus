/**
 * Kernel Throne — the unified cockpit view of the Governance Kernel.
 *
 * Flattens the Crown (expressive) and Halo (diagnostic) into a
 * single operator-facing snapshot purpose-built for rendering.
 * Read-only, no feedback into governance.
 */

import type { CrownSymbol } from "./kernelCrown";
import type { ShellStatus } from "./kernelShell";
import type { KernelStatus } from "./governanceKernel";

export interface ThroneView {
  readonly symbol: CrownSymbol;
  readonly glow: number;
  readonly pulse: number;
  readonly stability: number;

  readonly shellStatus: ShellStatus;
  readonly kernelStatus: KernelStatus;

  readonly overrideCount: number;
  readonly activeOverrides: readonly string[];
  readonly pendingCount: number;
  readonly activeTierCount: number;
  readonly cappingApplied: boolean;

  readonly invariantsHeld: number;
  readonly invariantsTotal: number;
  readonly invariantsPassed: boolean;
}

export const THRONE_IDLE: ThroneView = Object.freeze({
  symbol: "serene" as const,
  glow: 0.3,
  pulse: 0,
  stability: 1,

  shellStatus: "nominal" as const,
  kernelStatus: "clean" as const,

  overrideCount: 0,
  activeOverrides: Object.freeze([]) as readonly string[],
  pendingCount: 0,
  activeTierCount: 0,
  cappingApplied: false,

  invariantsHeld: 0,
  invariantsTotal: 0,
  invariantsPassed: true,
});
