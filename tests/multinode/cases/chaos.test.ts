import { MultiNodeHarness } from "../harness/MultiNodeHarness";
import { createTestNodeAgent } from "./testNodeAgentFactory";
import { runChaosScenario, runChaosMixedScenario } from "../harness/ChaosScenarios";
import { assertNodeJoined } from "../utils/assertions";

function makeHarness() {
  return new MultiNodeHarness({ createAgent: createTestNodeAgent });
}

describe("multi-node: chaos mode", () => {
  // ── Basic stability ────────────────────────────────────────────

  it("maintains overall stability under random partitions and packet loss", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runChaosScenario(harness, {
      nodeCount: 20,
      durationMs: 2 * 60 * 1000,
    });

    const orchestrator = harness.getOrchestrator();

    for (const node of result.nodes) {
      assertNodeJoined(node, orchestrator);
    }

    expect(result.droppedHeartbeats).toBeGreaterThan(0);
    expect(result.totalSteps).toBeGreaterThan(50);

    await harness.stop();
  }, 30_000);

  // ── Full recovery ──────────────────────────────────────────────

  it("recovers all nodes to online after chaos ends", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runChaosScenario(harness, {
      nodeCount: 30,
      durationMs: 60_000,
      chaos: {
        randomPacketLossProbability: 0.2,
        randomPartitionProbability: 0.1,
      },
    });

    const orchestrator = harness.getOrchestrator();

    const onlineCount = result.nodes.filter(
      n => orchestrator.getNode(n.id)!.status === "online",
    ).length;
    expect(onlineCount).toBe(30);

    await harness.stop();
  }, 30_000);

  // ── Scale under chaos ──────────────────────────────────────────

  it("handles 100 nodes under sustained chaos", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runChaosScenario(harness, {
      nodeCount: 100,
      durationMs: 60_000,
      chaos: {
        randomPacketLossProbability: 0.08,
        randomPartitionProbability: 0.03,
      },
    });

    const orchestrator = harness.getOrchestrator();

    for (const node of result.nodes) {
      assertNodeJoined(node, orchestrator);
    }

    const onlineCount = result.nodes.filter(
      n => orchestrator.getNode(n.id)!.status === "online",
    ).length;
    expect(onlineCount).toBe(100);

    expect(result.droppedHeartbeats).toBeGreaterThan(0);

    await harness.stop();
  }, 30_000);

  // ── Bounded error accumulation ─────────────────────────────────

  it("does not accumulate unbounded errors in orchestrator", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runChaosScenario(harness, {
      nodeCount: 50,
      durationMs: 2 * 60 * 1000,
      chaos: {
        randomPacketLossProbability: 0.15,
        randomPartitionProbability: 0.05,
      },
    });

    const orchestrator = harness.getOrchestrator();

    const totalEvents = orchestrator.events.length;
    const maxExpected = result.totalHeartbeats * 3;
    expect(totalEvents).toBeLessThan(maxExpected);

    const statusChanges = orchestrator.getEventsByType("node_status_changed");
    const changesPerNode = new Map<string, number>();
    for (const e of statusChanges) {
      changesPerNode.set(e.nodeId, (changesPerNode.get(e.nodeId) ?? 0) + 1);
    }
    for (const [, count] of changesPerNode) {
      expect(count).toBeLessThan(result.totalSteps);
    }

    await harness.stop();
  }, 30_000);

  // ── Mixed ops under chaos ──────────────────────────────────────

  it("handles mixed heartbeat + caps + expressive under chaos", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runChaosMixedScenario(harness, {
      nodeCount: 30,
      durationMs: 60_000,
      capSyncProbability: 0.2,
      expressiveSyncProbability: 0.2,
      chaos: {
        randomPacketLossProbability: 0.1,
        randomPartitionProbability: 0.05,
      },
    });

    const orchestrator = harness.getOrchestrator();

    for (const node of result.nodes) {
      assertNodeJoined(node, orchestrator);
    }

    const onlineCount = result.nodes.filter(
      n => orchestrator.getNode(n.id)!.status === "online",
    ).length;
    expect(onlineCount).toBe(30);

    expect(result.droppedHeartbeats).toBeGreaterThan(0);

    await harness.stop();
  }, 30_000);

  // ── No deadlocks or hangs ──────────────────────────────────────

  it("completes chaos scenario without hanging under extreme loss", async () => {
    const harness = makeHarness();
    await harness.start();

    const result = await runChaosScenario(harness, {
      nodeCount: 20,
      durationMs: 30_000,
      chaos: {
        randomPacketLossProbability: 0.5,
        randomPartitionProbability: 0.2,
      },
    });

    expect(result.totalSteps).toBeGreaterThan(10);

    const orchestrator = harness.getOrchestrator();
    const onlineCount = result.nodes.filter(
      n => orchestrator.getNode(n.id)!.status === "online",
    ).length;
    expect(onlineCount).toBe(20);

    await harness.stop();
  }, 30_000);

  // ── Chaos toggle mid-run ───────────────────────────────────────

  it("transitions cleanly between chaos and calm phases", async () => {
    const harness = makeHarness();
    await harness.start();

    const nodes = [];
    for (let i = 0; i < 20; i++) {
      nodes.push(await harness.spawnNode(`toggle_${i + 1}`));
    }

    const network = harness.getNetwork();
    const clock = harness.getClock();
    const orchestrator = harness.getOrchestrator();

    // Phase 1: calm
    for (let step = 0; step < 20; step++) {
      clock.advance(500);
      await Promise.all(nodes.map(n => Promise.resolve(n.agent.sendHeartbeat())));
    }

    const calmHb = orchestrator.getEventsByType("node_heartbeat").length;

    // Phase 2: chaos
    network.enableChaos({
      randomPacketLossProbability: 0.3,
      randomPartitionProbability: 0.1,
    });

    for (let step = 0; step < 40; step++) {
      clock.advance(500);
      await Promise.all(nodes.map(n => Promise.resolve(n.agent.sendHeartbeat())));
    }

    const chaosHb = orchestrator.getEventsByType("node_heartbeat").length - calmHb;

    // Phase 3: calm again + recovery
    network.disableChaos();
    network.heal();

    for (let step = 0; step < 20; step++) {
      clock.advance(500);
      await Promise.all(nodes.map(n => Promise.resolve(n.agent.sendHeartbeat())));
    }

    const recoveryHb =
      orchestrator.getEventsByType("node_heartbeat").length - calmHb - chaosHb;

    // Calm phases deliver all heartbeats; chaos delivers fewer
    expect(calmHb).toBe(20 * 20);
    expect(chaosHb).toBeLessThan(40 * 20);
    expect(recoveryHb).toBe(20 * 20);

    const onlineCount = nodes.filter(
      n => orchestrator.getNode(n.id)!.status === "online",
    ).length;
    expect(onlineCount).toBe(20);

    await harness.stop();
  }, 30_000);
});
