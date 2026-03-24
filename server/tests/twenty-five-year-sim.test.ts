/**
 * DAEDALUS TWENTY-FIVE-YEAR OPERATIONAL SIMULATION
 * ═════════════════════════════════════════════════
 *
 * Models 25 years (300 months) of Daedalus operation at civilizational scale:
 *
 *   ERA 1 — GENESIS (Y1-3):   0 → 220 nodes, Gen 1-3 hardware, rapid buildout
 *   ERA 2 — GROWTH  (Y4-10):  220 → 500 nodes, Gen 4-6, second wave expansion
 *   ERA 3 — MATURITY (Y11-18): 500 → 800 nodes, Gen 7-9, stable high-scale ops
 *   ERA 4 — LEGACY  (Y19-25): 800 plateau, Gen 10, fleet refresh & consolidation
 *
 *   10 hardware generations across 25 years
 *   Mass hardware refresh events (entire fleet upgraded in waves)
 *   Data center failure scenarios (20-40% fleet loss + recovery)
 *   Governance storms, posture cycling, incident management at scale
 *   Memory, snapshot, constitution, and state accumulation tracking
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

jest.setTimeout(600_000);

// ═══════════════════════════════════════════════════════════════════════════════
// HARDWARE GENERATION MODEL — 10 GENERATIONS OVER 25 YEARS
// ═══════════════════════════════════════════════════════════════════════════════

type NodeKind = "server" | "desktop" | "mobile" | "embedded";

interface HwGenSpec {
  gen: number;
  os: string;
  osVersion: string;
  model: string;
  cores: number;
  capabilities: Capability[];
  availableKinds: NodeKind[];
  introducedAtMonth: number;
}

function mkCaps(names: [string, string][]): Capability[] {
  return names.map(([name, value]) => ({ name, value, enabled: true }));
}

const HW_GENS: HwGenSpec[] = [
  // ERA 1 — GENESIS
  {
    gen: 1, os: "linux", osVersion: "5.15", model: "mk1-pioneer", cores: 4,
    capabilities: mkCaps([["daedalus.core", "1.0"], ["daedalus.heartbeat", "1.0"]]),
    availableKinds: ["server", "desktop"], introducedAtMonth: 1,
  },
  {
    gen: 2, os: "linux", osVersion: "6.1", model: "mk2-scout", cores: 8,
    capabilities: mkCaps([["daedalus.core", "2.0"], ["daedalus.heartbeat", "1.1"], ["daedalus.expressive", "1.0"]]),
    availableKinds: ["server", "desktop", "mobile"], introducedAtMonth: 7,
  },
  {
    gen: 3, os: "linux", osVersion: "6.5", model: "mk3-sentinel", cores: 16,
    capabilities: mkCaps([["daedalus.core", "3.0"], ["daedalus.heartbeat", "2.0"], ["daedalus.expressive", "2.0"], ["daedalus.negotiation", "1.0"]]),
    availableKinds: ["server", "desktop", "mobile", "embedded"], introducedAtMonth: 18,
  },
  // ERA 2 — GROWTH
  {
    gen: 4, os: "darwin", osVersion: "24.0", model: "mk4-arm-atlas", cores: 16,
    capabilities: mkCaps([["daedalus.core", "4.0"], ["daedalus.heartbeat", "2.1"], ["daedalus.expressive", "3.0"], ["daedalus.negotiation", "2.0"], ["daedalus.federation", "1.0"]]),
    availableKinds: ["server", "desktop", "mobile"], introducedAtMonth: 37,
  },
  {
    gen: 5, os: "linux", osVersion: "7.0", model: "mk5-nexus", cores: 32,
    capabilities: mkCaps([["daedalus.core", "5.0"], ["daedalus.heartbeat", "3.0"], ["daedalus.expressive", "4.0"], ["daedalus.negotiation", "3.0"], ["daedalus.federation", "2.0"], ["daedalus.telemetry", "1.0"]]),
    availableKinds: ["server", "desktop", "mobile", "embedded"], introducedAtMonth: 60,
  },
  {
    gen: 6, os: "linux", osVersion: "7.5", model: "mk6-horizon", cores: 64,
    capabilities: mkCaps([["daedalus.core", "6.0"], ["daedalus.heartbeat", "3.1"], ["daedalus.expressive", "5.0"], ["daedalus.negotiation", "4.0"], ["daedalus.federation", "3.0"], ["daedalus.telemetry", "2.0"], ["daedalus.autonomy", "1.0"]]),
    availableKinds: ["server", "desktop", "mobile", "embedded"], introducedAtMonth: 84,
  },
  // ERA 3 — MATURITY
  {
    gen: 7, os: "linux", osVersion: "8.0", model: "mk7-meridian", cores: 64,
    capabilities: mkCaps([["daedalus.core", "7.0"], ["daedalus.heartbeat", "4.0"], ["daedalus.expressive", "6.0"], ["daedalus.negotiation", "5.0"], ["daedalus.federation", "4.0"], ["daedalus.telemetry", "3.0"], ["daedalus.autonomy", "2.0"], ["daedalus.mesh", "1.0"]]),
    availableKinds: ["server", "desktop", "mobile", "embedded"], introducedAtMonth: 132,
  },
  {
    gen: 8, os: "linux", osVersion: "8.5", model: "mk8-zenith", cores: 128,
    capabilities: mkCaps([["daedalus.core", "8.0"], ["daedalus.heartbeat", "4.1"], ["daedalus.expressive", "7.0"], ["daedalus.negotiation", "6.0"], ["daedalus.federation", "5.0"], ["daedalus.telemetry", "4.0"], ["daedalus.autonomy", "3.0"], ["daedalus.mesh", "2.0"], ["daedalus.sovereign", "1.0"]]),
    availableKinds: ["server", "desktop", "mobile", "embedded"], introducedAtMonth: 168,
  },
  {
    gen: 9, os: "darwin", osVersion: "28.0", model: "mk9-apex", cores: 128,
    capabilities: mkCaps([["daedalus.core", "9.0"], ["daedalus.heartbeat", "5.0"], ["daedalus.expressive", "8.0"], ["daedalus.negotiation", "7.0"], ["daedalus.federation", "6.0"], ["daedalus.telemetry", "5.0"], ["daedalus.autonomy", "4.0"], ["daedalus.mesh", "3.0"], ["daedalus.sovereign", "2.0"], ["daedalus.temporal", "1.0"]]),
    availableKinds: ["server", "desktop", "mobile", "embedded"], introducedAtMonth: 204,
  },
  // ERA 4 — LEGACY
  {
    gen: 10, os: "linux", osVersion: "9.0", model: "mk10-eternal", cores: 256,
    capabilities: mkCaps([["daedalus.core", "10.0"], ["daedalus.heartbeat", "6.0"], ["daedalus.expressive", "9.0"], ["daedalus.negotiation", "8.0"], ["daedalus.federation", "7.0"], ["daedalus.telemetry", "6.0"], ["daedalus.autonomy", "5.0"], ["daedalus.mesh", "4.0"], ["daedalus.sovereign", "3.0"], ["daedalus.temporal", "2.0"], ["daedalus.prescience", "1.0"]]),
    availableKinds: ["server", "desktop", "mobile", "embedded"], introducedAtMonth: 240,
  },
];

function getAvailableGens(month: number): HwGenSpec[] {
  return HW_GENS.filter((g) => g.introducedAtMonth <= month);
}
function getLatestGen(month: number): HwGenSpec {
  const avail = getAvailableGens(month);
  return avail[avail.length - 1];
}
function pickNewNodeGen(month: number): HwGenSpec {
  const avail = getAvailableGens(month);
  const r = Math.random();
  if (r < 0.7 || avail.length === 1) return avail[avail.length - 1];
  if (r < 0.9 || avail.length === 2) return avail[avail.length - 2];
  return avail[Math.max(0, avail.length - 3)];
}
function pickKind(gen: HwGenSpec): NodeKind {
  return gen.availableKinds[Math.floor(Math.random() * gen.availableKinds.length)];
}

// ═══════════════════════════════════════════════════════════════════════════════
// FLEET EXPANSION — MULTI-ERA S-CURVE
// ═══════════════════════════════════════════════════════════════════════════════

function targetFleetAtMonth(month: number): number {
  // Era 1 (M1-36):   sigmoid up to 220
  // Era 2 (M37-120): sigmoid from 220 to 500
  // Era 3 (M121-216): sigmoid from 500 to 800
  // Era 4 (M217-300): plateau at 800
  if (month <= 36) {
    return Math.round(220 / (1 + Math.exp(-0.25 * (month - 8))));
  }
  if (month <= 120) {
    const base = 220;
    const add = 280 / (1 + Math.exp(-0.1 * (month - 78)));
    return Math.round(base + add);
  }
  if (month <= 216) {
    const base = 500;
    const add = 300 / (1 + Math.exp(-0.08 * (month - 168)));
    return Math.round(base + add);
  }
  return 800;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

const OP = { id: "operator", role: "OPERATOR" as const, label: "Operator" };

function mkJoin(nodeId: string, gen: HwGenSpec, kind: NodeKind): NodeJoinPayload {
  return {
    nodeId, name: nodeId, capabilities: gen.capabilities,
    expressive: {
      glow: { level: "low", intensity: 0.3 },
      posture: "companion" as const,
      attention: { level: "aware" as const },
      continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: true },
    },
    profile: { id: nodeId, name: nodeId, kind, model: gen.model, os: gen.os, osVersion: gen.osVersion, operatorId: "operator" },
  };
}

function mkHb(nodeId: string) {
  return { nodeId, timestamp: new Date().toISOString(), status: "alive" as const };
}

interface NodeRecord {
  id: string;
  gen: number;
  kind: NodeKind;
  joinedAtMonth: number;
  lastUpgradeMonth: number;
}

interface EraMetrics {
  era: number;
  label: string;
  months: number;
  startNodes: number;
  endNodes: number;
  heartbeats: number;
  joins: number;
  detaches: number;
  upgrades: number;
  capSyncs: number;
  errors: number;
  quarantines: number;
  incidents: number;
  dcFailures: number;
  genDistEnd: Record<number, number>;
  kindDistEnd: Record<string, number>;
  heapEnd: number;
}

function snapMem() {
  const m = process.memoryUsage();
  return { heapMB: +(m.heapUsed / 1024 / 1024).toFixed(2), rssMB: +(m.rss / 1024 / 1024).toFixed(2) };
}

function checkConstitution(): boolean {
  try {
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;
    const behavioral = computeBehavioralField(beingMap);
    return validateBeingConstitution(beings, [], behavioral.dominantBeingId).allPassed;
  } catch { return false; }
}

// ═══════════════════════════════════════════════════════════════════════════════
// SIMULATION
// ═══════════════════════════════════════════════════════════════════════════════

describe("DAEDALUS 25-YEAR OPERATIONAL SIMULATION", () => {
  let reg: NodeMirrorRegistry;
  let bus: ReturnType<typeof getDaedalusEventBus>;
  let snapshotPath: string;
  let persistence: SnapshotPersistence;
  let app: ReturnType<typeof createOrchestratorApp>;

  const issues: string[] = [];
  const memSamples: { month: number; heap: number; rss: number; nodes: number }[] = [];
  const postureSamples: Record<string, number> = {};

  let totalHb = 0, totalJoins = 0, totalDetaches = 0, totalQuarantines = 0;
  let totalErrors = 0, totalUpgrades = 0, totalCapSyncs = 0, totalProfileSyncs = 0;
  let totalSweepedOvr = 0, totalSweepedDft = 0, totalIncidents = 0;
  let totalDcFailures = 0, totalSnapshotSaves = 0;
  let constitutionChecks = 0, constitutionFails = 0;

  const fleet = new Map<string, NodeRecord>();
  let nodeIdSeq = 0;

  const eraMetrics: EraMetrics[] = [];
  let eraHbStart = 0, eraJoinStart = 0, eraDetachStart = 0, eraUpgradeStart = 0;
  let eraCapSyncStart = 0, eraErrorStart = 0, eraQuarStart = 0, eraIncStart = 0;
  let eraDcStart = 0, eraStartNodes = 0;

  beforeAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    reg = getNodeMirrorRegistry();
    bus = getDaedalusEventBus();
    app = createOrchestratorApp();
    snapshotPath = path.join(__dirname, ".25yr-snapshot.json");
    persistence = new SnapshotPersistence(snapshotPath);
  });

  afterAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
    actionLog.clear();
    try { fs.unlinkSync(snapshotPath); } catch {}
  });

  function spawnNode(month: number): string {
    nodeIdSeq++;
    const gen = pickNewNodeGen(month);
    const kind = pickKind(gen);
    const id = `n${nodeIdSeq}`;
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
    const latest = getLatestGen(month);
    if (latest.gen <= rec.gen) return;
    reg.handleProfileSync({ nodeId: id, profile: { id, name: id, kind: rec.kind, model: latest.model, os: latest.os, osVersion: latest.osVersion, operatorId: "operator" }, timestamp: new Date().toISOString() });
    totalProfileSyncs++;
    reg.handleCapSync({ nodeId: id, capabilities: latest.capabilities, timestamp: new Date().toISOString() });
    totalCapSyncs++;
    rec.gen = latest.gen;
    rec.lastUpgradeMonth = month;
    totalUpgrades++;
  }

  function heartbeatAll() {
    for (const id of fleet.keys()) {
      reg.handleHeartbeat(mkHb(id));
      totalHb++;
    }
  }

  function errorNode(id: string, msg: string) {
    if (!fleet.has(id)) return;
    reg.handleError(id, msg);
    totalErrors++;
    const m = reg.getMirror(id);
    if (m && m.lifecycle.phase === "quarantined") totalQuarantines++;
  }

  function randomNode(): string | null {
    const arr = Array.from(fleet.keys());
    return arr.length > 0 ? arr[Math.floor(Math.random() * arr.length)] : null;
  }

  function cleanQuarantined(month: number) {
    for (const m of reg.getAllMirrors()) {
      if (m.lifecycle.phase === "quarantined") {
        removeNode(m.id);
        spawnNode(month);
      }
    }
  }

  function syncActiveSet() {
    for (const id of [...fleet.keys()]) {
      const m = reg.getMirror(id);
      if (!m || m.lifecycle.phase === "quarantined" || m.lifecycle.phase === "detached") fleet.delete(id);
    }
  }

  function fleetByGen(): Record<number, number> {
    const d: Record<number, number> = {};
    for (const r of fleet.values()) d[r.gen] = (d[r.gen] ?? 0) + 1;
    return d;
  }

  function fleetByKind(): Record<string, number> {
    const d: Record<string, number> = {};
    for (const r of fleet.values()) d[r.kind] = (d[r.kind] ?? 0) + 1;
    return d;
  }

  function getEraLabel(month: number): string {
    if (month <= 36) return "GENESIS";
    if (month <= 120) return "GROWTH";
    if (month <= 216) return "MATURITY";
    return "LEGACY";
  }

  function getEraNum(month: number): number {
    if (month <= 36) return 1;
    if (month <= 120) return 2;
    if (month <= 216) return 3;
    return 4;
  }

  function startEra() {
    eraHbStart = totalHb; eraJoinStart = totalJoins; eraDetachStart = totalDetaches;
    eraUpgradeStart = totalUpgrades; eraCapSyncStart = totalCapSyncs;
    eraErrorStart = totalErrors; eraQuarStart = totalQuarantines;
    eraIncStart = totalIncidents; eraDcStart = totalDcFailures;
    eraStartNodes = fleet.size;
  }

  function endEra(month: number, eraNum: number, label: string) {
    eraMetrics.push({
      era: eraNum, label,
      months: month <= 36 ? 36 : month <= 120 ? 84 : month <= 216 ? 96 : 84,
      startNodes: eraStartNodes, endNodes: fleet.size,
      heartbeats: totalHb - eraHbStart, joins: totalJoins - eraJoinStart,
      detaches: totalDetaches - eraDetachStart, upgrades: totalUpgrades - eraUpgradeStart,
      capSyncs: totalCapSyncs - eraCapSyncStart, errors: totalErrors - eraErrorStart,
      quarantines: totalQuarantines - eraQuarStart, incidents: totalIncidents - eraIncStart,
      dcFailures: totalDcFailures - eraDcStart,
      genDistEnd: fleetByGen(), kindDistEnd: fleetByKind(), heapEnd: snapMem().heapMB,
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // MAIN SIMULATION — 300 MONTHS
  // ═══════════════════════════════════════════════════════════════════════

  test("300-month simulation across 4 eras", () => {
    const MONTHS = 300;
    const HB_PER_MONTH = 400;

    let currentEra = 1;
    startEra();

    for (let month = 1; month <= MONTHS; month++) {
      const simYear = Math.ceil(month / 12);
      const simMonth = ((month - 1) % 12) + 1;
      const era = getEraNum(month);

      if (era !== currentEra) {
        endEra(month - 1, currentEra, getEraLabel(month - 1));
        currentEra = era;
        startEra();
      }

      // ── Fleet expansion ──────────────────────────────────────
      const target = targetFleetAtMonth(month);
      while (fleet.size < target) spawnNode(month);

      // ── Monthly churn: 2-4% ──────────────────────────────────
      const churnCount = Math.max(1, Math.floor(fleet.size * (0.02 + Math.random() * 0.02)));
      const sortedByAge = Array.from(fleet.values()).sort((a, b) => a.gen - b.gen);
      let churned = 0;
      for (const rec of sortedByAge) {
        if (churned >= churnCount || fleet.size <= 10) break;
        const latest = getLatestGen(month);
        if (rec.gen < latest.gen - 1 || Math.random() < 0.25) {
          removeNode(rec.id);
          spawnNode(month);
          churned++;
        }
      }

      // ── In-place hardware upgrades: 5-8% monthly ────────────
      const upgradeRate = 0.05 + Math.random() * 0.03;
      const upgradeCandidates = Array.from(fleet.values())
        .filter((r) => r.gen < getLatestGen(month).gen)
        .sort((a, b) => a.gen - b.gen);
      const upgradeCount = Math.floor(fleet.size * upgradeRate);
      for (let u = 0; u < Math.min(upgradeCount, upgradeCandidates.length); u++) {
        upgradeNode(upgradeCandidates[u].id, month);
      }

      // ── Heartbeat cycles ─────────────────────────────────────
      for (let c = 0; c < HB_PER_MONTH; c++) {
        heartbeatAll();
        if (Math.random() < 0.01) {
          const errorCount = Math.max(1, Math.floor(fleet.size * 0.02));
          for (let e = 0; e < errorCount; e++) {
            const t = randomNode();
            if (t) errorNode(t, `err-m${month}-c${c}`);
          }
        }
      }

      // ── Periodic capability resync (every 3 months) ──────────
      if (simMonth % 3 === 0) {
        for (const rec of fleet.values()) {
          const genSpec = HW_GENS.find((g) => g.gen === rec.gen);
          if (genSpec) {
            reg.handleCapSync({ nodeId: rec.id, capabilities: genSpec.capabilities, timestamp: new Date().toISOString() });
            totalCapSyncs++;
          }
        }
      }

      // ── DATA CENTER FAILURE: ~once every 3-5 years ───────────
      if (simMonth === 6 && (simYear === 4 || simYear === 8 || simYear === 12 || simYear === 17 || simYear === 22)) {
        totalDcFailures++;
        const lossRate = 0.2 + Math.random() * 0.2;
        const toLose = Math.floor(fleet.size * lossRate);
        const victims = Array.from(fleet.keys()).slice(0, toLose);
        for (const v of victims) removeNode(v);
        // Recovery: spawn replacements
        while (fleet.size < target) spawnNode(month);
        // Open a critical incident
        incidentService.openIncident({
          title: `DC failure Y${simYear}: ${toLose} nodes lost`,
          severity: "CRITICAL",
          notes: `Data center failure simulation. ${lossRate.toFixed(0)}% fleet lost and recovered.`,
        });
        totalIncidents++;
      }

      // ── MASS HARDWARE REFRESH: when new gen drops, push hard ──
      const latestGen = getLatestGen(month);
      if (latestGen.introducedAtMonth === month) {
        const refreshCount = Math.floor(fleet.size * 0.15);
        const oldNodes = Array.from(fleet.values())
          .filter((r) => r.gen < latestGen.gen)
          .sort((a, b) => a.gen - b.gen)
          .slice(0, refreshCount);
        for (const rec of oldNodes) upgradeNode(rec.id, month);
      }

      // ── Governance ───────────────────────────────────────────
      for (let w = 0; w < 4; w++) {
        if (Math.random() < 0.25) {
          governanceService.applyOverride({
            createdBy: OP,
            reason: `Maint Y${simYear}M${simMonth}W${w}`,
            scope: "NODE" as const,
            effect: "ALLOW" as const,
            expiresAt: new Date(Date.now() + 1 + Math.floor(Math.random() * 5)).toISOString(),
          });
        }
      }
      governanceService.sweepExpired().expiredOverrides && totalSweepedOvr++;
      governanceService.sweepExpired().expiredDrifts && totalSweepedDft++;

      if (Math.random() < 0.2) {
        const sevs: Array<"LOW" | "MEDIUM" | "HIGH"> = ["LOW", "MEDIUM", "HIGH"];
        governanceService.recordDrift({
          severity: sevs[Math.floor(Math.random() * (simYear > 10 ? 3 : 2))],
          summary: `Drift Y${simYear}M${simMonth}`,
          expiresAt: new Date(Date.now() + 1 + Math.floor(Math.random() * 5)).toISOString(),
        });
      }

      if (simMonth % 3 === 0 && Math.random() < 0.4) {
        governanceService.castVote({
          being: OP,
          vote: (Math.random() < 0.85 ? "ALLOW" : "ESCALATE") as "ALLOW" | "ESCALATE",
          weight: 0.5 + Math.random() * 0.5,
        });
      }

      // Periodic cleanup
      if (simMonth % 4 === 0) {
        governanceService.clearVotes();
        if (governanceService.listOverrides().length > 50) governanceService.clearOverrides();
        if (governanceService.listDrifts().length > 20) governanceService.clearDrifts();
      }

      // ── Incidents ────────────────────────────────────────────
      if (simMonth % 3 === 0 && Math.random() < 0.5) {
        const sevs: Array<"LOW" | "MEDIUM" | "HIGH" | "CRITICAL"> = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
        incidentService.openIncident({
          title: `Incident Y${simYear}M${simMonth}`,
          severity: sevs[Math.min(Math.floor(Math.random() * (simYear > 10 ? 4 : 3)), 3)],
        });
        totalIncidents++;
      }
      for (const inc of incidentService.listIncidents({ status: "open" })) {
        if (Math.random() < 0.6) incidentService.resolveIncident(inc.id);
      }
      if (month % 12 === 0) incidentService.clearResolved();

      // ── Chaos: quarterly ─────────────────────────────────────
      if (simMonth % 3 === 0) {
        const stormSize = Math.min(Math.floor(fleet.size * 0.08), 30);
        for (let s = 0; s < stormSize; s++) {
          const t = randomNode();
          if (t) for (let e = 0; e < 6; e++) errorNode(t, `chaos-m${month}`);
        }
        heartbeatAll();
        totalHb += fleet.size;
      }

      // ── Cleanup ──────────────────────────────────────────────
      cleanQuarantined(month);
      syncActiveSet();

      // ── Snapshot every 3 months ──────────────────────────────
      if (simMonth % 3 === 0) {
        persistence.save({
          beings: daedalusStore.getBeingPresences(),
          overrides: governanceService.listOverrides(),
          drifts: governanceService.listDrifts(),
          votes: governanceService.listVotes(),
          mirrors: reg.getAllMirrors(),
          eventHistory: bus.getHistory(),
          savedAt: new Date().toISOString(),
        });
        totalSnapshotSaves++;
      }

      // ── Constitution check every 6 months ────────────────────
      if (simMonth % 6 === 0) {
        constitutionChecks++;
        if (!checkConstitution()) {
          constitutionFails++;
          issues.push(`[Y${simYear}M${simMonth}] Constitution FAILED`);
        }
      }

      // ── Posture ──────────────────────────────────────────────
      const p = governanceService.getPostureSnapshot().posture;
      postureSamples[p] = (postureSamples[p] ?? 0) + 1;

      // ── Memory sample every 12 months ────────────────────────
      if (simMonth === 12 || month === 1) {
        const mem = snapMem();
        memSamples.push({ month, heap: mem.heapMB, rss: mem.rssMB, nodes: fleet.size });
      }
    }

    // Close final era
    endEra(MONTHS, currentEra, getEraLabel(MONTHS));

    // ── Assertions ───────────────────────────────────────────────
    expect(totalHb).toBeGreaterThan(10_000_000);
    expect(totalJoins).toBeGreaterThan(1000);
    expect(totalUpgrades).toBeGreaterThan(500);
    expect(totalCapSyncs).toBeGreaterThan(5000);
    expect(totalDcFailures).toBe(5);
    expect(constitutionFails).toBe(0);
    expect(fleet.size).toBeGreaterThan(700);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // POST-SIMULATION CHECKS
  // ═══════════════════════════════════════════════════════════════════════

  test("Snapshot restore after 25 years", () => {
    const loaded = persistence.load();
    expect(loaded).not.toBeNull();
    expect(loaded!.mirrors.length).toBeGreaterThan(0);
    const models = new Set(loaded!.mirrors.map((m: any) => m.profile.model));
    expect(models.size).toBeGreaterThanOrEqual(1);
  });

  test("HTTP endpoints responsive after 25 years of state", async () => {
    const [summary, nodes, posture, constitution] = await Promise.all([
      request(app).get("/daedalus/cockpit/summary"),
      request(app).get("/daedalus/cockpit/nodes"),
      request(app).get("/daedalus/governance/posture"),
      request(app).get("/daedalus/constitution"),
    ]);
    expect(summary.status).toBe(200);
    expect(summary.body.totalNodes).toBeGreaterThan(700);
    expect(nodes.status).toBe(200);
    expect(nodes.body.length).toBeGreaterThan(700);
    expect(posture.status).toBe(200);
    expect(constitution.status).toBe(200);
    expect(constitution.body.allPassed).toBe(true);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // REPORT
  // ═══════════════════════════════════════════════════════════════════════

  test("25-YEAR OPERATIONAL REPORT", () => {
    const firstMem = memSamples[0];
    const lastMem = memSamples[memSamples.length - 1];
    const peakHeap = Math.max(...memSamples.map(s => s.heap));
    const peakNodes = Math.max(...memSamples.map(s => s.nodes));

    const report: string[] = [
      "",
      "╔══════════════════════════════════════════════════════════════════════╗",
      "║       DAEDALUS 25-YEAR OPERATIONAL SIMULATION — FINAL REPORT       ║",
      "╚══════════════════════════════════════════════════════════════════════╝",
      "",
      "┌─ SIMULATION SCALE ───────────────────────────────────────────────────┐",
      `│  Duration: 25 years (300 months)`,
      `│  HB cycles/month: 400`,
      `│  Total heartbeats: ${totalHb.toLocaleString()}`,
      `│  Total node joins: ${totalJoins.toLocaleString()}`,
      `│  Total node detaches: ${totalDetaches.toLocaleString()}`,
      `│  Total quarantines: ${totalQuarantines.toLocaleString()}`,
      `│  Total errors: ${totalErrors.toLocaleString()}`,
      `│  Total hw upgrades: ${totalUpgrades.toLocaleString()}`,
      `│  Total cap syncs: ${totalCapSyncs.toLocaleString()}`,
      `│  Total profile syncs: ${totalProfileSyncs.toLocaleString()}`,
      `│  Data center failures: ${totalDcFailures}`,
      `│  Total incidents: ${totalIncidents}`,
      `│  Snapshots saved: ${totalSnapshotSaves}`,
      `│  Constitution checks: ${constitutionChecks} (failures: ${constitutionFails})`,
      "└─────────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ HARDWARE GENERATIONS (10 across 25 years) ──────────────────────────┐",
    ];

    for (const g of HW_GENS) {
      const y = Math.ceil(g.introducedAtMonth / 12);
      const m = ((g.introducedAtMonth - 1) % 12) + 1;
      report.push(`│  Gen ${String(g.gen).padStart(2, " ")} ${g.model.padEnd(20)} Y${y}M${m}  ${g.os} ${g.osVersion}  ${String(g.cores).padStart(3)}c  ${g.capabilities.length} caps`);
    }
    report.push("└─────────────────────────────────────────────────────────────────────┘");

    report.push("");
    report.push("┌─ ERA BREAKDOWN ────────────────────────────────────────────────────┐");
    for (const e of eraMetrics) {
      report.push(`│  ERA ${e.era}: ${e.label} (${e.months} months)`);
      report.push(`│    Fleet: ${e.startNodes} → ${e.endNodes} nodes`);
      report.push(`│    ${e.heartbeats.toLocaleString()} hb | ${e.joins} joins | ${e.detaches} det | ${e.upgrades} upg | ${e.capSyncs.toLocaleString()} caps`);
      report.push(`│    ${e.errors} errors | ${e.quarantines} quar | ${e.incidents} inc | ${e.dcFailures} DC failures`);
      report.push(`│    Gen dist: ${JSON.stringify(e.genDistEnd)}`);
      report.push(`│    Kind dist: ${JSON.stringify(e.kindDistEnd)}`);
      report.push(`│    Heap: ${e.heapEnd}MB`);
      report.push("│");
    }
    report.push("└─────────────────────────────────────────────────────────────────────┘");

    report.push("");
    report.push("┌─ MEMORY TREND (yearly) ────────────────────────────────────────────┐");
    for (const s of memSamples) {
      report.push(`│  M${String(s.month).padStart(3, " ")}: heap=${s.heap}MB  rss=${s.rss}MB  nodes=${s.nodes}`);
    }
    report.push(`│  Peak heap: ${peakHeap}MB  |  Peak nodes: ${peakNodes}`);
    report.push(`│  Heap growth M1→M300: ${(lastMem.heap - firstMem.heap).toFixed(2)}MB`);
    report.push("└─────────────────────────────────────────────────────────────────────┘");

    report.push("");
    report.push("┌─ GOVERNANCE POSTURE DISTRIBUTION ──────────────────────────────────┐");
    for (const [p, count] of Object.entries(postureSamples)) {
      report.push(`│  ${p}: ${count} months (${Math.round(count / 300 * 100)}%)`);
    }
    report.push("└─────────────────────────────────────────────────────────────────────┘");

    report.push("");
    report.push("┌─ FINAL FLEET COMPOSITION ──────────────────────────────────────────┐");
    report.push(`│  Total: ${fleet.size} nodes`);
    report.push(`│  By gen: ${JSON.stringify(fleetByGen())}`);
    report.push(`│  By kind: ${JSON.stringify(fleetByKind())}`);
    report.push("└─────────────────────────────────────────────────────────────────────┘");

    if (issues.length > 0) {
      report.push("");
      report.push("┌─ ISSUES ───────────────────────────────────────────────────────────┐");
      for (const i of issues) report.push(`│  ${i}`);
      report.push("└─────────────────────────────────────────────────────────────────────┘");
    }

    const heapGrowth = lastMem.heap - firstMem.heap;
    const memOk = Math.abs(heapGrowth) < 300;
    const constOk = constitutionFails === 0;
    const fleetOk = fleet.size >= 700;
    const allOk = memOk && constOk && fleetOk && issues.length === 0;

    report.push("");
    report.push("┌─ VERDICT ──────────────────────────────────────────────────────────┐");
    report.push(`│  Memory: ${memOk ? "STABLE" : "GROWTH"} (${heapGrowth.toFixed(1)}MB over 25yr)`);
    report.push(`│  Constitution: ${constOk ? "CLEAN" : "FAILURES"} (${constitutionChecks} checks)`);
    report.push(`│  Fleet health: ${fleetOk ? "HEALTHY" : "DEGRADED"} (${fleet.size} nodes)`);
    report.push(`│  Issues: ${issues.length}`);
    report.push("│");
    if (allOk) {
      report.push("│  ╔═══════════════════════════════════════════════════════════════╗");
      report.push("│  ║  25-YEAR SIMULATION: PASSED — ALL SYSTEMS NOMINAL            ║");
      report.push("│  ╚═══════════════════════════════════════════════════════════════╝");
    } else {
      report.push("│  ╔═══════════════════════════════════════════════════════════════╗");
      report.push(`│  ║  25-YEAR SIMULATION: ${issues.length} ISSUE(S) — SEE ABOVE                  ║`);
      report.push("│  ╚═══════════════════════════════════════════════════════════════╝");
    }
    report.push("└─────────────────────────────────────────────────────────────────────┘");

    console.log(report.join("\n"));

    expect(constitutionFails).toBe(0);
    expect(Math.abs(heapGrowth)).toBeLessThan(300);
  });
});
