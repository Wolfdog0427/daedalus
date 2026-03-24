import type { Logger } from '../../infrastructure/logging.js';

export interface CapabilityProfile {
  name: string;
  description: string;
  capabilities: Record<string, boolean>;
}

export interface CapabilityProfileRegistryDeps {
  logger: Logger;
}

export class CapabilityProfileRegistry {
  private readonly logger: Logger;
  private profiles: Map<string, CapabilityProfile> = new Map();

  constructor(deps: CapabilityProfileRegistryDeps) {
    this.logger = deps.logger;
  }

  public register(profile: CapabilityProfile): void {
    this.profiles.set(profile.name, profile);
    this.logger.info('[profiles] registered', { name: profile.name });
  }

  public list(): CapabilityProfile[] {
    return Array.from(this.profiles.values());
  }

  public get(name: string): CapabilityProfile | undefined {
    return this.profiles.get(name);
  }
}

export function createCapabilityProfileRegistry(
  deps: CapabilityProfileRegistryDeps,
): CapabilityProfileRegistry {
  const registry = new CapabilityProfileRegistry(deps);

  registry.register({
    name: 'expressive',
    description: 'Full expressive glow, notifications, and posture dynamics',
    capabilities: { expressive: true, notifications: true },
  });

  registry.register({
    name: 'silent',
    description: 'No expressive output, no notifications — quiet operations',
    capabilities: { expressive: false, notifications: false },
  });

  registry.register({
    name: 'diagnostic',
    description: 'Notifications active, expressive glow suppressed',
    capabilities: { expressive: false, notifications: true },
  });

  return registry;
}
