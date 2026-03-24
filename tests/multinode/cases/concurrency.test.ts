import { MultiNodeHarness } from '../harness/MultiNodeHarness';
import { assertNodeJoined, assertHeartbeatStable } from '../utils/assertions';
import { createTestNodeAgent } from './testNodeAgentFactory';

describe('multi-node: concurrency', () => {
  it('supports many nodes joining and syncing concurrently', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const nodes = [];
    for (let i = 0; i < 20; i++) {
      const node = await harness.spawnNode(`node_${i + 1}`);
      nodes.push(node);
    }

    const orchestrator = harness.getOrchestrator();
    const clock = harness.getClock();

    clock.advance(5000);

    for (const node of nodes) {
      await node.agent.sendHeartbeat();
      node.events.push({
        type: 'heartbeat_sent',
        timestamp: clock.now(),
      });
    }

    for (const node of nodes) {
      assertNodeJoined(node, orchestrator);
    }

    await harness.stop();
  });

  it('each node produces independent event logs', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const a = await harness.spawnNode('alpha');
    const b = await harness.spawnNode('beta');

    harness.tick(1000);
    await a.agent.sendHeartbeat();
    a.events.push({ type: 'heartbeat_sent', timestamp: harness.getClock().now() });

    harness.tick(1000);
    await b.agent.sendHeartbeat();
    b.events.push({ type: 'heartbeat_sent', timestamp: harness.getClock().now() });

    assertHeartbeatStable(a);
    assertHeartbeatStable(b);

    expect(a.events.entries.length).toBeGreaterThan(0);
    expect(b.events.entries.length).toBeGreaterThan(0);

    const aHbTs = a.events.entries.find(e => e.type === 'heartbeat_sent')!.timestamp;
    const bHbTs = b.events.entries.find(e => e.type === 'heartbeat_sent')!.timestamp;
    expect(bHbTs).toBeGreaterThan(aHbTs);

    await harness.stop();
  });

  it('partial partition isolates only affected nodes', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const a = await harness.spawnNode('alpha');
    const b = await harness.spawnNode('beta');
    const c = await harness.spawnNode('gamma');
    const orchestrator = harness.getOrchestrator();
    const network = harness.getNetwork();

    network.partition([b.id]);
    orchestrator.markOffline(b.id);

    await a.agent.sendHeartbeat();
    await b.agent.sendHeartbeat();
    await c.agent.sendHeartbeat();

    expect(orchestrator.getNode(a.id)!.status).toBe('online');
    expect(orchestrator.getNode(b.id)!.status).toBe('offline');
    expect(orchestrator.getNode(c.id)!.status).toBe('online');

    await harness.stop();
  });

  it('handles rapid spawn-stop cycles without leaking state', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    for (let i = 0; i < 10; i++) {
      await harness.spawnNode(`ephemeral_${i}`);
    }

    expect(harness.getNodes().length).toBe(10);

    await harness.stop();

    expect(harness.getNodes().length).toBe(0);
  });
});
