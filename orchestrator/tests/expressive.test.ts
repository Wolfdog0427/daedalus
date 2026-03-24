import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { ExpressiveEngine } from '../src/orchestrator/expressive/ExpressiveEngine.js';

function makeDeps() {
  return { logger: { info() {}, debug() {}, warn() {}, error() {} } } as any;
}

describe('ExpressiveEngine', () => {
  it('defaults to calm glow', () => {
    const engine = new ExpressiveEngine(makeDeps());
    const snap = engine.getSnapshot();
    assert.equal(snap.label, 'calm');
    assert.equal(snap.hue, '#3fb950');
  });

  it('computes alert glow for defensive posture', () => {
    const engine = new ExpressiveEngine(makeDeps());
    engine.computeGlow({ mode: 'defensive', lastChangedAt: null }, 0);

    const snap = engine.getSnapshot();
    assert.equal(snap.label, 'alert');
    assert.equal(snap.hue, '#f85149');
    assert.equal(snap.intensity, 1.0);
  });

  it('computes watchful glow for elevated posture', () => {
    const engine = new ExpressiveEngine(makeDeps());
    engine.computeGlow({ mode: 'elevated', lastChangedAt: null }, 0);

    assert.equal(engine.getSnapshot().label, 'watchful');
    assert.equal(engine.getSnapshot().hue, '#d29922');
  });

  it('computes resting glow for idle posture', () => {
    const engine = new ExpressiveEngine(makeDeps());
    engine.computeGlow({ mode: 'idle', lastChangedAt: null }, 0);

    assert.equal(engine.getSnapshot().label, 'resting');
    assert.equal(engine.getSnapshot().hue, '#58a6ff');
  });

  it('boosts intensity with node count', () => {
    const engine = new ExpressiveEngine(makeDeps());
    engine.computeGlow({ mode: 'normal', lastChangedAt: null }, 0);
    const base = engine.getSnapshot().intensity;

    engine.computeGlow({ mode: 'normal', lastChangedAt: null }, 3);
    const boosted = engine.getSnapshot().intensity;

    assert.ok(boosted > base);
  });

  it('caps intensity at 1.0', () => {
    const engine = new ExpressiveEngine(makeDeps());
    engine.computeGlow({ mode: 'defensive', lastChangedAt: null }, 100);

    assert.ok(engine.getSnapshot().intensity <= 1.0);
  });

  it('is deterministic for same inputs', () => {
    const engine = new ExpressiveEngine(makeDeps());
    engine.computeGlow({ mode: 'elevated', lastChangedAt: null }, 2);
    const a = engine.getSnapshot();

    engine.computeGlow({ mode: 'elevated', lastChangedAt: null }, 2);
    const b = engine.getSnapshot();

    assert.deepEqual(a, b);
  });

  it('snapshot shape has hue, intensity, and label', () => {
    const engine = new ExpressiveEngine(makeDeps());
    const snap = engine.getSnapshot();

    assert.equal(typeof snap.hue, 'string');
    assert.equal(typeof snap.intensity, 'number');
    assert.equal(typeof snap.label, 'string');
  });
});
