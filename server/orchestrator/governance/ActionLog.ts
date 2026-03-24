import { nowIso } from "../DaedalusEventBus";
import { governanceService } from "./GovernanceService";
import { incidentService } from "./IncidentService";

export type ActionKind =
  | "CREATE_OVERRIDE"
  | "REMOVE_OVERRIDE"
  | "CLEAR_OVERRIDES"
  | "CAST_VOTE"
  | "CLEAR_VOTES"
  | "RECORD_DRIFT"
  | "CLEAR_DRIFTS"
  | "OPEN_INCIDENT"
  | "UPDATE_INCIDENT";

export interface ActionEntry {
  id: number;
  kind: ActionKind;
  timestamp: string;
  payload: any;
  undone: boolean;
  undoable: boolean;
}

export class ActionLog {
  private entries: ActionEntry[] = [];
  private nextId = 1;
  private static readonly MAX_ENTRIES = 500;

  record(kind: ActionKind, payload: any, undoable = true): ActionEntry {
    const entry: ActionEntry = {
      id: this.nextId++,
      kind,
      timestamp: nowIso(),
      payload,
      undone: false,
      undoable,
    };
    if (this.entries.length >= ActionLog.MAX_ENTRIES) {
      this.entries.shift();
    }
    this.entries.push(entry);
    return entry;
  }

  undo(actionId: number): { success: boolean; reason?: string } {
    const entry = this.entries.find((e) => e.id === actionId);
    if (!entry) return { success: false, reason: "Action not found" };
    if (entry.undone) return { success: false, reason: "Already undone" };
    if (!entry.undoable) return { success: false, reason: "Action is not undoable" };

    switch (entry.kind) {
      case "CREATE_OVERRIDE": {
        const removed = governanceService.removeOverride(entry.payload?.id);
        if (!removed) return { success: false, reason: "Override already removed" };
        break;
      }
      case "RECORD_DRIFT": {
        const drifts = governanceService.listDrifts();
        const idx = drifts.findIndex((d) => d.id === entry.payload?.id);
        if (idx === -1) return { success: false, reason: "Drift already cleared" };
        governanceService.clearDrifts();
        for (const d of drifts) {
          if (d.id !== entry.payload.id) governanceService.recordDrift(d);
        }
        break;
      }
      case "OPEN_INCIDENT": {
        incidentService.resolveIncident(entry.payload?.id);
        break;
      }
      default:
        return { success: false, reason: `Undo not implemented for ${entry.kind}` };
    }

    entry.undone = true;
    return { success: true };
  }

  list(limit?: number): ActionEntry[] {
    if (!limit) return [...this.entries];
    return this.entries.slice(-limit);
  }

  clear(): void {
    this.entries = [];
  }
}

export const actionLog = new ActionLog();
