import { ContinuityEvent } from '../types';

export function summarizeContinuity(events: ContinuityEvent[]): {
  lastEvent?: ContinuityEvent;
  count: number;
} {
  if (events.length === 0) {
    return { count: 0 };
  }
  return {
    lastEvent: events[events.length - 1],
    count: events.length,
  };
}
