import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { RiskEngine } from '../src/orchestrator/risk/RiskEngine.js';

function makeDeps() {
  return {
    logger: { info() {}, debug() {}, warn() {}, error() {} },
    stateStore: {} as any,
    eventBus: {} as any,
  } as any;
}

describe('RiskEngine', () => {
  it('defaults to low risk', () => {
    const engine = new RiskEngine(makeDeps());
    assert.equal(engine.getSnapshot().tier, 'low');
  });

  it('classifies elevated when posture is defensive', () => {
    const engine = new RiskEngine(makeDeps());
    engine.assess({
      posture: { mode: 'defensive', lastChangedAt: null },
      nodeCount: 1,
      recentEventCount: 0,
    });
    assert.equal(engine.getSnapshot().tier, 'elevated');
    assert.ok(engine.getSnapshot().factors.includes('posture:defensive'));
  });

  it('classifies medium when posture is elevated', () => {
    const engine = new RiskEngine(makeDeps());
    engine.assess({
      posture: { mode: 'elevated', lastChangedAt: null },
      nodeCount: 1,
      recentEventCount: 0,
    });
    assert.equal(engine.getSnapshot().tier, 'medium');
  });

  it('classifies medium when no nodes registered', () => {
    const engine = new RiskEngine(makeDeps());
    engine.assess({
      posture: { mode: 'normal', lastChangedAt: null },
      nodeCount: 0,
      recentEventCount: 0,
    });
    assert.equal(engine.getSnapshot().tier, 'medium');
    assert.ok(engine.getSnapshot().factors.includes('no_nodes_registered'));
  });

  it('classifies medium on high event volume', () => {
    const engine = new RiskEngine(makeDeps());
    engine.assess({
      posture: { mode: 'normal', lastChangedAt: null },
      nodeCount: 1,
      recentEventCount: 150,
    });
    assert.equal(engine.getSnapshot().tier, 'medium');
    assert.ok(engine.getSnapshot().factors.includes('high_event_volume'));
  });

  it('accumulates multiple factors', () => {
    const engine = new RiskEngine(makeDeps());
    engine.assess({
      posture: { mode: 'defensive', lastChangedAt: null },
      nodeCount: 0,
      recentEventCount: 200,
    });
    assert.equal(engine.getSnapshot().tier, 'elevated');
    assert.equal(engine.getSnapshot().factors.length, 3);
  });
});
