import type { NodeAgentConfig } from '../../../node-agent/src/NodeAgent.config';
import { NodeAgent as RealNodeAgent } from '../../../node-agent/src/NodeAgent';
import type { NodeAgent } from '../harness/NodeSpawner';
import type { OrchestratorStub } from '../harness/OrchestratorStub';
import type { TestNetwork } from '../harness/TestNetwork';
import type { ITestClock } from '../harness/TestClock';
import { TestTransport } from '../harness/TestTransport';

/**
 * Adapter that wraps the real NodeAgent to conform to the harness's
 * NodeAgent interface. Two critical responsibilities:
 *
 * 1. After start(), immediately stops the auto-timers (heartbeat interval
 *    and expressive periodic sync) so tests control timing deterministically
 *    via TestClock rather than real setInterval ticks.
 *
 * 2. Bridges the async real agent methods to the harness's
 *    void | Promise<void> interface.
 */
class RealAgentAdapter implements NodeAgent {
  constructor(private readonly real: RealNodeAgent) {}

  async start(): Promise<void> {
    await this.real.start();
    this.real.lifecycle.stopHeartbeat();
    this.real.expressive.stopPeriodicSync();
  }

  stop(): void {
    this.real.stop();
  }

  async sendHeartbeat(): Promise<void> {
    await this.real.sendHeartbeat();
  }

  async syncCapabilities(): Promise<void> {
    await this.real.syncCapabilities();
  }

  async syncProfile(): Promise<void> {
    await this.real.syncProfile();
  }

  async syncExpressive(): Promise<void> {
    await this.real.syncExpressive();
  }
}

export function createTestNodeAgent(
  config: NodeAgentConfig,
  deps: {
    orchestrator: OrchestratorStub;
    network: TestNetwork;
    clock: ITestClock;
    log: { push: (entry: any) => void };
  },
): NodeAgent {
  const transport = new TestTransport(
    { nodeId: config.nodeId },
    { orchestrator: deps.orchestrator, network: deps.network },
  );

  const real = new RealNodeAgent(config, transport);
  return new RealAgentAdapter(real);
}
