import { computeEpistemicReport } from "../../shared/daedalus/epistemicIntakeEngine";
import type { ConnectivitySnapshot, ConnectivityNode } from "../../shared/daedalus/connectivity";
import { CONNECTIVITY_IDLE } from "../../shared/daedalus/connectivity";

function mkNode(overrides: Partial<ConnectivityNode> = {}): ConnectivityNode {
  return Object.freeze({
    id: "n",
    trusted: true,
    quarantined: false,
    health: 1,
    capabilityCount: 1,
    capabilities: Object.freeze(["cap"]),
    hasHeartbeat: true,
    joinRequested: false,
    suggestedTrustTier: "high" as const,
    ...overrides,
  });
}

function mkConn(overrides: Partial<ConnectivitySnapshot> = {}): ConnectivitySnapshot {
  return Object.freeze({
    ...CONNECTIVITY_IDLE,
    sseConnected: true,
    ...overrides,
  });
}

describe("computeEpistemicReport", () => {
  it("returns healthy for idle connectivity with SSE on", () => {
    const report = computeEpistemicReport(mkConn({ totalCount: 0, sseConnected: true }));
    expect(report.healthy).toBe(true);
    expect(report.overallQuality).toBe(0.8);
    expect(report.connectivityPenalty).toBe(0);
  });

  it("returns unhealthy for idle connectivity with SSE off", () => {
    const report = computeEpistemicReport(mkConn({ totalCount: 0, sseConnected: false }));
    expect(report.healthy).toBe(false);
    expect(report.overallQuality).toBe(0.5);
    expect(report.connectivityPenalty).toBe(0.2);
  });

  it("computes trust ratio correctly", () => {
    const report = computeEpistemicReport(
      mkConn({ totalCount: 4, trustedCount: 3, quarantinedCount: 0, networkQuality: 0.8 }),
    );
    expect(report.trustedRatio).toBe(0.75);
    expect(report.quarantinedRatio).toBe(0);
  });

  it("applies quarantine penalty", () => {
    const clean = computeEpistemicReport(
      mkConn({ totalCount: 4, trustedCount: 4, quarantinedCount: 0, networkQuality: 0.8 }),
    );
    const dirty = computeEpistemicReport(
      mkConn({ totalCount: 4, trustedCount: 2, quarantinedCount: 2, networkQuality: 0.8 }),
    );
    expect(dirty.overallQuality).toBeLessThan(clean.overallQuality);
    expect(dirty.quarantinedRatio).toBe(0.5);
  });

  it("reports healthy when quality >= 0.5 and quarantine ratio < 0.5", () => {
    const report = computeEpistemicReport(
      mkConn({ totalCount: 4, trustedCount: 3, quarantinedCount: 1, networkQuality: 0.8 }),
    );
    expect(report.healthy).toBe(true);
  });

  it("reports unhealthy when quarantine ratio >= 0.5", () => {
    const report = computeEpistemicReport(
      mkConn({ totalCount: 4, trustedCount: 1, quarantinedCount: 2, networkQuality: 0.8 }),
    );
    expect(report.healthy).toBe(false);
  });

  it("reports unhealthy when quality < 0.5", () => {
    const report = computeEpistemicReport(
      mkConn({ totalCount: 4, trustedCount: 0, quarantinedCount: 3, networkQuality: 0.2, sseConnected: false }),
    );
    expect(report.overallQuality).toBeLessThan(0.5);
    expect(report.healthy).toBe(false);
  });

  it("applies SSE disconnection penalty for nodes", () => {
    const on = computeEpistemicReport(
      mkConn({ totalCount: 2, trustedCount: 2, quarantinedCount: 0, networkQuality: 0.8, sseConnected: true }),
    );
    const off = computeEpistemicReport(
      mkConn({ totalCount: 2, trustedCount: 2, quarantinedCount: 0, networkQuality: 0.8, sseConnected: false }),
    );
    expect(off.overallQuality).toBeLessThan(on.overallQuality);
    expect(off.connectivityPenalty).toBe(0.2);
  });

  it("clamps overall quality to [0, 1]", () => {
    const report = computeEpistemicReport(
      mkConn({ totalCount: 2, trustedCount: 2, quarantinedCount: 0, networkQuality: 1.0 }),
    );
    expect(report.overallQuality).toBeLessThanOrEqual(1);
    expect(report.overallQuality).toBeGreaterThanOrEqual(0);
  });

  it("produces a frozen object", () => {
    const report = computeEpistemicReport(mkConn());
    expect(Object.isFrozen(report)).toBe(true);
  });

  it("high trust and quality gives a high overall score", () => {
    const report = computeEpistemicReport(
      mkConn({ totalCount: 5, trustedCount: 5, quarantinedCount: 0, networkQuality: 1.0 }),
    );
    expect(report.overallQuality).toBeGreaterThan(0.9);
    expect(report.healthy).toBe(true);
  });

  // ── Freshness ───────────────────────────────────────────────────

  it("freshness is 1 when all nodes have heartbeats", () => {
    const nodes = Object.freeze([mkNode({ id: "a" }), mkNode({ id: "b" })]);
    const report = computeEpistemicReport(
      mkConn({ totalCount: 2, trustedCount: 2, nodes, networkQuality: 1 }),
    );
    expect(report.freshness).toBe(1);
  });

  it("freshness drops when nodes lack heartbeats", () => {
    const nodes = Object.freeze([
      mkNode({ id: "a", hasHeartbeat: true }),
      mkNode({ id: "b", hasHeartbeat: false }),
    ]);
    const report = computeEpistemicReport(
      mkConn({ totalCount: 2, trustedCount: 2, nodes, networkQuality: 1 }),
    );
    expect(report.freshness).toBeCloseTo(0.5);
  });

  it("freshness is 0 when no nodes have heartbeats", () => {
    const nodes = Object.freeze([
      mkNode({ id: "a", hasHeartbeat: false }),
      mkNode({ id: "b", hasHeartbeat: false }),
    ]);
    const report = computeEpistemicReport(
      mkConn({ totalCount: 2, trustedCount: 2, nodes, networkQuality: 1 }),
    );
    expect(report.freshness).toBe(0);
  });

  it("freshness is 1 (default) for empty node list with SSE on", () => {
    const report = computeEpistemicReport(mkConn({ totalCount: 0, sseConnected: true }));
    expect(report.freshness).toBe(1);
  });

  it("freshness is 0 for empty node list with SSE off", () => {
    const report = computeEpistemicReport(mkConn({ totalCount: 0, sseConnected: false }));
    expect(report.freshness).toBe(0);
  });

  // ── Unverified warning ──────────────────────────────────────────

  it("no unverified warning when all nodes are trusted", () => {
    const nodes = Object.freeze([mkNode({ id: "a" }), mkNode({ id: "b" })]);
    const report = computeEpistemicReport(
      mkConn({ totalCount: 2, trustedCount: 2, nodes, networkQuality: 1 }),
    );
    expect(report.unverifiedCount).toBe(0);
    expect(report.unverifiedWarning).toBe(false);
  });

  it("flags unverified nodes (untrusted, not quarantined, no heartbeat)", () => {
    const nodes = Object.freeze([
      mkNode({ id: "a", trusted: true }),
      mkNode({ id: "b", trusted: false, quarantined: false, hasHeartbeat: false }),
    ]);
    const report = computeEpistemicReport(
      mkConn({ totalCount: 2, trustedCount: 1, nodes, networkQuality: 0.8 }),
    );
    expect(report.unverifiedCount).toBe(1);
    expect(report.unverifiedWarning).toBe(true);
  });

  it("does not flag quarantined nodes as unverified", () => {
    const nodes = Object.freeze([
      mkNode({ id: "a", trusted: false, quarantined: true, hasHeartbeat: false }),
    ]);
    const report = computeEpistemicReport(
      mkConn({ totalCount: 1, trustedCount: 0, quarantinedCount: 1, nodes, networkQuality: 0.5 }),
    );
    expect(report.unverifiedCount).toBe(0);
    expect(report.unverifiedWarning).toBe(false);
  });

  it("does not flag untrusted nodes with heartbeats as unverified", () => {
    const nodes = Object.freeze([
      mkNode({ id: "a", trusted: false, quarantined: false, hasHeartbeat: true }),
    ]);
    const report = computeEpistemicReport(
      mkConn({ totalCount: 1, trustedCount: 0, nodes, networkQuality: 0.6 }),
    );
    expect(report.unverifiedCount).toBe(0);
    expect(report.unverifiedWarning).toBe(false);
  });

  it("no unverified warning for empty node list", () => {
    const report = computeEpistemicReport(mkConn({ totalCount: 0 }));
    expect(report.unverifiedCount).toBe(0);
    expect(report.unverifiedWarning).toBe(false);
  });
});
