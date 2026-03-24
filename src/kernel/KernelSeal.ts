import { Kernel } from './Kernel';
import { KernelInvariants } from './KernelInvariants';
import { KernelShell } from './KernelShell';
import { KernelHalo } from './KernelHalo';
import { KernelCrown } from './KernelCrown';
import { KernelThrone } from './KernelThrone';

export class KernelSeal {
  private static sealed = false;

  static applySeal() {
    if (this.sealed) return;

    // Freeze all governance surfaces
    Object.freeze(KernelShell);
    Object.freeze(KernelInvariants);
    Object.freeze(Kernel);
    Object.freeze(KernelHalo);
    Object.freeze(KernelCrown);
    Object.freeze(KernelThrone);

    // Mark sealed
    this.sealed = true;
  }

  static isSealed() {
    return this.sealed;
  }
}
