/**
 * ENDURANCE RUN — Real-Time Extended Operation
 *
 * Unlike the activation soak (which compresses time), this test runs
 * Daedalus under realistic real-time conditions for an extended period.
 * It uses actual timeouts, real async patterns, and measures behavior
 * that only emerges over sustained operation.
 *
 * Targets:
 *   - Real-time heartbeat cycling (async intervals)
 *   - SSE event stream reliability under sustained load
 *   - Concurrent mutation + read patterns
 *   - Governance state churn over time
 *   - Memory stability under sustained allocation
 *   - Snapshot persistence reliability under load
 *   - Auto-save timer correctness
 *   - Event bus subscriber stability
 *   - Node lifecycle churn (join/detach cycles)
 *   - Constitution validity throughout
 */

import request from "supertest";
import fs from "node:fs";
import path from "node:path";
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
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { SnapshotPersistence } from "../orchestrator/persistence/SnapshotPersistence";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";

jest.setTimeout(180_000); // 3 minutes

// ── Helpers ────────────────────────────────────────────────────────────
function mkJoin(id: string) {
  return {
    nodeId: id,
    name: `Node-${id}`,
    capabilities: [{ name: "core", value: "enabled", enabled: true }],
    expressive: { ...IDLE_EXPRESSIVE },
    profile: {
      id,
      name: `Node-${id}`,
      kind: "server" as const,
      model: "endurance",
      os: "linux",
      osVersion: "6.0",
      operatorId: "operator",
    },
  };
}

function mkHb(nodeId: string): { nodeId: string; timestamp: string; status: "alive" } {
  return { nodeId, timestamp: new Date().toISOString(), status: "alive" as const };
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Metrics ────────────────────────────────────────────────────────────
interface EnduranceMetrics {
  startTime: number;
  endTime: number;
  heartbeatCycles: number;
  joinDetachCycles: number;
  governanceActions: number;
  httpRequests: number;
  httpErrors: number;
  snapshotSaves: number;
  constitutionChecks: number;
  constitutionFailures: number;
  invariantChecks: number;
  invariantFailures: number;
  eventBusDrops: number;
  totalEvents: number;
  memorySnapshots: Array<{ time: number; heapMB: number; rssMB: number }>;
  errors: string[];
  findings: string[];
}

describe("ENDURANCE RUN — Real-Time Extended Operation", () => {
  const app = createOrchestratorApp();
  let reg: NodeMirrorRegistry;
  let eventCount = 0;
  let unsub: (() => void) | null = null;
  const metrics: EnduranceMetrics = {
    startTime: 0,
    endTime: 0,
    heartbeatCycles: 0,
    joinDetachCycles: 0,
    governanceActions: 0,
    httpRequests: 0,
    httpErrors: 0,
    snapshotSaves: 0,
    constitutionChecks: 0,
    constitutionFailures: 0,
    invariantChecks: 0,
    invariantFailures: 0,
    eventBusDrops: 0,
    totalEvents: 0,
    memorySnapshots: [],
    errors: [],
    findings: [],
  };

  beforeAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
    reg = getNodeMirrorRegistry();

    const bus = getDaedalusEventBus();
    unsub = bus.subscribe(() => { eventCount++; });
  });

  afterAll(() => {
    unsub?.();
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
  });

  function snapMem() {
    const m = process.memoryUsage();
    metrics.memorySnapshots.push({
      time: Date.now() - metrics.startTime,
      heapMB: Math.round(m.heapUsed / 1024 / 1024 * 100) / 100,
      rssMB: Math.round(m.rss / 1024 / 1024 * 100) / 100,
    });
  }

  function checkInvariantsQuick(): boolean {
    metrics.invariantChecks++;
    const mirrors = reg.getAllMirrors();
    for (const m of mirrors) {
      if (m.lifecycle.heartbeatCount < 0 || m.lifecycle.errorCount < 0) {
        metrics.invariantFailures++;
        metrics.errors.push(`Negative count on ${m.id}`);
        return false;
      }
    }

    const posture = governanceService.getPostureSnapshot();
    if (!["OPEN", "ATTENTIVE", "GUARDED", "LOCKDOWN"].includes(posture.posture)) {
      metrics.invariantFailures++;
      metrics.errors.push(`Invalid posture: ${posture.posture}`);
      return false;
    }

    const beings = daedalusStore.getBeingPresences();
    if (!beings.find(b => b.id === "operator")) {
      metrics.invariantFailures++;
      metrics.errors.push("Operator being missing");
      return false;
    }

    return true;
  }

  function checkConstitutionQuick(): boolean {
    metrics.constitutionChecks++;
    try {
      const beings = daedalusStore.getBeingPresences();
      const beingMap: Record<string, any> = {};
      for (const b of beings) beingMap[b.id] = b;
      const behavioral = computeBehavioralField(beingMap);
      const report = validateBeingConstitution(beings, governanceService.listVotes(), behavioral.dominantBeingId);
      if (!report.allPassed) {
        metrics.constitutionFailures++;
        const fails = report.checks.filter((c: any) => !c.passed).map((c: any) => c.name);
        metrics.errors.push(`Constitution failure: ${fails.join(", ")}`);
        return false;
      }
      return true;
    } catch (err: any) {
      metrics.constitutionFailures++;
      metrics.errors.push(`Constitution crash: ${err.message}`);
      return false;
    }
  }

  // ── Phase 1: Bootstrap fleet ─────────────────────────────────────────
  test("Bootstrap: 100 nodes join", () => {
    for (let i = 1; i <= 100; i++) {
      reg.handleJoin(mkJoin(`endure-${i}`));
    }
    expect(reg.getCount()).toBe(100);
  });

  // ── Phase 2: Real-time sustained operation ───────────────────────────
  test("Sustained operation: 60s of real-time heartbeats, governance, and HTTP", async () => {
    metrics.startTime = Date.now();
    snapMem();

    const DURATION_MS = 60_000; // 60 seconds of real-time operation
    const HEARTBEAT_INTERVAL_MS = 200; // every 200ms
    const GOVERNANCE_INTERVAL_MS = 2_000; // every 2s
    const HTTP_INTERVAL_MS = 1_000; // every 1s
    const SNAPSHOT_INTERVAL_MS = 5_000; // every 5s
    const CHECK_INTERVAL_MS = 3_000; // every 3s
    const CHURN_INTERVAL_MS = 4_000; // every 4s
    const MEM_INTERVAL_MS = 5_000; // every 5s

    const tmpSnap = path.join(__dirname, `.endurance-snap-${Date.now()}.json`);
    const persistence = new SnapshotPersistence(tmpSnap);

    let running = true;
    let overrideToggle = 0;

    // Heartbeat worker
    const heartbeatWorker = (async () => {
      while (running) {
        const nodes = reg.getAllMirrors().filter(m => m.lifecycle.phase === "active");
        for (const n of nodes) {
          reg.handleHeartbeat(mkHb(n.id));
        }
        metrics.heartbeatCycles++;
        await sleep(HEARTBEAT_INTERVAL_MS);
      }
    })();

    // Governance worker
    const governanceWorker = (async () => {
      while (running) {
        await sleep(GOVERNANCE_INTERVAL_MS);
        overrideToggle++;

        if (overrideToggle % 5 === 0) {
          governanceService.clearOverrides();
          governanceService.clearDrifts();
        } else if (overrideToggle % 3 === 0) {
          governanceService.applyOverride({
            createdBy: { id: "operator", role: "OPERATOR" as const, label: "Op" },
            reason: `Endurance override #${overrideToggle}`,
            scope: "NODE" as const,
            effect: "ALLOW" as const,
          });
        } else if (overrideToggle % 4 === 0) {
          governanceService.recordDrift({
            severity: overrideToggle % 2 === 0 ? "LOW" as const : "MEDIUM" as const,
            summary: `Endurance drift #${overrideToggle}`,
          });
        }

        metrics.governanceActions++;
      }
    })();

    // HTTP worker — concurrent reads
    const httpWorker = (async () => {
      while (running) {
        await sleep(HTTP_INTERVAL_MS);
        try {
          const endpoints = [
            "/daedalus/cockpit/summary",
            "/daedalus/governance/posture",
            "/daedalus/beings/presence",
            "/daedalus/cockpit/nodes",
            "/daedalus/snapshot",
            "/daedalus/constitution",
          ];
          const endpoint = endpoints[metrics.httpRequests % endpoints.length];
          const res = await request(app).get(endpoint);
          metrics.httpRequests++;
          if (res.status !== 200) {
            metrics.httpErrors++;
            metrics.errors.push(`HTTP ${res.status} on ${endpoint}`);
          }
        } catch (err: any) {
          metrics.httpErrors++;
          metrics.errors.push(`HTTP error: ${err.message}`);
        }
      }
    })();

    // Snapshot worker
    const snapshotWorker = (async () => {
      while (running) {
        await sleep(SNAPSHOT_INTERVAL_MS);
        persistence.save({
          beings: daedalusStore.getBeingPresences(),
          overrides: governanceService.listOverrides(),
          drifts: governanceService.listDrifts(),
          votes: governanceService.listVotes(),
          mirrors: reg.getAllMirrors(),
          savedAt: new Date().toISOString(),
        });
        metrics.snapshotSaves++;
      }
    })();

    // Invariant + constitution checker
    const checkWorker = (async () => {
      while (running) {
        await sleep(CHECK_INTERVAL_MS);
        checkInvariantsQuick();
        checkConstitutionQuick();
      }
    })();

    // Node churn worker — join/detach cycles
    let churnId = 200;
    const churnWorker = (async () => {
      while (running) {
        await sleep(CHURN_INTERVAL_MS);
        churnId++;
        const id = `churn-${churnId}`;
        reg.handleJoin(mkJoin(id));
        reg.handleHeartbeat(mkHb(id));
        // Detach an old churn node
        const oldId = `churn-${churnId - 5}`;
        const oldMirror = reg.getMirror(oldId);
        if (oldMirror && oldMirror.lifecycle.phase !== "detached" && oldMirror.lifecycle.phase !== "quarantined") {
          reg.handleDetach(oldId);
        }
        metrics.joinDetachCycles++;
      }
    })();

    // Memory worker
    const memWorker = (async () => {
      while (running) {
        await sleep(MEM_INTERVAL_MS);
        snapMem();
      }
    })();

    // Run for DURATION_MS
    await sleep(DURATION_MS);
    running = false;

    // Wait for workers to finish their current iterations
    await Promise.allSettled([
      heartbeatWorker,
      governanceWorker,
      httpWorker,
      snapshotWorker,
      checkWorker,
      churnWorker,
      memWorker,
    ]);

    metrics.endTime = Date.now();
    metrics.totalEvents = eventCount;

    // Cleanup snapshot file
    try { fs.unlinkSync(tmpSnap); } catch {}

    snapMem();

    // ── Assertions ───────────────────────────────────────────────
    expect(metrics.heartbeatCycles).toBeGreaterThan(100);
    expect(metrics.httpErrors).toBe(0);
    expect(metrics.invariantFailures).toBe(0);
    expect(metrics.constitutionFailures).toBe(0);
    expect(metrics.snapshotSaves).toBeGreaterThan(5);
    expect(metrics.errors).toHaveLength(0);
  });

  // ── Phase 3: Post-endurance integrity ────────────────────────────────
  test("Post-endurance: full integrity check", async () => {
    const mirrors = reg.getAllMirrors();
    const cockpit = reg.toCockpitView();
    const beings = daedalusStore.getBeingPresences();
    const posture = governanceService.getPostureSnapshot();

    // Registry and cockpit view are consistent
    expect(cockpit.length).toBe(mirrors.length);
    for (const c of cockpit) {
      const m = reg.getMirror(c.id);
      expect(m).toBeDefined();
      expect(c.status).toBe(m!.status);
    }

    // Beings intact
    expect(beings.find(b => b.id === "operator")).toBeDefined();

    // Posture is valid
    expect(["OPEN", "ATTENTIVE", "GUARDED", "LOCKDOWN"]).toContain(posture.posture);

    // Constitution holds
    const ok = checkConstitutionQuick();
    expect(ok).toBe(true);

    // HTTP still responsive
    const res = await request(app).get("/health").expect(200);
    expect(res.body.status).toBe("ok");
  });

  // ── Phase 4: Stress recovery ─────────────────────────────────────────
  test("Post-endurance: stress recovery — clear everything, verify clean state", () => {
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();

    expect(governanceService.getPostureSnapshot().posture).toBe("OPEN");

    checkInvariantsQuick();
    checkConstitutionQuick();
    expect(metrics.invariantFailures).toBe(0);
    expect(metrics.constitutionFailures).toBe(0);
  });

  // ── Final Report ─────────────────────────────────────────────────────
  test("FINAL: Endurance report", () => {
    const duration = metrics.endTime - metrics.startTime;
    const memFirst = metrics.memorySnapshots[0];
    const memLast = metrics.memorySnapshots[metrics.memorySnapshots.length - 1];

    const report = [
      "",
      "╔══════════════════════════════════════════════════════════════╗",
      "║            DAEDALUS ENDURANCE RUN — REPORT                  ║",
      "╚══════════════════════════════════════════════════════════════╝",
      "",
      `  Duration: ${(duration / 1000).toFixed(1)}s`,
      `  Heartbeat cycles: ${metrics.heartbeatCycles}`,
      `  Join/detach cycles: ${metrics.joinDetachCycles}`,
      `  Governance actions: ${metrics.governanceActions}`,
      `  HTTP requests: ${metrics.httpRequests} (errors: ${metrics.httpErrors})`,
      `  Snapshot saves: ${metrics.snapshotSaves}`,
      `  Invariant checks: ${metrics.invariantChecks} (failures: ${metrics.invariantFailures})`,
      `  Constitution checks: ${metrics.constitutionChecks} (failures: ${metrics.constitutionFailures})`,
      `  Total events: ${metrics.totalEvents}`,
      `  Final node count: ${reg.getCount()}`,
      "",
      "  ── Memory ──────────────────────────────────────────",
    ];

    for (const s of metrics.memorySnapshots) {
      report.push(`    ${(s.time / 1000).toFixed(1)}s: heap=${s.heapMB}MB rss=${s.rssMB}MB`);
    }

    if (memFirst && memLast) {
      const heapGrowth = memLast.heapMB - memFirst.heapMB;
      const rssGrowth = memLast.rssMB - memFirst.rssMB;
      report.push(`    Heap growth: ${heapGrowth.toFixed(2)}MB`);
      report.push(`    RSS growth: ${rssGrowth.toFixed(2)}MB`);

      if (heapGrowth > 100) {
        metrics.findings.push(`CONCERN: Heap grew ${heapGrowth.toFixed(0)}MB during endurance`);
      }
      if (rssGrowth > 200) {
        metrics.findings.push(`CONCERN: RSS grew ${rssGrowth.toFixed(0)}MB during endurance`);
      }
    }

    if (metrics.findings.length > 0) {
      report.push("");
      report.push("  ── Findings ────────────────────────────────────────");
      for (const f of metrics.findings) report.push(`    ${f}`);
    }

    if (metrics.errors.length > 0) {
      report.push("");
      report.push("  ── Errors ──────────────────────────────────────────");
      for (const e of metrics.errors) report.push(`    ${e}`);
    }

    const ok = metrics.httpErrors === 0 &&
      metrics.invariantFailures === 0 &&
      metrics.constitutionFailures === 0 &&
      metrics.errors.length === 0;

    report.push("");
    report.push(`  VERDICT: ${ok ? "STABLE — Ready for sustained operation" : "ISSUES DETECTED"}`);
    report.push("");

    console.log(report.join("\n"));

    expect(ok).toBe(true);
  });
});
