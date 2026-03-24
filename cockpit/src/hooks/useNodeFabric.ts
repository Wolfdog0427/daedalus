import { useState, useMemo, useCallback } from 'react';
import {
  NodeId,
  NodeKind,
  NodeStatus,
  NodeRiskTier,
  NodeJoinProposal,
  NodeJoinDecision,
  JoinDecisionKind,
  NodeHealthSnapshot,
  NodePhysiologyState,
  NodeSummary,
  NodeDetail,
  MOBILE_CAPABILITIES,
} from '../shared/daedalus/nodeContracts';
import {
  NodeRegistry,
  createEmptyRegistry,
  registerJoinProposal,
  resolveDecision,
  updateHeartbeat,
  updatePhysiology,
  quarantineNode,
  detachNode,
  listNodesForOperator,
  getNodeDetail,
} from '../shared/daedalus/nodeFabricEngine';
import { evaluateJoinProposal } from '../shared/daedalus/nodeNegotiationEngine';
import { NodeNotification } from '../shared/daedalus/nodeNotifications';
import {
  createJoinRequestNotification,
  createQuarantineNotification,
  createDetachNotification,
} from '../shared/daedalus/nodeNotificationEngine';

export interface NodeFabricState {
  readonly registry: NodeRegistry;
  readonly notifications: readonly NodeNotification[];
  readonly operatorId: string;
}

export function useNodeFabric(operatorId: string) {
  const [registry, setRegistry] = useState<NodeRegistry>(() => createEmptyRegistry());
  const [notifications, setNotifications] = useState<NodeNotification[]>([]);

  const handleJoinProposal = useCallback(
    (proposal: NodeJoinProposal) => {
      const decision = evaluateJoinProposal(proposal, []);
      setRegistry(prev => registerJoinProposal(prev, proposal, decision));

      if (decision.decision === JoinDecisionKind.NEEDS_OPERATOR_APPROVAL) {
        setNotifications(prev => [...prev, createJoinRequestNotification(proposal)]);
      }

      return decision;
    },
    [],
  );

  const handleApprove = useCallback(
    (nodeId: NodeId) => {
      const decision: NodeJoinDecision = Object.freeze({
        nodeId,
        decision: JoinDecisionKind.APPROVED,
        reason: 'Operator approved',
        decidedAt: Date.now(),
      });
      setRegistry(prev => resolveDecision(prev, nodeId, decision));
    },
    [],
  );

  const handleReject = useCallback(
    (nodeId: NodeId) => {
      const decision: NodeJoinDecision = Object.freeze({
        nodeId,
        decision: JoinDecisionKind.REJECTED,
        reason: 'Operator rejected',
        decidedAt: Date.now(),
      });
      setRegistry(prev => resolveDecision(prev, nodeId, decision));
    },
    [],
  );

  const handleQuarantine = useCallback(
    (nodeId: NodeId) => {
      setRegistry(prev => quarantineNode(prev, nodeId));
      setNotifications(prev => [
        ...prev,
        createQuarantineNotification(nodeId, 'Node quarantined by operator', 'Operator action'),
      ]);
    },
    [],
  );

  const handleDetach = useCallback(
    (nodeId: NodeId) => {
      setRegistry(prev => detachNode(prev, nodeId));
      setNotifications(prev => [
        ...prev,
        createDetachNotification(nodeId, 'Node detached by operator'),
      ]);
    },
    [],
  );

  const handleHeartbeat = useCallback(
    (nodeId: NodeId, snapshot: NodeHealthSnapshot) => {
      setRegistry(prev => updateHeartbeat(prev, nodeId, snapshot));
    },
    [],
  );

  const handlePhysiology = useCallback(
    (nodeId: NodeId, state: NodePhysiologyState) => {
      setRegistry(prev => updatePhysiology(prev, nodeId, state));
    },
    [],
  );

  const nodes = useMemo(
    () => listNodesForOperator(registry, operatorId),
    [registry, operatorId],
  );

  const getDetail = useCallback(
    (nodeId: NodeId) => getNodeDetail(registry, nodeId),
    [registry],
  );

  return {
    registry,
    nodes,
    notifications,
    getDetail,
    handleJoinProposal,
    handleApprove,
    handleReject,
    handleQuarantine,
    handleDetach,
    handleHeartbeat,
    handlePhysiology,
  };
}
