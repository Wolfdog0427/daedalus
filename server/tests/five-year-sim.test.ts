/**
 * DAEDALUS FIVE-YEAR OPERATIONAL SIMULATION (v2)
 * ═══════════════════════════════════════════════
 *
 * Models 5 years of realistic Daedalus operation with full fleet lifecycle:
 *
 *   NODE EXPANSION (front-loaded)
 *     - Y1: Aggressive buildout 5 → 180 nodes (rapid early adoption)
 *     - Y2: Continued growth to ~210 nodes
 *     - Y3-5: Plateau at ~220 with steady churn
 *
 *   HARDWARE GENERATIONS
 *     - Gen 1 (Y1): linux 5.x, 4-core, basic capabilities
 *     - Gen 2 (Y1-Q3): linux 6.x, 8-core, +expressive engine
 *     - Gen 3 (Y2-Q2): linux 6.x, 16-core, +advanced negotiation
 *     - Gen 4 (Y3-Q1): mixed linux/darwin, ARM + x86, +federation
 *     - Gen 5 (Y4): next-gen hardware, all capabilities
 *
 *   HARDWARE UPGRADES
 *     - Nodes are periodically upgraded via profile sync + cap sync
 *     - Old-gen nodes are retired and replaced with new-gen
 *     - Mixed-generation fleet is maintained and validated
 *
 *   FLEET HETEROGENEITY
 *     - Mix of server, desktop, mobile, embedded nodes
 *     - Different capability surfaces per hardware type
 *     - Capability negotiation under mixed generations
 *
 *   CAPABILITY EVOLUTION
 *     - New capabilities added with each hardware generation
 *     - Capability deltas tracked and validated
 *     - Backward compatibility: old-gen nodes retain core caps
 */

import { createOrchestratorApp } from "../orchestrator";
import {
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  NodeMirrorRegistry,
} from "../orchestrator/mirror/NodeMirror";
import type {
  NodeJoinPayload,
  NodeCapSyncPayload,
  NodeProfileSyncPayload,
  NodeProfile,
} from "../orchestrator/mirror/NodeMirror.types";
import type { Capability } from "../../shared/daedalus/contracts";
import { governanceService } from "../orchestrator/governance/GovernanceService";
import { incidentService } from "../orchestrator/governance/IncidentService";
import { actionLog } from "../orchestrator/governance/ActionLog";
import { daedalusStore } from "../orchestrator/daedalusStore";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
} from "../orchestrator/DaedalusEventBus";
import { SnapshotPersistence } from "../orchestrator/persistence/SnapshotPersistence";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";
import type { BeingPresenceDetail } from "../../shared/daedalus/contracts";
import request from "supertest";
import fs from "node:fs";
import path from "node:path";

jest.setTimeout(300_000);

// ═══════════════════════════════════════════════════════════════════════════════
// HARDWARE GENERATION MODEL
// ═══════════════════════════════════════════════════════════════════════════════

type HwGen = 1 | 2 | 3 | 4 | 5;
type NodeKind = "server" | "desktop" | "mobile" | "embedded";

interface HwGenSpec {
  gen: HwGen;
  os: string;
  osVersion: string;
  model: string;
  cores: number;
  capabilities: Capability[];
  availableKinds: NodeKind[];
  introducedAtMonth: number;
}

const HW_GENS: HwGenSpec[] = [
  {
    gen: 1,
    os: "linux",
    osVersion: "5.15",
    model: "daedalus-node-mk1",
    cores: 4,
    capabilities: [
      { name: "daedalus.core", value: "1.0", enabled: true },
      { name: "daedalus.heartbeat", value: "1.0", enabled: true },
    ],
    availableKinds: ["server", "desktop"],
    introducedAtMonth: 1,
  },
  {
    gen: 2,
    os: "linux",
    osVersion: "6.1",
    model: "daedalus-node-mk2",
    cores: 8,
    capabilities: [
      { name: "daedalus.core", value: "2.0", enabled: true },
      { name: "daedalus.heartbeat", value: "1.1", enabled: true },
      { name: "daedalus.expressive", value: "1.0", enabled: true },
    ],
    availableKinds: ["server", "desktop", "mobile"],
    introducedAtMonth: 7,
  },
  {
    gen: 3,
    os: "linux",
    osVersion: "6.5",
    model: "daedalus-node-mk3",
    cores: 16,
    capabilities: [
      { name: "daedalus.core", value: "3.0", enabled: true },
      { name: "daedalus.heartbeat", value: "2.0", enabled: true },
      { name: "daedalus.expressive", value: "2.0", enabled: true },
      { name: "daedalus.negotiation", value: "1.0", enabled: true },
    ],
    availableKinds: ["server", "desktop", "mobile", "embedded"],
    introducedAtMonth: 18,
  },
  {
    gen: 4,
    os: "darwin",
    osVersion: "24.0",
    model: "daedalus-node-mk4-arm",
    cores: 16,
    capabilities: [
      { name: "daedalus.core", value: "4.0", enabled: true },
      { name: "daedalus.heartbeat", value: "2.1", enabled: true },
      { name: "daedalus.expressive", value: "3.0", enabled: true },
      { name: "daedalus.negotiation", value: "2.0", enabled: true },
      { name: "daedalus.federation", value: "1.0", enabled: true },
    ],
    availableKinds: ["server", "desktop", "mobile"],
    introducedAtMonth: 25,
  },
  {
    gen: 5,
    os: "linux",
    osVersion: "7.0",
    model: "daedalus-node-mk5-nextgen",
    cores: 32,
    capabilities: [
      { name: "daedalus.core", value: "5.0", enabled: true },
      { name: "daedalus.heartbeat", value: "3.0", enabled: true },
      { name: "daedalus.expressive", value: "4.0", enabled: true },
      { name: "daedalus.negotiation", value: "3.0", enabled: true },
      { name: "daedalus.federation", value: "2.0", enabled: true },
      { name: "daedalus.telemetry", value: "1.0", enabled: true },
    ],
    availableKinds: ["server", "desktop", "mobile", "embedded"],
    introducedAtMonth: 37,
  },
];

function getAvailableGens(month: number): HwGenSpec[] {
  return HW_GENS.filter((g) => g.introducedAtMonth <= month);
}

function getLatestGen(month: number): HwGenSpec {
  const available = getAvailableGens(month);
  return available[available.length - 1];
}

function pickNewNodeGen(month: number): HwGenSpec {
  const available = getAvailableGens(month);
  // 70% latest gen, 20% previous, 10% older
  const r = Math.random();
  if (r < 0.7 || available.length === 1) return available[available.length - 1];
  if (r < 0.9 || available.length === 2) return available[available.length - 2];
  return available[Math.max(0, available.length - 3)];
}

function pickKind(gen: HwGenSpec): NodeKind {
  return gen.availableKinds[Math.floor(Math.random() * gen.availableKinds.length)];
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLEET EXPANSION CURVE (front-loaded)
// ═══════════════════════════════════════════════════════════════════════════════

function targetFleetAtMonth(month: number): number {
  // Logistic curve: rapid early growth, plateau at ~220
  // S-curve: 220 / (1 + e^(-0.25*(month - 8)))
  const cap = 220;
  const k = 0.25;
  const midpoint = 8;
  return Math.round(cap / (1 + Math.exp(-k * (month - midpoint))));
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

const OP: { id: string; role: "OPERATOR"; label: string } = {
  id: "operator",
  role: "OPERATOR",
  label: "Operator",
};

function mkJoin(nodeId: string, gen: HwGenSpec, kind: NodeKind): NodeJoinPayload {
  return {
    nodeId,
    name: nodeId,
    capabilities: gen.capabilities,
    expressive: {
      glow: { level: "low", intensity: 0.3 },
      posture: "companion" as const,
      attention: { level: "aware" as const },
      continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: true },
    },
    profile: {
      id: nodeId,
      name: nodeId,
      kind,
      model: gen.model,
      os: gen.os,
      osVersion: gen.osVersion,
      operatorId: "operator",
    },
  };
}

function mkHb(nodeId: string): { nodeId: string; timestamp: string; status: "alive" } {
  return { nodeId, timestamp: new Date().toISOString(), status: "alive" };
}

function mkCapSync(nodeId: string, caps: Capability[]): NodeCapSyncPayload {
  return { nodeId, capabilities: caps, timestamp: new Date().toISOString() };
}

function mkProfileSync(nodeId: string, profile: NodeProfile): NodeProfileSyncPayload {
  return { nodeId, profile, timestamp: new Date().toISOString() };
}

interface NodeRecord {
  id: string;
  gen: HwGen;
  kind: NodeKind;
  joinedAtMonth: number;
  lastUpgradeMonth: number;
}

interface MonthMetrics {
  month: number;
  simYear: number;
  simMonth: number;
  nodeCount: number;
  totalHeartbeats: number;
  totalErrors: number;
  totalJoins: number;
  totalDetaches: number;
  totalQuarantines: number;
  totalCapSyncs: number;
  totalProfileSyncs: number;
  totalUpgrades: number;
  overrideCount: number;
  driftCount: number;
  voteCount: number;
  incidentCount: number;
  posture: string;
  constitutionPassed: boolean;
  heapMB: number;
  rssMB: number;
  snapshotSizeKB: number;
  eventHistorySize: number;
  sweepedOverrides: number;
  sweepedDrifts: number;
  fleetByGen: Record<number, number>;
  fleetByKind: Record<string, number>;
  latestGenAvailable: number;
  issues: string[];
}

function snapMem() {
  const m = process.memoryUsage();
  return {
    heapMB: Math.round((m.heapUsed / 1024 / 1024) * 100) / 100,
    rssMB: Math.round((m.rss / 1024 / 1024) * 100) / 100,
  };
}

function checkConstitution(): boolean {
  try {
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;
    const behavioral = computeBehavioralField(beingMap);
    const report = validateBeingConstitution(beings, [], behavioral.dominantBeingId);
    return report.allPassed;
  } catch {
    return false;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// SIMULATION
// ═══════════════════════════════════════════════════════════════════════════════

describe("DAEDALUS FIVE-YEAR SIMULATION — NODE EXPANSION & HARDWARE UPGRADES", () => {
  let reg: NodeMirrorRegistry;
  let bus: ReturnType<typeof getDaedalusEventBus>;
  let snapshotPath: string;
  let persistence: SnapshotPersistence;
  let app: ReturnType<typeof createOrchestratorApp>;

  const metrics: MonthMetrics[] = [];
  const issues: string[] = [];

  let totalHeartbeats = 0;
  let totalErrors = 0;
  let totalJoins = 0;
  let totalDetaches = 0;
  let totalQuarantines = 0;
  let totalCapSyncs = 0;
  let totalProfileSyncs = 0;
  let totalUpgrades = 0;
  let totalSweepedOverrides = 0;
  let totalSweepedDrifts = 0;
  let totalIncidents = 0;
  let totalSnapshotSaves = 0;
  let totalConstitutionChecks = 0;
  let totalConstitutionFailures = 0;

  const fleet = new Map<string, NodeRecord>();
  let nodeIdCounter = 0;

  beforeAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    reg = getNodeMirrorRegistry();
    bus = getDaedalusEventBus();
    app = createOrchestratorApp();
    snapshotPath = path.join(__dirname, ".five-year-v2-snapshot.json");
    persistence = new SnapshotPersistence(snapshotPath);
  });

  afterAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
    actionLog.clear();
    try {
      fs.unlinkSync(snapshotPath);
    } catch {}
  });

  function spawnNode(month: number): string {
    nodeIdCounter++;
    const gen = pickNewNodeGen(month);
    const kind = pickKind(gen);
    const id = `node-${nodeIdCounter}`;
    reg.handleJoin(mkJoin(id, gen, kind));
    fleet.set(id, { id, gen: gen.gen, kind, joinedAtMonth: month, lastUpgradeMonth: month });
    totalJoins++;
    return id;
  }

  function removeNode(id: string) {
    if (!fleet.has(id)) return;
    reg.handleDetach(id);
    fleet.delete(id);
    totalDetaches++;
  }

  function upgradeNode(id: string, month: number) {
    const rec = fleet.get(id);
    if (!rec) return;
    const latestGen = getLatestGen(month);
    if (latestGen.gen <= rec.gen) return;

    const profile: NodeProfile = {
      id: rec.id,
      name: rec.id,
      kind: rec.kind,
      model: latestGen.model,
      os: latestGen.os,
      osVersion: latestGen.osVersion,
      operatorId: "operator",
    };
    reg.handleProfileSync(mkProfileSync(id, profile));
    totalProfileSyncs++;

    reg.handleCapSync(mkCapSync(id, latestGen.capabilities));
    totalCapSyncs++;

    rec.gen = latestGen.gen;
    rec.lastUpgradeMonth = month;
    totalUpgrades++;
  }

  function heartbeatAll() {
    for (const id of fleet.keys()) {
      reg.handleHeartbeat(mkHb(id));
      totalHeartbeats++;
    }
  }

  function errorNode(id: string, msg: string) {
    if (!fleet.has(id)) return;
    reg.handleError(id, msg);
    totalErrors++;
    const mirror = reg.getMirror(id);
    if (mirror && mirror.lifecycle.phase === "quarantined") {
      totalQuarantines++;
    }
  }

  function randomFleetNode(): string | null {
    const arr = Array.from(fleet.keys());
    if (arr.length === 0) return null;
    return arr[Math.floor(Math.random() * arr.length)];
  }

  function fleetByGen(): Record<number, number> {
    const dist: Record<number, number> = {};
    for (const r of fleet.values()) {
      dist[r.gen] = (dist[r.gen] ?? 0) + 1;
    }
    return dist;
  }

  function fleetByKind(): Record<string, number> {
    const dist: Record<string, number> = {};
    for (const r of fleet.values()) {
      dist[r.kind] = (dist[r.kind] ?? 0) + 1;
    }
    return dist;
  }

  function saveSnapshot(): number {
    const snap = {
      beings: daedalusStore.getBeingPresences(),
      overrides: governanceService.listOverrides(),
      drifts: governanceService.listDrifts(),
      votes: governanceService.listVotes(),
      mirrors: reg.getAllMirrors(),
      eventHistory: bus.getHistory(),
      savedAt: new Date().toISOString(),
    };
    persistence.save(snap);
    totalSnapshotSaves++;
    try {
      return Math.round(fs.statSync(snapshotPath).size / 1024);
    } catch {
      return 0;
    }
  }

  function syncActiveSet() {
    const toRemove: string[] = [];
    for (const id of fleet.keys()) {
      const m = reg.getMirror(id);
      if (!m || m.lifecycle.phase === "quarantined" || m.lifecycle.phase === "detached") {
        toRemove.push(id);
      }
    }
    for (const id of toRemove) fleet.delete(id);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // THE 5-YEAR SIMULATION — 60 MONTHS
  // ═══════════════════════════════════════════════════════════════════════

  test("60-month simulation with node expansion and hardware upgrades", () => {
    const MONTHS = 60;
    const HB_CYCLES_PER_MONTH = 700;

    for (let month = 1; month <= MONTHS; month++) {
      const simYear = Math.ceil(month / 12);
      const simMonth = ((month - 1) % 12) + 1;
      const monthIssues: string[] = [];

      // ── Fleet expansion (logistic / front-loaded) ──────────
      const target = targetFleetAtMonth(month);
      while (fleet.size < target) {
        spawnNode(month);
      }

      // ── Monthly churn: retire old nodes, replace with new-gen ──
      const churnRate = 0.02 + Math.random() * 0.03;
      const churnCount = Math.max(1, Math.floor(fleet.size * churnRate));
      const sortedByAge = Array.from(fleet.values()).sort(
        (a, b) => a.joinedAtMonth - b.joinedAtMonth,
      );
      let churned = 0;
      for (const rec of sortedByAge) {
        if (churned >= churnCount) break;
        if (fleet.size <= 5) break;
        // Preferentially retire oldest / lowest-gen nodes
        const latestGen = getLatestGen(month);
        if (rec.gen < latestGen.gen - 1 || Math.random() < 0.3) {
          removeNode(rec.id);
          spawnNode(month);
          churned++;
        }
      }

      // ── Hardware upgrades: in-place upgrade ~5-10% of fleet monthly ──
      const upgradeRate = 0.05 + Math.random() * 0.05;
      const upgradeCount = Math.floor(fleet.size * upgradeRate);
      const upgradeCandidates = Array.from(fleet.values())
        .filter((r) => r.gen < getLatestGen(month).gen)
        .sort((a, b) => a.gen - b.gen);
      for (let u = 0; u < Math.min(upgradeCount, upgradeCandidates.length); u++) {
        upgradeNode(upgradeCandidates[u].id, month);
      }

      // ── Heartbeat cycles ─────────────────────────────────────
      for (let cycle = 0; cycle < HB_CYCLES_PER_MONTH; cycle++) {
        heartbeatAll();

        if (Math.random() < 0.01) {
          const errorCount = Math.max(1, Math.floor(fleet.size * 0.02));
          for (let e = 0; e < errorCount; e++) {
            const target = randomFleetNode();
            if (target) errorNode(target, `sim-error-m${month}-c${cycle}`);
          }
        }
      }

      // ── Capability sync wave: periodic fleet-wide cap sync ───
      if (simMonth % 2 === 0) {
        for (const rec of fleet.values()) {
          const genSpec = HW_GENS.find((g) => g.gen === rec.gen);
          if (genSpec) {
            reg.handleCapSync(mkCapSync(rec.id, genSpec.capabilities));
            totalCapSyncs++;
          }
        }
      }

      // ── Governance ───────────────────────────────────────────
      for (let w = 0; w < 4; w++) {
        if (Math.random() < 0.3) {
          const ttlMs = 1 + Math.floor(Math.random() * 5);
          governanceService.applyOverride({
            createdBy: OP,
            reason: `Maintenance Y${simYear}M${simMonth}W${w}`,
            scope: "NODE" as const,
            effect: "ALLOW" as const,
            expiresAt: new Date(Date.now() + ttlMs).toISOString(),
          });
        }
      }

      const swept = governanceService.sweepExpired();
      totalSweepedOverrides += swept.expiredOverrides;
      totalSweepedDrifts += swept.expiredDrifts;

      if (Math.random() < 0.25) {
        const severities: Array<"LOW" | "MEDIUM" | "HIGH"> = ["LOW", "MEDIUM", "HIGH"];
        const sev = severities[Math.floor(Math.random() * (simYear > 3 ? 3 : 2))];
        const ttlMs = 1 + Math.floor(Math.random() * 5);
        governanceService.recordDrift({
          severity: sev,
          summary: `Drift Y${simYear}M${simMonth}`,
          expiresAt: new Date(Date.now() + ttlMs).toISOString(),
        });
      }

      if (simMonth % 3 === 0 && Math.random() < 0.5) {
        governanceService.castVote({
          being: OP,
          vote: (Math.random() < 0.8 ? "ALLOW" : "ESCALATE") as "ALLOW" | "ESCALATE",
          weight: 0.5 + Math.random() * 0.5,
        });
      }

      if (simMonth % 6 === 0) {
        governanceService.clearVotes();
        if (governanceService.listOverrides().length > 50)
          governanceService.clearOverrides();
        if (governanceService.listDrifts().length > 20)
          governanceService.clearDrifts();
      }

      // ── Incidents ────────────────────────────────────────────
      if (simMonth % 3 === 0 && Math.random() < 0.6) {
        const sevs: Array<"LOW" | "MEDIUM" | "HIGH" | "CRITICAL"> = [
          "LOW", "MEDIUM", "HIGH", "CRITICAL",
        ];
        incidentService.openIncident({
          title: `Incident Y${simYear}Q${Math.ceil(simMonth / 3)}`,
          severity: sevs[Math.min(Math.floor(Math.random() * (simYear > 2 ? 4 : 3)), 3)],
          notes: `Sim incident`,
        });
        totalIncidents++;
      }
      for (const inc of incidentService.listIncidents({ status: "open" })) {
        if (Math.random() < 0.5) incidentService.resolveIncident(inc.id);
      }

      // ── Chaos: quarterly storms ──────────────────────────────
      if (simMonth % 3 === 0) {
        const stormSize = Math.min(Math.floor(fleet.size * 0.1), 20);
        for (let s = 0; s < stormSize; s++) {
          const target = randomFleetNode();
          if (target) {
            for (let e = 0; e < 6; e++)
              errorNode(target, `chaos-storm-m${month}`);
          }
        }
        heartbeatAll();
        totalHeartbeats += fleet.size;
      }

      // ── Quarantine cleanup ───────────────────────────────────
      for (const m of reg.getAllMirrors()) {
        if (m.lifecycle.phase === "quarantined") {
          removeNode(m.id);
          spawnNode(month);
        }
      }
      syncActiveSet();

      // ── Snapshot + Constitution ──────────────────────────────
      const snapshotSizeKB = saveSnapshot();
      totalConstitutionChecks++;
      const constitutionPassed = checkConstitution();
      if (!constitutionPassed) {
        totalConstitutionFailures++;
        monthIssues.push("Constitution FAILED");
      }

      // ── Fleet distribution validation ────────────────────────
      const genDist = fleetByGen();
      const kindDist = fleetByKind();
      const latestAvail = getLatestGen(month).gen;

      // Check: no more than 40% of fleet on gen that is 2+ behind latest
      // (allows a 1-quarter grace period when a new gen is introduced)
      const outdatedCount = Array.from(fleet.values()).filter(
        (r) => r.gen < latestAvail - 1,
      ).length;
      const outdatedPct = fleet.size > 0 ? outdatedCount / fleet.size : 0;
      const genAge = month - getLatestGen(month).introducedAtMonth;
      if (outdatedPct > 0.4 && month > 12 && genAge > 3) {
        monthIssues.push(
          `Outdated fleet: ${(outdatedPct * 100).toFixed(0)}% on gen<=${latestAvail - 2} (${genAge} months since gen ${latestAvail})`,
        );
      }

      // Check: fleet should be heterogeneous (at least 2 kinds after Y1)
      if (month > 12 && Object.keys(kindDist).length < 2) {
        monthIssues.push("Fleet not heterogeneous: only 1 node kind");
      }

      // ── Memory + posture ─────────────────────────────────────
      const mem = snapMem();
      const posture = governanceService.getPostureSnapshot();

      if (month > 6 && posture.posture === "LOCKDOWN") {
        const lockdownMonths = metrics.filter((m) => m.posture === "LOCKDOWN").length;
        if (lockdownMonths > 6)
          monthIssues.push("Posture stuck in LOCKDOWN >6 months");
      }

      // ── Record ───────────────────────────────────────────────
      metrics.push({
        month,
        simYear,
        simMonth,
        nodeCount: reg.getCount(),
        totalHeartbeats,
        totalErrors,
        totalJoins,
        totalDetaches,
        totalQuarantines,
        totalCapSyncs,
        totalProfileSyncs,
        totalUpgrades,
        overrideCount: governanceService.listOverrides().length,
        driftCount: governanceService.listDrifts().length,
        voteCount: governanceService.listVotes().length,
        incidentCount: totalIncidents,
        posture: posture.posture,
        constitutionPassed,
        heapMB: mem.heapMB,
        rssMB: mem.rssMB,
        snapshotSizeKB,
        eventHistorySize: bus.getHistory().length,
        sweepedOverrides: totalSweepedOverrides,
        sweepedDrifts: totalSweepedDrifts,
        fleetByGen: genDist,
        fleetByKind: kindDist,
        latestGenAvailable: latestAvail,
        issues: monthIssues,
      });

      if (monthIssues.length > 0) {
        issues.push(...monthIssues.map((i) => `[Y${simYear}M${simMonth}] ${i}`));
      }
    }

    // ── Assertions ───────────────────────────────────────────────
    expect(totalHeartbeats).toBeGreaterThan(1_000_000);
    expect(totalJoins).toBeGreaterThan(300);
    expect(totalUpgrades).toBeGreaterThan(50);
    expect(totalCapSyncs).toBeGreaterThan(1000);
    expect(totalProfileSyncs).toBeGreaterThan(50);
    expect(totalConstitutionFailures).toBe(0);
    expect(reg.getCount()).toBeGreaterThan(0);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // PERSISTENCE CHECK
  // ═══════════════════════════════════════════════════════════════════════

  test("Snapshot restore after 5 years with mixed hardware", () => {
    const loaded = persistence.load();
    expect(loaded).not.toBeNull();
    expect(loaded!.mirrors.length).toBeGreaterThan(0);

    const profiles = loaded!.mirrors.map((m: any) => m.profile);
    const models = new Set(profiles.map((p: any) => p.model));
    expect(models.size).toBeGreaterThan(1);

    const kinds = new Set(profiles.map((p: any) => p.kind));
    expect(kinds.size).toBeGreaterThan(1);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // HTTP CHECK
  // ═══════════════════════════════════════════════════════════════════════

  test("HTTP endpoints handle mixed-generation fleet", async () => {
    const res1 = await request(app).get("/daedalus/cockpit/summary");
    expect(res1.status).toBe(200);
    expect(res1.body.totalNodes).toBeGreaterThan(0);

    const res2 = await request(app).get("/daedalus/cockpit/nodes");
    expect(res2.status).toBe(200);
    expect(res2.body.length).toBeGreaterThan(0);

    const capSets = new Set<number>();
    for (const node of res2.body) {
      capSets.add(node.capabilities?.length ?? 0);
    }
    expect(capSets.size).toBeGreaterThanOrEqual(1);

    const res3 = await request(app).get("/daedalus/governance/posture");
    expect(res3.status).toBe(200);

    const res4 = await request(app).get("/daedalus/constitution");
    expect(res4.status).toBe(200);
    expect(res4.body.allPassed).toBe(true);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // REPORT
  // ═══════════════════════════════════════════════════════════════════════

  test("FIVE-YEAR EXPANSION & HARDWARE REPORT", () => {
    const first = metrics[0];
    const last = metrics[metrics.length - 1];
    const peakNodes = Math.max(...metrics.map((m) => m.nodeCount));
    const peakHeap = Math.max(...metrics.map((m) => m.heapMB));
    const peakRss = Math.max(...metrics.map((m) => m.rssMB));
    const avgHeap =
      Math.round(
        (metrics.reduce((s, m) => s + m.heapMB, 0) / metrics.length) * 100,
      ) / 100;
    const peakSnapshot = Math.max(...metrics.map((m) => m.snapshotSizeKB));

    const postureHist: Record<string, number> = {};
    for (const m of metrics) postureHist[m.posture] = (postureHist[m.posture] ?? 0) + 1;

    // Expansion curve
    const expansionCurve: string[] = [];
    for (let i = 0; i < metrics.length; i += 3) {
      const m = metrics[i];
      expansionCurve.push(
        `│  M${String(m.month).padStart(2, " ")}: ${String(m.nodeCount).padStart(3, " ")} nodes | target=${String(targetFleetAtMonth(m.month)).padStart(3, " ")} | gen dist: ${JSON.stringify(m.fleetByGen)}`,
      );
    }

    // Hardware generation timeline
    const genTimeline: string[] = [];
    for (const g of HW_GENS) {
      const introMonth = g.introducedAtMonth;
      const introYear = Math.ceil(introMonth / 12);
      const introM = ((introMonth - 1) % 12) + 1;
      genTimeline.push(
        `│  Gen ${g.gen} (${g.model}): introduced Y${introYear}M${introM} | ${g.os} ${g.osVersion} | ${g.cores} cores | ${g.capabilities.length} caps`,
      );
    }

    // Fleet evolution by kind
    const kindEvolution: string[] = [];
    for (let i = 0; i < metrics.length; i += 12) {
      const m = metrics[i];
      kindEvolution.push(
        `│  Y${m.simYear}: ${JSON.stringify(m.fleetByKind)}`,
      );
    }
    kindEvolution.push(`│  Y5 final: ${JSON.stringify(last.fleetByKind)}`);

    // Yearly summaries
    const yearlySummaries: string[] = [];
    for (let y = 1; y <= 5; y++) {
      const yearMetrics = metrics.filter((m) => m.simYear === y);
      const ym = yearMetrics[yearMetrics.length - 1];
      const prev = y === 1 ? null : metrics.filter((m) => m.simYear === y - 1).pop()!;
      const yearHb = ym.totalHeartbeats - (prev?.totalHeartbeats ?? 0);
      const yearJoins = ym.totalJoins - (prev?.totalJoins ?? 0);
      const yearUpgrades = ym.totalUpgrades - (prev?.totalUpgrades ?? 0);
      const yearCapSyncs = ym.totalCapSyncs - (prev?.totalCapSyncs ?? 0);
      yearlySummaries.push(
        `│  Y${y}: ${ym.nodeCount} nodes | ${yearHb.toLocaleString()} hb | ${yearJoins} joins | ${yearUpgrades} upgrades | ${yearCapSyncs} cap-syncs | heap=${ym.heapMB}MB`,
      );
    }

    // Memory trend
    const memTrend: string[] = [];
    for (let i = 0; i < metrics.length; i += 6) {
      const m = metrics[i];
      memTrend.push(
        `│  M${String(m.month).padStart(2, " ")}: heap=${m.heapMB}MB  rss=${m.rssMB}MB  nodes=${m.nodeCount}`,
      );
    }
    memTrend.push(
      `│  M${last.month}: heap=${last.heapMB}MB  rss=${last.rssMB}MB  nodes=${last.nodeCount}`,
    );

    const report = [
      "",
      "╔════════════════════════════════════════════════════════════════════╗",
      "║   DAEDALUS 5-YEAR SIM — NODE EXPANSION & HARDWARE UPGRADES      ║",
      "╚════════════════════════════════════════════════════════════════════╝",
      "",
      "┌─ SIMULATION PARAMETERS ──────────────────────────────────────────┐",
      `│  Duration: 5 years (60 months)`,
      `│  HB cycles/month: 700`,
      `│  Peak fleet: ${peakNodes} nodes`,
      `│  Total heartbeats: ${last.totalHeartbeats.toLocaleString()}`,
      `│  Total joins: ${last.totalJoins.toLocaleString()}`,
      `│  Total detaches: ${last.totalDetaches.toLocaleString()}`,
      `│  Total quarantines: ${last.totalQuarantines.toLocaleString()}`,
      `│  Total errors: ${last.totalErrors.toLocaleString()}`,
      `│  Total hw upgrades: ${last.totalUpgrades}`,
      `│  Total cap syncs: ${last.totalCapSyncs.toLocaleString()}`,
      `│  Total profile syncs: ${last.totalProfileSyncs}`,
      `│  Snapshots saved: ${totalSnapshotSaves}`,
      `│  Constitution checks: ${totalConstitutionChecks} (failures: ${totalConstitutionFailures})`,
      `│  TTL swept: ${totalSweepedOverrides} overrides, ${totalSweepedDrifts} drifts`,
      "└─────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ HARDWARE GENERATIONS ───────────────────────────────────────────┐",
      ...genTimeline,
      "└─────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ FLEET EXPANSION CURVE (every 3 months) ─────────────────────────┐",
      ...expansionCurve,
      "└─────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ FLEET BY NODE KIND (yearly) ────────────────────────────────────┐",
      ...kindEvolution,
      "└─────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ YEARLY BREAKDOWN ───────────────────────────────────────────────┐",
      ...yearlySummaries,
      "└─────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ MEMORY TREND (every 6 months) ──────────────────────────────────┐",
      ...memTrend,
      `│  Peak heap: ${peakHeap}MB  |  Avg heap: ${avgHeap}MB  |  Peak RSS: ${peakRss}MB`,
      `│  Heap growth M1→M60: ${(last.heapMB - first.heapMB).toFixed(2)}MB`,
      "└─────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ GOVERNANCE POSTURE ─────────────────────────────────────────────┐",
      ...Object.entries(postureHist).map(
        ([k, v]) => `│  ${k}: ${v} months (${Math.round((v / 60) * 100)}%)`,
      ),
      "└─────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ STATE ACCUMULATION ─────────────────────────────────────────────┐",
      `│  Final overrides: ${last.overrideCount} (cap: 200)`,
      `│  Final drifts: ${last.driftCount} (cap: 200)`,
      `│  Final votes: ${last.voteCount} (cap: 50)`,
      `│  Event ring: ${last.eventHistorySize} (cap: 1000)`,
      `│  Peak snapshot: ${peakSnapshot}KB  |  Final: ${last.snapshotSizeKB}KB`,
      "└─────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ FINAL FLEET COMPOSITION ────────────────────────────────────────┐",
      `│  By generation: ${JSON.stringify(last.fleetByGen)}`,
      `│  By kind: ${JSON.stringify(last.fleetByKind)}`,
      `│  Latest gen available: Gen ${last.latestGenAvailable}`,
      "└─────────────────────────────────────────────────────────────────┘",
      "",
    ];

    if (issues.length > 0) {
      report.push(
        "┌─ ISSUES ───────────────────────────────────────────────────────┐",
      );
      for (const i of issues) report.push(`│  ${i}`);
      report.push(
        "└─────────────────────────────────────────────────────────────────┘",
      );
      report.push("");
    }

    const memOk = peakHeap < 800;
    const constOk = totalConstitutionFailures === 0;
    const postureOk = !issues.some((i) => i.includes("stuck"));
    const fleetOk = Object.keys(last.fleetByKind).length >= 2;
    const upgradeOk = totalUpgrades > 50;
    const allOk = memOk && constOk && postureOk && fleetOk && upgradeOk && issues.length === 0;

    report.push(
      "┌─ VERDICT ───────────────────────────────────────────────────────┐",
    );
    report.push(
      `│  Memory: ${memOk ? "STABLE" : "GROWTH"} (peak=${peakHeap.toFixed(0)}MB, final=${last.heapMB.toFixed(0)}MB)`,
    );
    report.push(
      `│  Constitution: ${constOk ? "CLEAN" : "FAILURES"} (${totalConstitutionChecks} checks)`,
    );
    report.push(`│  Posture: ${postureOk ? "HEALTHY" : "STUCK"}`);
    report.push(
      `│  Fleet diversity: ${fleetOk ? "HETEROGENEOUS" : "HOMOGENEOUS"} (${Object.keys(last.fleetByKind).length} kinds)`,
    );
    report.push(
      `│  Hw upgrades: ${upgradeOk ? "EXERCISED" : "INSUFFICIENT"} (${totalUpgrades} total)`,
    );
    report.push(`│  Issues: ${issues.length}`);
    report.push("│");
    if (allOk) {
      report.push(
        "│  ╔════════════════════════════════════════════════════════════╗",
      );
      report.push(
        "│  ║  PASSED — 5yr expansion + upgrades: NO ISSUES FOUND      ║",
      );
      report.push(
        "│  ╚════════════════════════════════════════════════════════════╝",
      );
    } else {
      report.push(
        "│  ╔════════════════════════════════════════════════════════════╗",
      );
      report.push(
        `│  ║  ${issues.length} ISSUE(S) FOUND — see above                          ║`,
      );
      report.push(
        "│  ╚════════════════════════════════════════════════════════════╝",
      );
    }
    report.push(
      "└─────────────────────────────────────────────────────────────────┘",
    );

    console.log(report.join("\n"));

    expect(totalConstitutionFailures).toBe(0);
    expect(peakHeap).toBeLessThan(800);
    expect(totalUpgrades).toBeGreaterThan(50);
  });
});
