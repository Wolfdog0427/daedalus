/**
 * Kernel Shell — the protective boundary around the Governance Kernel.
 *
 * The shell computes kernel state, validates invariants, and
 * provides safe degradation: if any invariant is violated, the
 * shell returns KERNEL_IDLE instead of the corrupted state and
 * sets status to "degraded".
 */

/** Feature toggle: set to false to bypass the shell boundary. */
export const KERNEL_SHELL_ENABLED = true;

/**
 * Shell status:
 * - "nominal"  — all invariants held, kernel state is authoritative
 * - "degraded" — one or more invariants violated, kernel returned
 *                safe fallback (KERNEL_IDLE) to prevent downstream
 *                corruption
 */
export type ShellStatus = "nominal" | "degraded";

import type { KernelState } from "./governanceKernel";
import type { InvariantReport } from "./kernelInvariants";

export interface KernelShellState {
  shellStatus: ShellStatus;
  kernel: KernelState;
  invariants: InvariantReport;
}
