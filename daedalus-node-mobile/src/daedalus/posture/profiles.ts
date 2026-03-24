import { PostureProfile } from '../types';

export const POSTURE_PROFILES: Record<string, PostureProfile> = {
  'default.comfort': {
    id: 'default.comfort',
    label: 'Default Comfort',
    description: 'Relaxed, high comfort, medium autonomy, relaxed defense.',
    comfort: 'high',
    autonomy: 'medium',
    defenseMode: 'relaxed',
  },
  'analysis.focused': {
    id: 'analysis.focused',
    label: 'Analysis Focused',
    description: 'Higher autonomy, more focused, slightly more guarded.',
    comfort: 'medium',
    autonomy: 'high',
    defenseMode: 'guarded',
  },
  'defense.locked': {
    id: 'defense.locked',
    label: 'Defense Locked',
    description: 'Maximum defense, low autonomy, low comfort.',
    comfort: 'low',
    autonomy: 'low',
    defenseMode: 'locked',
  },
};
