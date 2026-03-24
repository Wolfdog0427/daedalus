import type {
  OrchestratorEventBus,
  OrchestratorPipeline,
  OrchestratorPipelineDeps,
} from '../shared/types.js';

export function createOrchestratorPipeline(
  deps: OrchestratorPipelineDeps,
): OrchestratorPipeline {
  const {
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
  } = deps;

  const bus: OrchestratorEventBus = eventBus;

  function handleInboundEvent(event: any) {
    logger.debug('[pipeline] inbound event', { type: event.type });

    // Stage 1: presence — track nodes, beings, sessions
    presenceEngine.onEvent(event, { systemContext, operatorContext });

    // Stage 2: continuity — update threads, record timeline
    continuityEngine.onEvent(event, { systemContext, operatorContext });

    // Stage 3: posture — adjust defensive posture
    postureEngine.onEvent(event, { systemContext, operatorContext });

    // Stage 4: risk — assess tier from posture + presence + event volume
    riskEngine.assess({
      posture: postureEngine.getSnapshot(),
      nodeCount: presenceEngine.getNodeRegistrySnapshot().count,
      recentEventCount: stateStore.getSnapshot().events.length,
    });

    // Stage 5: verification — update requirement from risk tier
    verificationEngine.updateFromRiskTier(riskEngine.getSnapshot().tier);
    verificationEngine.onEvent(event);

    // Stage 6: expressive — compute glow from posture + node count
    if (capabilityRegistry.isEnabled('expressive')) {
      expressiveEngine.computeGlow(
        postureEngine.getSnapshot(),
        presenceEngine.getNodeRegistrySnapshot().count,
      );
    }

    // Stage 7: notifications — process notification triggers
    if (capabilityRegistry.isEnabled('notifications')) {
      notificationEngine.onEvent(event);
    }

    // Stage 8: state — persist the event
    stateStore.applyEvent(event);

    // Stage 9: publish processed event
    bus.publish({
      ...event,
      meta: {
        ...(event.meta ?? {}),
        processedAt: new Date().toISOString(),
        riskTier: riskEngine.getSnapshot().tier,
        glow: expressiveEngine.getSnapshot().label,
      },
    });
  }

  function dispatchCommand(command: any) {
    logger.debug('[pipeline] dispatch command', { type: command.type });

    const event = {
      type: `command.${command.type}`,
      payload: command.payload,
      meta: {
        issuedAt: new Date().toISOString(),
        operator: operatorContext.getCurrentOperator(),
      },
    };

    handleInboundEvent(event);
  }

  return {
    handleInboundEvent,
    dispatchCommand,
  };
}
