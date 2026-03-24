import type { Capability } from "../../../shared/daedalus/contracts";
import type { NodeMirror, CapabilityMap, CapabilityDelta, NodeCapSyncPayload } from "./NodeMirror.types";

const nowIso = () => new Date().toISOString();

export function computeCapabilityDeltas(
  current: CapabilityMap,
  incoming: Capability[],
): CapabilityDelta[] {
  const deltas: CapabilityDelta[] = [];
  const currentMap = new Map(current.entries.map(c => [c.name, c]));

  for (const cap of incoming) {
    const prev = currentMap.get(cap.name);
    if (!prev) {
      deltas.push({
        name: cap.name,
        from: null,
        to: { enabled: cap.enabled, value: cap.value },
      });
    } else if (prev.enabled !== cap.enabled || prev.value !== cap.value) {
      deltas.push({
        name: cap.name,
        from: { enabled: prev.enabled, value: prev.value },
        to: { enabled: cap.enabled, value: cap.value },
      });
    }
  }

  for (const [name] of currentMap) {
    if (!incoming.find(c => c.name === name)) {
      const prev = currentMap.get(name)!;
      deltas.push({
        name,
        from: { enabled: prev.enabled, value: prev.value },
        to: { enabled: false, value: "removed" },
      });
    }
  }

  return deltas;
}

export function negotiateCapabilities(
  localCaps: Capability[],
  remoteCaps: Capability[],
): Capability[] {
  const remoteMap = new Map(remoteCaps.map(c => [c.name, c]));
  return localCaps
    .filter(c => remoteMap.has(c.name))
    .map(c => {
      const remote = remoteMap.get(c.name)!;
      return {
        name: c.name,
        value: c.enabled && remote.enabled ? "enabled" : "disabled",
        enabled: c.enabled && remote.enabled,
      };
    });
}

export function validateCapabilities(caps: Capability[]): string[] {
  const errors: string[] = [];
  const seen = new Set<string>();
  for (const cap of caps) {
    if (!cap.name || cap.name.trim() === "") {
      errors.push("Capability missing name");
    }
    if (seen.has(cap.name)) {
      errors.push(`Duplicate capability: ${cap.name}`);
    }
    seen.add(cap.name);
  }
  return errors;
}

export function processCapSync(
  mirror: NodeMirror,
  payload: NodeCapSyncPayload,
): { mirror: NodeMirror; deltas: CapabilityDelta[] } {
  const deltas = computeCapabilityDeltas(mirror.capabilities, payload.capabilities);
  const errors = validateCapabilities(payload.capabilities);

  if (errors.length > 0) {
    return {
      mirror: {
        ...mirror,
        lifecycle: {
          ...mirror.lifecycle,
          errorCount: mirror.lifecycle.errorCount + 1,
          lastError: `Cap validation: ${errors.join("; ")}`,
        },
      },
      deltas: [],
    };
  }

  return {
    mirror: {
      ...mirror,
      capabilities: { entries: [...payload.capabilities] },
      lifecycle: { ...mirror.lifecycle, lastCapSync: payload.timestamp },
    },
    deltas,
  };
}
