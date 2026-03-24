import { createHttpServer } from './infrastructure/http.js';
import { createEventBus } from './infrastructure/events.js';
import { createLogger } from './infrastructure/logging.js';
import { loadConfig } from './infrastructure/config.js';

import { Orchestrator } from './orchestrator/Orchestrator.js';
import { createOrchestratorPipeline } from './orchestrator/pipeline.js';
import { createPresenceEngine } from './orchestrator/presence/PresenceEngine.js';
import { createContinuityEngine } from './orchestrator/continuity/ContinuityEngine.js';
import { createPostureEngine } from './orchestrator/posture/PostureEngine.js';
import { createRiskEngine } from './orchestrator/risk/RiskEngine.js';
import { createVerificationEngine } from './orchestrator/verification/VerificationEngine.js';
import { createExpressiveEngine } from './orchestrator/expressive/ExpressiveEngine.js';
import { createNotificationEngine } from './orchestrator/notifications/NotificationEngine.js';
import { createCapabilityRegistry } from './orchestrator/capabilities/CapabilityRegistry.js';
import { createNodeCapabilityMap } from './orchestrator/capabilities/NodeCapabilityMap.js';
import { createCapabilityProfileRegistry } from './orchestrator/profiles/CapabilityProfileRegistry.js';

import { createOperatorContext } from './core/context/OperatorContext.js';
import { createSystemContext } from './core/context/SystemContext.js';

import { OrchestratorStateStore } from './core/state/OrchestratorState.js';
import { ConsoleAdapter } from './adapters/ConsoleAdapter.js';

import { registerRoutes } from './orchestrator/routes/index.js';
import type { OrchestratorEventBus } from './shared/types.js';

async function main() {
  const logger = createLogger();
  const config = loadConfig();

  logger.info('[orchestrator] starting v0.4', {
    version: '0.4.0',
    env: config.env,
    port: config.http.port,
  });

  const eventBus: OrchestratorEventBus = createEventBus(logger);
  const stateStore = new OrchestratorStateStore(logger);

  const systemContext = createSystemContext(config, logger);
  const operatorContext = createOperatorContext();

  const presenceEngine = createPresenceEngine({ logger, stateStore, eventBus });
  const continuityEngine = createContinuityEngine({ logger, stateStore, eventBus });
  const postureEngine = createPostureEngine({ logger, stateStore, eventBus });
  const riskEngine = createRiskEngine({ logger, stateStore, eventBus });
  const verificationEngine = createVerificationEngine({ logger, eventBus });
  const expressiveEngine = createExpressiveEngine({ logger });
  const notificationEngine = createNotificationEngine({ logger, eventBus });
  const capabilityRegistry = createCapabilityRegistry({ logger });
  const nodeCapabilityMap = createNodeCapabilityMap({ logger });
  const profileRegistry = createCapabilityProfileRegistry({ logger });

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

  const orchestrator = new Orchestrator({
    logger,
    eventBus,
    stateStore,
    pipeline,
    presenceEngine,
    continuityEngine,
    postureEngine,
    riskEngine,
    verificationEngine,
    expressiveEngine,
    notificationEngine,
    capabilityRegistry,
    nodeCapabilityMap,
    profileRegistry,
    systemContext,
    operatorContext,
  });

  const consoleAdapter = new ConsoleAdapter(logger, orchestrator);
  consoleAdapter.attach();

  const server = createHttpServer({
    logger,
    config,
    orchestrator,
    eventBus,
    operatorContext,
  });

  registerRoutes(server, {
    orchestrator,
    eventBus,
    logger,
    operatorContext,
    systemContext,
  });

  const port = config.http.port;
  server.listen(port, () => {
    logger.info('[orchestrator] HTTP server listening', { port });
  });
}

main().catch((err) => {
  console.error('[orchestrator] fatal error', err);
  process.exit(1);
});
