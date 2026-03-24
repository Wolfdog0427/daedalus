/**
 * Daedalus Kernel types — local type definitions for kernel-specific
 * behavior, extending the shared contracts.
 */

export interface KernelConfig {
  kernelId: string;
  orchestratorUrl: string;
}

export interface BeingDescriptor {
  id: string;
  name: string;
  traits: Record<string, unknown>;
  createdAt: string;
}
