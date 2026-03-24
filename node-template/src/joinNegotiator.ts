import {
  NodeStatus,
  JoinDecisionKind,
  NodeJoinProposal,
  NodeJoinDecision,
  DeviceFingerprint,
  NodeContinuityBinding,
} from '../../shared/daedalus/nodeContracts';
import { applyJoinDecision, shouldRepropose } from '../../shared/daedalus/nodeNegotiationEngine';
import type { NodeTransport } from './transport';
import { NodeLifecycle } from './lifecycle/stateMachine';
import { assertNoSilentJoin } from './invariants/invariants';

export interface JoinNegotiatorConfig {
  readonly transport: NodeTransport;
  readonly lifecycle: NodeLifecycle;
}

export function createJoinNegotiator(config: JoinNegotiatorConfig) {
  let lastFingerprint: DeviceFingerprint | null = null;
  let binding: NodeContinuityBinding | null = null;
  let lastDecision: NodeJoinDecision | null = null;

  return {
    async proposeJoin(proposal: NodeJoinProposal): Promise<NodeJoinDecision> {
      lastFingerprint = proposal.fingerprint;
      const decision = await config.transport.sendJoinProposal(proposal);
      lastDecision = decision;

      assertNoSilentJoin(decision, applyJoinDecision(config.lifecycle.getStatus(), decision));

      const newStatus = applyJoinDecision(config.lifecycle.getStatus(), decision);
      config.lifecycle.forceStatus(newStatus);

      return decision;
    },

    handleDecision(decision: NodeJoinDecision): void {
      lastDecision = decision;
      assertNoSilentJoin(decision, applyJoinDecision(config.lifecycle.getStatus(), decision));
      const newStatus = applyJoinDecision(config.lifecycle.getStatus(), decision);
      config.lifecycle.forceStatus(newStatus);
    },

    getStatus(): NodeStatus {
      return config.lifecycle.getStatus();
    },

    getLastDecision(): NodeJoinDecision | null {
      return lastDecision;
    },

    setBinding(b: NodeContinuityBinding): void {
      binding = b;
    },

    getBinding(): NodeContinuityBinding | null {
      return binding;
    },

    needsReproposal(
      newFingerprint: DeviceFingerprint,
      knownFingerprints: readonly DeviceFingerprint[],
    ): boolean {
      return shouldRepropose(binding, newFingerprint, knownFingerprints);
    },
  };
}

export type JoinNegotiator = ReturnType<typeof createJoinNegotiator>;
