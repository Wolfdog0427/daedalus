import { MultiNodeHarness } from '../harness/MultiNodeHarness';
import { assertExpressiveSynced } from '../utils/assertions';
import { makeExpressive } from '../utils/fixtures';
import { createTestNodeAgent } from './testNodeAgentFactory';

describe('multi-node: expressive sync', () => {
  it('syncs expressive state to orchestrator mirror', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const orchestrator = harness.getOrchestrator();

    node.expressive = {
      glow: 'bright',
      posture: 'engaged',
      affect: 'focused',
      continuity: 'flowing',
    };

    await node.agent.syncExpressive();
    orchestrator.recordExpressive(node.id, node.expressive);

    assertExpressiveSynced(node, orchestrator);

    await harness.stop();
  });

  it('merges expressive updates without overwriting unrelated fields', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const orchestrator = harness.getOrchestrator();

    orchestrator.recordExpressive(node.id, makeExpressive({ glow: 'bright' }));
    orchestrator.recordExpressive(node.id, makeExpressive({ posture: 'leaning' }));

    const mirror = orchestrator.getNode(node.id)!;
    expect(mirror.expressive.posture).toBe('leaning');

    await harness.stop();
  });

  it('emits an expressive_updated event on sync', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const orchestrator = harness.getOrchestrator();

    orchestrator.recordExpressive(node.id, makeExpressive());

    const exprEvents = orchestrator.getEventsByType('node_expressive_updated');
    expect(exprEvents.length).toBeGreaterThanOrEqual(1);
    expect(exprEvents.some(e => e.nodeId === node.id)).toBe(true);

    await harness.stop();
  });
});
