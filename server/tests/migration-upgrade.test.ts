/**
 * UPGRADE / MIGRATION IN ANGER
 *
 * Takes a real persisted snapshot from a running system, applies schema
 * changes (add fields, remove fields, rename fields, change enum values),
 * writes a migration, and verifies Daedalus can survive its own evolution
 * without losing continuity, beings, or governance sanity.
 */

import fs from "node:fs";
import path from "node:path";
import request from "supertest";
import { createOrchestratorApp } from "../orchestrator";
import { daedalusStore } from "../orchestrator/daedalusStore";
import { governanceService } from "../orchestrator/governance/GovernanceService";
import {
  getNodeMirrorRegistry,
  resetNodeMirrorRegistry,
} from "../orchestrator/mirror/NodeMirror";
import { IDLE_EXPRESSIVE } from "../orchestrator/mirror/NodeMirror.types";
import {
  resetDaedalusEventBus,
} from "../orchestrator/DaedalusEventBus";
import { SnapshotPersistence, PersistableSnapshot } from "../orchestrator/persistence/SnapshotPersistence";
import { validateBeingConstitution } from "../../shared/daedalus/beingConstitution";
import { computeBehavioralField } from "../../shared/daedalus/behavioralGrammar";

jest.setTimeout(30_000);

function mkJoin(id: string) {
  return {
    nodeId: id,
    name: `Node-${id}`,
    capabilities: [{ name: "core", value: "enabled", enabled: true }],
    expressive: { ...IDLE_EXPRESSIVE },
    profile: {
      id,
      name: `Node-${id}`,
      kind: "server" as const,
      model: "migration-test",
      os: "linux",
      osVersion: "6.0",
      operatorId: "operator",
    },
  };
}

function mkHb(nodeId: string) {
  return { nodeId, timestamp: new Date().toISOString(), status: "alive" as const };
}

describe("UPGRADE / MIGRATION IN ANGER", () => {
  const app = createOrchestratorApp();
  const tmpDir = path.join(__dirname, ".migration-test");
  let reg = getNodeMirrorRegistry();

  beforeAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();
    reg = getNodeMirrorRegistry();

    if (!fs.existsSync(tmpDir)) fs.mkdirSync(tmpDir, { recursive: true });
  });

  afterAll(() => {
    resetNodeMirrorRegistry();
    resetDaedalusEventBus();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();

    try { fs.rmSync(tmpDir, { recursive: true }); } catch {}
  });

  // ═══════════════════════════════════════════════════════════════════════
  // PHASE 1: Build a realistic snapshot from live state
  // ═══════════════════════════════════════════════════════════════════════
  test("Phase 1: Build realistic state and persist", () => {
    // Join 10 nodes
    for (let i = 1; i <= 10; i++) {
      reg.handleJoin(mkJoin(`mig-${i}`));
      reg.handleHeartbeat(mkHb(`mig-${i}`));
    }

    // Add governance state
    governanceService.applyOverride({
      createdBy: { id: "operator", role: "OPERATOR" as const, label: "Op" },
      reason: "Pre-migration override",
      scope: "NODE" as const,
      effect: "ALLOW" as const,
    });
    governanceService.recordDrift({ severity: "LOW" as const, summary: "Pre-migration drift" });
    governanceService.castVote({
      being: { id: "operator", role: "OPERATOR" as const, label: "Op" },
      vote: "ALLOW" as const,
      weight: 0.5,
    });

    // Update a being
    daedalusStore.updateBeingPresence("operator", {
      continuity: { streak: 42, lastCheckIn: new Date().toISOString(), healthy: true },
      influenceLevel: 0.9,
    });

    // Save snapshot
    const snapshot: PersistableSnapshot = {
      beings: daedalusStore.getBeingPresences(),
      overrides: governanceService.listOverrides(),
      drifts: governanceService.listDrifts(),
      votes: governanceService.listVotes(),
      mirrors: reg.getAllMirrors(),
      savedAt: new Date().toISOString(),
    };

    const persistence = new SnapshotPersistence(path.join(tmpDir, "v1.json"));
    persistence.save(snapshot);

    expect(snapshot.beings.length).toBeGreaterThanOrEqual(2);
    expect(snapshot.mirrors.length).toBe(10);
    expect(snapshot.overrides.length).toBe(1);
    expect(snapshot.drifts.length).toBe(1);
    expect(snapshot.votes.length).toBe(1);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // PHASE 2: Simulate schema evolution scenarios
  // ═══════════════════════════════════════════════════════════════════════

  describe("Schema migration scenarios", () => {
    function loadV1(): PersistableSnapshot {
      const raw = fs.readFileSync(path.join(tmpDir, "v1.json"), "utf-8");
      return JSON.parse(raw);
    }

    test("Migration A: Add new field to beings (tags)", () => {
      const snapshot = loadV1();

      // Migrate: add `tags` field to each being
      const migrated = {
        ...snapshot,
        beings: snapshot.beings.map((b: any) => ({
          ...b,
          tags: b.tags ?? ["migrated"],
        })),
      };

      // Save migrated snapshot
      const persistence = new SnapshotPersistence(path.join(tmpDir, "v2a.json"));
      persistence.save(migrated);

      // Restore and verify
      const loaded = persistence.load()!;
      for (const b of loaded.beings) {
        expect((b as any).tags).toBeDefined();
        expect(Array.isArray((b as any).tags)).toBe(true);
      }

      // Original fields preserved
      const op = loaded.beings.find((b: any) => b.id === "operator");
      expect(op).toBeDefined();
      expect((op as any).influenceLevel).toBe(0.9);
      expect((op as any).continuity.streak).toBe(42);
    });

    test("Migration B: Remove deprecated field from overrides", () => {
      const snapshot = loadV1();

      // Migrate: remove a field (simulate deprecation)
      const migrated = {
        ...snapshot,
        overrides: snapshot.overrides.map((o: any) => {
          const { targetId, ...rest } = o; // Remove optional targetId
          return { ...rest, migratedAt: new Date().toISOString() };
        }),
      };

      const persistence = new SnapshotPersistence(path.join(tmpDir, "v2b.json"));
      persistence.save(migrated);

      const loaded = persistence.load()!;
      expect(loaded.overrides.length).toBe(1);
      expect((loaded.overrides[0] as any).migratedAt).toBeDefined();
    });

    test("Migration C: Rename field in mirrors (lifecycle.lastHeartbeat → lifecycle.lastPing)", () => {
      const snapshot = loadV1();

      const migrated = {
        ...snapshot,
        mirrors: snapshot.mirrors.map((m: any) => ({
          ...m,
          lifecycle: {
            ...m.lifecycle,
            lastPing: m.lifecycle.lastHeartbeat,
          },
        })),
      };

      const persistence = new SnapshotPersistence(path.join(tmpDir, "v2c.json"));
      persistence.save(migrated);

      const loaded = persistence.load()!;
      for (const m of loaded.mirrors) {
        expect((m as any).lifecycle.lastPing).toBeDefined();
      }
    });

    test("Migration D: Change enum value in drifts (LOW → MINOR)", () => {
      const snapshot = loadV1();

      const SEVERITY_MAP: Record<string, string> = {
        LOW: "MINOR",
        MEDIUM: "MODERATE",
        HIGH: "CRITICAL",
      };

      const migrated = {
        ...snapshot,
        drifts: snapshot.drifts.map((d: any) => ({
          ...d,
          severity: SEVERITY_MAP[d.severity] ?? d.severity,
        })),
      };

      const persistence = new SnapshotPersistence(path.join(tmpDir, "v2d.json"));
      persistence.save(migrated);

      const loaded = persistence.load()!;
      expect((loaded.drifts[0] as any).severity).toBe("MINOR");
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  // PHASE 3: Restore old snapshot into current runtime
  // ═══════════════════════════════════════════════════════════════════════
  test("Phase 3: Restore v1 snapshot into current runtime and verify continuity", () => {
    // Clear current state
    resetNodeMirrorRegistry();
    governanceService.clearOverrides();
    governanceService.clearDrifts();
    governanceService.clearVotes();

    reg = getNodeMirrorRegistry();

    // Load v1 snapshot
    const persistence = new SnapshotPersistence(path.join(tmpDir, "v1.json"));
    const snapshot = persistence.load()!;

    // Restore beings
    for (const being of snapshot.beings) {
      daedalusStore.updateBeingPresence(being.id, being);
    }

    // Restore governance
    for (const override of snapshot.overrides) {
      governanceService.applyOverride(override);
    }
    for (const drift of snapshot.drifts) {
      governanceService.recordDrift(drift);
    }
    for (const vote of snapshot.votes) {
      governanceService.castVote(vote);
    }

    // Verify beings survived
    const beings = daedalusStore.getBeingPresences();
    const op = beings.find(b => b.id === "operator");
    expect(op).toBeDefined();
    expect(op!.continuity?.streak).toBe(42);
    expect(op!.influenceLevel).toBe(0.9);

    // Verify governance survived
    expect(governanceService.listOverrides().length).toBe(1);
    expect(governanceService.listDrifts().length).toBe(1);
    expect(governanceService.listVotes().length).toBe(1);

    // Verify constitution holds
    const beingMap: Record<string, any> = {};
    for (const b of beings) beingMap[b.id] = b;
    const behavioral = computeBehavioralField(beingMap);
    const report = validateBeingConstitution(beings, governanceService.listVotes(), behavioral.dominantBeingId);
    expect(report.allPassed).toBe(true);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // PHASE 4: Restore then continue operating (evolution under load)
  // ═══════════════════════════════════════════════════════════════════════
  test("Phase 4: Continue operating after restore — no weird state", () => {
    // Join new nodes on top of restored state
    for (let i = 20; i <= 25; i++) {
      reg.handleJoin(mkJoin(`post-mig-${i}`));
      reg.handleHeartbeat(mkHb(`post-mig-${i}`));
    }

    // More governance actions
    governanceService.applyOverride({
      createdBy: { id: "operator", role: "OPERATOR" as const, label: "Op" },
      reason: "Post-migration override",
      scope: "GLOBAL" as const,
      effect: "ALLOW" as const,
    });

    // Cockpit view should include new nodes
    const views = reg.toCockpitView();
    expect(views.length).toBeGreaterThanOrEqual(6);

    // Posture should reflect accumulated state
    const posture = governanceService.getPostureSnapshot();
    expect(["OPEN", "ATTENTIVE", "GUARDED", "LOCKDOWN"]).toContain(posture.posture);

    // Constitution still holds
    const beings = daedalusStore.getBeingPresences();
    const beingMap: Record<string, any> = {};
    for (const b of beings) beingMap[b.id] = b;
    const behavioral = computeBehavioralField(beingMap);
    const report = validateBeingConstitution(beings, governanceService.listVotes(), behavioral.dominantBeingId);
    expect(report.allPassed).toBe(true);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // PHASE 5: Snapshot with extra/missing fields — forward compatibility
  // ═══════════════════════════════════════════════════════════════════════
  test("Phase 5: Load snapshot from 'future' version with extra fields", () => {
    const futureSnapshot = {
      beings: [{
        id: "operator",
        name: "Operator",
        posture: "companion",
        glow: { level: "low", intensity: 0.5 },
        attention: { level: "aware" },
        continuity: { streak: 99, lastCheckIn: new Date().toISOString(), healthy: true },
        influenceLevel: 0.95,
        updatedAt: new Date().toISOString(),
        // Future fields
        aiModel: "gpt-5",
        trustScore: 0.99,
        neuralFingerprint: "abc123",
      }],
      overrides: [],
      drifts: [],
      votes: [],
      mirrors: [],
      savedAt: new Date().toISOString(),
      // Future top-level fields
      schemaVersion: 2,
      clusterState: { leader: "node-1" },
    };

    const persistence = new SnapshotPersistence(path.join(tmpDir, "v-future.json"));
    persistence.save(futureSnapshot as any);

    const loaded = persistence.load()!;
    expect(loaded).not.toBeNull();
    expect(loaded.beings.length).toBe(1);
    expect((loaded.beings[0] as any).id).toBe("operator");
    expect((loaded as any).schemaVersion).toBe(2);

    // Can restore without crash
    daedalusStore.updateBeingPresence("operator", loaded.beings[0] as any);
    const op = daedalusStore.getBeingPresences().find(b => b.id === "operator");
    expect(op).toBeDefined();
    expect(op!.continuity?.streak).toBe(99);
  });

  // ═══════════════════════════════════════════════════════════════════════
  // PHASE 6: Snapshot from 'older' version with missing fields
  // ═══════════════════════════════════════════════════════════════════════
  test("Phase 6: Load snapshot from 'older' version with missing fields", () => {
    const oldSnapshot = {
      beings: [{
        id: "operator",
        name: "Operator",
        // Missing: posture, glow, attention, continuity, influenceLevel
      }],
      overrides: [],
      drifts: [],
      votes: [],
      // Missing: mirrors, savedAt
    };

    const persistence = new SnapshotPersistence(path.join(tmpDir, "v-old.json"));
    persistence.save(oldSnapshot as any);

    const loaded = persistence.load()!;
    expect(loaded).not.toBeNull();
    expect(loaded.beings.length).toBe(1);
    expect(loaded.mirrors).toBeUndefined();

    // Restore with defensive defaults
    const being = loaded.beings[0] as any;
    daedalusStore.updateBeingPresence(being.id, {
      ...being,
      posture: being.posture ?? "companion",
      glow: being.glow ?? { level: "low", intensity: 0.5 },
      attention: being.attention ?? { level: "aware" },
      continuity: being.continuity ?? { streak: 0, lastCheckIn: new Date().toISOString(), healthy: true },
      influenceLevel: being.influenceLevel ?? 0.5,
    });

    const op = daedalusStore.getBeingPresences().find(b => b.id === "operator");
    expect(op).toBeDefined();
  });

  // ═══════════════════════════════════════════════════════════════════════
  // PHASE 7: HTTP endpoints work after migration
  // ═══════════════════════════════════════════════════════════════════════
  test("Phase 7: All HTTP endpoints respond after migration cycles", async () => {
    const endpoints = [
      "/daedalus/snapshot",
      "/daedalus/governance/posture",
      "/daedalus/cockpit/nodes",
      "/daedalus/beings/presence",
      "/daedalus/constitution",
      "/daedalus/cockpit/summary",
    ];

    for (const ep of endpoints) {
      const res = await request(app).get(ep);
      expect(res.status).toBe(200);
    }
  });
});
