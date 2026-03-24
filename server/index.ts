import { createOrchestratorApp } from "./orchestrator";
import { getSnapshotPersistence } from "./orchestrator/persistence/SnapshotPersistence";
import { daedalusStore } from "./orchestrator/daedalusStore";
import { governanceService } from "./orchestrator/governance/GovernanceService";
import { getNodeMirrorRegistry } from "./orchestrator/mirror/NodeMirror";
import { getDaedalusEventBus } from "./orchestrator/DaedalusEventBus";

const PORT = parseInt(process.env.DAEDALUS_PORT ?? "3001", 10);
const HOST = process.env.DAEDALUS_HOST ?? "0.0.0.0";

const app = createOrchestratorApp();

function collectSnapshot() {
  governanceService.sweepExpired();
  return {
    beings: daedalusStore.getBeingPresences(),
    overrides: governanceService.listOverrides(),
    drifts: governanceService.listDrifts(),
    votes: governanceService.listVotes(),
    mirrors: getNodeMirrorRegistry().getAllMirrors(),
    eventHistory: getDaedalusEventBus().getHistory(),
    savedAt: new Date().toISOString(),
  };
}

const server = app.listen(PORT, HOST, () => {
  console.log(`[daedalus] Orchestrator listening on http://${HOST}:${PORT}`);

  const persistence = getSnapshotPersistence();
  try {
    const saved = persistence.load();
    if (saved) {
      console.log(`[persistence] Restoring snapshot from ${saved.savedAt}`);
      for (const being of saved.beings ?? []) {
        try {
          const updated = daedalusStore.updateBeingPresence(being.id, being);
          if (!updated) {
            daedalusStore.addBeingPresence(being);
          }
        } catch (err: any) {
          console.warn(`[persistence] Skipping being "${being?.id}":`, err?.message);
        }
      }
      for (const override of saved.overrides ?? []) {
        try { governanceService.applyOverride(override); } catch (err: any) {
          console.warn("[persistence] Skipping override:", err?.message);
        }
      }
      for (const vote of saved.votes ?? []) {
        try { governanceService.castVote(vote); } catch (err: any) {
          console.warn("[persistence] Skipping vote:", err?.message);
        }
      }
      for (const drift of saved.drifts ?? []) {
        try { governanceService.recordDrift(drift); } catch (err: any) {
          console.warn("[persistence] Skipping drift:", err?.message);
        }
      }
    }
  } catch (err: any) {
    console.error("[persistence] Failed to restore snapshot:", err?.message);
  }

  persistence.startAutoSave(collectSnapshot);
});

function gracefulShutdown(signal: string) {
  console.log(`[daedalus] ${signal} received — saving final snapshot...`);
  const persistence = getSnapshotPersistence();
  persistence.stopAutoSave();
  persistence.save(collectSnapshot());
  console.log("[daedalus] Snapshot saved. Shutting down.");
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000);
}

process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
process.on("SIGINT", () => gracefulShutdown("SIGINT"));
