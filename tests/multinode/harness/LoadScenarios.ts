import type { MultiNodeHarness } from "./MultiNodeHarness";
import type { NodeHandle } from "./NodeSpawner";
import { randomInt, randomSubset, randomChoice } from "../utils/random";

// ── Result ───────────────────────────────────────────────────────────

export interface LoadResult {
  nodes: NodeHandle[];
  totalHeartbeats: number;
  totalSteps: number;
  elapsedSimMs: number;
}

// ── Configs ──────────────────────────────────────────────────────────

export interface LoadScenarioConfig {
  nodeCount: number;
  maxJoinSkewMs: number;
  heartbeatIntervalMs: number;
  durationMs: number;
}

export interface PartitionChurnConfig extends LoadScenarioConfig {
  partitionProbability: number;
  partitionSizeFraction: number;
  healEveryNSteps: number;
}

export interface MixedOpsConfig extends LoadScenarioConfig {
  capSyncProbability: number;
  expressiveSyncProbability: number;
}

// ── Shared spawn helper ──────────────────────────────────────────────

async function spawnSwarm(
  harness: MultiNodeHarness,
  config: LoadScenarioConfig,
): Promise<NodeHandle[]> {
  const nodes: NodeHandle[] = [];
  const clock = harness.getClock();

  for (let i = 0; i < config.nodeCount; i++) {
    if (config.maxJoinSkewMs > 0 && i > 0) {
      const skew = randomInt(0, Math.floor(config.maxJoinSkewMs / config.nodeCount));
      clock.advance(skew);
    }

    const node = await harness.spawnNode(`load_${i + 1}`, {
      heartbeatIntervalMs: config.heartbeatIntervalMs,
    });
    nodes.push(node);
  }

  return nodes;
}

// ── Scenario 1: Sustained heartbeat ──────────────────────────────────

export async function runLoadScenario(
  harness: MultiNodeHarness,
  config: LoadScenarioConfig,
): Promise<LoadResult> {
  const nodes = await spawnSwarm(harness, config);
  const clock = harness.getClock();

  let elapsed = 0;
  let totalHeartbeats = 0;
  let totalSteps = 0;

  while (elapsed < config.durationMs) {
    const step = randomInt(100, 1000);
    clock.advance(step);
    elapsed += step;
    totalSteps++;

    await Promise.all(
      nodes.map(node => Promise.resolve(node.agent.sendHeartbeat())),
    );
    totalHeartbeats += nodes.length;

    const now = clock.now();
    for (const node of nodes) {
      node.events.push({ type: "heartbeat_sent", timestamp: now });
    }
  }

  return { nodes, totalHeartbeats, totalSteps, elapsedSimMs: elapsed };
}

// ── Scenario 2: Partition churn ──────────────────────────────────────

export async function runPartitionChurnScenario(
  harness: MultiNodeHarness,
  config: PartitionChurnConfig,
): Promise<LoadResult> {
  const nodes = await spawnSwarm(harness, config);
  const clock = harness.getClock();
  const network = harness.getNetwork();
  const orchestrator = harness.getOrchestrator();

  let elapsed = 0;
  let totalHeartbeats = 0;
  let totalSteps = 0;

  while (elapsed < config.durationMs) {
    const step = randomInt(100, 1000);
    clock.advance(step);
    elapsed += step;
    totalSteps++;

    if (Math.random() < config.partitionProbability) {
      const count = Math.max(1, Math.floor(nodes.length * config.partitionSizeFraction));
      const victims = randomSubset(nodes, count);
      network.partition(victims.map(n => n.id));
      for (const v of victims) {
        orchestrator.markOffline(v.id);
      }
    }

    if (totalSteps % config.healEveryNSteps === 0) {
      network.heal();
    }

    await Promise.all(
      nodes.map(node => Promise.resolve(node.agent.sendHeartbeat())),
    );
    totalHeartbeats += nodes.length;

    const now = clock.now();
    for (const node of nodes) {
      node.events.push({ type: "heartbeat_sent", timestamp: now });
    }
  }

  network.heal();

  await Promise.all(
    nodes.map(node => Promise.resolve(node.agent.sendHeartbeat())),
  );
  totalHeartbeats += nodes.length;

  return { nodes, totalHeartbeats, totalSteps, elapsedSimMs: elapsed };
}

// ── Scenario 3: Mixed operations ─────────────────────────────────────

export async function runMixedOpsScenario(
  harness: MultiNodeHarness,
  config: MixedOpsConfig,
): Promise<LoadResult> {
  const nodes = await spawnSwarm(harness, config);
  const clock = harness.getClock();
  const orchestrator = harness.getOrchestrator();

  let elapsed = 0;
  let totalHeartbeats = 0;
  let totalSteps = 0;

  const glows = ["baseline", "bright", "dim", "pulsing"];
  const postures = ["neutral", "engaged", "reclined", "leaning"];
  const affects = ["calm", "focused", "alert", "relaxed"];
  const continuities = ["fresh", "active", "flowing", "steady"];

  while (elapsed < config.durationMs) {
    const step = randomInt(100, 1000);
    clock.advance(step);
    elapsed += step;
    totalSteps++;

    await Promise.all(
      nodes.map(node => Promise.resolve(node.agent.sendHeartbeat())),
    );
    totalHeartbeats += nodes.length;

    if (Math.random() < config.capSyncProbability) {
      const target = randomChoice(nodes);
      target.capabilities[`cap.load.${totalSteps}`] = true;
      await Promise.resolve(target.agent.syncCapabilities());
      orchestrator.recordCapabilities(target.id, target.capabilities);
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
      orchestrator.recordExpressive(target.id, target.expressive);
    }
  }

  return { nodes, totalHeartbeats, totalSteps, elapsedSimMs: elapsed };
}
