import { CapabilityMap, ExpressiveState, NodeProfile } from '../harness/OrchestratorStub';

export function makeProfile(name: string): NodeProfile {
  return {
    name,
    kind: 'test-node',
    tags: ['test', 'multinode'],
  };
}

export function makeCapabilities(base?: Partial<CapabilityMap>): CapabilityMap {
  return {
    'daedalus.core': true,
    'daedalus.expressive': true,
    ...base,
  };
}

export function makeExpressive(base?: Partial<ExpressiveState>): ExpressiveState {
  return {
    glow: 'baseline',
    posture: 'neutral',
    affect: 'calm',
    continuity: 'fresh',
    ...base,
  };
}
