export interface DaedalusContract {
  version: string;
  surfaces: {
    presence: string;
    capabilities: string;
    expressive: string;
    continuity: string;
    risk: string;
    verification: string;
    notifications: string;
  };
  invariants: {
    operatorSovereignty: boolean;
    explicitOverride: boolean;
    trustBoundaries: boolean;
    expressiveDiscipline: boolean;
  };
}

export const DaedalusContractV04: DaedalusContract = {
  version: '0.4',
  surfaces: {
    presence: 'v0.3',
    capabilities: 'v0.4',
    expressive: 'v0.4',
    continuity: 'v0.3',
    risk: 'v0.3',
    verification: 'v0.3',
    notifications: 'v0.4',
  },
  invariants: {
    operatorSovereignty: true,
    explicitOverride: true,
    trustBoundaries: true,
    expressiveDiscipline: true,
  },
};
