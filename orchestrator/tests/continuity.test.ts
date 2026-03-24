import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { ContinuityEngine } from '../src/orchestrator/continuity/ContinuityEngine.js';

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

describe('ContinuityEngine', () => {
  it('records timeline entries for all events', () => {
    const engine = new ContinuityEngine(makeDeps());
    engine.onEvent({ type: 'some.event', payload: {} }, ctx);
    engine.onEvent({ type: 'another.event', payload: {} }, ctx);

    const snap = engine.getTimelineSnapshot();
    assert.equal(snap.entries.length, 2);
    assert.equal(snap.entries[0].type, 'some.event');
    assert.equal(snap.entries[1].type, 'another.event');
  });

  it('tracks conversation threads', () => {
    const engine = new ContinuityEngine(makeDeps());
    engine.onEvent({
      type: 'conversation.message',
      payload: { id: 'm1', role: 'user', content: 'hello', threadId: 't1' },
    }, ctx);

    const snap = engine.getSnapshot();
    assert.ok(snap.threads['t1']);
    assert.equal(snap.threads['t1'].messages.length, 1);
    assert.equal(snap.threads['t1'].messages[0].role, 'user');
  });

  it('includes thread IDs in timeline snapshot', () => {
    const engine = new ContinuityEngine(makeDeps());
    engine.onEvent({
      type: 'conversation.message',
      payload: { id: 'm1', role: 'user', content: 'hi', threadId: 'thread-a' },
    }, ctx);

    const snap = engine.getTimelineSnapshot();
    assert.ok(snap.threadIds.includes('thread-a'));
  });

  it('summarizes known event types', () => {
    const engine = new ContinuityEngine(makeDeps());
    engine.onEvent({
      type: 'node.joined',
      payload: { id: 'node-1' },
    }, ctx);

    const entry = engine.getTimelineSnapshot().entries[0];
    assert.equal(entry.summary, 'node joined: node-1');
  });

  it('caps timeline at max entries', () => {
    const engine = new ContinuityEngine(makeDeps());
    for (let i = 0; i < 250; i++) {
      engine.onEvent({ type: 'tick', payload: { i } }, ctx);
    }
    assert.equal(engine.getTimelineSnapshot().entries.length, 200);
  });
});
