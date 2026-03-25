import {
  NodeMirrorRegistry,
  getNodeMirrorRegistry,
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
import { daedalusStore } from "../orchestrator/daedalusStore";

function mkJoin(id: string, overrides?: any): NodeJoinPayload {
  return {
    nodeId: id,
    name: `Node ${id}`,
    profile: {
      id,
      name: `Node ${id}`,
      kind: "server",
      model: "test-model",
      os: "linux",
      osVersion: "6.1",
      operatorId: "op1",
    },
    capabilities: [
      { name: "vision", value: "enabled", enabled: true },
      { name: "audio", value: "disabled", enabled: false },
    ],
    expressive: { ...IDLE_EXPRESSIVE },
    ...overrides,
  };
}

function mkHeartbeat(id: string): NodeHeartbeatPayload {
  return { nodeId: id, timestamp: new Date().toISOString(), status: "alive" };
}

// ─── MAX NODE COUNT ─────────────────────────────────────────────────

describe("MAX NODE COUNT", () => {
  let reg: NodeMirrorRegistry;

  beforeEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    reg = new NodeMirrorRegistry();
  });

  test("1000 nodes: all join successfully", () => {
    for (let i = 0; i < 1000; i++) {
      reg.handleJoin(mkJoin(`n-${i}`));
    }
    expect(reg.getCount()).toBe(1000);
  });

  test("1000 nodes: heartbeat all, verify all active", () => {
    for (let i = 0; i < 1000; i++) {
      reg.handleJoin(mkJoin(`n-${i}`));
    }
    for (let i = 0; i < 1000; i++) {
      reg.handleHeartbeat(mkHeartbeat(`n-${i}`));
    }
    const mirrors = reg.getAllMirrors();
    for (const m of mirrors) {
      expect(m.lifecycle.heartbeatCount).toBeGreaterThan(0);
    }
  });

  test("1000 nodes: toCockpitView returns all", () => {
    for (let i = 0; i < 1000; i++) {
      reg.handleJoin(mkJoin(`n-${i}`));
    }
    const views = reg.toCockpitView();
    expect(views).toHaveLength(1000);
  });

  test("5000 nodes: join + heartbeat under 2 seconds", () => {
    const start = performance.now();
    for (let i = 0; i < 5000; i++) {
      reg.handleJoin(mkJoin(`n-${i}`));
    }
    for (let i = 0; i < 5000; i++) {
      reg.handleHeartbeat(mkHeartbeat(`n-${i}`));
    }
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(2000);
  });
});

// ─── MAX EVENT RATE ─────────────────────────────────────────────────

describe("MAX EVENT RATE", () => {
  let bus: DaedalusEventBus;

  beforeEach(() => {
    resetDaedalusEventBus();
    resetNodeMirrorRegistry();
    bus = new DaedalusEventBus();
  });

  test("10000 events published without error", () => {
    let counter = 0;
    bus.subscribe(() => { counter++; });

    for (let i = 0; i < 10000; i++) {
      bus.publish({
        type: "MIRROR_NODE_HEARTBEAT",
        timestamp: new Date().toISOString(),
        nodeId: `n-${i}`,
      });
    }
    expect(counter).toBe(10000);
  });

  test("1000 rapid heartbeats: no event loss", () => {
    resetDaedalusEventBus();
    const globalBus = getDaedalusEventBus();
    const received: DaedalusEventPayload[] = [];
    globalBus.subscribe((e) => received.push(e));

    const reg = getNodeMirrorRegistry();
    for (let i = 0; i < 10; i++) {
      reg.handleJoin(mkJoin(`n-${i}`));
    }

    const joinEventCount = received.length;

    for (let round = 0; round < 100; round++) {
      for (let i = 0; i < 10; i++) {
        reg.handleHeartbeat(mkHeartbeat(`n-${i}`));
      }
    }

    const heartbeatEvents = received
      .slice(joinEventCount)
      .filter((e) => e.type === "MIRROR_NODE_HEARTBEAT");
    expect(heartbeatEvents).toHaveLength(1000);
  });

  test("mixed event storm: heartbeats + cap syncs + expressive syncs", () => {
    resetDaedalusEventBus();
    const globalBus = getDaedalusEventBus();
    const received: DaedalusEventPayload[] = [];
    globalBus.subscribe((e) => received.push(e));

    const reg = getNodeMirrorRegistry();
    for (let i = 0; i < 20; i++) {
      reg.handleJoin(mkJoin(`n-${i}`));
    }

    const afterJoin = received.length;

    for (let i = 0; i < 20; i++) {
      reg.handleHeartbeat(mkHeartbeat(`n-${i}`));
      reg.handleCapSync({
        nodeId: `n-${i}`,
        capabilities: [{ name: "vision", value: "enabled", enabled: true }],
        timestamp: new Date().toISOString(),
      });
      reg.handleExpressiveSync({
        nodeId: `n-${i}`,
        expressive: { ...IDLE_EXPRESSIVE },
        timestamp: new Date().toISOString(),
      });
    }

    const eventSlice = received.slice(afterJoin);
    const heartbeats = eventSlice.filter((e) => e.type === "MIRROR_NODE_HEARTBEAT");
    const capSyncs = eventSlice.filter((e) => e.type === "MIRROR_NODE_CAP_SYNCED");
    const expSyncs = eventSlice.filter((e) => e.type === "MIRROR_NODE_EXPRESSIVE_SYNCED");

    expect(heartbeats).toHaveLength(20);
    expect(capSyncs).toHaveLength(20);
    expect(expSyncs).toHaveLength(20);
  });
});

// ─── COCKPIT PRESSURE ───────────────────────────────────────────────

describe("COCKPIT PRESSURE", () => {
  let reg: NodeMirrorRegistry;

  beforeEach(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    reg = new NodeMirrorRegistry();
  });

  test("toCockpitView with 1000 nodes completes under 100ms", () => {
    for (let i = 0; i < 1000; i++) {
      reg.handleJoin(mkJoin(`n-${i}`));
    }
    const start = performance.now();
    const views = reg.toCockpitView();
    const elapsed = performance.now() - start;
    expect(views).toHaveLength(1000);
    expect(elapsed).toBeLessThan(100);
  });

  test("getSnapshot with 1000 mirror nodes: returns valid JSON", () => {
    resetNodeMirrorRegistry();
    const singletonReg = getNodeMirrorRegistry();
    for (let i = 0; i < 1000; i++) {
      singletonReg.handleJoin(mkJoin(`n-${i}`));
    }
    const snapshot = daedalusStore.getSnapshot();
    expect(snapshot.nodes).toHaveLength(1000);
    expect(snapshot.beings).toBeDefined();
    expect(Array.isArray(snapshot.beings)).toBe(true);
    const json = JSON.stringify(snapshot);
    expect(() => JSON.parse(json)).not.toThrow();
  });
});
