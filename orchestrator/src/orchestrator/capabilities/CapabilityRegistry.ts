import type { Logger } from '../../infrastructure/logging.js';

export interface CapabilityDefinition {
  name: string;
  description: string;
  enabled: boolean;
}

export interface CapabilityRegistryDeps {
  logger: Logger;
}

export class CapabilityRegistry {
  private readonly logger: Logger;
  private capabilities: Map<string, CapabilityDefinition> = new Map();

  constructor(deps: CapabilityRegistryDeps) {
    this.logger = deps.logger;
  }

  public register(cap: CapabilityDefinition): void {
    this.capabilities.set(cap.name, cap);
    this.logger.info('[capabilities] registered', { name: cap.name });
  }

  public unregister(name: string): void {
    this.capabilities.delete(name);
  }

  public enable(name: string): void {
    const cap = this.capabilities.get(name);
    if (cap) cap.enabled = true;
  }

  public disable(name: string): void {
    const cap = this.capabilities.get(name);
    if (cap) cap.enabled = false;
  }

  public get(name: string): CapabilityDefinition | undefined {
    return this.capabilities.get(name);
  }

  public isEnabled(name: string): boolean {
    return this.capabilities.get(name)?.enabled ?? false;
  }

  public setEnabled(name: string, enabled: boolean): CapabilityDefinition | undefined {
    const cap = this.capabilities.get(name);
    if (!cap) return undefined;
    cap.enabled = enabled;
    this.logger.info('[capabilities] toggled', { name, enabled });
    return cap;
  }

  public list(): CapabilityDefinition[] {
    return Array.from(this.capabilities.values());
  }

  public listEnabled(): CapabilityDefinition[] {
    return this.list().filter((c) => c.enabled);
  }
}

export function createCapabilityRegistry(
  deps: CapabilityRegistryDeps,
): CapabilityRegistry {
  const registry = new CapabilityRegistry(deps);

  registry.register({ name: 'echo', description: 'Echo command', enabled: true });
  registry.register({ name: 'presence', description: 'Node presence tracking', enabled: true });
  registry.register({ name: 'risk', description: 'Risk assessment', enabled: true });
  registry.register({ name: 'verification', description: 'Verification requirements', enabled: true });
  registry.register({ name: 'continuity', description: 'Continuity timeline', enabled: true });
  registry.register({ name: 'expressive', description: 'Expressive glow computation', enabled: true });
  registry.register({ name: 'notifications', description: 'Notification delivery', enabled: true });

  return registry;
}
