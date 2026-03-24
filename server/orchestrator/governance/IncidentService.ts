import crypto from "crypto";
import { getDaedalusEventBus, nowIso } from "../DaedalusEventBus";

export interface Incident {
  id: string;
  title: string;
  notes: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: "open" | "investigating" | "mitigated" | "resolved";
  openedAt: string;
  closedAt: string | null;
  updatedAt: string;
}

export class IncidentService {
  private incidents: Incident[] = [];
  private static readonly MAX_INCIDENTS = 100;

  openIncident(input: {
    title: string;
    notes?: string;
    severity: Incident["severity"];
  }): Incident {
    const incident: Incident = {
      id: crypto.randomUUID(),
      title: input.title,
      notes: input.notes ?? "",
      severity: input.severity,
      status: "open",
      openedAt: nowIso(),
      closedAt: null,
      updatedAt: nowIso(),
    };

    if (this.incidents.length >= IncidentService.MAX_INCIDENTS) {
      this.incidents.shift();
    }
    this.incidents.push(incident);

    getDaedalusEventBus().publish({
      type: "GOVERNANCE_OVERRIDE_APPLIED",
      timestamp: nowIso(),
      summary: `Incident opened: ${incident.title} [${incident.severity}]`,
    });

    return incident;
  }

  updateIncident(
    id: string,
    patch: Partial<Pick<Incident, "title" | "notes" | "severity" | "status">>,
  ): Incident | null {
    const incident = this.incidents.find((i) => i.id === id);
    if (!incident) return null;

    if (patch.title !== undefined) incident.title = patch.title;
    if (patch.notes !== undefined) incident.notes = patch.notes;
    if (patch.severity !== undefined) incident.severity = patch.severity;
    if (patch.status !== undefined) {
      incident.status = patch.status;
      if (patch.status === "resolved" || patch.status === "mitigated") {
        incident.closedAt = nowIso();
      }
    }
    incident.updatedAt = nowIso();

    return { ...incident };
  }

  resolveIncident(id: string): Incident | null {
    return this.updateIncident(id, { status: "resolved" });
  }

  listIncidents(filter?: { status?: Incident["status"] }): Incident[] {
    if (filter?.status) {
      return this.incidents.filter((i) => i.status === filter.status);
    }
    return [...this.incidents];
  }

  getIncident(id: string): Incident | null {
    return this.incidents.find((i) => i.id === id) ?? null;
  }

  clearResolved(): number {
    const before = this.incidents.length;
    this.incidents = this.incidents.filter((i) => i.status !== "resolved");
    return before - this.incidents.length;
  }
}

export const incidentService = new IncidentService();
