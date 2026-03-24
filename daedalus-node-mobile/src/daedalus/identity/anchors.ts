export const IDENTITY_ANCHORS_DEFS: Record<
  string,
  { label: string; kind: 'operator' | 'node' | 'environment' }
> = {
  operator: {
    label: 'Operator',
    kind: 'operator',
  },
  node: {
    label: 'Node',
    kind: 'node',
  },
  environment: {
    label: 'Environment',
    kind: 'environment',
  },
};
