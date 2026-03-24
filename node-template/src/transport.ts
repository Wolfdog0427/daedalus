import type {
  NodeJoinProposal,
  NodeJoinDecision,
  NodeHealthSnapshot,
  NodePhysiologyState,
} from '../../shared/daedalus/nodeContracts';

export interface NodeTransport {
  sendJoinProposal(proposal: NodeJoinProposal): Promise<NodeJoinDecision>;
  sendHeartbeat(snapshot: NodeHealthSnapshot): Promise<void>;
  sendPhysiology(state: NodePhysiologyState): Promise<void>;
}
