import { TestClock, ITestClock } from './TestClock';
import { TestNetwork } from './TestNetwork';
import { OrchestratorStub } from './OrchestratorStub';
import { NodeSpawner, NodeHandle, NodeSpawnerConfig, NodeAgent, CreateAgentFn } from './NodeSpawner';
import type { NodeAgentConfig } from '../../../node-agent/src/NodeAgent.config';

export interface HarnessConfig {
  nodeSpawner?: Partial<NodeSpawnerConfig>;
  network?: {
    defaultLatencyMs?: number;
    packetLossProbability?: number;
  };
  clockEpoch?: number;
  createAgent: CreateAgentFn;
}

export class MultiNodeHarness {
  private clock: TestClock;
  private network: TestNetwork;
  private orchestrator: OrchestratorStub;
  private spawner: NodeSpawner;
  private nodes: Map<string, NodeHandle> = new Map();
  private started = false;

  constructor(private config: HarnessConfig) {
    this.clock = new TestClock(config.clockEpoch ?? 0);
    this.network = new TestNetwork(config.network ?? {}, () => this.clock.now());
    this.orchestrator = new OrchestratorStub(() => this.clock.now());
    this.spawner = new NodeSpawner(
      this.orchestrator,
      this.network,
      this.clock,
      config.nodeSpawner ?? {},
      config.createAgent,
    );
  }

  async start(): Promise<void> {
    if (this.started) return;
    this.started = true;
  }

  async stop(): Promise<void> {
    for (const node of this.nodes.values()) {
      await Promise.resolve(node.agent.stop());
      node.events.push({
        type: 'stopped',
        timestamp: this.clock.now(),
      });
    }
    this.nodes.clear();
    this.started = false;
  }

  async spawnNode(name: string, overrides: Partial<NodeAgentConfig> = {}): Promise<NodeHandle> {
    if (!this.started) {
      throw new Error('MultiNodeHarness.spawnNode: harness not started');
    }

    const id = overrides.nodeId ?? `node_${this.nodes.size + 1}`;

    const handle = await this.spawner.spawnNode(id, name, overrides);
    this.nodes.set(id, handle);
    return handle;
  }

  getOrchestrator(): OrchestratorStub {
    return this.orchestrator;
  }

  getClock(): TestClock {
    return this.clock;
  }

  getNetwork(): TestNetwork {
    return this.network;
  }

  getNode(id: string): NodeHandle | undefined {
    return this.nodes.get(id);
  }

  tick(ms: number): void {
    this.clock.advance(ms);
  }

  getNodes(): NodeHandle[] {
    return [...this.nodes.values()];
  }
}
