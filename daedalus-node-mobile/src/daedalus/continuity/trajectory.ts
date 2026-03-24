import { ContinuityEvent } from '../types';

export function deriveTrajectory(events: ContinuityEvent[]): string {
  if (events.length === 0) {
    return 'idle';
  }
  const last = events[events.length - 1];
  if (last.kind.includes('error')) return 'risk';
  if (last.kind.includes('mounted')) return 'booting';
  return 'flow';
}
