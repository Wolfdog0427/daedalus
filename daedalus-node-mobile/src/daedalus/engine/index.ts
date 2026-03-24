import { PostureProfile, DaedalusState, NotificationPayload } from '../types';
import { resolvePostureProfile } from './postureEngine';
import { applyContinuityEvent } from './continuityEngine';
import { resolveIdentityAnchor } from './identityEngine';
import { routeNotification } from './notificationEngine';

export function createInitialState(): DaedalusState {
  return {
    postureProfile: null,
    identityAnchors: [],
    continuityEvents: [],
  };
}

export function setPostureProfile(state: DaedalusState, id: string): DaedalusState {
  const profile: PostureProfile | null = resolvePostureProfile(id);
  return {
    ...state,
    postureProfile: profile,
  };
}

export function setIdentityAnchor(
  state: DaedalusState,
  id: string,
  value: string
): DaedalusState {
  const anchor = resolveIdentityAnchor(id, value);
  const others = state.identityAnchors.filter(a => a.id !== id);
  return {
    ...state,
    identityAnchors: [...others, anchor],
  };
}

export function addContinuityEvent(
  state: DaedalusState,
  kind: string,
  payload?: Record<string, unknown>
): DaedalusState {
  return applyContinuityEvent(state, kind, payload);
}

export function dispatchNotification(payload: NotificationPayload) {
  routeNotification(payload);
}
