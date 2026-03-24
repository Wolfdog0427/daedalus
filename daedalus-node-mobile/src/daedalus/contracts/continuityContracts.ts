export interface ContinuityContract {
  markEvent: (kind: string, payload?: Record<string, unknown>) => void;
}
