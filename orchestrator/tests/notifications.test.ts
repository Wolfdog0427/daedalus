import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { NotificationEngine } from '../src/orchestrator/notifications/NotificationEngine.js';

function makeDeps() {
  const published: any[] = [];
  return {
    deps: {
      logger: { info() {}, debug() {}, warn() {}, error() {} },
      eventBus: {
        publish(e: any) { published.push(e); },
        subscribe() { return { unsubscribe() {} }; },
      },
    } as any,
    published,
  };
}

describe('NotificationEngine', () => {
  it('sends a notification with UUID and timestamp', () => {
    const { deps } = makeDeps();
    const engine = new NotificationEngine(deps);
    const n = engine.send('test', { msg: 'hello' });

    assert.ok(n.id);
    assert.equal(n.type, 'test');
    assert.ok(n.timestamp);
  });

  it('lists all sent notifications', () => {
    const { deps } = makeDeps();
    const engine = new NotificationEngine(deps);
    engine.send('a', {});
    engine.send('b', {});

    assert.equal(engine.list().length, 2);
  });

  it('returns recent notifications', () => {
    const { deps } = makeDeps();
    const engine = new NotificationEngine(deps);
    engine.send('a', {});
    engine.send('b', {});
    engine.send('c', {});

    assert.equal(engine.recent(2).length, 2);
    assert.equal(engine.recent(2)[1].type, 'c');
  });

  it('publishes notification.sent event on the bus', () => {
    const { deps, published } = makeDeps();
    const engine = new NotificationEngine(deps);
    engine.send('alert', { level: 'high' });

    assert.equal(published.length, 1);
    assert.equal(published[0].type, 'notification.sent');
  });

  it('auto-notifies on posture.changed event', () => {
    const { deps } = makeDeps();
    const engine = new NotificationEngine(deps);
    engine.onEvent({ type: 'posture.changed', payload: { mode: 'defensive', reason: 'risk' } });

    const list = engine.list();
    assert.equal(list.length, 1);
    assert.equal(list[0].type, 'posture_shift');
  });

  it('caps at max notifications', () => {
    const { deps } = makeDeps();
    const engine = new NotificationEngine(deps);
    for (let i = 0; i < 120; i++) {
      engine.send('tick', { i });
    }
    assert.equal(engine.list().length, 100);
  });
});
