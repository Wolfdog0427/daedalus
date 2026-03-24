import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { PresenceEngine } from '../src/orchestrator/presence/PresenceEngine.js';

function makeDeps() {
  return {
    logger: { info() {}, debug() {}, warn() {}, error() {} },
    stateStore: { applyEvent() {}, getSnapshot() { return { events: [], audit: [], config: {}, nodes: {}, memory: {}, shards: {} }; } },
    eventBus: { publish() {}, subscribe() { return { unsubscribe() {} }; } },
  } as any;
}

const ctx = {
  systemContext: {} as any,
  operatorContext: {} as any,
};

describe('PresenceEngine', () => {
  it('registers a node on node.joined', () => {
    const engine = new PresenceEngine(makeDeps());
    engine.onEvent({ type: 'node.joined', payload: { id: 'n1', capabilities: ['echo'] } }, ctx);

    const snap = engine.getNodeRegistrySnapshot();
    assert.equal(snap.count, 1);
    assert.equal(snap.nodes['n1'].id, 'n1');
    assert.deepEqual(snap.nodes['n1'].capabilities, ['echo']);
  });

  it('updates heartbeat timestamp', () => {
    const engine = new PresenceEngine(makeDeps());
    engine.onEvent({ type: 'node.joined', payload: { id: 'n1', capabilities: [] } }, ctx);
    const first = engine.getNodeRegistrySnapshot().nodes['n1'].lastHeartbeat;

    engine.onEvent({ type: 'node.heartbeat', payload: { id: 'n1' } }, ctx);
    const second = engine.getNodeRegistrySnapshot().nodes['n1'].lastHeartbeat;

    assert.ok(second >= first);
  });

  it('updates capabilities via node.capabilities event', () => {
    const engine = new PresenceEngine(makeDeps());
    engine.onEvent({ type: 'node.joined', payload: { id: 'n1', capabilities: [] } }, ctx);
    engine.onEvent({ type: 'node.capabilities', payload: { id: 'n1', capabilities: ['risk', 'shard'] } }, ctx);

    const caps = engine.getNodeRegistrySnapshot().nodes['n1'].capabilities;
    assert.deepEqual(caps, ['risk', 'shard']);
  });

  it('updates capabilities inline with heartbeat', () => {
    const engine = new PresenceEngine(makeDeps());
    engine.onEvent({ type: 'node.joined', payload: { id: 'n1', capabilities: ['a'] } }, ctx);
    engine.onEvent({ type: 'node.heartbeat', payload: { id: 'n1', capabilities: ['a', 'b'] } }, ctx);

    const caps = engine.getNodeRegistrySnapshot().nodes['n1'].capabilities;
    assert.deepEqual(caps, ['a', 'b']);
  });

  it('ignores heartbeat for unknown node', () => {
    const engine = new PresenceEngine(makeDeps());
    engine.onEvent({ type: 'node.heartbeat', payload: { id: 'unknown' } }, ctx);
    assert.equal(engine.getNodeRegistrySnapshot().count, 0);
  });

  it('tracks beings and sessions via presence snapshot', () => {
    const engine = new PresenceEngine(makeDeps());
    engine.onEvent({ type: 'being.registered', payload: { id: 'b1' } }, ctx);
    engine.onEvent({ type: 'session.started', payload: { id: 's1' } }, ctx);

    const snap = engine.getSnapshot();
    assert.ok(snap.beings['b1']);
    assert.ok(snap.sessions['s1']);
  });
});
