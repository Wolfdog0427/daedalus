import { TestNetwork } from './TestNetwork';
import { OrchestratorStub, NodeMirror, CapabilityMap, ExpressiveState, NodeProfile } from './OrchestratorStub';
import { ITestClock } from './TestClock';
import type { NodeAgentConfig } from '../../../node-agent/src/NodeAgent.config';

export type { NodeAgentConfig };

/**
 * Harness contract for any node agent (real or stub).
 * Method return types use void | Promise<void> so both sync stubs
 * and the real async NodeAgent satisfy the interface structurally.
 */
export interface NodeAgent {
  start(): Promise<void>;
  stop(): void | Promise<void>;
  sendHeartbeat(): void | Promise<void>;
  syncCapabilities(): void | Promise<void>;
  syncProfile(): void | Promise<void>;
  syncExpressive(): void | Promise<void>;
}

export interface EventLogEntry {
  type:
    | 'started'
    | 'stopped'
    | 'heartbeat_sent'
    | 'capabilities_synced'
    | 'profile_synced'
    | 'expressive_synced';
  timestamp: number;
  payload?: any;
}

export interface EventLog {
  entries: EventLogEntry[];
  push(entry: EventLogEntry): void;
}

export class InMemoryEventLog implements EventLog {
  entries: EventLogEntry[] = [];

  push(entry: EventLogEntry): void {
    this.entries.push(entry);
  }
}

export interface NodeHandle {
  id: string;
  name: string;
  agent: NodeAgent;
  events: EventLog;
  profile: NodeProfile;
  capabilities: CapabilityMap;
  expressive: ExpressiveState;
}

export interface NodeSpawnerConfig {
  defaultHeartbeatIntervalMs: number;
  defaultExpressiveSyncIntervalMs: number;
}

export type CreateAgentFn = (
  config: NodeAgentConfig,
  deps: {
    orchestrator: OrchestratorStub;
    network: TestNetwork;
    clock: ITestClock;
    log: EventLog;
  },
) => NodeAgent;

export class NodeSpawner {
  private orchestrator: OrchestratorStub;
  private network: TestNetwork;
  private clock: ITestClock;
  private config: NodeSpawnerConfig;
  private createAgent: CreateAgentFn;

  constructor(
    orchestrator: OrchestratorStub,
    network: TestNetwork,
    clock: ITestClock,
    config: Partial<NodeSpawnerConfig>,
    createAgent: CreateAgentFn,
  ) {
    this.orchestrator = orchestrator;
    this.network = network;
    this.clock = clock;
    this.config = {
      defaultHeartbeatIntervalMs: config.defaultHeartbeatIntervalMs ?? 5000,
      defaultExpressiveSyncIntervalMs: config.defaultExpressiveSyncIntervalMs ?? 5000,
    };
    this.createAgent = createAgent;
  }

  async spawnNode(
    id: string,
    name: string,
    overrides: Partial<NodeAgentConfig> = {},
  ): Promise<NodeHandle> {
    const log = new InMemoryEventLog();

    const agentConfig: NodeAgentConfig = {
      nodeId: overrides.nodeId ?? id,
      nodeName: overrides.nodeName ?? name,
      kind: overrides.kind ?? 'server',
      model: overrides.model ?? 'test-harness',
      os: overrides.os ?? 'test-os',
      osVersion: overrides.osVersion ?? '1.0.0',
      operatorId: overrides.operatorId ?? 'test-operator',
      orchestratorUrl: overrides.orchestratorUrl ?? 'stub://orchestrator',
      heartbeatIntervalMs: overrides.heartbeatIntervalMs ?? this.config.defaultHeartbeatIntervalMs,
      expressiveSyncIntervalMs: overrides.expressiveSyncIntervalMs ?? this.config.defaultExpressiveSyncIntervalMs,
      capabilities: overrides.capabilities ?? [],
    };

    const agent = this.createAgent(agentConfig, {
      orchestrator: this.orchestrator,
      network: this.network,
      clock: this.clock,
      log,
    });

    const profile: NodeProfile = {
      name,
      kind: 'test-node',
      tags: [],
    };

    const capabilities: CapabilityMap = {};
    const expressive: ExpressiveState = {
      glow: 'baseline',
      posture: 'neutral',
      affect: 'calm',
      continuity: 'fresh',
    };

    const mirror: NodeMirror = {
      id,
      name,
      status: 'joining',
      capabilities,
      profile,
      expressive,
      lifecycle: {
        lastHeartbeatAt: null,
        joinedAt: this.clock.now(),
        status: 'joining',
      },
    };

    this.orchestrator.recordJoin(mirror);

    await agent.start();
    log.push({
      type: 'started',
      timestamp: this.clock.now(),
    });

    return {
      id,
      name,
      agent,
      events: log,
      profile,
      capabilities,
      expressive,
    };
  }
}
