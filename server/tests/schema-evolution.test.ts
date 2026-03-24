import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { SnapshotPersistence } from "../orchestrator/persistence/SnapshotPersistence";
import {
  NodeMirrorRegistry,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload } from "../orchestrator/mirror";
import { GovernanceService } from "../orchestrator/governance/GovernanceService";
import { resetDaedalusEventBus } from "../orchestrator/DaedalusEventBus";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";
import { daedalusStore } from "../orchestrator/daedalusStore";

// ─── Helpers ──────────────────────────────────────────────────────────

function tmpFilePath(): string {
  return path.join(
    os.tmpdir(),
    `daedalus-test-${Date.now()}-${Math.random().toString(36).slice(2)}.json`,
  );
}

function cleanup(filePath: string) {
  try {
    fs.unlinkSync(filePath);
  } catch {}
}

function mkJoinPayload(id = "evo-node"): NodeJoinPayload {
  return {
    nodeId: id,
    name: `Node ${id}`,
    profile: {
      id,
      name: `Node ${id}`,
      kind: "server",
      model: "test",
      os: "linux",
      osVersion: "6.0",
      operatorId: "operator",
    },
    capabilities: [{ name: "core", value: "enabled", enabled: true }],
    expressive: { ...IDLE_EXPRESSIVE },
  };
}

function makeValidSnapshot() {
  return {
    beings: [
      {
        id: "operator",
        name: "Operator",
        posture: "companion",
        glow: { level: "high", intensity: 0.85 },
        attention: { level: "focused" },
        influenceLevel: 0.9,
        presenceMode: "active",
        continuity: { streak: 12, lastCheckIn: new Date().toISOString(), healthy: true },
      },
    ],
    overrides: [],
    drifts: [],
    votes: [],
    mirrors: [],
    savedAt: new Date().toISOString(),
  };
}

// ─── Snapshot Compatibility ───────────────────────────────────────────

describe("Snapshot compatibility", () => {
  let filePath: string;

  beforeEach(() => {
    filePath = tmpFilePath();
  });

  afterEach(() => {
    cleanup(filePath);
  });

  test("old snapshot without 'votes' field loads safely", () => {
    const snapshot = {
      beings: [{ id: "operator", name: "Op" }],
      overrides: [],
      drifts: [],
      mirrors: [],
      savedAt: new Date().toISOString(),
    };
    fs.writeFileSync(filePath, JSON.stringify(snapshot), "utf-8");

    const persistence = new SnapshotPersistence(filePath);
    const loaded = persistence.load();

    expect(loaded).not.toBeNull();
    expect(loaded!.beings).toHaveLength(1);
    expect((loaded as any).votes ?? []).toEqual([]);
  });

  test("old snapshot with unknown extra fields loads safely", () => {
    const snapshot = {
      ...makeValidSnapshot(),
      newField: true,
      futureConfig: { threshold: 42 },
    };
    fs.writeFileSync(filePath, JSON.stringify(snapshot), "utf-8");

    const persistence = new SnapshotPersistence(filePath);
    const loaded = persistence.load();

    expect(loaded).not.toBeNull();
    expect(loaded!.savedAt).toBeDefined();
    expect((loaded as any).newField).toBe(true);
  });

  test("empty snapshot file loads as null", () => {
    fs.writeFileSync(filePath, "", "utf-8");

    const persistence = new SnapshotPersistence(filePath);
    const loaded = persistence.load();
    expect(loaded).toBeNull();
  });

  test("null values in snapshot arrays are tolerated", () => {
    const snapshot = {
      beings: [null, { id: "operator", name: "Op" }],
      overrides: [],
      drifts: [],
      votes: [],
      mirrors: [null],
      savedAt: new Date().toISOString(),
    };
    fs.writeFileSync(filePath, JSON.stringify(snapshot), "utf-8");

    const persistence = new SnapshotPersistence(filePath);
    const loaded = persistence.load();

    expect(loaded).not.toBeNull();
    expect(loaded!.beings).toHaveLength(2);
  });
});

// ─── Mirror Payload Evolution ─────────────────────────────────────────

describe("Mirror payload evolution", () => {
  let reg: NodeMirrorRegistry;

  beforeEach(() => {
    resetDaedalusEventBus();
    reg = new NodeMirrorRegistry();
  });

  test("join with extra fields in profile: no crash", () => {
    const payload = {
      ...mkJoinPayload("extra-node"),
      profile: {
        ...mkJoinPayload("extra-node").profile,
        futureField: "hello",
        nestedExtra: { x: 1 },
      } as any,
    };

    const mirror = reg.handleJoin(payload);
    expect(mirror.id).toBe("extra-node");
    expect(mirror.lifecycle.phase).toBe("active");
  });

  test("heartbeat with missing timestamp: defaults gracefully", () => {
    reg.handleJoin(mkJoinPayload("hb-node"));

    const result = reg.handleHeartbeat({
      nodeId: "hb-node",
      status: "alive",
    } as any);

    expect(result).not.toBeNull();
    expect(result!.lifecycle.heartbeatCount).toBe(1);
  });

  test("cap sync with empty entries: no crash", () => {
    reg.handleJoin(mkJoinPayload("cap-node"));

    const deltas = reg.handleCapSync({
      nodeId: "cap-node",
      capabilities: [],
      timestamp: new Date().toISOString(),
    });

    expect(Array.isArray(deltas)).toBe(true);
  });
});

// ─── Governance Payload Evolution ─────────────────────────────────────

describe("Governance payload evolution", () => {
  let gov: GovernanceService;

  beforeEach(() => {
    resetDaedalusEventBus();
    gov = new GovernanceService();
  });

  test("override with extra field: accepted", () => {
    const override = gov.applyOverride({
      createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
      reason: "Test",
      scope: "NODE",
      targetId: "n1",
      effect: "ALLOW",
      futureFlag: true,
    } as any);

    expect(override.id).toBeDefined();
    expect(override.reason).toBe("Test");
    expect((override as any).futureFlag).toBe(true);
  });

  test("drift with missing optional fields: accepted", () => {
    const drift = gov.recordDrift({
      severity: "LOW",
      summary: "Minimal drift",
    });

    expect(drift.id).toBeDefined();
    expect(drift.severity).toBe("LOW");
    expect(drift.detectedAt).toBeDefined();
  });

  test("vote with fractional weight: accepted", () => {
    const vote = gov.castVote({
      being: { id: "operator", role: "OPERATOR", label: "Operator" },
      vote: "ALLOW",
      weight: 0.333,
    });

    expect(vote.weight).toBe(0.333);

    const votes = gov.listVotes();
    expect(votes).toHaveLength(1);
    expect(votes[0].weight).toBeCloseTo(0.333, 5);
  });
});

// ─── Constitution Forward Compatibility ───────────────────────────────

describe("Constitution forward compatibility", () => {
  test("constitution check with extra being fields: still passes", () => {
    const beings = daedalusStore.getBeingPresences().map((b) => ({
      ...b,
      futureField: "extra",
      newScore: 42,
    }));

    const report = validateBeingConstitution(beings as any);
    expect(report.allPassed).toBe(true);
  });

  test("constitution check with minimal being: crashes on missing attention (known limitation)", () => {
    const minimal = [
      { id: "operator", name: "Op" } as any,
    ];

    expect(() => validateBeingConstitution(minimal)).toThrow();
  });

  test("constitution check with complete-but-sparse being: passes gracefully", () => {
    const sparse = [
      {
        id: "operator",
        name: "Op",
        posture: "companion",
        glow: { level: "medium", intensity: 0.5 },
        attention: { level: "aware" },
        heartbeat: Date.now(),
        influenceLevel: 0.5,
        presenceMode: "active",
        isSpeaking: false,
        isGuiding: false,
        continuity: { streak: 0, lastCheckIn: new Date().toISOString(), healthy: true },
        autopilot: { enabled: false, scope: "none" },
        updatedAt: new Date().toISOString(),
      } as any,
    ];

    const report = validateBeingConstitution(sparse);
    expect(report.allPassed).toBe(true);
  });
});
