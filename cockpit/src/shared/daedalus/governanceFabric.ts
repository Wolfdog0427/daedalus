/** Feature toggle: set to false to disable governance fabric. */
export const GOVERNANCE_FABRIC_ENABLED = true;

import type { TierName, GovernanceFabricSnapshot } from "./postAutonomy";

export type FabricHealthLabel = "stable" | "active" | "busy" | "overloaded";

export interface FabricHealth {
  label: FabricHealthLabel;
  totalDecisions: number;
  approvals: number;
  rejections: number;
  decisionRate: number; // decisions per minute within window
}

/**
 * The complete governance dashboard — a single-pane view
 * over the entire autonomy stack for the operator.
 */
export interface FabricDashboard {
  health: FabricHealth;
  activeTierCount: number;
  activeTiers: TierName[];
  escalationDetected: boolean;
  cappingApplied: boolean;
  pendingCount: number;
}

export interface FabricConfig {
  windowMs: number;
  busyThreshold: number;      // decisions/min to be considered "busy"
  overloadedThreshold: number; // decisions/min to be considered "overloaded"
}

export const FABRIC_CONFIG_DEFAULTS: FabricConfig = {
  windowMs: 120_000, // 2-minute decision window
  busyThreshold: 5,
  overloadedThreshold: 10,
};

export const FABRIC_HEALTH_IDLE: FabricHealth = {
  label: "stable",
  totalDecisions: 0,
  approvals: 0,
  rejections: 0,
  decisionRate: 0,
};

export const FABRIC_DASHBOARD_IDLE: FabricDashboard = {
  health: FABRIC_HEALTH_IDLE,
  activeTierCount: 0,
  activeTiers: [],
  escalationDetected: false,
  cappingApplied: false,
  pendingCount: 0,
};
