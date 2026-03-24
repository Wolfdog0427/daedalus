import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { createHttpServer } from '../src/infrastructure/http.js';
import { Orchestrator } from '../src/orchestrator/Orchestrator.js';
import { createOrchestratorPipeline } from '../src/orchestrator/pipeline.js';
import { createPresenceEngine } from '../src/orchestrator/presence/PresenceEngine.js';
import { createContinuityEngine } from '../src/orchestrator/continuity/ContinuityEngine.js';
import { createPostureEngine } from '../src/orchestrator/posture/PostureEngine.js';
import { createRiskEngine } from '../src/orchestrator/risk/RiskEngine.js';
import { createVerificationEngine } from '../src/orchestrator/verification/VerificationEngine.js';
import { createExpressiveEngine } from '../src/orchestrator/expressive/ExpressiveEngine.js';
import { createNotificationEngine } from '../src/orchestrator/notifications/NotificationEngine.js';
import { createCapabilityRegistry } from '../src/orchestrator/capabilities/CapabilityRegistry.js';
import { createNodeCapabilityMap } from '../src/orchestrator/capabilities/NodeCapabilityMap.js';
import { createCapabilityProfileRegistry } from '../src/orchestrator/profiles/CapabilityProfileRegistry.js';
import { OrchestratorStateStore } from '../src/core/state/OrchestratorState.js';
import { createOperatorContext } from '../src/core/context/OperatorContext.js';
import { registerRoutes } from '../src/orchestrator/routes/index.js';

function makeLogger() {
  return { info() {}, debug() {}, warn() {}, error() {} } as any;
}

async function fetchJson(port: number, path: string) {
  return new Promise<{ status: number; body: any }>((resolve, reject) => {
    http.get(`http://127.0.0.1:${port}${path}`, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        resolve({ status: res.statusCode!, body: JSON.parse(data) });
      });
    }).on('error', reject);
  });
}

async function postJson(port: number, path: string, body: any) {
  return new Promise<{ status: number; body: any }>((resolve, reject) => {
    const payload = JSON.stringify(body);
    const req = http.request(
      `http://127.0.0.1:${port}${path}`,
      { method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } },
      (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          resolve({ status: res.statusCode!, body: JSON.parse(data) });
        });
      },
    );
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

async function patchJson(port: number, path: string, body: any) {
  return new Promise<{ status: number; body: any }>((resolve, reject) => {
    const payload = JSON.stringify(body);
    const req = http.request(
      `http://127.0.0.1:${port}${path}`,
      { method: 'PATCH', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } },
      (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          resolve({ status: res.statusCode!, body: JSON.parse(data) });
        });
      },
    );
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

describe('v0.4 HTTP endpoints', () => {
  let server: any;
  const port = 14567;

  before(async () => {
    const logger = makeLogger();
    const eventBus = {
      publish() {},
      subscribe() { return { unsubscribe() {} }; },
    } as any;
    const stateStore = new OrchestratorStateStore(logger);
    const systemContext = {
      getSnapshot() { return { env: 'test', version: '0.4.0', startedAt: new Date().toISOString() }; },
    } as any;
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
      logger, eventBus, stateStore, presenceEngine, continuityEngine,
      postureEngine, riskEngine, verificationEngine, expressiveEngine,
      notificationEngine, capabilityRegistry, systemContext, operatorContext,
    });

    const orchestrator = new Orchestrator({
      logger, eventBus, stateStore, pipeline, presenceEngine, continuityEngine,
      postureEngine, riskEngine, verificationEngine, expressiveEngine,
      notificationEngine, capabilityRegistry, nodeCapabilityMap, profileRegistry, systemContext, operatorContext,
    });

    server = createHttpServer({
      logger, config: { env: 'test', http: { port } }, orchestrator, eventBus, operatorContext,
    });

    registerRoutes(server, { orchestrator, eventBus, logger, operatorContext, systemContext });

    await new Promise<void>((resolve) => server.listen(port, resolve));
  });

  after(async () => {
    await new Promise<void>((resolve) => server.close(resolve));
  });

  it('GET /capabilities returns an array of capabilities', async () => {
    const { status, body } = await fetchJson(port, '/capabilities');
    assert.equal(status, 200);
    assert.ok(Array.isArray(body));
    assert.ok(body.length > 0);
    assert.ok(body[0].name);
    assert.equal(typeof body[0].enabled, 'boolean');
  });

  it('GET /glow returns glow snapshot', async () => {
    const { status, body } = await fetchJson(port, '/glow');
    assert.equal(status, 200);
    assert.equal(typeof body.hue, 'string');
    assert.equal(typeof body.intensity, 'number');
    assert.equal(typeof body.label, 'string');
  });

  it('GET /notifications returns an array', async () => {
    const { status, body } = await fetchJson(port, '/notifications');
    assert.equal(status, 200);
    assert.ok(Array.isArray(body));
  });

  it('GET /health includes glow label', async () => {
    const { body } = await fetchJson(port, '/health');
    assert.equal(body.version, '0.4.0');
    assert.equal(typeof body.glow, 'string');
  });

  it('GET /state includes glow and verification', async () => {
    const { body } = await fetchJson(port, '/state');
    assert.ok(body.glow);
    assert.ok(body.risk);
    assert.ok(body.verification);
  });

  it('GET /nodes returns node registry', async () => {
    const { status, body } = await fetchJson(port, '/nodes');
    assert.equal(status, 200);
    assert.equal(typeof body.count, 'number');
  });

  it('GET /risk returns risk + verification', async () => {
    const { status, body } = await fetchJson(port, '/risk');
    assert.equal(status, 200);
    assert.ok(body.risk.tier);
    assert.ok(body.verification.requirement);
  });

  it('returns 404 for unknown path', async () => {
    const { status } = await fetchJson(port, '/nonexistent');
    assert.equal(status, 404);
  });

  it('PATCH /capabilities/:name toggles a capability off', async () => {
    const { status, body } = await patchJson(port, '/capabilities/expressive', { enabled: false });
    assert.equal(status, 200);
    assert.equal(body.name, 'expressive');
    assert.equal(body.enabled, false);
  });

  it('PATCH /capabilities/:name toggles a capability back on', async () => {
    const { status, body } = await patchJson(port, '/capabilities/expressive', { enabled: true });
    assert.equal(status, 200);
    assert.equal(body.enabled, true);
  });

  it('PATCH /capabilities/:name returns 404 for unknown capability', async () => {
    const { status, body } = await patchJson(port, '/capabilities/nonexistent', { enabled: true });
    assert.equal(status, 404);
    assert.ok(body.error);
  });

  it('PATCH /capabilities/:name returns 400 for invalid body', async () => {
    const { status, body } = await patchJson(port, '/capabilities/expressive', { enabled: 'yes' });
    assert.equal(status, 400);
    assert.ok(body.error);
  });

  it('GET /capabilities reflects toggled state', async () => {
    await patchJson(port, '/capabilities/notifications', { enabled: false });
    const { body } = await fetchJson(port, '/capabilities');
    const notif = body.find((c: any) => c.name === 'notifications');
    assert.equal(notif.enabled, false);

    await patchJson(port, '/capabilities/notifications', { enabled: true });
  });

  it('GET /profiles returns an array of profiles', async () => {
    const { status, body } = await fetchJson(port, '/profiles');
    assert.equal(status, 200);
    assert.ok(Array.isArray(body));
    assert.ok(body.length >= 3);
    assert.ok(body.some((p: any) => p.name === 'expressive'));
    assert.ok(body.some((p: any) => p.name === 'silent'));
    assert.ok(body.some((p: any) => p.name === 'diagnostic'));
  });

  it('POST /profiles/:name/apply applies a profile', async () => {
    const { status, body } = await postJson(port, '/profiles/silent/apply', {});
    assert.equal(status, 200);
    assert.equal(body.name, 'silent');

    const { body: caps } = await fetchJson(port, '/capabilities');
    const expressive = caps.find((c: any) => c.name === 'expressive');
    const notifications = caps.find((c: any) => c.name === 'notifications');
    assert.equal(expressive.enabled, false);
    assert.equal(notifications.enabled, false);

    await postJson(port, '/profiles/expressive/apply', {});
  });

  it('POST /profiles/:name/apply returns 404 for unknown profile', async () => {
    const { status, body } = await postJson(port, '/profiles/nonexistent/apply', {});
    assert.equal(status, 404);
    assert.ok(body.error);
  });

  it('GET /nodes/capabilities returns empty list initially', async () => {
    const { status, body } = await fetchJson(port, '/nodes/capabilities');
    assert.equal(status, 200);
    assert.ok(Array.isArray(body));
  });

  it('GET /nodes/:nodeId/capabilities returns 404 for unknown node', async () => {
    const { status } = await fetchJson(port, '/nodes/ghost/capabilities');
    assert.equal(status, 404);
  });

  it('POST /nodes/:nodeId/profiles/:profileName/apply sets node capabilities', async () => {
    const { status, body } = await postJson(port, '/nodes/n1/profiles/silent/apply', {});
    assert.equal(status, 200);
    assert.equal(body.nodeId, 'n1');
    assert.equal(body.capabilities.expressive, false);
    assert.equal(body.capabilities.notifications, false);
  });

  it('GET /nodes/:nodeId/capabilities returns state after profile apply', async () => {
    const { status, body } = await fetchJson(port, '/nodes/n1/capabilities');
    assert.equal(status, 200);
    assert.equal(body.nodeId, 'n1');
  });

  it('POST /capabilities/negotiate merges node states into global', async () => {
    await postJson(port, '/nodes/n1/profiles/expressive/apply', {});
    await postJson(port, '/nodes/n2/profiles/diagnostic/apply', {});

    const { status, body } = await postJson(port, '/capabilities/negotiate', {});
    assert.equal(status, 200);
    assert.equal(body.expressive, false, 'n2 diagnostic disables expressive');
    assert.equal(body.notifications, true, 'both have notifications on');

    await postJson(port, '/profiles/expressive/apply', {});
  });
});
