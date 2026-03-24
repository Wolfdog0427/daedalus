export interface NetworkMessage {
  id: string;
  from: string;
  to: string;
  payload: any;
  createdAt: number;
}

export interface NetworkConfig {
  defaultLatencyMs: number;
  packetLossProbability: number;
}

export interface ChaosConfig {
  randomLatencyMaxMs?: number;
  randomPacketLossProbability?: number;
  randomPartitionProbability?: number;
}

export class TestNetwork {
  private messages: NetworkMessage[] = [];
  private partitions: Set<string> = new Set();
  private config: NetworkConfig;
  private chaos: ChaosConfig = {};
  private now: () => number;
  private nextId = 1;

  constructor(config: Partial<NetworkConfig> = {}, now: () => number) {
    this.config = {
      defaultLatencyMs: config.defaultLatencyMs ?? 0,
      packetLossProbability: config.packetLossProbability ?? 0,
    };
    this.now = now;
  }

  // ── Chaos controls ─────────────────────────────────────────────────

  enableChaos(config: ChaosConfig): void {
    this.chaos = { ...config };
  }

  disableChaos(): void {
    this.chaos = {};
  }

  getChaos(): Readonly<ChaosConfig> {
    return this.chaos;
  }

  // ── Blocking ───────────────────────────────────────────────────────

  /**
   * Pure deterministic check — only persistent partitions.
   * Unchanged from the original; used by tests that assert on
   * explicit partition/heal semantics.
   */
  isPartitioned(id: string): boolean {
    return this.partitions.has(id);
  }

  /**
   * Combined gate: persistent partitions + transient chaos effects.
   * When chaos is disabled (empty config) this degrades to isPartitioned.
   * TestTransport calls this for every request.
   */
  isBlocked(id: string): boolean {
    if (this.partitions.has(id)) return true;

    const lossProb =
      this.chaos.randomPacketLossProbability ?? this.config.packetLossProbability;
    if (lossProb > 0 && Math.random() < lossProb) return true;

    const partProb = this.chaos.randomPartitionProbability ?? 0;
    if (partProb > 0 && Math.random() < partProb) return true;

    return false;
  }

  // ── Message queue ──────────────────────────────────────────────────

  send(from: string, to: string, payload: any): void {
    if (this.isPartitioned(from) || this.isPartitioned(to)) {
      return;
    }

    const lossProb =
      this.chaos.randomPacketLossProbability ?? this.config.packetLossProbability;

    if (Math.random() < lossProb) {
      return;
    }

    const msg: NetworkMessage = {
      id: `msg_${this.nextId++}`,
      from,
      to,
      payload,
      createdAt: this.now(),
    };

    this.messages.push(msg);

    const partProb = this.chaos.randomPartitionProbability ?? 0;
    if (partProb > 0 && Math.random() < partProb) {
      this.partition([to]);
    }
  }

  deliverNext(): NetworkMessage | undefined {
    if (this.messages.length === 0) return undefined;
    return this.messages.shift()!;
  }

  drain(): NetworkMessage[] {
    const drained = [...this.messages];
    this.messages = [];
    return drained;
  }

  partition(nodeIds: string[]): void {
    for (const id of nodeIds) {
      this.partitions.add(id);
    }
  }

  heal(): void {
    this.partitions.clear();
  }

  getPendingCount(): number {
    return this.messages.length;
  }
}
