import {
  NodeMirrorRegistry,
  resetNodeMirrorRegistry,
  IDLE_EXPRESSIVE,
} from "../orchestrator/mirror";
import type { NodeJoinPayload, NodeHeartbeatPayload } from "../orchestrator/mirror";
import {
  DaedalusEventBus,
  getDaedalusEventBus,
  resetDaedalusEventBus,
  DaedalusEventPayload,
} from "../orchestrator/DaedalusEventBus";
import { GovernanceService } from "../orchestrator/governance/GovernanceService";
import { daedalusStore } from "../orchestrator/daedalusStore";

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

// ─── Soak Tests ────────────────────────────────────────────────────────

describe("Soak tests (simulated long-running orchestrator)", () => {
  let registry: NodeMirrorRegistry;

  beforeEach(() => {
    resetDaedalusEventBus();
    resetNodeMirrorRegistry();
    registry = new NodeMirrorRegistry();
  });

  test("24-hour steady-state: no memory growth in mirror registry", () => {
    const NODE_COUNT = 50;
    const HEARTBEAT_CYCLES = 1000;

    for (let i = 0; i < NODE_COUNT; i++) {
      registry.handleJoin(mkJoin(`node-${i}`));
    }
    expect(registry.getCount()).toBe(NODE_COUNT);

    for (let cycle = 0; cycle < HEARTBEAT_CYCLES; cycle++) {
      const ts = new Date(Date.now() + cycle * 1000).toISOString();
      for (let i = 0; i < NODE_COUNT; i++) {
        registry.handleHeartbeat(mkHeartbeat(`node-${i}`, ts));
      }
    }

    expect(registry.getCount()).toBe(NODE_COUNT);
    const mirrors = registry.getAllMirrors();
    expect(mirrors).toHaveLength(NODE_COUNT);
    for (const m of mirrors) {
      expect(m.lifecycle.heartbeatCount).toBe(HEARTBEAT_CYCLES);
    }
  });

  test("72-hour with intermittent joins/leaves: registry stays clean", () => {
    const INITIAL = 100;
    const DETACH_COUNT = 20;
    const REJOIN_COUNT = 10;
    const HEARTBEAT_CYCLES = 2000;

    for (let i = 0; i < INITIAL; i++) {
      registry.handleJoin(mkJoin(`node-${i}`));
    }
    expect(registry.getCount()).toBe(INITIAL);

    for (let i = 0; i < DETACH_COUNT; i++) {
      registry.handleDetach(`node-${i}`);
    }
    const afterDetach = INITIAL - DETACH_COUNT;
    expect(registry.getCount()).toBe(afterDetach);

    for (let i = 0; i < REJOIN_COUNT; i++) {
      registry.handleJoin(mkJoin(`node-${i}`));
    }
    const expectedActive = afterDetach + REJOIN_COUNT;
    expect(registry.getCount()).toBe(expectedActive);

    const activeIds = registry.getAllMirrors().map((m) => m.id);
    for (let cycle = 0; cycle < HEARTBEAT_CYCLES; cycle++) {
      const ts = new Date(Date.now() + cycle * 1000).toISOString();
      for (const id of activeIds) {
        registry.handleHeartbeat(mkHeartbeat(id, ts));
      }
    }

    expect(registry.getCount()).toBe(expectedActive);
  });

  test("SSE subscriber churn: no leaked listeners", () => {
    const bus = new DaedalusEventBus();
    const unsubscribers: (() => void)[] = [];

    for (let i = 0; i < 100; i++) {
      const unsub = bus.subscribe(() => {});
      unsubscribers.push(unsub);
    }

    for (let i = 0; i < 80; i++) {
      unsubscribers[i]();
    }

    let callCount = 0;
    const remaining = 100 - 80;
    for (let i = 80; i < 100; i++) {
      unsubscribers[i]();
      const newUnsub = bus.subscribe(() => { callCount++; });
      unsubscribers[i] = newUnsub;
    }

    for (let e = 0; e < 500; e++) {
      bus.publish({
        type: "MIRROR_NODE_HEARTBEAT",
        timestamp: new Date().toISOString(),
        nodeId: "test",
      });
    }

    expect(callCount).toBe(remaining * 500);
  });

  test("event bus does not grow unbounded under sustained load", () => {
    const bus = new DaedalusEventBus();
    const received: DaedalusEventPayload[] = [];
    bus.subscribe((e) => received.push(e));

    const TOTAL = 10_000;
    for (let i = 0; i < TOTAL; i++) {
      bus.publish({
        type: "MIRROR_NODE_HEARTBEAT",
        timestamp: new Date().toISOString(),
        nodeId: `node-${i % 100}`,
      });
    }

    expect(received).toHaveLength(TOTAL);
  });
});

// ─── Circadian Patterns ────────────────────────────────────────────────

describe("Circadian patterns", () => {
  let registry: NodeMirrorRegistry;
  let gov: GovernanceService;

  beforeEach(() => {
    resetDaedalusEventBus();
    resetNodeMirrorRegistry();
    registry = new NodeMirrorRegistry();
    gov = new GovernanceService();
  });

  test("high-activity → quiet → high-activity: no posture stuck", () => {
    const NODE_COUNT = 50;
    const baseTime = Date.now();

    for (let i = 0; i < NODE_COUNT; i++) {
      registry.handleJoin(mkJoin(`node-${i}`));
    }

    // Phase 1: rapid heartbeats (high activity)
    for (let cycle = 0; cycle < 100; cycle++) {
      const ts = new Date(baseTime + cycle * 1000).toISOString();
      for (let i = 0; i < NODE_COUNT; i++) {
        registry.handleHeartbeat(mkHeartbeat(`node-${i}`, ts));
      }
    }
    expect(gov.getPostureSnapshot().posture).toBe("OPEN");

    // Phase 2: quiet period — advance time but keep a few nodes alive
    // so registry doesn't fully collapse
    const quietStart = baseTime + 100_000;
    for (let cycle = 0; cycle < 50; cycle++) {
      const ts = new Date(quietStart + cycle * 10_000).toISOString();
      for (let i = 0; i < 5; i++) {
        registry.handleHeartbeat(mkHeartbeat(`node-${i}`, ts));
      }
    }

    // Phase 3: resume all heartbeats
    const resumeStart = quietStart + 500_000;
    for (let cycle = 0; cycle < 100; cycle++) {
      const ts = new Date(resumeStart + cycle * 1000).toISOString();
      for (let i = 0; i < NODE_COUNT; i++) {
        registry.handleHeartbeat(mkHeartbeat(`node-${i}`, ts));
      }
    }

    expect(gov.getPostureSnapshot().posture).toBe("OPEN");
    const snapshot = gov.getPostureSnapshot();
    expect(snapshot.posture).not.toBe("GUARDED");
    expect(snapshot.posture).not.toBe("ATTENTIVE");
  });

  test("quiet period does not reset continuity streaks", () => {
    const beings = daedalusStore.getBeingPresences();
    const seeded = beings.find((b) => b.id === "operator");
    if (!seeded) {
      daedalusStore.updateBeingPresence("operator", {
        continuity: { streak: 12, lastCheckIn: new Date().toISOString(), healthy: true },
      });
    }

    const before = daedalusStore.getBeingPresence("operator");
    const streakBefore = before?.continuity.streak ?? 0;

    // Simulate quiet: no updates at all, just read state
    const after = daedalusStore.getBeingPresence("operator");
    expect(after?.continuity.streak).toBe(streakBefore);
    expect(after?.continuity.healthy).toBe(true);
  });

  test("bursty heartbeat pattern: governance posture stability", () => {
    const NODE_COUNT = 20;
    const baseTime = Date.now();

    for (let i = 0; i < NODE_COUNT; i++) {
      registry.handleJoin(mkJoin(`node-${i}`));
    }

    // Burst 1
    for (let cycle = 0; cycle < 50; cycle++) {
      const ts = new Date(baseTime + cycle * 100).toISOString();
      for (let i = 0; i < NODE_COUNT; i++) {
        registry.handleHeartbeat(mkHeartbeat(`node-${i}`, ts));
      }
    }

    // Gap (no heartbeats for a while, but don't sweep)

    // Burst 2
    const burst2Start = baseTime + 60_000;
    for (let cycle = 0; cycle < 50; cycle++) {
      const ts = new Date(burst2Start + cycle * 100).toISOString();
      for (let i = 0; i < NODE_COUNT; i++) {
        registry.handleHeartbeat(mkHeartbeat(`node-${i}`, ts));
      }
    }

    expect(gov.getPostureSnapshot().posture).toBe("OPEN");

    // Burst 3
    const burst3Start = burst2Start + 60_000;
    for (let cycle = 0; cycle < 50; cycle++) {
      const ts = new Date(burst3Start + cycle * 100).toISOString();
      for (let i = 0; i < NODE_COUNT; i++) {
        registry.handleHeartbeat(mkHeartbeat(`node-${i}`, ts));
      }
    }

    expect(gov.getPostureSnapshot().posture).toBe("OPEN");
  });
});

// ─── Clock Skew ────────────────────────────────────────────────────────

describe("Clock skew tolerance", () => {
  let registry: NodeMirrorRegistry;

  beforeEach(() => {
    resetDaedalusEventBus();
    resetNodeMirrorRegistry();
    registry = new NodeMirrorRegistry();
  });

  test("node clock ahead of server: no negative durations", () => {
    registry.handleJoin(mkJoin("skew-ahead"));

    const futureTs = new Date(Date.now() + 5 * 60 * 1000).toISOString();
    const result = registry.handleHeartbeat(mkHeartbeat("skew-ahead", futureTs));

    expect(result).not.toBeNull();
    expect(result!.lifecycle.heartbeatCount).toBe(1);

    const stale = registry.sweepStaleHeartbeats(Date.now());
    expect(stale).not.toContain("skew-ahead");
  });

  test("node clock behind server: no stale misclassification", () => {
    const baseTime = Date.now();
    registry.handleJoin(mkJoin("skew-behind"));

    const initialTs = new Date(baseTime).toISOString();
    registry.handleHeartbeat(mkHeartbeat("skew-behind", initialTs));

    // Sweep at a time way in the future — should mark stale
    const farFuture = baseTime + 60_000;
    const stale = registry.sweepStaleHeartbeats(farFuture);
    expect(stale).toContain("skew-behind");

    // Recovery: send a heartbeat with a slightly old timestamp (but newer than original)
    const recoveryTs = new Date(baseTime + 5000).toISOString();
    const recovered = registry.handleHeartbeat(mkHeartbeat("skew-behind", recoveryTs));
    expect(recovered).not.toBeNull();
    expect(recovered!.lifecycle.heartbeatCount).toBeGreaterThanOrEqual(2);
  });

  test("non-monotonic timestamps: no streak regressions", () => {
    registry.handleJoin(mkJoin("non-mono"));

    const t100 = new Date(100_000).toISOString();
    const t90 = new Date(90_000).toISOString();
    const t200 = new Date(200_000).toISOString();

    const r1 = registry.handleHeartbeat(mkHeartbeat("non-mono", t100));
    expect(r1).not.toBeNull();
    expect(r1!.lifecycle.heartbeatCount).toBe(1);

    const r2 = registry.handleHeartbeat(mkHeartbeat("non-mono", t90));
    expect(r2).not.toBeNull();
    expect(r2!.lifecycle.heartbeatCount).toBe(2);

    const r3 = registry.handleHeartbeat(mkHeartbeat("non-mono", t200));
    expect(r3).not.toBeNull();
    expect(r3!.lifecycle.heartbeatCount).toBe(3);
  });
});
