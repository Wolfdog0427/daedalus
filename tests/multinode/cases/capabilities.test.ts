import { MultiNodeHarness } from '../harness/MultiNodeHarness';
import { assertCapabilitiesSynced } from '../utils/assertions';
import { makeCapabilities } from '../utils/fixtures';
import { createTestNodeAgent } from './testNodeAgentFactory';

describe('multi-node: capabilities', () => {
  it('syncs capabilities to orchestrator mirror', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const orchestrator = harness.getOrchestrator();

    node.capabilities['daedalus.core'] = true;
    node.capabilities['daedalus.expressive'] = true;
    node.capabilities['test.feature'] = 'enabled';

    await node.agent.syncCapabilities();
    orchestrator.recordCapabilities(node.id, node.capabilities);

    assertCapabilitiesSynced(node, orchestrator);

    await harness.stop();
  });

  it('merges capability updates without overwriting existing keys', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const orchestrator = harness.getOrchestrator();

    orchestrator.recordCapabilities(node.id, { 'cap.one': true });
    orchestrator.recordCapabilities(node.id, { 'cap.two': true });

    const mirror = orchestrator.getNode(node.id)!;
    expect(mirror.capabilities['cap.one']).toBe(true);
    expect(mirror.capabilities['cap.two']).toBe(true);

    await harness.stop();
  });

  it('emits a capabilities_updated event on sync', async () => {
    const harness = new MultiNodeHarness({
      createAgent: createTestNodeAgent,
    });

    await harness.start();

    const node = await harness.spawnNode('alpha');
    const orchestrator = harness.getOrchestrator();

    orchestrator.recordCapabilities(node.id, makeCapabilities());

    const capEvents = orchestrator.getEventsByType('node_capabilities_updated');
    expect(capEvents.length).toBeGreaterThanOrEqual(1);
    expect(capEvents.some(e => e.nodeId === node.id)).toBe(true);

    await harness.stop();
  });
});
