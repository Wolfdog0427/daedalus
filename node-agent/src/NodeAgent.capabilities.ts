import type { Capability } from "../../shared/daedalus/contracts";
import type { NodeAgentTransport } from "./NodeAgent.transport";

export interface CapabilityDelta {
  readonly name: string;
  readonly from: boolean;
  readonly to: boolean;
}

export function createCapabilityManager(
  nodeId: string,
  transport: NodeAgentTransport,
  initialCaps: Capability[],
) {
  let caps: Capability[] = [...initialCaps];
  const listeners = new Set<(caps: Capability[]) => void>();

  function emit() {
    for (const fn of listeners) fn(caps);
  }

  function computeDeltas(incoming: Capability[]): CapabilityDelta[] {
    const deltas: CapabilityDelta[] = [];
    const currentMap = new Map(caps.map(c => [c.name, c]));
    for (const cap of incoming) {
      const prev = currentMap.get(cap.name);
      if (!prev || prev.enabled !== cap.enabled) {
        deltas.push({ name: cap.name, from: prev?.enabled ?? false, to: cap.enabled });
      }
    }
    return deltas;
  }

  return {
    getCaps(): Capability[] { return caps; },

    registerCap(cap: Capability) {
      const existing = caps.find(c => c.name === cap.name);
      if (existing) {
        existing.enabled = cap.enabled;
        existing.value = cap.value;
      } else {
        caps.push({ ...cap });
      }
      emit();
    },

    removeCap(name: string) {
      caps = caps.filter(c => c.name !== name);
      emit();
    },

    negotiate(remoteCaps: Capability[]): Capability[] {
      const remoteMap = new Map(remoteCaps.map(c => [c.name, c]));
      return caps
        .filter(c => remoteMap.has(c.name))
        .map(c => ({
          name: c.name,
          value: c.enabled && remoteMap.get(c.name)!.enabled ? "enabled" : "disabled",
          enabled: c.enabled && remoteMap.get(c.name)!.enabled,
        }));
    },

    async sync(): Promise<CapabilityDelta[]> {
      const now = new Date().toISOString();
      await transport.post("/daedalus/mirror/caps", {
        nodeId,
        capabilities: caps,
        timestamp: now,
      });
      return [];
    },

    computeDeltas,

    onCapsChange(handler: (caps: Capability[]) => void): () => void {
      listeners.add(handler);
      return () => { listeners.delete(handler); };
    },
  };
}

export type CapabilityManager = ReturnType<typeof createCapabilityManager>;
