/**
 * DAEDALUS 1,000-YEAR OPERATIONAL SIMULATION
 * ═══════════════════════════════════════════
 *
 * Simulates a full millennium of continuous Daedalus operation.
 * 12,000 months. 100 hardware generations. Fleet scales 0 → 3,000.
 *
 *   ERA 1  — SPARK         (Y1-10)      0 → 300     Gens 1-4      founding fleet
 *   ERA 2  — EXPANSION     (Y11-50)     300 → 1000  Gens 5-20     rapid scaling
 *   ERA 3  — EMPIRE        (Y51-150)    1000 → 2000 Gens 21-60    global scale
 *   ERA 4  — ZENITH        (Y151-250)   2000 → 3000 Gens 61-100   peak capacity
 *   ERA 5  — EQUILIBRIUM   (Y251-350)   3000 stable               long plateau
 *   ERA 6  — CONTRACTION   (Y351-400)   3000 → 1500               fleet pruning
 *   ERA 7  — DARK AGE      (Y401-500)   1500 → 1000               decline
 *   ERA 8  — RESURGENCE    (Y501-650)   1000 → 2500               rebuilding
 *   ERA 9  — SECOND ZENITH (Y651-800)   2500 → 3000               restored peak
 *   ERA 10 — ETERNITY      (Y801-1000)  3000 stable               final plateau
 *
 * Every subsystem is exercised: heartbeats, governance, incidents, chaos,
 * data center failures, hardware upgrades, capability evolution, persistence,
 * constitution checks, memory stability.
 */

import { createOrchestratorApp } from "../orchestrator";
import {
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
  NodeMirrorRegistry,
} from "../orchestrator/mirror/NodeMirror";
import type {
  NodeJoinPayload,
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

jest.setTimeout(7_200_000);

// ═══════════════════════════════════════════════════════════════════════
// HARDWARE GENERATION MODEL — 100 GENS OVER 1,000 YEARS
// ═══════════════════════════════════════════════════════════════════════

type NodeKind = "server" | "desktop" | "mobile" | "embedded";
const KINDS: NodeKind[] = ["server", "desktop", "mobile", "embedded"];

interface HwGenSpec {
  gen: number; model: string; os: string; osVersion: string;
  cores: number; capabilities: Capability[]; introducedAtMonth: number;
}

function buildGens(): HwGenSpec[] {
  const gens: HwGenSpec[] = [];
  const osRotation = ["linux", "darwin", "linux", "linux", "darwin"];
  const modelNames = [
    "alpha","beta","gamma","delta","epsilon","zeta","eta","theta","iota","kappa",
    "lambda","mu","nu","xi","omicron","pi","rho","sigma","tau","upsilon",
  ];
  for (let g = 1; g <= 100; g++) {
    const introMonth = g === 1 ? 1 : Math.round(6 + (g - 1) * 119.5);
    const os = osRotation[(g - 1) % osRotation.length];
    const ver = `${5 + Math.floor(g / 5)}.${g % 10}`;
    const cores = Math.min(2 ** (2 + Math.floor(g / 4)), 8192);
    const capNames = [
      "daedalus.core","daedalus.heartbeat","daedalus.expressive",
      "daedalus.negotiation","daedalus.federation","daedalus.telemetry",
      "daedalus.autonomy","daedalus.mesh","daedalus.sovereign",
      "daedalus.temporal","daedalus.prescience","daedalus.synthesis",
      "daedalus.resonance","daedalus.transcendence","daedalus.omega",
      "daedalus.continuum","daedalus.eternity","daedalus.singularity",
    ];
    const capCount = Math.min(2 + Math.floor(g / 5.5), capNames.length);
    const caps: Capability[] = [];
    for (let c = 0; c < capCount; c++) {
      caps.push({ name: capNames[c], value: `${Math.ceil(g / 5)}.${g % 5}`, enabled: true });
    }
    gens.push({
      gen: g,
      model: `mk${g}-${modelNames[g % modelNames.length]}`,
      os, osVersion: ver, cores, capabilities: caps, introducedAtMonth: introMonth,
    });
  }
  return gens;
}

const HW_GENS = buildGens();

function getLatestGen(month: number): HwGenSpec {
  let latest = HW_GENS[0];
  for (const g of HW_GENS) {
    if (g.introducedAtMonth <= month) latest = g; else break;
  }
  return latest;
}

function pickNewGen(month: number): HwGenSpec {
  const latest = getLatestGen(month);
  if (Math.random() < 0.75) return latest;
  const prev = HW_GENS.find(g => g.gen === latest.gen - 1);
  return prev && prev.introducedAtMonth <= month ? prev : latest;
}

function pickKind(): NodeKind { return KINDS[Math.floor(Math.random() * KINDS.length)]; }

// ═══════════════════════════════════════════════════════════════════════
// FLEET CURVE — 10 ERAS
// ═══════════════════════════════════════════════════════════════════════

function targetFleet(month: number): number {
  const y = month / 12;
  if (y <= 10) return Math.round(300 / (1 + Math.exp(-0.5 * (y - 5))));
  if (y <= 50) return Math.round(300 + 700 * ((y - 10) / 40));
  if (y <= 150) return Math.round(1000 + 1000 * ((y - 50) / 100));
  if (y <= 250) return Math.round(2000 + 1000 * ((y - 150) / 100));
  if (y <= 350) return 3000;
  if (y <= 400) return Math.round(3000 - 1500 * ((y - 350) / 50));
  if (y <= 500) return Math.round(1500 - 500 * ((y - 400) / 100));
  if (y <= 650) return Math.round(1000 + 1500 * ((y - 500) / 150));
  if (y <= 800) return Math.round(2500 + 500 * ((y - 650) / 150));
  return 3000;
}

function getEra(month: number): { num: number; label: string } {
  const y = month / 12;
  if (y <= 10) return { num: 1, label: "SPARK" };
  if (y <= 50) return { num: 2, label: "EXPANSION" };
  if (y <= 150) return { num: 3, label: "EMPIRE" };
  if (y <= 250) return { num: 4, label: "ZENITH" };
  if (y <= 350) return { num: 5, label: "EQUILIBRIUM" };
  if (y <= 400) return { num: 6, label: "CONTRACTION" };
  if (y <= 500) return { num: 7, label: "DARK AGE" };
  if (y <= 650) return { num: 8, label: "RESURGENCE" };
  if (y <= 800) return { num: 9, label: "SECOND ZENITH" };
  return { num: 10, label: "ETERNITY" };
}

// ═══════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════

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

function mkHb(id: string) {
  return { nodeId: id, timestamp: new Date().toISOString(), status: "alive" as const };
}

interface NodeRec { id: string; gen: number; kind: NodeKind }

function snapMem() {
  const m = process.memoryUsage();
  return { heap: +(m.heapUsed / 1048576).toFixed(1), rss: +(m.rss / 1048576).toFixed(1) };
}

function checkConstitution(): boolean {
  try {
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, BeingPresenceDetail> = {};
    for (const b of beings) beingMap[b.id] = b;
    return validateBeingConstitution(beings, [], computeBehavioralField(beingMap).dominantBeingId).allPassed;
  } catch { return false; }
}

// ═══════════════════════════════════════════════════════════════════════
// SIMULATION
// ═══════════════════════════════════════════════════════════════════════

describe("DAEDALUS 1,000-YEAR OPERATIONAL SIMULATION", () => {
  let reg: NodeMirrorRegistry;
  let bus: ReturnType<typeof getDaedalusEventBus>;
  let snapshotPath: string;
  let persistence: SnapshotPersistence;
  let app: ReturnType<typeof createOrchestratorApp>;

  const issues: string[] = [];
  const memSamples: { month: number; heap: number; rss: number; nodes: number }[] = [];
  const postureDist: Record<string, number> = {};
  const eraSummaries: string[] = [];

  let totalHb = 0, totalJoins = 0, totalDetaches = 0, totalQuarantines = 0;
  let totalErrors = 0, totalUpgrades = 0, totalCapSyncs = 0;
  let totalDcFailures = 0, totalIncidents = 0, totalSnapshots = 0;
  let constChecks = 0, constFails = 0;

  const fleet = new Map<string, NodeRec>();
  let nodeSeq = 0;

  let eraHb = 0, eraJoins = 0, eraDet = 0, eraUpg = 0, eraErr = 0;
  let eraQuar = 0, eraDc = 0, eraInc = 0;

  beforeAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    reg = getNodeMirrorRegistry();
    bus = getDaedalusEventBus();
    app = createOrchestratorApp();
    snapshotPath = path.join(__dirname, ".1000yr-snapshot.json");
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

  function spawn(month: number): string {
    nodeSeq++;
    const gen = pickNewGen(month);
    const id = `n${nodeSeq}`;
    const kind = pickKind();
    reg.handleJoin(mkJoin(id, gen, kind));
    fleet.set(id, { id, gen: gen.gen, kind });
    totalJoins++; eraJoins++;
    return id;
  }

  function remove(id: string) {
    if (!fleet.has(id)) return;
    reg.handleDetach(id);
    fleet.delete(id);
    totalDetaches++; eraDet++;
  }

  function upgrade(id: string, month: number) {
    const rec = fleet.get(id);
    if (!rec) return;
    const latest = getLatestGen(month);
    if (latest.gen <= rec.gen) return;
    reg.handleProfileSync({
      nodeId: id,
      profile: { id, name: id, kind: rec.kind, model: latest.model, os: latest.os, osVersion: latest.osVersion, operatorId: "operator" },
      timestamp: new Date().toISOString(),
    });
    reg.handleCapSync({ nodeId: id, capabilities: latest.capabilities, timestamp: new Date().toISOString() });
    rec.gen = latest.gen;
    totalUpgrades++; eraUpg++;
    totalCapSyncs++;
  }

  function heartbeatAll() {
    for (const id of fleet.keys()) { reg.handleHeartbeat(mkHb(id)); totalHb++; eraHb++; }
  }

  function injectError(id: string, msg: string) {
    if (!fleet.has(id)) return;
    reg.handleError(id, msg);
    totalErrors++; eraErr++;
    const m = reg.getMirror(id);
    if (m && m.lifecycle.phase === "quarantined") { totalQuarantines++; eraQuar++; }
  }

  function randNode(): string | null {
    const arr = Array.from(fleet.keys());
    return arr.length > 0 ? arr[Math.floor(Math.random() * arr.length)] : null;
  }

  function cleanQuarantined(month: number) {
    for (const m of reg.getAllMirrors()) {
      if (m.lifecycle.phase === "quarantined") { remove(m.id); spawn(month); }
    }
  }

  function syncFleetSet() {
    for (const id of [...fleet.keys()]) {
      const m = reg.getMirror(id);
      if (!m || m.lifecycle.phase === "quarantined" || m.lifecycle.phase === "detached") fleet.delete(id);
    }
  }

  function genDist(): Record<number, number> {
    const d: Record<number, number> = {};
    for (const r of fleet.values()) d[r.gen] = (d[r.gen] ?? 0) + 1;
    return d;
  }

  function kindDist(): Record<string, number> {
    const d: Record<string, number> = {};
    for (const r of fleet.values()) d[r.kind] = (d[r.kind] ?? 0) + 1;
    return d;
  }

  function resetEraCounters() { eraHb = 0; eraJoins = 0; eraDet = 0; eraUpg = 0; eraErr = 0; eraQuar = 0; eraDc = 0; eraInc = 0; }

  function recordEra(era: { num: number; label: string }, startNodes: number) {
    const gd = genDist();
    const topGens = Object.entries(gd).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([g, c]) => `g${g}:${c}`).join(" ");
    eraSummaries.push(
      `│  ERA ${String(era.num).padStart(2)} ${era.label.padEnd(14)} ${String(startNodes).padStart(4)}→${String(fleet.size).padStart(4)} nodes | ` +
      `${(eraHb / 1e6).toFixed(1)}M hb | ${eraJoins} j | ${eraUpg} upg | ${eraErr} err | ${eraDc} DC`
    );
  }

  // ═══════════════════════════════════════════════════════════════════
  // THE SIMULATION — 12,000 MONTHS
  // ═══════════════════════════════════════════════════════════════════

  test("12,000-month simulation across 10 eras", () => {
    const MONTHS = 12_000;
    const HB_PER_MONTH = 100;

    let currentEra = getEra(1);
    let eraStartNodes = 0;
    resetEraCounters();

    for (let month = 1; month <= MONTHS; month++) {
      const simYear = Math.ceil(month / 12);
      const simMonth = ((month - 1) % 12) + 1;
      const era = getEra(month);

      if (era.num !== currentEra.num) {
        recordEra(currentEra, eraStartNodes);
        currentEra = era;
        eraStartNodes = fleet.size;
        resetEraCounters();
      }

      const target = targetFleet(month);

      while (fleet.size < target) spawn(month);

      if (fleet.size > target + 5) {
        const excess = fleet.size - target;
        const sorted = Array.from(fleet.values()).sort((a, b) => a.gen - b.gen);
        for (let i = 0; i < excess && fleet.size > target; i++) remove(sorted[i].id);
      }

      const churnCount = Math.max(1, Math.floor(fleet.size * (0.02 + Math.random() * 0.01)));
      const candidates = Array.from(fleet.values()).sort((a, b) => a.gen - b.gen);
      let churned = 0;
      for (const rec of candidates) {
        if (churned >= churnCount || fleet.size <= 5) break;
        if (rec.gen < getLatestGen(month).gen - 1 || Math.random() < 0.2) {
          remove(rec.id); spawn(month); churned++;
        }
      }

      const upgCandidates = Array.from(fleet.values())
        .filter(r => r.gen < getLatestGen(month).gen)
        .sort((a, b) => a.gen - b.gen);
      const upgCount = Math.floor(fleet.size * (0.04 + Math.random() * 0.02));
      for (let u = 0; u < Math.min(upgCount, upgCandidates.length); u++) {
        upgrade(upgCandidates[u].id, month);
      }

      for (let c = 0; c < HB_PER_MONTH; c++) {
        heartbeatAll();
        if (Math.random() < 0.008) {
          const errCount = Math.max(1, Math.floor(fleet.size * 0.015));
          for (let e = 0; e < errCount; e++) {
            const t = randNode();
            if (t) injectError(t, `e${month}c${c}`);
          }
        }
      }

      if (simMonth % 6 === 0) {
        for (const rec of fleet.values()) {
          const g = HW_GENS.find(x => x.gen === rec.gen);
          if (g) { reg.handleCapSync({ nodeId: rec.id, capabilities: g.capabilities, timestamp: new Date().toISOString() }); totalCapSyncs++; }
        }
      }

      if (simMonth === 6 && simYear % 11 === 0 && simYear > 1) {
        totalDcFailures++; eraDc++;
        const lossRate = 0.15 + Math.random() * 0.25;
        const toLose = Math.floor(fleet.size * lossRate);
        const victims = Array.from(fleet.keys()).slice(0, toLose);
        for (const v of victims) remove(v);
        while (fleet.size < target) spawn(month);
        incidentService.openIncident({ title: `DC-FAIL Y${simYear}: ${toLose} lost`, severity: "CRITICAL" });
        totalIncidents++; eraInc++;
      }

      const latest = getLatestGen(month);
      if (latest.introducedAtMonth === month && latest.gen > 1) {
        const count = Math.floor(fleet.size * 0.12);
        const old = Array.from(fleet.values()).filter(r => r.gen < latest.gen).sort((a, b) => a.gen - b.gen).slice(0, count);
        for (const r of old) upgrade(r.id, month);
      }

      if (Math.random() < 0.2) {
        governanceService.applyOverride({
          createdBy: OP, reason: `M${month}`, scope: "NODE" as const, effect: "ALLOW" as const,
          expiresAt: new Date(Date.now() + 1 + Math.floor(Math.random() * 5)).toISOString(),
        });
      }
      governanceService.sweepExpired();

      if (Math.random() < 0.15) {
        governanceService.recordDrift({
          severity: (["LOW","MEDIUM","HIGH"] as const)[Math.floor(Math.random() * 3)],
          summary: `D${month}`,
          expiresAt: new Date(Date.now() + 1 + Math.floor(Math.random() * 5)).toISOString(),
        });
      }

      if (simMonth % 3 === 0 && Math.random() < 0.3) {
        governanceService.castVote({
          being: OP,
          vote: (Math.random() < 0.85 ? "ALLOW" : "ESCALATE") as "ALLOW" | "ESCALATE",
          weight: 0.5 + Math.random() * 0.5,
        });
      }

      if (simMonth % 4 === 0) {
        governanceService.clearVotes();
        if (governanceService.listOverrides().length > 40) governanceService.clearOverrides();
        if (governanceService.listDrifts().length > 15) governanceService.clearDrifts();
      }

      if (simMonth % 4 === 0 && Math.random() < 0.4) {
        incidentService.openIncident({ title: `I-Y${simYear}M${simMonth}`, severity: (["LOW","MEDIUM","HIGH","CRITICAL"] as const)[Math.floor(Math.random() * 4)] });
        totalIncidents++; eraInc++;
      }
      for (const inc of incidentService.listIncidents({ status: "open" })) {
        if (Math.random() < 0.6) incidentService.resolveIncident(inc.id);
      }
      if (month % 24 === 0) incidentService.clearResolved();

      if (simMonth % 3 === 0) {
        const stormSize = Math.min(Math.floor(fleet.size * 0.06), 40);
        for (let s = 0; s < stormSize; s++) {
          const t = randNode();
          if (t) for (let e = 0; e < 6; e++) injectError(t, `chaos${month}`);
        }
        heartbeatAll();
        totalHb += fleet.size; eraHb += fleet.size;
      }

      cleanQuarantined(month);
      syncFleetSet();

      if (simMonth % 6 === 0) {
        persistence.save({
          beings: daedalusStore.getBeingPresences(),
          overrides: governanceService.listOverrides(),
          drifts: governanceService.listDrifts(),
          votes: governanceService.listVotes(),
          mirrors: reg.getAllMirrors(),
          eventHistory: bus.getHistory(),
          savedAt: new Date().toISOString(),
        });
        totalSnapshots++;
      }

      if (simMonth === 12) {
        constChecks++;
        if (!checkConstitution()) { constFails++; issues.push(`[Y${simYear}] Constitution FAILED`); }
      }

      const p = governanceService.getPostureSnapshot().posture;
      postureDist[p] = (postureDist[p] ?? 0) + 1;

      if ((simYear % 10 === 0 && simMonth === 12) || month === 1) {
        memSamples.push({ month, ...snapMem(), nodes: fleet.size });
      }
    }

    recordEra(currentEra, eraStartNodes);

    expect(totalHb).toBeGreaterThan(100_000_000);
    expect(totalJoins).toBeGreaterThan(10_000);
    expect(totalUpgrades).toBeGreaterThan(5_000);
    expect(totalDcFailures).toBeGreaterThanOrEqual(10);
    expect(constFails).toBe(0);
    expect(fleet.size).toBeGreaterThan(1000);
  });

  test("Snapshot restore after 1,000 years", () => {
    const loaded = persistence.load();
    expect(loaded).not.toBeNull();
    expect(loaded!.mirrors.length).toBeGreaterThan(0);
  });

  test("HTTP endpoints responsive after 1,000 years", async () => {
    const [summary, nodes, constitution] = await Promise.all([
      request(app).get("/daedalus/cockpit/summary"),
      request(app).get("/daedalus/cockpit/nodes"),
      request(app).get("/daedalus/constitution"),
    ]);
    expect(summary.status).toBe(200);
    expect(summary.body.totalNodes).toBeGreaterThan(1000);
    expect(nodes.status).toBe(200);
    expect(constitution.status).toBe(200);
    expect(constitution.body.allPassed).toBe(true);
  });

  test("1,000-YEAR OPERATIONAL REPORT", () => {
    const first = memSamples[0];
    const last = memSamples[memSamples.length - 1];
    const peakHeap = Math.max(...memSamples.map(s => s.heap));
    const peakNodes = Math.max(...memSamples.map(s => s.nodes));

    const report: string[] = [
      "",
      "╔═══════════════════════════════════════════════════════════════════════════╗",
      "║         DAEDALUS 1,000-YEAR OPERATIONAL SIMULATION — FINAL REPORT       ║",
      "╚═══════════════════════════════════════════════════════════════════════════╝",
      "",
      "┌─ SCALE ─────────────────────────────────────────────────────────────────┐",
      `│  Duration:     1,000 years (12,000 months)`,
      `│  Heartbeats:   ${totalHb.toLocaleString()}`,
      `│  Node joins:   ${totalJoins.toLocaleString()}`,
      `│  Node detaches:${totalDetaches.toLocaleString()}`,
      `│  Quarantines:  ${totalQuarantines.toLocaleString()}`,
      `│  Errors:       ${totalErrors.toLocaleString()}`,
      `│  HW upgrades:  ${totalUpgrades.toLocaleString()}`,
      `│  Cap syncs:    ${totalCapSyncs.toLocaleString()}`,
      `│  DC failures:  ${totalDcFailures}`,
      `│  Incidents:    ${totalIncidents}`,
      `│  Snapshots:    ${totalSnapshots}`,
      `│  Constitution: ${constChecks} checks, ${constFails} failures`,
      `│  HW gens used: 100 (mk1 through mk100)`,
      "└─────────────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ ERA BREAKDOWN ─────────────────────────────────────────────────────────┐",
      ...eraSummaries,
      "└─────────────────────────────────────────────────────────────────────────┘",
      "",
      "┌─ MEMORY TREND (every ~10 years) ────────────────────────────────────────┐",
    ];

    for (const s of memSamples) {
      const yr = Math.ceil(s.month / 12);
      report.push(`│  Y${String(yr).padStart(4)}: heap=${String(s.heap).padStart(7)}MB  rss=${String(s.rss).padStart(7)}MB  nodes=${String(s.nodes).padStart(4)}`);
    }
    report.push(`│  Peak heap: ${peakHeap}MB  |  Peak nodes: ${peakNodes}`);
    report.push(`│  Heap M1→M12000: ${(last.heap - first.heap).toFixed(1)}MB`);
    report.push("└─────────────────────────────────────────────────────────────────────────┘");

    report.push("");
    report.push("┌─ GOVERNANCE POSTURE (across 12,000 months) ───────────────────────────┐");
    for (const [p, c] of Object.entries(postureDist).sort((a, b) => b[1] - a[1])) {
      report.push(`│  ${p.padEnd(10)} ${String(c).padStart(5)} months (${Math.round(c / 12000 * 100)}%)`);
    }
    report.push("└─────────────────────────────────────────────────────────────────────────┘");

    report.push("");
    report.push("┌─ FINAL FLEET (Year 1000) ──────────────────────────────────────────────┐");
    report.push(`│  Total: ${fleet.size} nodes`);
    const gd = genDist();
    const topGens = Object.entries(gd).sort((a, b) => b[1] - a[1]).slice(0, 5);
    report.push(`│  Top gens: ${topGens.map(([g, c]) => `Gen${g}:${c}`).join("  ")}`);
    report.push(`│  By kind: ${JSON.stringify(kindDist())}`);
    report.push("└─────────────────────────────────────────────────────────────────────────┘");

    if (issues.length > 0) {
      report.push("");
      report.push("┌─ ISSUES ───────────────────────────────────────────────────────────────┐");
      for (const i of issues) report.push(`│  ${i}`);
      report.push("└─────────────────────────────────────────────────────────────────────────┘");
    }

    const heapGrowth = last.heap - first.heap;
    const memOk = Math.abs(heapGrowth) < 800;
    const constOk = constFails === 0;
    const allOk = memOk && constOk && issues.length === 0;

    report.push("");
    report.push("┌─ VERDICT ──────────────────────────────────────────────────────────────┐");
    report.push(`│  Memory:       ${memOk ? "STABLE" : "GROWTH"} (${heapGrowth.toFixed(1)}MB over 1,000yr)`);
    report.push(`│  Constitution: ${constOk ? "CLEAN" : "FAILURES"} (${constChecks} checks)`);
    report.push(`│  Fleet:        ${fleet.size} nodes operational`);
    report.push(`│  Issues:       ${issues.length}`);
    report.push("│");
    if (allOk) {
      report.push("│  ╔══════════════════════════════════════════════════════════════════╗");
      report.push("│  ║  1,000-YEAR SIMULATION: PASSED — ALL SYSTEMS NOMINAL            ║");
      report.push("│  ╚══════════════════════════════════════════════════════════════════╝");
    } else {
      report.push("│  ╔══════════════════════════════════════════════════════════════════╗");
      report.push(`│  ║  1,000-YEAR SIMULATION: ${issues.length} ISSUE(S) — SEE ABOVE                     ║`);
      report.push("│  ╚══════════════════════════════════════════════════════════════════╝");
    }
    report.push("└─────────────────────────────────────────────────────────────────────────┘");

    console.log(report.join("\n"));

    expect(constFails).toBe(0);
    expect(Math.abs(heapGrowth)).toBeLessThan(800);
  });
});
