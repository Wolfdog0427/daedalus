import {
  computeNodeGlow,
  computeNodeHeartbeat,
  computeNodeContinuity,
  mapNodePresenceEntry,
  computeNodePresence,
} from "../../shared/daedalus/nodePresenceEngine";
import { NODE_PRESENCE_IDLE } from "../../shared/daedalus/nodePresence";
import type { ConnectivitySnapshot, ConnectivityNode } from "../../shared/daedalus/connectivity";
import { CONNECTIVITY_IDLE } from "../../shared/daedalus/connectivity";

function mkConnNode(overrides: Partial<ConnectivityNode> = {}): ConnectivityNode {
  return Object.freeze({
    id: "n1",
    trusted: true,
    quarantined: false,
    health: 0.9,
    capabilityCount: 2,
    capabilities: Object.freeze(["cap-a", "cap-b"]),
    hasHeartbeat: true,
    joinRequested: false,
    suggestedTrustTier: "high" as const,
    ...overrides,
  });
}

function mkSnapshot(
  nodes: ConnectivityNode[],
  overrides: Partial<ConnectivitySnapshot> = {},
): ConnectivitySnapshot {
  return Object.freeze({
    ...CONNECTIVITY_IDLE,
    nodes: Object.freeze(nodes),
    totalCount: nodes.length,
    trustedCount: nodes.filter((n) => n.trusted).length,
    quarantinedCount: nodes.filter((n) => n.quarantined).length,
    pendingJoinCount: nodes.filter((n) => n.joinRequested).length,
    sseConnected: true,
    ...overrides,
  });
}

describe("computeNodeGlow", () => {
  it("trusted node: health*0.7 + 0.3", () => {
    expect(computeNodeGlow(1, true, false)).toBeCloseTo(1);
    expect(computeNodeGlow(0.5, true, false)).toBeCloseTo(0.65);
  });

  it("untrusted node: health*0.7, no trust bonus", () => {
    expect(computeNodeGlow(1, false, false)).toBeCloseTo(0.7);
    expect(computeNodeGlow(0.5, false, false)).toBeCloseTo(0.35);
  });

  it("join-requested node: dimmed to health*0.4", () => {
    expect(computeNodeGlow(1, false, true)).toBeCloseTo(0.4);
    expect(computeNodeGlow(0.5, true, true)).toBeCloseTo(0.2);
  });

  it("clamps to [0,1]", () => {
    expect(computeNodeGlow(2, true, false)).toBe(1);
    expect(computeNodeGlow(-1, false, false)).toBe(0);
  });
});

describe("computeNodeHeartbeat", () => {
  it("join-requested node always pulses at 1", () => {
    expect(computeNodeHeartbeat(0.5, true)).toBe(1);
    expect(computeNodeHeartbeat(0, true)).toBe(1);
  });

  it("normal node: 0.3 + health*0.5", () => {
    expect(computeNodeHeartbeat(1, false)).toBeCloseTo(0.8);
    expect(computeNodeHeartbeat(0.4, false)).toBeCloseTo(0.5);
  });

  it("clamps to [0,1]", () => {
    expect(computeNodeHeartbeat(2, false)).toBe(1);
  });
});

describe("computeNodeContinuity", () => {
  it("derives from health*0.8", () => {
    expect(computeNodeContinuity(1)).toBeCloseTo(0.8);
    expect(computeNodeContinuity(0.5)).toBeCloseTo(0.4);
  });

  it("clamps to [0,1]", () => {
    expect(computeNodeContinuity(2)).toBe(1);
    expect(computeNodeContinuity(-1)).toBe(0);
  });
});

describe("mapNodePresenceEntry", () => {
  it("produces a frozen entry", () => {
    const entry = mapNodePresenceEntry(mkConnNode());
    expect(Object.isFrozen(entry)).toBe(true);
  });

  it("forwards id, trusted, joinRequested, suggestedTrustTier", () => {
    const entry = mapNodePresenceEntry(mkConnNode({ id: "x", trusted: false, joinRequested: true, suggestedTrustTier: "low" }));
    expect(entry.id).toBe("x");
    expect(entry.trusted).toBe(false);
    expect(entry.joinRequested).toBe(true);
    expect(entry.suggestedTrustTier).toBe("low");
  });

  it("joins capabilities into a ribbon string", () => {
    const entry = mapNodePresenceEntry(mkConnNode({ capabilities: Object.freeze(["a", "b", "c"]) }));
    expect(entry.capabilityRibbon).toBe("a · b · c");
  });

  it("produces empty ribbon for no capabilities", () => {
    const entry = mapNodePresenceEntry(mkConnNode({ capabilities: Object.freeze([]) }));
    expect(entry.capabilityRibbon).toBe("");
  });
});

describe("computeNodePresence", () => {
  it("returns idle for empty connectivity", () => {
    const snap = computeNodePresence(CONNECTIVITY_IDLE);
    expect(snap.totalCount).toBe(0);
    expect(snap.pendingJoinCount).toBe(0);
    expect(snap.joinPulse).toBe(0);
    expect(snap.entries).toHaveLength(0);
  });

  it("computes entries for each node", () => {
    const snap = computeNodePresence(
      mkSnapshot([mkConnNode({ id: "a" }), mkConnNode({ id: "b" })]),
    );
    expect(snap.entries).toHaveLength(2);
    expect(snap.totalCount).toBe(2);
  });

  it("counts pending join nodes", () => {
    const snap = computeNodePresence(
      mkSnapshot([
        mkConnNode({ id: "a", joinRequested: true }),
        mkConnNode({ id: "b", joinRequested: false }),
        mkConnNode({ id: "c", joinRequested: true }),
      ]),
    );
    expect(snap.pendingJoinCount).toBe(2);
  });

  it("computes joinPulse as ratio of pending to total", () => {
    const snap = computeNodePresence(
      mkSnapshot([
        mkConnNode({ id: "a", joinRequested: true }),
        mkConnNode({ id: "b", joinRequested: false }),
      ]),
    );
    expect(snap.joinPulse).toBeCloseTo(0.5);
  });

  it("joinPulse is 0 when no pending nodes", () => {
    const snap = computeNodePresence(
      mkSnapshot([mkConnNode({ id: "a" })]),
    );
    expect(snap.joinPulse).toBe(0);
  });

  it("produces a frozen snapshot", () => {
    const snap = computeNodePresence(
      mkSnapshot([mkConnNode()]),
    );
    expect(Object.isFrozen(snap)).toBe(true);
    expect(Object.isFrozen(snap.entries)).toBe(true);
  });
});

describe("NODE_PRESENCE_IDLE", () => {
  it("is frozen", () => {
    expect(Object.isFrozen(NODE_PRESENCE_IDLE)).toBe(true);
    expect(Object.isFrozen(NODE_PRESENCE_IDLE.entries)).toBe(true);
  });

  it("has zero-state defaults", () => {
    expect(NODE_PRESENCE_IDLE.totalCount).toBe(0);
    expect(NODE_PRESENCE_IDLE.pendingJoinCount).toBe(0);
    expect(NODE_PRESENCE_IDLE.joinPulse).toBe(0);
  });
});
