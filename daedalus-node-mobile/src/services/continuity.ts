import AsyncStorage from "@react-native-async-storage/async-storage";

const CONTINUITY_KEY = "@daedalus:continuity";

export type ContinuityState = {
  lastHeartbeatAt: string | null;
  lastJoinAt: string | null;
  lastPresenceAckAt: string | null;
};

const defaultState: ContinuityState = {
  lastHeartbeatAt: null,
  lastJoinAt: null,
  lastPresenceAckAt: null
};

export async function loadContinuity(): Promise<ContinuityState> {
  try {
    const raw = await AsyncStorage.getItem(CONTINUITY_KEY);
    if (!raw) return defaultState;
    return { ...defaultState, ...JSON.parse(raw) };
  } catch {
    return defaultState;
  }
}

export async function saveContinuity(patch: Partial<ContinuityState>) {
  const current = await loadContinuity();
  const next = { ...current, ...patch };
  await AsyncStorage.setItem(CONTINUITY_KEY, JSON.stringify(next));
  return next;
}
