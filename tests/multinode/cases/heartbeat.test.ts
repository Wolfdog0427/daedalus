import { MultiNodeHarness } from '../harness/MultiNodeHarness';
import { assertHeartbeatStable } from '../utils/assertions';
import { createTestNodeAgent } from './testNodeAgentFactory';

describe('multi-node: heartbeat', () => {
  it('tracks heartbeats and marks node online', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const clock = harness.getClock();

    for (let i = 0; i < 5; i++) {
      clock.advance(5000);
      await node.agent.sendHeartbeat();
      node.events.push({
        type: 'heartbeat_sent',
        timestamp: clock.now(),
      });
    }

    assertHeartbeatStable(node);

    const mirror = harness.getOrchestrator().getNode(node.id);
    expect(mirror!.status).toBe('online');

    await harness.stop();
  });

  it('records monotonically increasing heartbeat timestamps', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const clock = harness.getClock();
    const orchestrator = harness.getOrchestrator();

    for (let i = 0; i < 5; i++) {
      clock.advance(3000);
      await node.agent.sendHeartbeat();
      node.events.push({
        type: 'heartbeat_sent',
        timestamp: clock.now(),
      });
    }

    const hbEvents = orchestrator.getEventsByType('node_heartbeat');
    for (let i = 1; i < hbEvents.length; i++) {
      expect(hbEvents[i].timestamp).toBeGreaterThan(hbEvents[i - 1].timestamp);
    }

    await harness.stop();
  });

  it('transitions status from joining to online on first heartbeat', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const orchestrator = harness.getOrchestrator();

    expect(orchestrator.getNode(node.id)!.status).toBe('joining');

    harness.tick(1000);
    await node.agent.sendHeartbeat();

    expect(orchestrator.getNode(node.id)!.status).toBe('online');

    await harness.stop();
  });
});
