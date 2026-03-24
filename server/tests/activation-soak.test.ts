/**
 * ACTIVATION SOAK TEST — Full Lifecycle Simulation
 *
 * This test boots Daedalus from cold start and runs through every phase
 * of real-world operation. It is not a unit test — it is a simulation
 * of weeks of operation compressed into minutes.
 *
 * Phases:
 *   0. Cold boot & initial state validation
 *   1. Fleet assembly (progressive node joins)
 *   2. Steady-state operation (sustained heartbeats, being updates)
 *   3. Circadian simulation (high/low activity cycles)
 *   4. Chaos injection (errors, stale sweeps, quarantines)
 *   5. Governance storm (overrides, votes, drifts, posture changes)
 *   6. Operator intervention (manual actions via HTTP)
 *   7. Recovery & stabilization
 *   8. Persistence cycle (save → clear → restore → verify)
 *   9. Scale-up stress (large fleet, rapid events)
 *  10. Concurrent request barrage
 *  11. Final audit & report
 *
 * Metrics tracked: memory, event throughput, error rates, invariant health,
 * timing, state coherence, data integrity.
 */

import request from "supertest";
import fs from "node:fs";
import path from "node:path";
import { createOrchestratorApp } from "../orchestrator";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { governanceService } from "../orchestrator/governance/GovernanceService";
import {
  NodeMirrorRegistry,
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
} from "../orchestrator/mirror/NodeMirror";
import { IDLE_EXPRESSIVE } from "../orchestrator/mirror/NodeMirror.types";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { SnapshotPersistence } from "../orchestrator/persistence/SnapshotPersistence";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import { DAEDALUS_IDENTITY } from "../../shared/daedalus/identity";
import { GLOW_PALETTE } from "../../shared/daedalus/glowPalette";

// ── Metrics Collector ─────────────────────────────────────────────────
interface Metrics {
  phaseTimings: Record<string, number>;
  memorySnapshots: Array<{ phase: string; heapUsedMB: number; rss: number }>;
  eventCounts: Record<string, number>;
  totalEventsReceived: number;
  totalEventsDropped: number;
  invariantChecks: Array<{ phase: string; passed: boolean; failures: string[] }>;
  errorLog: string[];
  warnings: string[];
  httpResponseTimes: number[];
  peakNodeCount: number;
  peakOverrideCount: number;
  peakVoteCount: number;
  postureTransitions: string[];
  constitutionResults: Array<{ phase: string; allPassed: boolean; failedChecks: string[] }>;
}

function createMetrics(): Metrics {
  return {
    phaseTimings: {},
    memorySnapshots: [],
    eventCounts: {},
    totalEventsReceived: 0,
    totalEventsDropped: 0,
    invariantChecks: [],
    errorLog: [],
    warnings: [],
    httpResponseTimes: [],
    peakNodeCount: 0,
    peakOverrideCount: 0,
    peakVoteCount: 0,
    postureTransitions: [],
    constitutionResults: [],
  };
}

function snapMemory(metrics: Metrics, phase: string) {
  const mem = process.memoryUsage();
  metrics.memorySnapshots.push({
    phase,
    heapUsedMB: Math.round(mem.heapUsed / 1024 / 1024 * 100) / 100,
    rss: Math.round(mem.rss / 1024 / 1024 * 100) / 100,
  });
}

// ── Invariant Checker ──────────────────────────────────────────────────
function checkInvariants(
  reg: NodeMirrorRegistry,
  phaseName: string,
  metrics: Metrics,
) {
  const failures: string[] = [];
  const mirrors = reg.getAllMirrors();

  for (const m of mirrors) {
    if (m.lifecycle.heartbeatCount < 0) failures.push(`${m.id}: negative heartbeatCount`);
    if (m.lifecycle.errorCount < 0) failures.push(`${m.id}: negative errorCount`);
    if (m.lifecycle.errorCount > 100000) failures.push(`${m.id}: errorCount unbounded (${m.lifecycle.errorCount})`);

    const validPhases = ["discovered", "joining", "negotiating", "syncing", "active", "degraded", "quarantined", "detached"];
    if (!validPhases.includes(m.lifecycle.phase)) failures.push(`${m.id}: invalid phase "${m.lifecycle.phase}"`);

    if (m.status === "quarantined" && m.lifecycle.phase !== "quarantined") {
      failures.push(`${m.id}: status/phase mismatch: status=${m.status} phase=${m.lifecycle.phase}`);
    }
  }

  const posture = governanceService.getPostureSnapshot();
  const validPostures = ["OPEN", "ATTENTIVE", "GUARDED", "LOCKDOWN"];
  if (!validPostures.includes(posture.posture)) failures.push(`Invalid posture: ${posture.posture}`);
  if (posture.activeOverrides.length !== governanceService.listOverrides().length) {
    failures.push(`Posture overrides mismatch: snapshot=${posture.activeOverrides.length} actual=${governanceService.listOverrides().length}`);
  }

  for (const v of governanceService.listVotes()) {
    if (v.weight < 0 || v.weight > 1) failures.push(`Vote weight out of bounds: ${v.weight}`);
  }

  const beings = daedalusStore.getBeingPresences();
  const ids = beings.map(b => b.id);
  if (new Set(ids).size !== ids.length) failures.push("Duplicate being IDs");
  if (!beings.some(b => b.id === "operator")) failures.push("Operator being missing");

  for (const b of beings) {
    if (b.continuity && b.continuity.streak < 0) failures.push(`${b.id}: negative continuity streak`);
    if (b.influenceLevel < 0 || b.influenceLevel > 1) failures.push(`${b.id}: influenceLevel out of bounds`);
  }

  metrics.invariantChecks.push({ phase: phaseName, passed: failures.length === 0, failures });
  return failures.length === 0;
}

function checkConstitution(phaseName: string, metrics: Metrics) {
  const beings = daedalusStore.getBeingPresences();
  const beingMap: Record<string, any> = {};
  for (const b of beings) beingMap[b.id] = b;
  const behavioral = computeBehavioralField(beingMap);
  const report = validateBeingConstitution(beings, governanceService.listVotes(), behavioral.dominantBeingId);
  const failedChecks = report.checks.filter((c: any) => !c.passed).map((c: any) => c.name);
  metrics.constitutionResults.push({ phase: phaseName, allPassed: report.allPassed, failedChecks });
  return report.allPassed;
}

// ── Join Helper ────────────────────────────────────────────────────────
function mkJoin(id: string) {
  return {
    nodeId: id,
    name: `Node-${id}`,
    capabilities: [
      { name: "core", value: "enabled", enabled: true },
      { name: "heartbeat", value: "enabled", enabled: true },
    ],
    expressive: { ...IDLE_EXPRESSIVE },
    profile: {
      id,
      name: `Node-${id}`,
      kind: "server" as const,
      model: "soak-test",
      os: "linux",
      osVersion: "6.0",
      operatorId: "operator",
    },
  };
}

function mkHb(nodeId: string): { nodeId: string; timestamp: string; status: "alive" } {
  return { nodeId, timestamp: new Date().toISOString(), status: "alive" };
}

function mkOverride(
  scope: "NODE" | "CAPABILITY" | "GLOBAL" = "NODE",
  effect: "ALLOW" | "DENY" | "ESCALATE" = "ALLOW",
) {
  return {
    createdBy: { id: "operator", role: "OPERATOR" as const, label: "Operator" },
    reason: `Soak test override - ${Date.now()}`,
    scope,
    effect,
  };
}

function mkVote(
  beingId: string,
  vote: "ALLOW" | "DENY" | "ESCALATE" = "ALLOW",
  weight = 0.5,
) {
  return {
    being: { id: beingId, role: "OPERATOR" as const, label: beingId },
    vote,
    weight,
  };
}

// ── Main Test ─────────────────────────────────────────────────────────
jest.setTimeout(120_000);

describe("ACTIVATION SOAK — Full Lifecycle Simulation", () => {
  const app = createOrchestratorApp();
  const metrics = createMetrics();
  let reg: NodeMirrorRegistry;
  let eventLog: DaedalusEventPayload[] = [];
  let unsubscribe: (() => void) | null = null;

  beforeAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();

    reg = getNodeMirrorRegistry();

    const bus = getDaedalusEventBus();
    unsubscribe = bus.subscribe((event) => {
      eventLog.push(event);
      metrics.totalEventsReceived++;
      metrics.eventCounts[event.type] = (metrics.eventCounts[event.type] ?? 0) + 1;
      if (event.type === "POSTURE_CHANGED") {
        metrics.postureTransitions.push(`${event.posture} (${event.summary})`);
      }
    });
  });

  afterAll(() => {
    unsubscribe?.();
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
  });

  function timePhase(name: string, fn: () => void) {
    const start = performance.now();
    fn();
    metrics.phaseTimings[name] = Math.round(performance.now() - start);
  }

  async function timePhaseAsync(name: string, fn: () => Promise<void>) {
    const start = performance.now();
    await fn();
    metrics.phaseTimings[name] = Math.round(performance.now() - start);
  }

  // ── Phase 0: Cold Boot ──────────────────────────────────────────────
  test("Phase 0: Cold boot — identity, beings, governance, empty fabric", () => {
    timePhase("0_cold_boot", () => {
      snapMemory(metrics, "cold_boot");

      expect(DAEDALUS_IDENTITY.name).toBe("Daedalus");
      expect(DAEDALUS_IDENTITY.gates.length).toBeGreaterThan(0);
      expect(Object.keys(GLOW_PALETTE).length).toBeGreaterThanOrEqual(4);

      const beings = daedalusStore.getBeingPresences();
      expect(beings.length).toBeGreaterThanOrEqual(2);
      expect(beings.find(b => b.id === "operator")).toBeDefined();

      expect(governanceService.getPostureSnapshot().posture).toBe("OPEN");
      expect(governanceService.listOverrides()).toHaveLength(0);
      expect(governanceService.listVotes()).toHaveLength(0);
      expect(governanceService.listDrifts()).toHaveLength(0);

      expect(reg.getCount()).toBe(0);

      checkInvariants(reg, "Phase 0", metrics);
      checkConstitution("Phase 0", metrics);
    });
  });

  // ── Phase 1: Fleet Assembly ──────────────────────────────────────────
  test("Phase 1: Fleet assembly — 50 nodes join progressively", () => {
    timePhase("1_fleet_assembly", () => {
      for (let i = 1; i <= 50; i++) {
        reg.handleJoin(mkJoin(`fleet-${i}`));
      }
      expect(reg.getCount()).toBe(50);
      metrics.peakNodeCount = Math.max(metrics.peakNodeCount, reg.getCount());

      for (let i = 1; i <= 50; i++) {
        const m = reg.getMirror(`fleet-${i}`);
        expect(m).toBeDefined();
        expect(m!.lifecycle.phase).toBe("active");
        expect(m!.status).toBe("trusted");
      }

      snapMemory(metrics, "fleet_assembled_50");
      checkInvariants(reg, "Phase 1: 50 nodes", metrics);
    });
  });

  // ── Phase 2: Steady State ────────────────────────────────────────────
  test("Phase 2: Steady-state operation — 500 heartbeat cycles", () => {
    timePhase("2_steady_state", () => {
      for (let cycle = 0; cycle < 500; cycle++) {
        for (let i = 1; i <= 50; i++) {
          reg.handleHeartbeat(mkHb(`fleet-${i}`));
        }
      }

      for (let i = 1; i <= 50; i++) {
        const m = reg.getMirror(`fleet-${i}`)!;
        expect(m.lifecycle.heartbeatCount).toBe(500);
        expect(m.lifecycle.phase).toBe("active");
      }

      daedalusStore.updateBeingPresence("operator", {
        continuity: { streak: 100, lastCheckIn: new Date().toISOString(), healthy: true },
      });

      snapMemory(metrics, "steady_state_500_cycles");
      checkInvariants(reg, "Phase 2: 500 cycles", metrics);
      checkConstitution("Phase 2", metrics);
    });
  });

  // ── Phase 3: Circadian Simulation ────────────────────────────────────
  test("Phase 3: Circadian — high activity → quiet → high", () => {
    timePhase("3_circadian", () => {
      // High activity: 200 rapid heartbeats
      for (let cycle = 0; cycle < 200; cycle++) {
        for (let i = 1; i <= 50; i++) {
          reg.handleHeartbeat(mkHb(`fleet-${i}`));
        }
      }
      const postHigh = governanceService.getPostureSnapshot().posture;

      // Quiet period: no heartbeats, just check nothing drifts
      const quietBeings = daedalusStore.getBeingPresences();
      const quietStreaks = quietBeings.map(b => b.continuity?.streak ?? 0);

      // Resume high activity
      for (let cycle = 0; cycle < 100; cycle++) {
        for (let i = 1; i <= 50; i++) {
          reg.handleHeartbeat(mkHb(`fleet-${i}`));
        }
      }

      const postResume = governanceService.getPostureSnapshot().posture;
      expect(postResume).toBe("OPEN");

      // Streaks should be preserved (no drift during quiet)
      const afterBeings = daedalusStore.getBeingPresences();
      for (const b of afterBeings) {
        const before = quietStreaks[quietBeings.findIndex(qb => qb.id === b.id)] ?? 0;
        expect(b.continuity?.streak).toBeGreaterThanOrEqual(before);
      }

      snapMemory(metrics, "circadian_complete");
      checkInvariants(reg, "Phase 3: circadian", metrics);
    });
  });

  // ── Phase 4: Chaos Injection ─────────────────────────────────────────
  test("Phase 4: Chaos — errors, stale sweeps, quarantines", () => {
    timePhase("4_chaos", () => {
      // Introduce errors on 10 nodes
      for (let i = 1; i <= 10; i++) {
        for (let e = 0; e < 4; e++) {
          reg.handleError(`fleet-${i}`, `Chaos error ${e}`);
        }
      }
      // These should NOT be quarantined yet (threshold is 5)
      for (let i = 1; i <= 10; i++) {
        const m = reg.getMirror(`fleet-${i}`)!;
        expect(m.lifecycle.errorCount).toBe(4);
        expect(m.lifecycle.phase).not.toBe("quarantined");
      }

      // Push 5 nodes over the threshold
      for (let i = 1; i <= 5; i++) {
        reg.handleError(`fleet-${i}`, "Final chaos error");
      }
      for (let i = 1; i <= 5; i++) {
        expect(reg.getMirror(`fleet-${i}`)!.lifecycle.phase).toBe("quarantined");
      }
      for (let i = 6; i <= 10; i++) {
        expect(reg.getMirror(`fleet-${i}`)!.lifecycle.phase).not.toBe("quarantined");
      }

      // Stale heartbeat sweep
      const farFuture = Date.now() + 120_000;
      const stale = reg.sweepStaleHeartbeats(farFuture);
      expect(stale.length).toBeGreaterThan(0);

      snapMemory(metrics, "chaos_complete");
      checkInvariants(reg, "Phase 4: chaos", metrics);
    });
  });

  // ── Phase 5: Governance Storm ────────────────────────────────────────
  test("Phase 5: Governance storm — overrides, votes, drifts", () => {
    timePhase("5_governance_storm", () => {
      // 20 overrides
      for (let i = 0; i < 20; i++) {
        governanceService.applyOverride(mkOverride("NODE", "ALLOW"));
      }
      metrics.peakOverrideCount = Math.max(metrics.peakOverrideCount, governanceService.listOverrides().length);
      expect(governanceService.getPostureSnapshot().posture).toBe("ATTENTIVE");

      // GLOBAL DENY → LOCKDOWN
      governanceService.applyOverride(mkOverride("GLOBAL", "DENY"));
      expect(governanceService.getPostureSnapshot().posture).toBe("LOCKDOWN");

      // 30 votes from different beings
      for (let i = 0; i < 30; i++) {
        governanceService.castVote(mkVote(`soak-being-${i}`, "ALLOW", 0.3));
      }
      metrics.peakVoteCount = Math.max(metrics.peakVoteCount, governanceService.listVotes().length);

      // HIGH drift
      governanceService.recordDrift({ severity: "HIGH", summary: "Soak test drift" });
      governanceService.recordDrift({ severity: "MEDIUM", summary: "Secondary drift" });

      const posture = governanceService.getPostureSnapshot();
      expect(posture.posture).toBe("LOCKDOWN"); // GLOBAL DENY still active

      snapMemory(metrics, "governance_storm");
      checkInvariants(reg, "Phase 5: governance storm", metrics);
      checkConstitution("Phase 5", metrics);
    });
  });

  // ── Phase 6: Operator Intervention via HTTP ──────────────────────────
  test("Phase 6: Operator actions via HTTP", async () => {
    await timePhaseAsync("6_operator_http", async () => {
      // View governance posture
      let t0 = performance.now();
      let res = await request(app).get("/daedalus/governance/posture").expect(200);
      metrics.httpResponseTimes.push(performance.now() - t0);
      expect(res.body.posture).toBe("LOCKDOWN");

      // View cockpit nodes
      t0 = performance.now();
      res = await request(app).get("/daedalus/cockpit/nodes").expect(200);
      metrics.httpResponseTimes.push(performance.now() - t0);
      expect(res.body.length).toBeGreaterThan(0);

      // View cockpit summary
      t0 = performance.now();
      res = await request(app).get("/daedalus/cockpit/summary").expect(200);
      metrics.httpResponseTimes.push(performance.now() - t0);
      expect(res.body.totalNodes).toBeGreaterThan(0);

      // View beings
      t0 = performance.now();
      res = await request(app).get("/daedalus/beings/presence").expect(200);
      metrics.httpResponseTimes.push(performance.now() - t0);
      expect(res.body.length).toBeGreaterThanOrEqual(2);

      // View constitution
      t0 = performance.now();
      res = await request(app).get("/daedalus/constitution").expect(200);
      metrics.httpResponseTimes.push(performance.now() - t0);
      expect(res.body.allPassed).toBe(true);

      // Update being
      t0 = performance.now();
      res = await request(app)
        .put("/daedalus/beings/operator/presence")
        .send({ influenceLevel: 0.95 })
        .expect(200);
      metrics.httpResponseTimes.push(performance.now() - t0);
      expect(res.body.influenceLevel).toBe(0.95);

      // View snapshot
      t0 = performance.now();
      res = await request(app).get("/daedalus/snapshot").expect(200);
      metrics.httpResponseTimes.push(performance.now() - t0);
      expect(res.body.nodes).toBeDefined();
      expect(res.body.beings).toBeDefined();

      snapMemory(metrics, "operator_http");
    });
  });

  // ── Phase 7: Recovery & Stabilization ────────────────────────────────
  test("Phase 7: Recovery — clear governance, heal nodes", () => {
    timePhase("7_recovery", () => {
      governanceService.clearOverrides();
      governanceService.clearDrifts();
      governanceService.clearVotes();

      expect(governanceService.getPostureSnapshot().posture).toBe("OPEN");
      expect(governanceService.listOverrides()).toHaveLength(0);
      expect(governanceService.listVotes()).toHaveLength(0);
      expect(governanceService.listDrifts()).toHaveLength(0);

      // Detach quarantined nodes and rejoin them fresh
      const quarantined = reg.getAllMirrors().filter(m => m.lifecycle.phase === "quarantined");
      for (const m of quarantined) {
        reg.handleDetach(m.id);
        reg.handleJoin(mkJoin(m.id));
        reg.handleHeartbeat(mkHb(m.id));
      }

      // Heartbeat all remaining active nodes
      for (const m of reg.getAllMirrors()) {
        if (m.lifecycle.phase === "active" || m.lifecycle.phase === "degraded") {
          reg.handleHeartbeat(mkHb(m.id));
        }
      }

      snapMemory(metrics, "recovery_complete");
      checkInvariants(reg, "Phase 7: recovery", metrics);
      checkConstitution("Phase 7", metrics);
    });
  });

  // ── Phase 8: Persistence Cycle ───────────────────────────────────────
  test("Phase 8: Persistence — save, verify, restore", () => {
    timePhase("8_persistence", () => {
      const tmpPath = path.join(__dirname, `.soak-snapshot-${Date.now()}.json`);
      const persistence = new SnapshotPersistence(tmpPath);

      const snapshot = {
        beings: daedalusStore.getBeingPresences(),
        overrides: governanceService.listOverrides(),
        drifts: governanceService.listDrifts(),
        votes: governanceService.listVotes(),
        mirrors: reg.getAllMirrors(),
        savedAt: new Date().toISOString(),
      };

      persistence.save(snapshot);
      expect(fs.existsSync(tmpPath)).toBe(true);

      const loaded = persistence.load();
      expect(loaded).not.toBeNull();
      expect(loaded!.beings.length).toBe(snapshot.beings.length);
      expect(loaded!.mirrors.length).toBe(snapshot.mirrors.length);
      expect(loaded!.savedAt).toBe(snapshot.savedAt);

      // Verify JSON size is sane
      const fileSize = fs.statSync(tmpPath).size;
      metrics.warnings.push(`Snapshot file size: ${Math.round(fileSize / 1024)}KB`);
      if (fileSize > 10 * 1024 * 1024) {
        metrics.errorLog.push(`WARNING: Snapshot size exceeds 10MB (${fileSize} bytes)`);
      }

      // Cleanup
      fs.unlinkSync(tmpPath);

      snapMemory(metrics, "persistence_cycle");
    });
  });

  // ── Phase 9: Scale-Up Stress ─────────────────────────────────────────
  test("Phase 9: Scale-up — 500 additional nodes, rapid events", () => {
    timePhase("9_scale_up", () => {
      // Detach existing nodes to start clean count
      const existing = reg.getAllMirrors().map(m => m.id);
      for (const id of existing) {
        if (reg.getMirror(id)?.lifecycle.phase !== "quarantined" &&
            reg.getMirror(id)?.lifecycle.phase !== "detached") {
          reg.handleDetach(id);
        }
      }

      // Join 500 nodes
      for (let i = 1; i <= 500; i++) {
        reg.handleJoin(mkJoin(`scale-${i}`));
      }
      expect(reg.getCount()).toBe(500);
      metrics.peakNodeCount = Math.max(metrics.peakNodeCount, 500);

      // 3 heartbeat rounds
      for (let round = 0; round < 3; round++) {
        for (let i = 1; i <= 500; i++) {
          reg.handleHeartbeat(mkHb(`scale-${i}`));
        }
      }

      // Verify all active
      let activeCount = 0;
      for (let i = 1; i <= 500; i++) {
        if (reg.getMirror(`scale-${i}`)?.lifecycle.phase === "active") activeCount++;
      }
      expect(activeCount).toBe(500);

      // Cockpit view timing
      const t0 = performance.now();
      const views = reg.toCockpitView();
      const cockpitTime = performance.now() - t0;
      expect(views.length).toBe(500);
      if (cockpitTime > 200) {
        metrics.warnings.push(`toCockpitView at 500 nodes took ${Math.round(cockpitTime)}ms`);
      }

      snapMemory(metrics, "scale_up_500");
      checkInvariants(reg, "Phase 9: 500 nodes", metrics);
    });
  });

  // ── Phase 10: Concurrent Request Barrage ─────────────────────────────
  test("Phase 10: Concurrent HTTP barrage", async () => {
    await timePhaseAsync("10_concurrent", async () => {
      const promises: Promise<any>[] = [];

      // 50 concurrent GET requests
      for (let i = 0; i < 10; i++) {
        promises.push(request(app).get("/daedalus/cockpit/summary"));
        promises.push(request(app).get("/daedalus/governance/posture"));
        promises.push(request(app).get("/daedalus/beings/presence"));
        promises.push(request(app).get("/daedalus/cockpit/nodes"));
        promises.push(request(app).get("/daedalus/snapshot"));
      }

      const results = await Promise.all(promises);

      let okCount = 0;
      let errCount = 0;
      for (const res of results) {
        if (res.status === 200) okCount++;
        else errCount++;
      }

      expect(okCount).toBe(50);
      expect(errCount).toBe(0);

      if (errCount > 0) {
        metrics.errorLog.push(`${errCount} concurrent requests failed`);
      }

      snapMemory(metrics, "concurrent_barrage");
    });
  });

  // ── Phase 11: Extended Lifecycle Simulation ──────────────────────────
  test("Phase 11: Extended lifecycle — simulate weeks of operation", () => {
    timePhase("11_extended_lifecycle", () => {
      // Week 1: steady growth
      for (let day = 1; day <= 7; day++) {
        // Morning: some nodes join
        for (let i = 0; i < 5; i++) {
          const id = `week1-d${day}-n${i}`;
          reg.handleJoin(mkJoin(id));
        }

        // Day: heartbeats for all active
        const active = reg.getAllMirrors().filter(m => m.lifecycle.phase === "active");
        for (let hb = 0; hb < 10; hb++) {
          for (const m of active) {
            reg.handleHeartbeat(mkHb(m.id));
          }
        }

        // Evening: some governance activity
        if (day % 2 === 0) {
          governanceService.applyOverride(mkOverride("NODE", "ALLOW"));
        }
        if (day % 3 === 0) {
          governanceService.recordDrift({ severity: "LOW", summary: `Day ${day} drift` });
        }
      }

      // Week 2: chaos week
      for (let day = 8; day <= 14; day++) {
        // Random errors on 10% of active nodes
        const active = reg.getAllMirrors().filter(m => m.lifecycle.phase === "active");
        const errorTargets = active.slice(0, Math.floor(active.length * 0.1));
        for (const m of errorTargets) {
          reg.handleError(m.id, `Week 2 day ${day} error`);
        }

        // Some nodes detach and rejoin
        const detachTargets = active.slice(-3);
        for (const m of detachTargets) {
          reg.handleDetach(m.id);
          reg.handleJoin(mkJoin(m.id));
        }

        // Heartbeats continue for active
        const stillActive = reg.getAllMirrors().filter(m => m.lifecycle.phase === "active");
        for (let hb = 0; hb < 5; hb++) {
          for (const m of stillActive) {
            reg.handleHeartbeat(mkHb(m.id));
          }
        }
      }

      // Week 3: stabilization
      governanceService.clearOverrides();
      governanceService.clearDrifts();
      governanceService.clearVotes();

      // Final heartbeat round for all active
      const finalActive = reg.getAllMirrors().filter(m => m.lifecycle.phase === "active");
      for (let hb = 0; hb < 20; hb++) {
        for (const m of finalActive) {
          reg.handleHeartbeat(mkHb(m.id));
        }
      }

      snapMemory(metrics, "extended_lifecycle");
      metrics.peakNodeCount = Math.max(metrics.peakNodeCount, reg.getCount());
      checkInvariants(reg, "Phase 11: 3 weeks simulated", metrics);
      checkConstitution("Phase 11", metrics);
    });
  });

  // ── Phase 12: Data Integrity Deep Scan ───────────────────────────────
  test("Phase 12: Data integrity — cross-validate all state", () => {
    timePhase("12_integrity", () => {
      const mirrors = reg.getAllMirrors();
      const cockpit = reg.toCockpitView();
      const beings = daedalusStore.getBeingPresences();
      const posture = governanceService.getPostureSnapshot();

      // Cockpit view count matches registry
      expect(cockpit.length).toBe(mirrors.length);

      // All cockpit node IDs match registry
      const cockpitIds = new Set(cockpit.map(c => c.id));
      const mirrorIds = new Set(mirrors.map(m => m.id));
      expect(cockpitIds).toEqual(mirrorIds);

      // Cockpit status matches mirror status
      for (const c of cockpit) {
        const m = reg.getMirror(c.id);
        expect(m).toBeDefined();
        expect(c.status).toBe(m!.status);
        expect(c.phase).toBe(m!.lifecycle.phase);
        expect(c.errorCount).toBe(m!.lifecycle.errorCount);
      }

      // Beings all have required fields
      for (const b of beings) {
        expect(b.id).toBeTruthy();
        expect(b.name).toBeTruthy();
        expect(b.posture).toBeTruthy();
        expect(b.glow).toBeDefined();
        expect(b.attention).toBeDefined();
        expect(b.continuity).toBeDefined();
      }

      // Posture is self-consistent
      expect(posture.posture).toBe("OPEN");
      expect(posture.activeOverrides).toHaveLength(0);
      expect(posture.activeDrifts).toHaveLength(0);

      checkInvariants(reg, "Phase 12: integrity", metrics);
    });
  });

  // ── Phase 13: Memory Growth Analysis ─────────────────────────────────
  test("Phase 13: Memory stability — detect leaks", () => {
    timePhase("13_memory", () => {
      // Force GC if available
      if (global.gc) global.gc();
      snapMemory(metrics, "pre_gc");

      // Run 1000 more heartbeat cycles to see if memory grows
      const active = reg.getAllMirrors().filter(m => m.lifecycle.phase === "active");

      snapMemory(metrics, "pre_1000_cycles");
      const preHeap = process.memoryUsage().heapUsed;

      for (let cycle = 0; cycle < 1000; cycle++) {
        for (const m of active.slice(0, 50)) {
          reg.handleHeartbeat(mkHb(m.id));
        }
      }

      snapMemory(metrics, "post_1000_cycles");
      const postHeap = process.memoryUsage().heapUsed;

      const growthMB = (postHeap - preHeap) / 1024 / 1024;
      if (growthMB > 50) {
        metrics.errorLog.push(`LEAK DETECTED: ${growthMB.toFixed(1)}MB growth over 1000 cycles`);
      } else if (growthMB > 20) {
        metrics.warnings.push(`High memory growth: ${growthMB.toFixed(1)}MB over 1000 cycles`);
      }
    });
  });

  // ── Phase 14: Event Stream Completeness ──────────────────────────────
  test("Phase 14: Event stream — verify no silent drops", () => {
    timePhase("14_events", () => {
      const beforeCount = metrics.totalEventsReceived;

      // Create trackable events
      const trackableActions = 0;
      const expectedEvents: string[] = [];

      // Override → event
      governanceService.applyOverride(mkOverride("NODE", "ALLOW"));
      expectedEvents.push("GOVERNANCE_OVERRIDE_APPLIED", "POSTURE_CHANGED");

      // Drift → event
      governanceService.recordDrift({ severity: "HIGH", summary: "Track event" });
      expectedEvents.push("CONTINUITY_DRIFT_DETECTED", "POSTURE_CHANGED");

      // Vote → event
      governanceService.castVote(mkVote("operator", "ALLOW", 0.5));
      expectedEvents.push("GOVERNANCE_OVERRIDE_APPLIED");

      const afterCount = metrics.totalEventsReceived;
      const emitted = afterCount - beforeCount;

      // We expect at least the events we triggered (may include posture changes)
      expect(emitted).toBeGreaterThanOrEqual(3);

      // Cleanup
      governanceService.clearOverrides();
      governanceService.clearDrifts();
      governanceService.clearVotes();
    });
  });

  // ── FINAL: Generate Report ───────────────────────────────────────────
  test("FINAL: Activation readiness report", () => {
    snapMemory(metrics, "final");

    // ── Report Generation ──────────────────────────────────────────────
    const report: string[] = [
      "",
      "╔══════════════════════════════════════════════════════════════╗",
      "║          DAEDALUS ACTIVATION SOAK — READINESS REPORT        ║",
      "╚══════════════════════════════════════════════════════════════╝",
      "",
    ];

    // Identity
    report.push("┌─ IDENTITY ─────────────────────────────────────────────────┐");
    report.push(`│  Name: ${DAEDALUS_IDENTITY.name}`);
    report.push(`│  Gates: ${DAEDALUS_IDENTITY.gates.length}`);
    report.push(`│  Glow levels: ${Object.keys(GLOW_PALETTE).join(", ")}`);
    report.push("└────────────────────────────────────────────────────────────┘");

    // Phase Timings
    report.push("");
    report.push("┌─ PHASE TIMINGS ────────────────────────────────────────────┐");
    let totalTime = 0;
    for (const [phase, ms] of Object.entries(metrics.phaseTimings)) {
      report.push(`│  ${phase}: ${ms}ms`);
      totalTime += ms;
    }
    report.push(`│  TOTAL: ${totalTime}ms`);
    report.push("└────────────────────────────────────────────────────────────┘");

    // Memory
    report.push("");
    report.push("┌─ MEMORY PROFILE ───────────────────────────────────────────┐");
    for (const snap of metrics.memorySnapshots) {
      report.push(`│  ${snap.phase}: heap=${snap.heapUsedMB}MB rss=${snap.rss}MB`);
    }
    const firstHeap = metrics.memorySnapshots[0]?.heapUsedMB ?? 0;
    const lastHeap = metrics.memorySnapshots[metrics.memorySnapshots.length - 1]?.heapUsedMB ?? 0;
    const heapGrowth = lastHeap - firstHeap;
    report.push(`│  GROWTH: ${heapGrowth.toFixed(2)}MB (${firstHeap}MB → ${lastHeap}MB)`);
    report.push("└────────────────────────────────────────────────────────────┘");

    // Events
    report.push("");
    report.push("┌─ EVENT STREAM ─────────────────────────────────────────────┐");
    report.push(`│  Total events received: ${metrics.totalEventsReceived}`);
    for (const [type, count] of Object.entries(metrics.eventCounts).sort((a, b) => b[1] - a[1])) {
      report.push(`│    ${type}: ${count}`);
    }
    report.push(`│  Posture transitions: ${metrics.postureTransitions.length}`);
    for (const t of metrics.postureTransitions.slice(-5)) {
      report.push(`│    → ${t}`);
    }
    report.push("└────────────────────────────────────────────────────────────┘");

    // Scale
    report.push("");
    report.push("┌─ SCALE METRICS ────────────────────────────────────────────┐");
    report.push(`│  Peak node count: ${metrics.peakNodeCount}`);
    report.push(`│  Peak override count: ${metrics.peakOverrideCount}`);
    report.push(`│  Peak vote count: ${metrics.peakVoteCount}`);
    report.push(`│  Final registry size: ${reg.getCount()}`);
    report.push("└────────────────────────────────────────────────────────────┘");

    // HTTP Response Times
    report.push("");
    report.push("┌─ HTTP PERFORMANCE ─────────────────────────────────────────┐");
    if (metrics.httpResponseTimes.length > 0) {
      const sorted = [...metrics.httpResponseTimes].sort((a, b) => a - b);
      report.push(`│  Requests measured: ${sorted.length}`);
      report.push(`│  Min: ${sorted[0].toFixed(1)}ms`);
      report.push(`│  Median: ${sorted[Math.floor(sorted.length / 2)].toFixed(1)}ms`);
      report.push(`│  P95: ${sorted[Math.floor(sorted.length * 0.95)].toFixed(1)}ms`);
      report.push(`│  Max: ${sorted[sorted.length - 1].toFixed(1)}ms`);
    }
    report.push("└────────────────────────────────────────────────────────────┘");

    // Invariant Checks
    report.push("");
    report.push("┌─ INVARIANT CHECKS ─────────────────────────────────────────┐");
    let allPassed = true;
    for (const check of metrics.invariantChecks) {
      const status = check.passed ? "✓" : "✗";
      report.push(`│  ${status} ${check.phase}`);
      if (!check.passed) {
        allPassed = false;
        for (const f of check.failures) {
          report.push(`│    FAIL: ${f}`);
        }
      }
    }
    report.push(`│  RESULT: ${allPassed ? "ALL PASSED" : "FAILURES DETECTED"}`);
    report.push("└────────────────────────────────────────────────────────────┘");

    // Constitution
    report.push("");
    report.push("┌─ CONSTITUTION CHECKS ──────────────────────────────────────┐");
    for (const check of metrics.constitutionResults) {
      const status = check.allPassed ? "✓" : "✗";
      report.push(`│  ${status} ${check.phase}`);
      if (!check.allPassed) {
        for (const f of check.failedChecks) {
          report.push(`│    FAILED: ${f}`);
        }
      }
    }
    report.push("└────────────────────────────────────────────────────────────┘");

    // Errors & Warnings
    if (metrics.errorLog.length > 0) {
      report.push("");
      report.push("┌─ ERRORS ─────────────────────────────────────────────────┐");
      for (const e of metrics.errorLog) {
        report.push(`│  ⚠ ${e}`);
      }
      report.push("└────────────────────────────────────────────────────────────┘");
    }

    if (metrics.warnings.length > 0) {
      report.push("");
      report.push("┌─ WARNINGS ───────────────────────────────────────────────┐");
      for (const w of metrics.warnings) {
        report.push(`│  ⚠ ${w}`);
      }
      report.push("└────────────────────────────────────────────────────────────┘");
    }

    // Verdict
    report.push("");
    const hasErrors = metrics.errorLog.length > 0;
    const hasInvariantFailures = !allPassed;
    const hasConstitutionFailures = metrics.constitutionResults.some(c => !c.allPassed);

    let verdict: string;
    if (hasErrors || hasInvariantFailures || hasConstitutionFailures) {
      verdict = "⚠  NOT READY — Issues detected. Review errors above.";
    } else if (metrics.warnings.length > 3) {
      verdict = "⚡ CONDITIONAL — Ready with noted warnings.";
    } else {
      verdict = "✓  READY FOR ACTIVATION";
    }

    report.push("╔══════════════════════════════════════════════════════════════╗");
    report.push(`║  VERDICT: ${verdict.padEnd(49)}║`);
    report.push("╚══════════════════════════════════════════════════════════════╝");
    report.push("");

    // Print to console so it appears in test output
    console.log(report.join("\n"));

    // Assertions
    expect(allPassed).toBe(true);
    expect(hasConstitutionFailures).toBe(false);
    expect(hasErrors).toBe(false);
  });
});
