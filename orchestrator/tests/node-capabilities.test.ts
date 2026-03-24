import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { NodeCapabilityMap } from '../src/orchestrator/capabilities/NodeCapabilityMap.js';
import { createCapabilityRegistry } from '../src/orchestrator/capabilities/CapabilityRegistry.js';

function makeLogger() {
  return { info() {}, debug() {}, warn() {}, error() {} } as any;
}

describe('NodeCapabilityMap', () => {
  it('sets and retrieves node capabilities', () => {
    const map = new NodeCapabilityMap({ logger: makeLogger() });
    map.set('n1', { expressive: true, notifications: false });

    const state = map.get('n1');
    assert.ok(state);
    assert.equal(state!.nodeId, 'n1');
    assert.equal(state!.capabilities.expressive, true);
    assert.equal(state!.capabilities.notifications, false);
  });

  it('returns undefined for unknown node', () => {
    const map = new NodeCapabilityMap({ logger: makeLogger() });
    assert.equal(map.get('ghost'), undefined);
  });

  it('lists all node states', () => {
    const map = new NodeCapabilityMap({ logger: makeLogger() });
    map.set('n1', { expressive: true });
    map.set('n2', { notifications: false });

    const list = map.list();
    assert.equal(list.length, 2);
    assert.deepEqual(list.map((s) => s.nodeId).sort(), ['n1', 'n2']);
  });

  it('overwrites existing node state on re-set', () => {
    const map = new NodeCapabilityMap({ logger: makeLogger() });
    map.set('n1', { expressive: true });
    map.set('n1', { expressive: false });

    assert.equal(map.get('n1')!.capabilities.expressive, false);
    assert.equal(map.list().length, 1);
  });

  it('applies profile capabilities and merges with existing', () => {
    const map = new NodeCapabilityMap({ logger: makeLogger() });
    map.set('n1', { expressive: true, risk: true });

    const state = map.applyProfile('n1', { notifications: true, expressive: false });
    assert.equal(state.capabilities.risk, true, 'preserves pre-existing');
    assert.equal(state.capabilities.notifications, true, 'adds new from profile');
    assert.equal(state.capabilities.expressive, false, 'overrides from profile');
  });

  it('applies profile to a node that has no prior state', () => {
    const map = new NodeCapabilityMap({ logger: makeLogger() });
    const state = map.applyProfile('new-node', { expressive: true });

    assert.equal(state.nodeId, 'new-node');
    assert.equal(state.capabilities.expressive, true);
  });
});

describe('Capability negotiation logic', () => {
  it('enables capability when all nodes agree', () => {
    const map = new NodeCapabilityMap({ logger: makeLogger() });
    map.set('n1', { expressive: true });
    map.set('n2', { expressive: true });

    const result: Record<string, boolean> = {};
    for (const node of map.list()) {
      for (const [cap, enabled] of Object.entries(node.capabilities)) {
        if (!(cap in result)) {
          result[cap] = enabled;
        } else if (!enabled) {
          result[cap] = false;
        }
      }
    }

    assert.equal(result.expressive, true);
  });

  it('disables capability when any node disagrees', () => {
    const map = new NodeCapabilityMap({ logger: makeLogger() });
    map.set('n1', { notifications: true });
    map.set('n2', { notifications: false });

    const result: Record<string, boolean> = {};
    for (const node of map.list()) {
      for (const [cap, enabled] of Object.entries(node.capabilities)) {
        if (!(cap in result)) {
          result[cap] = enabled;
        } else if (!enabled) {
          result[cap] = false;
        }
      }
    }

    assert.equal(result.notifications, false);
  });

  it('applies negotiated result to the global registry', () => {
    const logger = makeLogger();
    const registry = createCapabilityRegistry({ logger });
    const map = new NodeCapabilityMap({ logger });

    map.set('n1', { expressive: true, notifications: true });
    map.set('n2', { expressive: true, notifications: false });

    for (const node of map.list()) {
      for (const [cap, enabled] of Object.entries(node.capabilities)) {
        if (!enabled) {
          registry.setEnabled(cap, false);
        }
      }
    }

    assert.equal(registry.isEnabled('expressive'), true);
    assert.equal(registry.isEnabled('notifications'), false);
  });
});
