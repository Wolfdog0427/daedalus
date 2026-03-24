import { PostureProfile } from '../types';
import { POSTURE_PROFILES } from '../posture/profiles';

export function resolvePostureProfile(id: string): PostureProfile | null {
  return POSTURE_PROFILES[id] ?? null;
}
