import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import {
  NodeMirrorRegistry,
  resetNodeMirrorRegistry,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload, NodeHeartbeatPayload } from "../orchestrator/mirror";
import {
  getDaedalusEventBus,
  resetDaedalusEventBus,
} from "../orchestrator/DaedalusEventBus";
import { GovernanceService } from "../orchestrator/governance/GovernanceService";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { SnapshotPersistence, PersistableSnapshot } from "../orchestrator/persistence/SnapshotPersistence";

function mkProfile(id: string) {
  return {
    id,
    name: `Node-${id}`,
    kind: "mobile" as const,
    model: "TestDevice",
    os: "android",
    osVersion: "15",
    operatorId: "op-test",
  };
}

function mkJoin(id: string): NodeJoinPayload {
  return {
    nodeId: id,
    name: `Test Node ${id}`,
    profile: mkProfile(id),
    capabilities: [
      { name: "vision", value: "enabled", enabled: true },
      { name: "audio", value: "enabled", enabled: true },
    ],
    expressive: { ...IDLE_EXPRESSIVE },
  };
}

function mkHeartbeat(id: string, timestamp?: string): NodeHeartbeatPayload {
  return {
    nodeId: id,
    timestamp: timestamp ?? new Date().toISOString(),
    status: "alive",
  };
}

function tmpFilePath(name: string): string {
  return path.join(os.tmpdir(), `daedalus-test-${name}-${Date.now()}.json`);
}

function cleanupFile(filePath: string): void {
  try { fs.unlinkSync(filePath); } catch {}
}

// ─── Persistence Recovery ──────────────────────────────────────────────

describe("Process-level failures (persistence recovery)", () => {
  const tempFiles: string[] = [];

  afterEach(() => {
    for (const f of tempFiles) cleanupFile(f);
    tempFiles.length = 0;
  });

  test("persistence save/load round-trip preserves beings", () => {
    const filePath = tmpFilePath("beings-roundtrip");
    tempFiles.push(filePath);

    const beings = daedalusStore.getBeingPresences();
    const snapshot: PersistableSnapshot = {
      beings,
      overrides: [],
      drifts: [],
      votes: [],
      mirrors: [],
      savedAt: new Date().toISOString(),
    };

    const writer = new SnapshotPersistence(filePath);
    writer.save(snapshot);

    const reader = new SnapshotPersistence(filePath);
    const loaded = reader.load();

    expect(loaded).not.toBeNull();
    expect(loaded!.beings).toEqual(beings);
    expect(loaded!.savedAt).toBe(snapshot.savedAt);
  });

  test("persistence save/load preserves governance state", () => {
    const filePath = tmpFilePath("governance-roundtrip");
    tempFiles.push(filePath);

    const gov = new GovernanceService();
    const override = gov.applyOverride({
      createdBy: { id: "op", role: "OPERATOR", label: "Operator" },
      reason: "test",
      scope: "NODE",
      targetId: "n1",
      effect: "DENY",
    });
    const drift = gov.recordDrift({ severity: "MEDIUM", summary: "test drift" });
    const vote = gov.castVote({
      being: { id: "op", role: "OPERATOR", label: "Operator" },
      vote: "ALLOW",
      weight: 1,
    });

    const snapshot: PersistableSnapshot = {
      beings: [],
      overrides: gov.listOverrides(),
      drifts: gov.listDrifts(),
      votes: gov.listVotes(),
      mirrors: [],
      savedAt: new Date().toISOString(),
    };

    const writer = new SnapshotPersistence(filePath);
    writer.save(snapshot);

    const reader = new SnapshotPersistence(filePath);
    const loaded = reader.load();

    expect(loaded).not.toBeNull();
    expect(loaded!.overrides).toHaveLength(1);
    expect(loaded!.overrides[0].id).toBe(override.id);
    expect(loaded!.drifts).toHaveLength(1);
    expect(loaded!.drifts[0].id).toBe(drift.id);
    expect(loaded!.votes).toHaveLength(1);
    expect(loaded!.votes[0].being.id).toBe(vote.being.id);
  });

  test("persistence handles corrupt JSON gracefully", () => {
    const filePath = tmpFilePath("corrupt");
    tempFiles.push(filePath);

    fs.writeFileSync(filePath, "{{not valid json!!", "utf-8");

    const reader = new SnapshotPersistence(filePath);
    const loaded = reader.load();

    expect(loaded).toBeNull();
  });

  test("persistence handles missing file gracefully", () => {
    const filePath = path.join(os.tmpdir(), `daedalus-nonexistent-${Date.now()}.json`);

    const reader = new SnapshotPersistence(filePath);
    const loaded = reader.load();

    expect(loaded).toBeNull();
  });
});

// ─── Partial Failures ──────────────────────────────────────────────────

describe("Partial failures", () => {
  let registry: NodeMirrorRegistry;

  beforeEach(() => {
    resetDaedalusEventBus();
    resetNodeMirrorRegistry();
    registry = new NodeMirrorRegistry();
  });

  test("stale sweep on short outage: doesn't overreact", () => {
    const NODE_COUNT = 10;
    const baseTime = Date.now();

    for (let i = 0; i < NODE_COUNT; i++) {
      registry.handleJoin(mkJoin(`node-${i}`));
      registry.handleHeartbeat(mkHeartbeat(`node-${i}`, new Date(baseTime).toISOString()));
    }

    // Advance 5s (well under the 30s default staleHeartbeatMs)
    const stale = registry.sweepStaleHeartbeats(baseTime + 5_000);
    expect(stale).toHaveLength(0);

    for (let i = 0; i < NODE_COUNT; i++) {
      const mirror = registry.getMirror(`node-${i}`);
      expect(mirror).toBeDefined();
      expect(mirror!.lifecycle.phase).toBe("active");
    }
  });

  test("stale sweep on medium outage: marks stale correctly", () => {
    const NODE_COUNT = 10;
    const baseTime = Date.now();

    for (let i = 0; i < NODE_COUNT; i++) {
      registry.handleJoin(mkJoin(`node-${i}`));
      registry.handleHeartbeat(mkHeartbeat(`node-${i}`, new Date(baseTime).toISOString()));
    }

    // Advance 35s (over the 30s default threshold)
    const stale = registry.sweepStaleHeartbeats(baseTime + 35_000);
    expect(stale).toHaveLength(NODE_COUNT);

    for (let i = 0; i < NODE_COUNT; i++) {
      const mirror = registry.getMirror(`node-${i}`);
      expect(mirror).toBeDefined();
      expect(mirror!.lifecycle.errorCount).toBeGreaterThanOrEqual(1);
    }
  });

  test("brief blip doesn't degrade continuity", () => {
    const being = daedalusStore.getBeingPresence("operator");
    if (being) {
      daedalusStore.updateBeingPresence("operator", {
        continuity: { streak: 10, lastCheckIn: new Date().toISOString(), healthy: true },
      });
    }

    // No updates for a while — just verify the state is unchanged
    const after = daedalusStore.getBeingPresence("operator");
    expect(after?.continuity.healthy).toBe(true);
    expect(after?.continuity.streak).toBe(10);
  });

  test("auto-quarantine requires sustained errors, not single flap", () => {
    registry.configureSafety({ errorQuarantineThreshold: 5 });
    registry.handleJoin(mkJoin("flappy"));

    // Send 4 errors (below threshold of 5)
    for (let i = 0; i < 4; i++) {
      registry.handleError("flappy", `error-${i}`);
    }

    let mirror = registry.getMirror("flappy");
    expect(mirror).toBeDefined();
    expect(mirror!.lifecycle.phase).not.toBe("quarantined");
    expect(mirror!.lifecycle.errorCount).toBe(4);

    // Successful heartbeat in between
    registry.handleHeartbeat(mkHeartbeat("flappy"));
    mirror = registry.getMirror("flappy");
    expect(mirror).toBeDefined();
    expect(mirror!.lifecycle.phase).not.toBe("quarantined");
  });
});

// ─── Network Partitions ────────────────────────────────────────────────

describe("Network partitions", () => {
  let registry: NodeMirrorRegistry;

  beforeEach(() => {
    resetDaedalusEventBus();
    resetNodeMirrorRegistry();
    registry = new NodeMirrorRegistry();
  });

  test("duplicate nodeId join after partition: last write wins", () => {
    registry.handleJoin(mkJoin("node-1"));
    registry.handleHeartbeat(mkHeartbeat("node-1"));

    const mirror1 = registry.getMirror("node-1");
    expect(mirror1).toBeDefined();
    expect(mirror1!.profile.model).toBe("TestDevice");

    // Partition detected → server detaches the stale node
    registry.handleDetach("node-1");
    expect(registry.getMirror("node-1")).toBeUndefined();

    // Node reconnects with updated profile
    const rejoinPayload: NodeJoinPayload = {
      nodeId: "node-1",
      name: "Rejoined Node",
      profile: {
        id: "node-1",
        name: "Node-1-v2",
        kind: "desktop",
        model: "NewDevice",
        os: "linux",
        osVersion: "6.0",
        operatorId: "op-test",
      },
      capabilities: [{ name: "llm", value: "enabled", enabled: true }],
      expressive: { ...IDLE_EXPRESSIVE },
    };

    registry.handleJoin(rejoinPayload);
    const mirror2 = registry.getMirror("node-1");
    expect(mirror2).toBeDefined();
    expect(mirror2!.profile.model).toBe("NewDevice");
    expect(mirror2!.profile.kind).toBe("desktop");
    expect(mirror2!.name).toBe("Rejoined Node");
  });

  test("heartbeat for non-existent node: returns null, no crash", () => {
    const result = registry.handleHeartbeat(mkHeartbeat("ghost-node"));
    expect(result).toBeNull();
    expect(registry.getCount()).toBe(0);
  });

  test("rapid partition/heal cycles: no zombie nodes", () => {
    const NODE_COUNT = 20;
    const PARTITIONED = 10;
    const baseTime = Date.now();

    for (let i = 0; i < NODE_COUNT; i++) {
      registry.handleJoin(mkJoin(`node-${i}`));
      registry.handleHeartbeat(mkHeartbeat(`node-${i}`, new Date(baseTime).toISOString()));
    }
    expect(registry.getCount()).toBe(NODE_COUNT);

    // Partition: only heartbeat the first half, sweep the rest
    // Use a threshold that won't quarantine — errorQuarantineThreshold high
    registry.configureSafety({ errorQuarantineThreshold: 100, staleHeartbeatMs: 10_000 });

    const partitionTime = baseTime + 15_000;
    for (let i = 0; i < PARTITIONED; i++) {
      registry.handleHeartbeat(mkHeartbeat(`node-${i}`, new Date(partitionTime).toISOString()));
    }

    const stale = registry.sweepStaleHeartbeats(partitionTime);
    expect(stale).toHaveLength(NODE_COUNT - PARTITIONED);

    // Heal: resume heartbeats for the "partitioned" nodes
    const healTime = partitionTime + 1000;
    for (let i = PARTITIONED; i < NODE_COUNT; i++) {
      registry.handleHeartbeat(mkHeartbeat(`node-${i}`, new Date(healTime).toISOString()));
    }

    expect(registry.getCount()).toBe(NODE_COUNT);
    for (let i = 0; i < NODE_COUNT; i++) {
      const mirror = registry.getMirror(`node-${i}`);
      expect(mirror).toBeDefined();
      expect(mirror!.lifecycle.phase).not.toBe("detached");
    }
  });
});
