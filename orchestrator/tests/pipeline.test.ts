import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { createOrchestratorPipeline } from '../src/orchestrator/pipeline.js';
import { PresenceEngine } from '../src/orchestrator/presence/PresenceEngine.js';
import { ContinuityEngine } from '../src/orchestrator/continuity/ContinuityEngine.js';
import { PostureEngine } from '../src/orchestrator/posture/PostureEngine.js';
import { RiskEngine } from '../src/orchestrator/risk/RiskEngine.js';
import { VerificationEngine } from '../src/orchestrator/verification/VerificationEngine.js';
import { ExpressiveEngine } from '../src/orchestrator/expressive/ExpressiveEngine.js';
import { NotificationEngine } from '../src/orchestrator/notifications/NotificationEngine.js';
import { CapabilityRegistry } from '../src/orchestrator/capabilities/CapabilityRegistry.js';
import { OrchestratorStateStore } from '../src/core/state/OrchestratorState.js';
import { OperatorContext } from '../src/core/context/OperatorContext.js';

function makeLogger() {
  return { info() {}, debug() {}, warn() {}, error() {} } as any;
}

function buildPipeline(overrides?: { capabilityOverrides?: Record<string, boolean> }) {
  const logger = makeLogger();
  const published: any[] = [];
  const eventBus = {
    publish(e: any) { published.push(e); },
    subscribe() { return { unsubscribe() {} }; },
  } as any;

  const stateStore = new OrchestratorStateStore(logger);
  const operatorContext = new OperatorContext();
  const systemContext = { getSnapshot() { return { env: 'test', version: '0.4.0', startedAt: new Date().toISOString() }; } } as any;

  const presenceEngine = new PresenceEngine({ logger, stateStore, eventBus });
  const continuityEngine = new ContinuityEngine({ logger, stateStore, eventBus });
  const postureEngine = new PostureEngine({ logger, stateStore, eventBus });
  const riskEngine = new RiskEngine({ logger, stateStore, eventBus });
  const verificationEngine = new VerificationEngine({ logger, eventBus });
  const expressiveEngine = new ExpressiveEngine({ logger });
  const notificationEngine = new NotificationEngine({ logger, eventBus });

  const capabilityRegistry = new CapabilityRegistry({ logger });
  capabilityRegistry.register({ name: 'expressive', description: 'Glow', enabled: true });
  capabilityRegistry.register({ name: 'notifications', description: 'Notifications', enabled: true });

  if (overrides?.capabilityOverrides) {
    for (const [name, enabled] of Object.entries(overrides.capabilityOverrides)) {
      capabilityRegistry.setEnabled(name, enabled);
    }
  }

  const pipeline = createOrchestratorPipeline({
    logger,
    eventBus,
    stateStore,
    presenceEngine,
    continuityEngine,
    postureEngine,
    riskEngine,
    verificationEngine,
    expressiveEngine,
    notificationEngine,
    capabilityRegistry,
    systemContext,
    operatorContext,
  });

  return {
    pipeline,
    published,
    stateStore,
    presenceEngine,
    continuityEngine,
    postureEngine,
    riskEngine,
    verificationEngine,
    expressiveEngine,
    notificationEngine,
    capabilityRegistry,
  };
}

describe('Pipeline v0.4 integration', () => {
  it('processes an event through all 9 stages', () => {
    const ctx = buildPipeline();

    ctx.pipeline.handleInboundEvent({
      type: 'node.joined',
      payload: { id: 'n1', capabilities: ['echo'] },
    });

    // Stage 1 (presence): node registered
    assert.equal(ctx.presenceEngine.getNodeRegistrySnapshot().count, 1);

    // Stage 2 (continuity): timeline entry recorded
    assert.equal(ctx.continuityEngine.getTimelineSnapshot().entries.length, 1);

    // Stage 3 (posture): still normal (node.joined doesn't change posture)
    assert.equal(ctx.postureEngine.getSnapshot().mode, 'normal');

    // Stage 4 (risk): assessed (node count is now 1)
    assert.ok(ctx.riskEngine.getSnapshot().assessedAt);

    // Stage 5 (verification): requirement set based on risk
    assert.ok(['none', 'soft', 'strong'].includes(ctx.verificationEngine.getSnapshot().requirement));

    // Stage 6 (expressive): glow computed
    assert.ok(ctx.expressiveEngine.getSnapshot().label);

    // Stage 7 (notifications): no auto-notification for node.joined
    // (only posture.changed and risk.detected trigger auto-notifications)

    // Stage 8 (state): event persisted
    assert.equal(ctx.stateStore.getSnapshot().events.length, 1);

    // Stage 9 (publish): processed event published with enriched meta
    assert.equal(ctx.published.length, 1);
    assert.ok(ctx.published[0].meta.processedAt);
    assert.ok(ctx.published[0].meta.riskTier);
    assert.ok(ctx.published[0].meta.glow);
  });

  it('dispatchCommand wraps command as event and runs pipeline', () => {
    const ctx = buildPipeline();

    ctx.pipeline.dispatchCommand({ type: 'echo', payload: { message: 'test' } });

    assert.equal(ctx.published.length, 1);
    assert.equal(ctx.published[0].type, 'command.echo');
    assert.equal(ctx.stateStore.getSnapshot().events.length, 1);
  });

  it('risk.detected event triggers posture shift and notification', () => {
    const ctx = buildPipeline();

    ctx.pipeline.handleInboundEvent({
      type: 'risk.detected',
      payload: { severity: 'high' },
    });

    // Posture should shift to defensive
    assert.equal(ctx.postureEngine.getSnapshot().mode, 'defensive');

    // Risk should be elevated (defensive posture → elevated risk)
    assert.equal(ctx.riskEngine.getSnapshot().tier, 'elevated');

    // Verification should require strong
    assert.equal(ctx.verificationEngine.getSnapshot().requirement, 'strong');

    // Expressive glow should be alert
    assert.equal(ctx.expressiveEngine.getSnapshot().label, 'alert');

    // Notifications: risk_alert from risk.detected
    const notes = ctx.notificationEngine.list();
    assert.ok(notes.some((n: any) => n.type === 'risk_alert'));
  });

  it('published event meta includes riskTier and glow label', () => {
    const ctx = buildPipeline();

    ctx.pipeline.handleInboundEvent({ type: 'test.event', payload: {} });

    const meta = ctx.published[0].meta;
    assert.equal(typeof meta.riskTier, 'string');
    assert.equal(typeof meta.glow, 'string');
    assert.equal(typeof meta.processedAt, 'string');
  });
});

describe('Pipeline capability enforcement', () => {
  it('skips expressive stage when expressive capability is disabled', () => {
    const ctx = buildPipeline({ capabilityOverrides: { expressive: false } });
    const glowBefore = ctx.expressiveEngine.getSnapshot();

    ctx.pipeline.handleInboundEvent({
      type: 'risk.detected',
      payload: { severity: 'high' },
    });

    const glowAfter = ctx.expressiveEngine.getSnapshot();
    assert.deepEqual(glowBefore, glowAfter, 'glow should not have changed');
  });

  it('skips notification stage when notifications capability is disabled', () => {
    const ctx = buildPipeline({ capabilityOverrides: { notifications: false } });

    ctx.pipeline.handleInboundEvent({
      type: 'risk.detected',
      payload: { severity: 'high' },
    });

    assert.equal(ctx.notificationEngine.list().length, 0, 'no notifications should be generated');
  });

  it('still runs other stages when expressive is disabled', () => {
    const ctx = buildPipeline({ capabilityOverrides: { expressive: false } });

    ctx.pipeline.handleInboundEvent({ type: 'node.joined', payload: { id: 'n1' } });

    assert.equal(ctx.presenceEngine.getNodeRegistrySnapshot().count, 1);
    assert.equal(ctx.stateStore.getSnapshot().events.length, 1);
    assert.equal(ctx.published.length, 1);
  });

  it('still runs other stages when notifications is disabled', () => {
    const ctx = buildPipeline({ capabilityOverrides: { notifications: false } });

    ctx.pipeline.handleInboundEvent({ type: 'test.event', payload: {} });

    assert.ok(ctx.riskEngine.getSnapshot().assessedAt);
    assert.equal(ctx.stateStore.getSnapshot().events.length, 1);
    assert.equal(ctx.published.length, 1);
  });

  it('re-enables stages at runtime when capability is toggled back on', () => {
    const ctx = buildPipeline({ capabilityOverrides: { expressive: false } });
    const glowBefore = ctx.expressiveEngine.getSnapshot();

    ctx.pipeline.handleInboundEvent({ type: 'risk.detected', payload: {} });
    assert.deepEqual(ctx.expressiveEngine.getSnapshot(), glowBefore);

    ctx.capabilityRegistry.setEnabled('expressive', true);
    ctx.pipeline.handleInboundEvent({ type: 'risk.detected', payload: {} });
    assert.equal(ctx.expressiveEngine.getSnapshot().label, 'alert');
  });
});
