/**
 * Kernel Halo — read-only introspection layer.
 *
 * A single frozen snapshot that unifies shell status, kernel
 * state, and invariant diagnostics into one immutable object.
 * Downstream consumers (HUDs, dashboards, diagnostics) read
 * from the halo; they can never write back into governance.
 */

import type { ShellStatus } from "./kernelShell";
import type { KernelStatus } from "./governanceKernel";

export interface KernelHaloSnapshot {
  readonly shellStatus: ShellStatus;
  readonly kernelStatus: KernelStatus;
  readonly overrideCount: number;
  readonly activeOverrides: readonly string[];
  readonly activeTierCount: number;
  readonly pendingCount: number;
  readonly cappingApplied: boolean;
  readonly invariantsHeld: number;
  readonly invariantsTotal: number;
  readonly invariantsPassed: boolean;
  readonly failedInvariants: readonly string[];
}

export const HALO_IDLE: KernelHaloSnapshot = Object.freeze({
  shellStatus: "nominal" as const,
  kernelStatus: "clean" as const,
  overrideCount: 0,
  activeOverrides: Object.freeze([]) as readonly string[],
  activeTierCount: 0,
  pendingCount: 0,
  cappingApplied: false,
  invariantsHeld: 0,
  invariantsTotal: 0,
  invariantsPassed: true,
  failedInvariants: Object.freeze([]) as readonly string[],
});
