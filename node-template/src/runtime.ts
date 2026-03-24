import {
  NodeStatus,
  NodeKind,
  NodeHealthSnapshot,
  NodePhysiologyState,
  NodeJoinProposal,
  JoinDecisionKind,
} from '../../shared/daedalus/nodeContracts';
import { createContinuityBinding } from '../../shared/daedalus/nodeNegotiationEngine';
import type { NodeTemplateConfig, ContinuitySignals, NodeRuntime } from './contracts';
import type { NodeTransport } from './transport';
import type { DeviceAdapter } from './deviceAdapter';
import { NodeLifecycle } from './lifecycle/stateMachine';
import { createHeartbeatEngine } from './heartbeatEngine';
import { createJoinNegotiator } from './joinNegotiator';
import { createPhysiologyDriver } from './physiologyDriver';
import { NODE_HEALTH_IDLE, NODE_PHYSIOLOGY_IDLE } from '../../shared/daedalus/nodeContracts';

export function createNodeRuntime(
  config: NodeTemplateConfig,
  transport: NodeTransport,
  device: DeviceAdapter,
): NodeRuntime {
  const lifecycle = new NodeLifecycle();

  const heartbeat = createHeartbeatEngine({
    nodeId: config.nodeId,
    transport,
    baseCadenceMs: config.baseCadenceMs,
    degradedCadenceMs: config.degradedCadenceMs,
  });

  const negotiator = createJoinNegotiator({ transport, lifecycle });

  const physiology = createPhysiologyDriver({
    nodeId: config.nodeId,
    transport,
  });

  let deviceUnsub: (() => void) | null = null;

  heartbeat.onSnapshot(snapshot => {
    physiology.updateHealth(snapshot);
  });

  return {
    async start() {
      device.startSensors();
      deviceUnsub = device.onContextChange(ctx => {
        heartbeat.updateContext(ctx);
      });
      heartbeat.updateContext(device.getCurrentContext());

      const proposal: NodeJoinProposal = Object.freeze({
        nodeId: config.nodeId,
        kind: config.kind,
        capabilities: config.capabilities,
        fingerprint: device.getFingerprint(),
        operatorId: config.operatorId,
        initialRiskSignals: [],
        proposedAt: Date.now(),
      });

      const decision = await negotiator.proposeJoin(proposal);

      if (decision.decision === JoinDecisionKind.APPROVED) {
        negotiator.setBinding(
          createContinuityBinding(config.operatorId, config.nodeId, config.trustDomain),
        );
        heartbeat.start();
      }
    },

    stop() {
      heartbeat.stop();
      device.stopSensors();
      if (deviceUnsub) { deviceUnsub(); deviceUnsub = null; }
    },

    getStatus() {
      return lifecycle.getStatus();
    },

    getHealth() {
      return heartbeat.getLastSnapshot() ?? { ...NODE_HEALTH_IDLE, nodeId: config.nodeId, timestamp: Date.now() };
    },

    getPhysiology() {
      return physiology.getCurrentState();
    },

    onStatusChange(handler) {
      return lifecycle.onStatusChange(handler);
    },

    onHealthChange(handler) {
      return heartbeat.onSnapshot(handler);
    },

    onPhysiologyChange(handler) {
      return physiology.onPhysiologyChange(handler);
    },

    updateContinuitySignals(signals: ContinuitySignals) {
      physiology.updateContinuitySignals(signals);
    },
  };
}
