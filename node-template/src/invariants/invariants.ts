import { NodeStatus, JoinDecisionKind, NodeJoinDecision } from '../../../shared/daedalus/nodeContracts';

export class InvariantViolation extends Error {
  constructor(public readonly invariant: string, message: string) {
    super(`Invariant [${invariant}]: ${message}`);
  }
}

export function assertNoSilentJoin(
  decision: NodeJoinDecision,
  targetStatus: NodeStatus,
): void {
  if (targetStatus === NodeStatus.ACTIVE && decision.decision !== JoinDecisionKind.APPROVED) {
    throw new InvariantViolation(
      'NO_SILENT_JOIN',
      `Cannot set ACTIVE without APPROVED decision (got ${decision.decision})`,
    );
  }
}

export function assertOperatorSovereignty(
  action: string,
  operatorApproved: boolean,
): void {
  if (!operatorApproved) {
    throw new InvariantViolation(
      'OPERATOR_SOVEREIGNTY',
      `Action "${action}" requires explicit operator approval`,
    );
  }
}

export function assertNotQuarantined(status: NodeStatus, action: string): void {
  if (status === NodeStatus.QUARANTINED) {
    throw new InvariantViolation(
      'QUARANTINED_NO_ACTION',
      `Quarantined nodes cannot perform "${action}"`,
    );
  }
}

export function assertNotDetached(status: NodeStatus, action: string): void {
  if (status === NodeStatus.DETACHED) {
    throw new InvariantViolation(
      'DETACHED_NO_ACTION',
      `Detached nodes cannot perform "${action}"`,
    );
  }
}
