import { mapNode, computeConnectivity } from "../../shared/daedalus/connectivityEngine";
import type { RawNode } from "../../shared/daedalus/connectivityEngine";

function mkNode(overrides: Partial<RawNode> = {}): RawNode {
  return {
    id: "n1",
    status: "trusted",
    lastHeartbeat: new Date().toISOString(),
    risk: "low",
    capabilities: [{ name: "cap-a" }],
    ...overrides,
  };
}

describe("mapNode", () => {
  it("maps trusted status", () => {
    const n = mapNode(mkNode({ status: "trusted" }));
    expect(n.trusted).toBe(true);
    expect(n.quarantined).toBe(false);
  });

  it("maps quarantined status", () => {
    const n = mapNode(mkNode({ status: "quarantined" }));
    expect(n.trusted).toBe(false);
    expect(n.quarantined).toBe(true);
  });

  it("maps unknown status as neither trusted nor quarantined", () => {
    const n = mapNode(mkNode({ status: "unknown" }));
    expect(n.trusted).toBe(false);
    expect(n.quarantined).toBe(false);
  });

  it("maps risk to health: low=1, medium=0.6, high=0.2", () => {
    expect(mapNode(mkNode({ risk: "low" })).health).toBe(1);
    expect(mapNode(mkNode({ risk: "medium" })).health).toBe(0.6);
    expect(mapNode(mkNode({ risk: "high" })).health).toBe(0.2);
  });

  it("defaults health to 0.5 for unknown risk", () => {
    expect(mapNode(mkNode({ risk: "exotic" })).health).toBe(0.5);
  });

  it("counts capabilities", () => {
    const n = mapNode(mkNode({ capabilities: [{ name: "a" }, { name: "b" }] }));
    expect(n.capabilityCount).toBe(2);
  });

  it("detects heartbeat presence", () => {
    expect(mapNode(mkNode({ lastHeartbeat: "2025-01-01" })).hasHeartbeat).toBe(true);
    expect(mapNode(mkNode({ lastHeartbeat: null })).hasHeartbeat).toBe(false);
  });

  it("produces a frozen object", () => {
    expect(Object.isFrozen(mapNode(mkNode()))).toBe(true);
  });

  it("maps pending status as joinRequested", () => {
    const n = mapNode(mkNode({ status: "pending" }));
    expect(n.joinRequested).toBe(true);
    expect(n.trusted).toBe(false);
  });

  it("non-pending nodes are not joinRequested", () => {
    expect(mapNode(mkNode({ status: "trusted" })).joinRequested).toBe(false);
    expect(mapNode(mkNode({ status: "quarantined" })).joinRequested).toBe(false);
  });

  it("extracts capability names", () => {
    const n = mapNode(mkNode({ capabilities: [{ name: "x" }, { name: "y" }] }));
    expect(n.capabilities).toEqual(["x", "y"]);
    expect(Object.isFrozen(n.capabilities)).toBe(true);
  });

  it("derives suggestedTrustTier high for low-risk with 2+ caps", () => {
    const n = mapNode(mkNode({ risk: "low", capabilities: [{ name: "a" }, { name: "b" }] }));
    expect(n.suggestedTrustTier).toBe("high");
  });

  it("derives suggestedTrustTier low for high-risk", () => {
    const n = mapNode(mkNode({ risk: "high" }));
    expect(n.suggestedTrustTier).toBe("low");
  });

  it("derives suggestedTrustTier medium otherwise", () => {
    const n = mapNode(mkNode({ risk: "medium" }));
    expect(n.suggestedTrustTier).toBe("medium");
  });
});

describe("computeConnectivity", () => {
  it("returns idle-like snapshot for empty node list with SSE off", () => {
    const snap = computeConnectivity([], false);
    expect(snap.totalCount).toBe(0);
    expect(snap.trustedCount).toBe(0);
    expect(snap.networkQuality).toBe(0.5);
    expect(snap.sseConnected).toBe(false);
  });

  it("returns quality 1 for empty node list with SSE on", () => {
    const snap = computeConnectivity([], true);
    expect(snap.networkQuality).toBe(1);
    expect(snap.sseConnected).toBe(true);
  });

  it("counts trusted, quarantined, and pending-join nodes", () => {
    const nodes = [
      mkNode({ id: "a", status: "trusted" }),
      mkNode({ id: "b", status: "quarantined" }),
      mkNode({ id: "c", status: "pending" }),
      mkNode({ id: "d", status: "unknown" }),
    ];
    const snap = computeConnectivity(nodes, true);
    expect(snap.totalCount).toBe(4);
    expect(snap.trustedCount).toBe(1);
    expect(snap.quarantinedCount).toBe(1);
    expect(snap.pendingJoinCount).toBe(1);
  });

  it("computes high network quality for all trusted, low-risk, SSE-on nodes", () => {
    const nodes = [
      mkNode({ id: "a", status: "trusted", risk: "low" }),
      mkNode({ id: "b", status: "trusted", risk: "low" }),
    ];
    const snap = computeConnectivity(nodes, true);
    expect(snap.networkQuality).toBe(1);
  });

  it("applies SSE penalty when disconnected", () => {
    const nodesOn = [mkNode({ id: "a", status: "trusted", risk: "low" })];
    const qOn = computeConnectivity(nodesOn, true).networkQuality;
    const qOff = computeConnectivity(nodesOn, false).networkQuality;
    expect(qOff).toBeLessThan(qOn);
  });

  it("reduces quality for high-risk nodes", () => {
    const lowRisk = [mkNode({ id: "a", status: "trusted", risk: "low" })];
    const highRisk = [mkNode({ id: "a", status: "trusted", risk: "high" })];
    const qLow = computeConnectivity(lowRisk, true).networkQuality;
    const qHigh = computeConnectivity(highRisk, true).networkQuality;
    expect(qHigh).toBeLessThan(qLow);
  });

  it("reduces quality when nodes are untrusted", () => {
    const trusted = [mkNode({ id: "a", status: "trusted", risk: "low" })];
    const untrusted = [mkNode({ id: "a", status: "unknown", risk: "low" })];
    const qT = computeConnectivity(trusted, true).networkQuality;
    const qU = computeConnectivity(untrusted, true).networkQuality;
    expect(qU).toBeLessThan(qT);
  });

  it("clamps network quality to [0, 1]", () => {
    const worst = [
      mkNode({ id: "a", status: "quarantined", risk: "high" }),
      mkNode({ id: "b", status: "quarantined", risk: "high" }),
    ];
    const snap = computeConnectivity(worst, false);
    expect(snap.networkQuality).toBeGreaterThanOrEqual(0);
    expect(snap.networkQuality).toBeLessThanOrEqual(1);
  });

  it("produces a frozen snapshot", () => {
    const snap = computeConnectivity([mkNode()], true);
    expect(Object.isFrozen(snap)).toBe(true);
    expect(Object.isFrozen(snap.nodes)).toBe(true);
  });
});
