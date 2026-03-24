import type { HttpServer } from '../../infrastructure/http.js';
import type { OrchestratorPublicAPI } from '../types.js';
import type { OrchestratorEventBus } from '../../shared/types.js';
import type { Logger } from '../../infrastructure/logging.js';
import type { OperatorContext } from '../../core/context/OperatorContext.js';
import type { SystemContext } from '../../core/context/SystemContext.js';

interface RouteDeps {
  orchestrator: OrchestratorPublicAPI;
  eventBus: OrchestratorEventBus;
  logger: Logger;
  operatorContext: OperatorContext;
  systemContext: SystemContext;
}

export function registerRoutes(server: HttpServer, deps: RouteDeps) {
  const { orchestrator, eventBus, logger, operatorContext, systemContext } =
    deps;

  server.get('/health', (_req, res) => {
    res.json({
      status: 'ok',
      version: '0.4.0',
      posture: orchestrator.getPostureSnapshot(),
      risk: orchestrator.getRiskSnapshot().tier,
      glow: orchestrator.getGlowSnapshot().label,
    });
  });

  server.get('/state', (_req, res) => {
    res.json({
      state: orchestrator.getStateSnapshot(),
      presence: orchestrator.getPresenceSnapshot(),
      continuity: orchestrator.getContinuitySnapshot(),
      posture: orchestrator.getPostureSnapshot(),
      risk: orchestrator.getRiskSnapshot(),
      verification: orchestrator.getVerificationSnapshot(),
      glow: orchestrator.getGlowSnapshot(),
    });
  });

  server.get('/nodes', (_req, res) => {
    res.json(orchestrator.getNodesSnapshot());
  });

  server.get('/risk', (_req, res) => {
    res.json({
      risk: orchestrator.getRiskSnapshot(),
      verification: orchestrator.getVerificationSnapshot(),
    });
  });

  server.get('/continuity/timeline', (_req, res) => {
    res.json(orchestrator.getTimelineSnapshot());
  });

  server.get('/capabilities', (_req, res) => {
    res.json(orchestrator.getCapabilities());
  });

  server.patch('/capabilities/:name', (req, res) => {
    const { name } = req.params;
    const { enabled } = req.body ?? {};

    if (typeof enabled !== 'boolean') {
      res.status(400).json({ error: 'enabled must be a boolean' });
      return;
    }

    const updated = orchestrator.setCapabilityEnabled(name, enabled);
    if (!updated) {
      res.status(404).json({ error: `Capability "${name}" not found` });
      return;
    }

    logger.info('[http] capability toggled', { name, enabled });
    res.json(updated);
  });

  server.get('/profiles', (_req, res) => {
    res.json(orchestrator.getProfiles());
  });

  server.post('/profiles/:name/apply', (req, res) => {
    const { name } = req.params;
    const profile = orchestrator.applyProfile(name);

    if (!profile) {
      res.status(404).json({ error: `Profile "${name}" not found` });
      return;
    }

    logger.info('[http] profile applied', { name });
    res.json(profile);
  });

  server.get('/nodes/capabilities', (_req, res) => {
    res.json(orchestrator.listNodeCapabilities());
  });

  server.get('/nodes/:nodeId/capabilities', (req, res) => {
    const { nodeId } = req.params;
    const state = orchestrator.getNodeCapabilities(nodeId);
    if (!state) {
      res.status(404).json({ error: `Node "${nodeId}" not found` });
      return;
    }
    res.json(state);
  });

  server.post('/nodes/:nodeId/profiles/:profileName/apply', (req, res) => {
    const { nodeId, profileName } = req.params;
    const state = orchestrator.applyProfileToNode(nodeId, profileName);
    if (!state) {
      res.status(404).json({ error: `Profile "${profileName}" not found` });
      return;
    }
    logger.info('[http] profile applied to node', { nodeId, profileName });
    res.json(state);
  });

  server.post('/capabilities/negotiate', (_req, res) => {
    const result = orchestrator.negotiateCapabilitiesFromNodes();
    res.json(result);
  });

  server.get('/glow', (_req, res) => {
    res.json(orchestrator.getGlowSnapshot());
  });

  server.get('/notifications', (_req, res) => {
    res.json(orchestrator.getNotifications());
  });

  server.get('/context', (_req, res) => {
    res.json({
      system: systemContext.getSnapshot(),
      operator: operatorContext.getSnapshot(),
    });
  });

  server.post('/events', (req, res) => {
    const event = req.body;
    logger.info('[http] inbound event', { type: event?.type });
    orchestrator.emitEvent(event);
    res.status(202).json({ accepted: true });
  });

  server.post('/commands', (req, res) => {
    const command = req.body;
    logger.info('[http] inbound command', { type: command?.type });
    orchestrator.dispatchCommand(command);
    res.status(202).json({ accepted: true });
  });

  server.get('/events/stream', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const subscription = eventBus.subscribe((event) => {
      res.write(`data: ${JSON.stringify(event)}\n\n`);
    });

    req.on('close', () => {
      subscription.unsubscribe();
    });
  });
}
