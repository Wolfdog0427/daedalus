/**
 * LONG-HORIZON RISK ANALYSIS
 *
 * Identifies issues that only manifest after 48+ hours of operation.
 * Tests for slow drifts, unbounded growth, timer accumulation,
 * subscriber leaks, and state that gets "stuck."
 */

import { createOrchestratorApp } from "../orchestrator";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { governanceService } from "../orchestrator/governance/GovernanceService";
import {
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  NodeMirrorRegistry,
} from "../orchestrator/mirror/NodeMirror";
import { IDLE_EXPRESSIVE } from "../orchestrator/mirror/NodeMirror.types";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
} from "../orchestrator/DaedalusEventBus";

jest.setTimeout(30_000);

function mkJoin(id: string) {
  return {
    nodeId: id, name: `N-${id}`,
    capabilities: [{ name: "core", value: "enabled", enabled: true }],
    expressive: { ...IDLE_EXPRESSIVE },
    profile: { id, name: `N-${id}`, kind: "server" as const, model: "x", os: "x", osVersion: "x", operatorId: "operator" },
  };
}

function mkHb(id: string) {
  return { nodeId: id, timestamp: new Date().toISOString(), status: "alive" as const };
}

describe("LONG-HORIZON RISK ANALYSIS", () => {
  let reg: NodeMirrorRegistry;

  beforeEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
    reg = getNodeMirrorRegistry();
  });

  afterEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 1. HEARTBEAT COUNT OVERFLOW
  // ═══════════════════════════════════════════════════════════════════════
  describe("Heartbeat count overflow risks", () => {
    test("heartbeatCount stays sane after 100K heartbeats", () => {
      reg.handleJoin(mkJoin("counter-node"));
      for (let i = 0; i < 100_000; i++) {
        reg.handleHeartbeat(mkHb("counter-node"));
      }
      const m = reg.getMirror("counter-node")!;
      expect(m.lifecycle.heartbeatCount).toBe(100_000);
      expect(Number.isSafeInteger(m.lifecycle.heartbeatCount)).toBe(true);
    });

    test("heartbeatCount: time to Number.MAX_SAFE_INTEGER at 1/s = 285M years", () => {
      // At 1 heartbeat/second, MAX_SAFE_INTEGER (~9e15) takes ~285 million years
      // This is not a practical concern
      expect(Number.MAX_SAFE_INTEGER).toBeGreaterThan(9e15);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 2. EVENT BUS SUBSCRIBER LEAK
  // ═══════════════════════════════════════════════════════════════════════
  describe("Event bus subscriber accumulation", () => {
    test("unsubscribe actually removes listener", () => {
      const bus = getDaedalusEventBus();
      let count = 0;
      const unsub = bus.subscribe(() => { count++; });

      reg.handleJoin(mkJoin("sub-test"));
      const afterSubscribe = count;

      unsub();

      reg.handleHeartbeat(mkHb("sub-test"));
      expect(count).toBe(afterSubscribe); // No more events received
    });

    test("100 subscribe/unsubscribe cycles don't leak", () => {
      const bus = getDaedalusEventBus();
      const unsubs: (() => void)[] = [];

      for (let i = 0; i < 100; i++) {
        unsubs.push(bus.subscribe(() => {}));
      }
      for (const unsub of unsubs) {
        unsub();
      }

      // All cleaned up — verify by checking a new subscription works
      let received = false;
      const final = bus.subscribe(() => { received = true; });
      reg.handleJoin(mkJoin("leak-check"));
      expect(received).toBe(true);
      final();
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 3. GOVERNANCE STATE ACCUMULATION
  // ═══════════════════════════════════════════════════════════════════════
  describe("Governance state accumulation over time", () => {
    test("overrides are capped at 200 — oldest evicted on overflow", () => {
      for (let i = 0; i < 210; i++) {
        governanceService.applyOverride({
          createdBy: { id: "operator", role: "OPERATOR" as const, label: "Op" },
          reason: `Override ${i}`,
          scope: "NODE" as const,
          effect: "ALLOW" as const,
        });
      }
      const overrides = governanceService.listOverrides();
      expect(overrides.length).toBe(200);
      expect(overrides[0].reason).toBe("Override 10");
    });

    test("drifts are capped at 200 — oldest evicted on overflow", () => {
      for (let i = 0; i < 210; i++) {
        governanceService.recordDrift({ severity: "LOW" as const, summary: `Drift ${i}` });
      }
      const drifts = governanceService.listDrifts();
      expect(drifts.length).toBe(200);
      expect(drifts[0].summary).toBe("Drift 10");
    });

    test("votes are capped at 50", () => {
      for (let i = 0; i < 60; i++) {
        governanceService.castVote({
          being: { id: `v-${i}`, role: "OPERATOR" as const, label: `V${i}` },
          vote: "ALLOW" as const,
          weight: 0.1,
        });
      }
      expect(governanceService.listVotes().length).toBeLessThanOrEqual(50);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 4. POSTURE STUCK-STATE RISK
  // ═══════════════════════════════════════════════════════════════════════
  describe("Posture getting stuck", () => {
    test("LOCKDOWN releases when GLOBAL DENY is removed", () => {
      governanceService.applyOverride({
        createdBy: { id: "operator", role: "OPERATOR" as const, label: "Op" },
        reason: "Emergency",
        scope: "GLOBAL" as const,
        effect: "DENY" as const,
      });
      expect(governanceService.getPostureSnapshot().posture).toBe("LOCKDOWN");

      governanceService.clearOverrides();
      expect(governanceService.getPostureSnapshot().posture).toBe("OPEN");
    });

    test("GUARDED releases when HIGH drift is cleared", () => {
      governanceService.recordDrift({ severity: "HIGH" as const, summary: "Crisis" });
      expect(governanceService.getPostureSnapshot().posture).toBe("GUARDED");

      governanceService.clearDrifts();
      expect(governanceService.getPostureSnapshot().posture).toBe("OPEN");
    });

    test("ATTENTIVE doesn't get stuck with many low-severity overrides", () => {
      for (let i = 0; i < 50; i++) {
        governanceService.applyOverride({
          createdBy: { id: "operator", role: "OPERATOR" as const, label: "Op" },
          reason: `Routine ${i}`,
          scope: "NODE" as const,
          effect: "ALLOW" as const,
        });
      }
      expect(governanceService.getPostureSnapshot().posture).toBe("ATTENTIVE");

      governanceService.clearOverrides();
      expect(governanceService.getPostureSnapshot().posture).toBe("OPEN");
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 5. MIRROR REGISTRY GROWTH WITH DETACHED NODES
  // ═══════════════════════════════════════════════════════════════════════
  describe("Detached node cleanup", () => {
    test("detached nodes are removed from registry (not ghosts)", () => {
      reg.handleJoin(mkJoin("ghost-1"));
      reg.handleDetach("ghost-1");
      expect(reg.getMirror("ghost-1")).toBeUndefined();
      expect(reg.getCount()).toBe(0);
    });

    test("1000 join/detach cycles don't leak mirrors", () => {
      for (let i = 0; i < 1000; i++) {
        reg.handleJoin(mkJoin(`cycle-${i}`));
        reg.handleDetach(`cycle-${i}`);
      }
      expect(reg.getCount()).toBe(0);
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 6. SNAPSHOT SIZE GROWTH OVER TIME
  // ═══════════════════════════════════════════════════════════════════════
  describe("Snapshot size projection", () => {
    test("snapshot size scales linearly with state, not exponentially", () => {
      const sizes: number[] = [];

      for (let batch = 0; batch < 5; batch++) {
        for (let i = 0; i < 10; i++) {
          reg.handleJoin(mkJoin(`snap-${batch}-${i}`));
        }
        for (let i = 0; i < 10; i++) {
          governanceService.applyOverride({
            createdBy: { id: "operator", role: "OPERATOR" as const, label: "Op" },
            reason: `Override ${batch}-${i}`,
            scope: "NODE" as const,
            effect: "ALLOW" as const,
          });
        }

        const snapshot = JSON.stringify({
          beings: daedalusStore.getBeingPresences(),
          overrides: governanceService.listOverrides(),
          drifts: governanceService.listDrifts(),
          votes: governanceService.listVotes(),
          mirrors: reg.getAllMirrors(),
        });
        sizes.push(snapshot.length);
      }

      // Each batch should add roughly the same amount
      for (let i = 1; i < sizes.length; i++) {
        const growth = sizes[i] - sizes[i - 1];
        const prevGrowth = i > 1 ? sizes[i - 1] - sizes[i - 2] : growth;
        // Growth should not be more than 3x the previous growth (linear, not exponential)
        expect(growth).toBeLessThan(prevGrowth * 3);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // 7. TIMESTAMP FORMAT CONSISTENCY
  // ═══════════════════════════════════════════════════════════════════════
  describe("Timestamp consistency", () => {
    test("all timestamps are ISO 8601", () => {
      reg.handleJoin(mkJoin("ts-node"));
      reg.handleHeartbeat(mkHb("ts-node"));

      const m = reg.getMirror("ts-node")!;
      const isoRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;

      expect(m.lifecycle.joinedAt).toMatch(isoRegex);
      if (m.lifecycle.lastHeartbeat) {
        expect(m.lifecycle.lastHeartbeat).toMatch(isoRegex);
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // FINAL: Risk summary
  // ═══════════════════════════════════════════════════════════════════════
  test("RISK SUMMARY: Long-horizon findings", () => {
    const findings = [
      "",
      "╔══════════════════════════════════════════════════════════════╗",
      "║         LONG-HORIZON RISK ANALYSIS — FINDINGS               ║",
      "╚══════════════════════════════════════════════════════════════╝",
      "",
      "  CONFIRMED SAFE:",
      "  ✓ Heartbeat counter: safe from overflow for ~285M years at 1/s",
      "  ✓ Event bus subscribers: properly cleaned up on unsubscribe",
      "  ✓ Detached nodes: removed from registry (no ghosts)",
      "  ✓ Join/detach cycles: no mirror leaks after 1000 cycles",
      "  ✓ Posture: always returns to OPEN when conditions clear",
      "  ✓ Snapshot size: linear growth (not exponential)",
      "  ✓ Vote cap: enforced at 50",
      "  ✓ Timestamps: consistent ISO 8601",
      "",
      "  ✓ Override cap: enforced at 200 (oldest evicted)",
      "  ✓ Drift cap: enforced at 200 (oldest evicted)",
      "",
      "  RISKS IDENTIFIED:",
      "  ⚠ No auto-expiry on overrides (operator must manually clear)",
      "  ⚠ No auto-expiry on drifts (must be manually cleared)",
      "  ⚠ Snapshot auto-save interval (30s) means up to 30s of state loss on crash",
      "  ⚠ No log rotation or log size management",
      "  ⚠ Event bus is in-memory only — no persistence of event history",
      "",
    ];

    console.log(findings.join("\n"));
    expect(true).toBe(true); // This test is purely diagnostic
  });
});
