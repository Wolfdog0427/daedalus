import { MultiNodeHarness } from '../harness/MultiNodeHarness';
import { assertNodeJoined } from '../utils/assertions';
import { createTestNodeAgent } from './testNodeAgentFactory';

describe('multi-node: join', () => {
  it('allows a single node to join and appear in orchestrator mirror', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');

    assertNodeJoined(node, harness.getOrchestrator());

    await harness.stop();
  });

  it('assigns unique ids to multiple nodes', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const a = await harness.spawnNode('alpha');
    const b = await harness.spawnNode('beta');
    const c = await harness.spawnNode('gamma');

    expect(new Set([a.id, b.id, c.id]).size).toBe(3);

    assertNodeJoined(a, harness.getOrchestrator());
    assertNodeJoined(b, harness.getOrchestrator());
    assertNodeJoined(c, harness.getOrchestrator());

    await harness.stop();
  });

  it('emits a node_joined event per node', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    await harness.spawnNode('alpha');
    await harness.spawnNode('beta');

    const joinEvents = harness.getOrchestrator().getEventsByType('node_joined');
    expect(joinEvents.length).toBe(2);

    await harness.stop();
  });

  it('records a started event in the node event log', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');

    const startedEvents = node.events.entries.filter(e => e.type === 'started');
    expect(startedEvents.length).toBeGreaterThanOrEqual(1);

    await harness.stop();
  });

  it('rejects spawnNode before harness start', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await expect(harness.spawnNode('alpha')).rejects.toThrow(
      'MultiNodeHarness.spawnNode: harness not started',
    );
  });
});
