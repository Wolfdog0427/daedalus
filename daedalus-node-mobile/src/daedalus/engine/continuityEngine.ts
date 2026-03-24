import { ContinuityEvent, DaedalusState } from '../types';

let continuityCounter = 0;

export function applyContinuityEvent(
  state: DaedalusState,
  kind: string,
  payload?: Record<string, unknown>
): DaedalusState {
  const event: ContinuityEvent = {
    id: `evt_${++continuityCounter}`,
    kind,
    at: Date.now(),
    payload,
  };

  return {
    ...state,
    continuityEvents: [...state.continuityEvents, event],
  };
}
