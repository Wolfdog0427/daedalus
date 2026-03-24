import type { MultiNodeHarness } from "./MultiNodeHarness";
import type { NodeHandle } from "./NodeSpawner";
import type { ChaosConfig } from "./TestNetwork";
import { randomInt, randomChoice } from "../utils/random";

// ── Result ───────────────────────────────────────────────────────────

export interface ChaosResult {
  nodes: NodeHandle[];
  totalHeartbeats: number;
  droppedHeartbeats: number;
  totalSteps: number;
  elapsedSimMs: number;
}

// ── Config ───────────────────────────────────────────────────────────

export interface ChaosScenarioConfig {
  nodeCount: number;
  durationMs: number;
  chaos?: Partial<ChaosConfig>;
}

export interface ChaosMixedConfig extends ChaosScenarioConfig {
  capSyncProbability: number;
  expressiveSyncProbability: number;
}

// ── Defaults ─────────────────────────────────────────────────────────

const DEFAULT_CHAOS: ChaosConfig = {
  randomLatencyMaxMs: 2000,
  randomPacketLossProbability: 0.1,
  randomPartitionProbability: 0.05,
};

// ── Scenario 1: Chaos heartbeat ──────────────────────────────────────

export async function runChaosScenario(
  harness: MultiNodeHarness,
  config: ChaosScenarioConfig,
): Promise<ChaosResult> {
  const nodes: NodeHandle[] = [];

  for (let i = 0; i < config.nodeCount; i++) {
    const node = await harness.spawnNode(`chaos_${i + 1}`);
    nodes.push(node);
  }

  const network = harness.getNetwork();
  const clock = harness.getClock();
  const orchestrator = harness.getOrchestrator();

  network.enableChaos({ ...DEFAULT_CHAOS, ...config.chaos });

  let elapsed = 0;
  let totalHeartbeats = 0;
  let droppedHeartbeats = 0;
  let totalSteps = 0;

  while (elapsed < config.durationMs) {
    const step = randomInt(100, 1000);
    clock.advance(step);
    elapsed += step;
    totalSteps++;

    const beforeHbCount = orchestrator.getEventsByType("node_heartbeat").length;

    await Promise.all(
      nodes.map(node => Promise.resolve(node.agent.sendHeartbeat())),
    );
    totalHeartbeats += nodes.length;

    const afterHbCount = orchestrator.getEventsByType("node_heartbeat").length;
    droppedHeartbeats += nodes.length - (afterHbCount - beforeHbCount);

    const now = clock.now();
    for (const node of nodes) {
      node.events.push({ type: "heartbeat_sent", timestamp: now });
    }
  }

  // ── Recovery phase ─────────────────────────────────────────────
  network.disableChaos();
  network.heal();
  clock.advance(1000);

  await Promise.all(
    nodes.map(node => Promise.resolve(node.agent.sendHeartbeat())),
  );
  totalHeartbeats += nodes.length;

  return { nodes, totalHeartbeats, droppedHeartbeats, totalSteps, elapsedSimMs: elapsed };
}

// ── Scenario 2: Chaos + mixed operations ─────────────────────────────

export async function runChaosMixedScenario(
  harness: MultiNodeHarness,
  config: ChaosMixedConfig,
): Promise<ChaosResult> {
  const nodes: NodeHandle[] = [];

  for (let i = 0; i < config.nodeCount; i++) {
    const node = await harness.spawnNode(`chaosmix_${i + 1}`);
    nodes.push(node);
  }

  const network = harness.getNetwork();
  const clock = harness.getClock();
  const orchestrator = harness.getOrchestrator();

  network.enableChaos({ ...DEFAULT_CHAOS, ...config.chaos });

  const glows = ["baseline", "bright", "dim", "pulsing"];
  const postures = ["neutral", "engaged", "reclined", "leaning"];
  const affects = ["calm", "focused", "alert", "relaxed"];
  const continuities = ["fresh", "active", "flowing", "steady"];

  let elapsed = 0;
  let totalHeartbeats = 0;
  let droppedHeartbeats = 0;
  let totalSteps = 0;

  while (elapsed < config.durationMs) {
    const step = randomInt(100, 1000);
    clock.advance(step);
    elapsed += step;
    totalSteps++;

    const beforeHbCount = orchestrator.getEventsByType("node_heartbeat").length;

    await Promise.all(
      nodes.map(node => Promise.resolve(node.agent.sendHeartbeat())),
    );
    totalHeartbeats += nodes.length;

    const afterHbCount = orchestrator.getEventsByType("node_heartbeat").length;
    droppedHeartbeats += nodes.length - (afterHbCount - beforeHbCount);

    if (Math.random() < config.capSyncProbability) {
      const target = randomChoice(nodes);
      target.capabilities[`cap.chaos.${totalSteps}`] = true;
      await Promise.resolve(target.agent.syncCapabilities());
      if (!network.isBlocked(target.id)) {
        orchestrator.recordCapabilities(target.id, target.capabilities);
      }
    }

    if (Math.random() < config.expressiveSyncProbability) {
      const target = randomChoice(nodes);
      target.expressive = {
        glow: randomChoice(glows),
        posture: randomChoice(postures),
        affect: randomChoice(affects),
        continuity: randomChoice(continuities),
      };
      await Promise.resolve(target.agent.syncExpressive());
      if (!network.isBlocked(target.id)) {
        orchestrator.recordExpressive(target.id, target.expressive);
      }
    }
  }

  // ── Recovery phase ─────────────────────────────────────────────
  network.disableChaos();
  network.heal();
  clock.advance(1000);

  await Promise.all(
    nodes.map(node => Promise.resolve(node.agent.sendHeartbeat())),
  );
  totalHeartbeats += nodes.length;

  return { nodes, totalHeartbeats, droppedHeartbeats, totalSteps, elapsedSimMs: elapsed };
}
