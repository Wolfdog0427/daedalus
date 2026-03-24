import { MultiNodeHarness } from "../harness/MultiNodeHarness";
import { createTestNodeAgent } from "./testNodeAgentFactory";
import {
  runLoadScenario,
  runPartitionChurnScenario,
  runMixedOpsScenario,
} from "../harness/LoadScenarios";
import { assertNodeJoined, assertHeartbeatStable } from "../utils/assertions";

function makeHarness() {
  return new MultiNodeHarness({ createAgent: createTestNodeAgent });
}

describe("multi-node: load scenarios", () => {
  // ── Sustained heartbeat ──────────────────────────────────────────

  it("handles 100 nodes under sustained heartbeat load", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runLoadScenario(harness, {
      nodeCount: 100,
      maxJoinSkewMs: 5000,
      heartbeatIntervalMs: 5000,
      durationMs: 5 * 60 * 1000,
    });

    const orchestrator = harness.getOrchestrator();
    for (const node of result.nodes) {
      assertNodeJoined(node, orchestrator);
    }

    expect(result.totalHeartbeats).toBeGreaterThan(0);
    expect(result.totalSteps).toBeGreaterThan(100);

    for (const node of result.nodes) {
      assertHeartbeatStable(node);
    }

    const onlineCount = result.nodes.filter(
      n => orchestrator.getNode(n.id)!.status === "online",
    ).length;
    expect(onlineCount).toBe(100);

    await harness.stop();
  }, 30_000);

  it("handles 250 nodes in a short burst", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runLoadScenario(harness, {
      nodeCount: 250,
      maxJoinSkewMs: 2000,
      heartbeatIntervalMs: 5000,
      durationMs: 30_000,
    });

    const orchestrator = harness.getOrchestrator();
    for (const node of result.nodes) {
      assertNodeJoined(node, orchestrator);
    }

    expect(result.nodes.length).toBe(250);
    expect(result.totalSteps).toBeGreaterThan(10);

    await harness.stop();
  }, 30_000);

  it("handles 500 nodes in a rapid join wave", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runLoadScenario(harness, {
      nodeCount: 500,
      maxJoinSkewMs: 1000,
      heartbeatIntervalMs: 10000,
      durationMs: 10_000,
    });

    const orchestrator = harness.getOrchestrator();
    for (const node of result.nodes) {
      assertNodeJoined(node, orchestrator);
    }

    expect(result.nodes.length).toBe(500);

    await harness.stop();
  }, 60_000);

  // ── Partition churn ──────────────────────────────────────────────

  it("survives partition churn across 100 nodes", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runPartitionChurnScenario(harness, {
      nodeCount: 100,
      maxJoinSkewMs: 3000,
      heartbeatIntervalMs: 5000,
      durationMs: 2 * 60 * 1000,
      partitionProbability: 0.15,
      partitionSizeFraction: 0.1,
      healEveryNSteps: 20,
    });

    const orchestrator = harness.getOrchestrator();

    for (const node of result.nodes) {
      assertNodeJoined(node, orchestrator);
    }

    const onlineCount = result.nodes.filter(
      n => orchestrator.getNode(n.id)!.status === "online",
    ).length;
    expect(onlineCount).toBe(100);

    const statusEvents = orchestrator.getEventsByType("node_status_changed");
    expect(statusEvents.length).toBeGreaterThan(0);

    await harness.stop();
  }, 30_000);

  it("survives heavy partition churn across 250 nodes", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runPartitionChurnScenario(harness, {
      nodeCount: 250,
      maxJoinSkewMs: 2000,
      heartbeatIntervalMs: 5000,
      durationMs: 30_000,
      partitionProbability: 0.2,
      partitionSizeFraction: 0.15,
      healEveryNSteps: 10,
    });

    const orchestrator = harness.getOrchestrator();

    for (const node of result.nodes) {
      assertNodeJoined(node, orchestrator);
    }

    expect(result.nodes.length).toBe(250);

    await harness.stop();
  }, 30_000);

  // ── Mixed operations ─────────────────────────────────────────────

  it("handles mixed heartbeat + caps + expressive ops for 100 nodes", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runMixedOpsScenario(harness, {
      nodeCount: 100,
      maxJoinSkewMs: 3000,
      heartbeatIntervalMs: 5000,
      durationMs: 2 * 60 * 1000,
      capSyncProbability: 0.3,
      expressiveSyncProbability: 0.3,
    });

    const orchestrator = harness.getOrchestrator();

    for (const node of result.nodes) {
      assertNodeJoined(node, orchestrator);
    }

    const capEvents = orchestrator.getEventsByType("node_capabilities_updated");
    expect(capEvents.length).toBeGreaterThan(0);

    const exprEvents = orchestrator.getEventsByType("node_expressive_updated");
    expect(exprEvents.length).toBeGreaterThan(0);

    const onlineCount = result.nodes.filter(
      n => orchestrator.getNode(n.id)!.status === "online",
    ).length;
    expect(onlineCount).toBe(100);

    await harness.stop();
  }, 30_000);

  // ── Consistency invariants ───────────────────────────────────────

  it("maintains orchestrator event ordering under load", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runLoadScenario(harness, {
      nodeCount: 50,
      maxJoinSkewMs: 2000,
      heartbeatIntervalMs: 5000,
      durationMs: 60_000,
    });

    const orchestrator = harness.getOrchestrator();
    const allEvents = orchestrator.events;

    for (let i = 1; i < allEvents.length; i++) {
      expect(allEvents[i].timestamp).toBeGreaterThanOrEqual(
        allEvents[i - 1].timestamp,
      );
    }

    const joinEvents = orchestrator.getEventsByType("node_joined");
    expect(joinEvents.length).toBe(50);

    const heartbeatEvents = orchestrator.getEventsByType("node_heartbeat");
    expect(heartbeatEvents.length).toBe(result.totalHeartbeats);

    await harness.stop();
  }, 30_000);

  it("no duplicate node IDs under load", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runLoadScenario(harness, {
      nodeCount: 200,
      maxJoinSkewMs: 1000,
      heartbeatIntervalMs: 5000,
      durationMs: 10_000,
    });

    const ids = result.nodes.map(n => n.id);
    expect(new Set(ids).size).toBe(ids.length);

    await harness.stop();
  }, 30_000);
});
