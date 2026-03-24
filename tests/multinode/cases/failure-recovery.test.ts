import { MultiNodeHarness } from '../harness/MultiNodeHarness';
import { assertNodeJoined } from '../utils/assertions';
import { createTestNodeAgent } from './testNodeAgentFactory';

describe('multi-node: failure & recovery', () => {
  it('handles network partition and rejoin with continuity', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const orchestrator = harness.getOrchestrator();
    const network = harness.getNetwork();
    const clock = harness.getClock();

    assertNodeJoined(node, orchestrator);

    network.partition([node.id]);

    clock.advance(10000);
    orchestrator.markOffline(node.id);

    expect(orchestrator.getNode(node.id)!.status).toBe('offline');

    network.heal();

    clock.advance(10000);
    await node.agent.sendHeartbeat();

    assertNodeJoined(node, orchestrator);
    expect(orchestrator.getNode(node.id)!.status).toBe('online');

    await harness.stop();
  });

  it('drops heartbeats while partitioned', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const orchestrator = harness.getOrchestrator();
    const network = harness.getNetwork();

    harness.tick(1000);
    await node.agent.sendHeartbeat();
    expect(orchestrator.getNode(node.id)!.status).toBe('online');

    const hbCountBefore = orchestrator.getEventsByType('node_heartbeat').length;

    network.partition([node.id]);

    harness.tick(5000);
    await node.agent.sendHeartbeat();
    await node.agent.sendHeartbeat();

    const hbCountAfter = orchestrator.getEventsByType('node_heartbeat').length;
    expect(hbCountAfter).toBe(hbCountBefore);

    await harness.stop();
  });

  it('recovers multiple nodes after global heal', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const a = await harness.spawnNode('alpha');
    const b = await harness.spawnNode('beta');
    const orchestrator = harness.getOrchestrator();
    const network = harness.getNetwork();

    network.partition([a.id, b.id]);
    orchestrator.markOffline(a.id);
    orchestrator.markOffline(b.id);

    expect(orchestrator.getNode(a.id)!.status).toBe('offline');
    expect(orchestrator.getNode(b.id)!.status).toBe('offline');

    network.heal();

    await a.agent.sendHeartbeat();
    await b.agent.sendHeartbeat();

    expect(orchestrator.getNode(a.id)!.status).toBe('online');
    expect(orchestrator.getNode(b.id)!.status).toBe('online');

    await harness.stop();
  });

  it('emits status_changed events for offline → online transitions', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const orchestrator = harness.getOrchestrator();
    const network = harness.getNetwork();

    network.partition([node.id]);
    orchestrator.markOffline(node.id);
    network.heal();
    await node.agent.sendHeartbeat();

    const statusEvents = orchestrator.getEventsByType('node_status_changed');
    const statuses = statusEvents.map(e => e.payload.status);
    expect(statuses).toContain('offline');
    expect(statuses).toContain('online');

    await harness.stop();
  });
});
