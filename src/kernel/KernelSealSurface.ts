import { KernelSeal } from './KernelSeal';

export const KernelSealSurface = {
  sealed: () => KernelSeal.isSealed(),
};
