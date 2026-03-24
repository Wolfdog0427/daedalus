import { IdentityAnchor } from '../types';
import { IDENTITY_ANCHORS_DEFS } from '../identity/anchors';

export function resolveIdentityAnchor(id: string, value: string): IdentityAnchor {
  const def = IDENTITY_ANCHORS_DEFS[id];
  return {
    id,
    label: def?.label ?? id,
    kind: def?.kind ?? 'environment',
    value,
  };
}
