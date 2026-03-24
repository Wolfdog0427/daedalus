/**
 * Daedalus shared constants — labels, enums, and magic values
 * used across orchestrator, node, kernel, and cockpit.
 */

export const RISK_TIER_LABELS: Record<string, string> = {
  low: 'Low',
  medium: 'Medium',
  elevated: 'Elevated',
  critical: 'Critical',
};

export const VERIFICATION_LABELS: Record<string, string> = {
  none: 'None required',
  soft: 'Soft verification',
  strong: 'Strong verification',
};

export const POSTURE_MODES = ['idle', 'normal', 'elevated', 'defensive'] as const;
