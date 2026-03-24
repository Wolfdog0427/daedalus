import fs from "node:fs";
import path from "node:path";

export interface PersistableSnapshot {
  beings: any[];
  overrides: any[];
  drifts: any[];
  votes: any[];
  mirrors: any[];
  eventHistory?: any[];
  incidents?: any[];
  savedAt: string;
}

const DEFAULT_PATH = path.resolve(process.cwd(), ".daedalus-snapshot.json");

export class SnapshotPersistence {
  private filePath: string;
  private intervalHandle: ReturnType<typeof setInterval> | null = null;

  constructor(filePath: string = DEFAULT_PATH) {
    this.filePath = filePath;
  }

  save(snapshot: PersistableSnapshot): void {
    try {
      const json = JSON.stringify(snapshot, null, 2);
      fs.writeFileSync(this.filePath, json, "utf-8");
    } catch (err) {
      console.error("[persistence] Failed to save snapshot:", err);
    }
  }

  load(): PersistableSnapshot | null {
    try {
      if (!fs.existsSync(this.filePath)) return null;
      const raw = fs.readFileSync(this.filePath, "utf-8");
      return JSON.parse(raw) as PersistableSnapshot;
    } catch (err) {
      console.error("[persistence] Failed to load snapshot:", err);
      return null;
    }
  }

  startAutoSave(collector: () => PersistableSnapshot, intervalMs: number = 30_000): void {
    this.stopAutoSave();
    this.intervalHandle = setInterval(() => {
      this.save(collector());
    }, intervalMs);
  }

  stopAutoSave(): void {
    if (this.intervalHandle) {
      clearInterval(this.intervalHandle);
      this.intervalHandle = null;
    }
  }
}

let singleton: SnapshotPersistence | null = null;

export function getSnapshotPersistence(): SnapshotPersistence {
  if (!singleton) singleton = new SnapshotPersistence();
  return singleton;
}
