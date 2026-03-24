import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { VerificationEngine } from '../src/orchestrator/verification/VerificationEngine.js';

function makeDeps() {
  return {
    logger: { info() {}, debug() {}, warn() {}, error() {} },
    eventBus: {} as any,
  } as any;
}

describe('VerificationEngine', () => {
  it('defaults to none requirement', () => {
    const engine = new VerificationEngine(makeDeps());
    assert.equal(engine.getSnapshot().requirement, 'none');
    assert.equal(engine.getSnapshot().lastEvent, null);
  });

  it('maps low risk to none', () => {
    const engine = new VerificationEngine(makeDeps());
    engine.updateFromRiskTier('low');
    assert.equal(engine.getSnapshot().requirement, 'none');
  });

  it('maps medium risk to soft', () => {
    const engine = new VerificationEngine(makeDeps());
    engine.updateFromRiskTier('medium');
    assert.equal(engine.getSnapshot().requirement, 'soft');
  });

  it('maps elevated risk to strong', () => {
    const engine = new VerificationEngine(makeDeps());
    engine.updateFromRiskTier('elevated');
    assert.equal(engine.getSnapshot().requirement, 'strong');
  });

  it('maps critical risk to strong', () => {
    const engine = new VerificationEngine(makeDeps());
    engine.updateFromRiskTier('critical');
    assert.equal(engine.getSnapshot().requirement, 'strong');
  });

  it('records verification event', () => {
    const engine = new VerificationEngine(makeDeps());
    engine.recordVerification('totp', 'operator-1');

    const snap = engine.getSnapshot();
    assert.ok(snap.lastEvent);
    assert.equal(snap.lastEvent!.method, 'totp');
    assert.equal(snap.lastEvent!.actor, 'operator-1');
  });

  it('records verification from event bus', () => {
    const engine = new VerificationEngine(makeDeps());
    engine.onEvent({
      type: 'verification.completed',
      payload: { method: 'sms', actor: 'admin' },
    });

    assert.equal(engine.getSnapshot().lastEvent!.method, 'sms');
  });
});
