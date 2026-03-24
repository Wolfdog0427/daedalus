export type NodeStatus = 'online' | 'offline' | 'joining' | 'error';

export interface CapabilityMap {
  [key: string]: any;
}

export interface ExpressiveState {
  glow: string;
  posture: string;
  affect: string;
  continuity: string;
  [key: string]: any;
}

export interface NodeProfile {
  name: string;
  kind?: string;
  tags?: string[];
  [key: string]: any;
}

export interface NodeLifecycleState {
  lastHeartbeatAt: number | null;
  joinedAt: number | null;
  status: NodeStatus;
}

export interface NodeMirror {
  id: string;
  name: string;
  status: NodeStatus;
  capabilities: CapabilityMap;
  profile: NodeProfile;
  expressive: ExpressiveState;
  lifecycle: NodeLifecycleState;
}

export interface OrchestratorEvent {
  type:
    | 'node_joined'
    | 'node_heartbeat'
    | 'node_capabilities_updated'
    | 'node_expressive_updated'
    | 'node_status_changed';
  nodeId: string;
  timestamp: number;
  payload?: any;
}

export class OrchestratorStub {
  readonly nodes: Map<string, NodeMirror> = new Map();
  readonly events: OrchestratorEvent[] = [];
  private now: () => number;

  constructor(now: () => number) {
    this.now = now;
  }

  recordJoin(node: NodeMirror): void {
    const existing = this.nodes.get(node.id);
    const timestamp = this.now();

    const lifecycle: NodeLifecycleState = existing?.lifecycle ?? {
      lastHeartbeatAt: null,
      joinedAt: timestamp,
      status: 'joining',
    };

    const mirror: NodeMirror = {
      ...node,
      lifecycle,
      status: 'joining',
    };

    this.nodes.set(node.id, mirror);

    this.events.push({
      type: 'node_joined',
      nodeId: node.id,
      timestamp,
      payload: { node: mirror },
    });
  }

  recordHeartbeat(id: string): void {
    const node = this.nodes.get(id);
    const timestamp = this.now();
    if (!node) return;

    node.lifecycle.lastHeartbeatAt = timestamp;

    if (node.status !== 'online') {
      node.status = 'online';
      node.lifecycle.status = 'online';
      this.events.push({
        type: 'node_status_changed',
        nodeId: id,
        timestamp,
        payload: { status: 'online' },
      });
    }

    this.events.push({
      type: 'node_heartbeat',
      nodeId: id,
      timestamp,
    });
  }

  recordCapabilities(id: string, caps: CapabilityMap): void {
    const node = this.nodes.get(id);
    const timestamp = this.now();
    if (!node) return;

    node.capabilities = { ...node.capabilities, ...caps };

    this.events.push({
      type: 'node_capabilities_updated',
      nodeId: id,
      timestamp,
      payload: { capabilities: node.capabilities },
    });
  }

  recordExpressive(id: string, state: ExpressiveState): void {
    const node = this.nodes.get(id);
    const timestamp = this.now();
    if (!node) return;

    node.expressive = { ...node.expressive, ...state };

    this.events.push({
      type: 'node_expressive_updated',
      nodeId: id,
      timestamp,
      payload: { expressive: node.expressive },
    });
  }

  getNode(id: string): NodeMirror | undefined {
    return this.nodes.get(id);
  }

  getEventsByType(type: OrchestratorEvent['type']): OrchestratorEvent[] {
    return this.events.filter(e => e.type === type);
  }

  markOffline(id: string): void {
    const node = this.nodes.get(id);
    const timestamp = this.now();
    if (!node) return;

    node.status = 'offline';
    node.lifecycle.status = 'offline';

    this.events.push({
      type: 'node_status_changed',
      nodeId: id,
      timestamp,
      payload: { status: 'offline' },
    });
  }
}
