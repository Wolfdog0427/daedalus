import { NodeStatus } from '../../../shared/daedalus/nodeContracts';

const TRANSITIONS: Record<NodeStatus, readonly NodeStatus[]> = {
  [NodeStatus.PENDING]: [NodeStatus.ACTIVE, NodeStatus.DETACHED],
  [NodeStatus.ACTIVE]: [NodeStatus.DEGRADED, NodeStatus.QUARANTINED, NodeStatus.DETACHED],
  [NodeStatus.DEGRADED]: [NodeStatus.ACTIVE, NodeStatus.QUARANTINED, NodeStatus.DETACHED],
  [NodeStatus.QUARANTINED]: [NodeStatus.DETACHED],
  [NodeStatus.DETACHED]: [],
};

export class NodeLifecycle {
  private current: NodeStatus = NodeStatus.PENDING;
  private listeners: Set<(status: NodeStatus) => void> = new Set();

  getStatus(): NodeStatus {
    return this.current;
  }

  canTransition(next: NodeStatus): boolean {
    return TRANSITIONS[this.current]?.includes(next) ?? false;
  }

  transition(next: NodeStatus): void {
    if (!this.canTransition(next)) {
      throw new Error(
        `Invalid lifecycle transition: ${this.current} → ${next}`,
      );
    }
    this.current = next;
    for (const fn of this.listeners) fn(this.current);
  }

  forceStatus(status: NodeStatus): void {
    this.current = status;
    for (const fn of this.listeners) fn(this.current);
  }

  onStatusChange(handler: (status: NodeStatus) => void): () => void {
    this.listeners.add(handler);
    return () => { this.listeners.delete(handler); };
  }
}
