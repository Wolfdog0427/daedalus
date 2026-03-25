import express, { Request, Response } from "express";
import { getNodeMirrorRegistry } from "./NodeMirror";
import type {
  NodeJoinPayload,
  NodeHeartbeatPayload,
  NodeCapSyncPayload,
  NodeExpressiveSyncPayload,
  NodeProfileSyncPayload,
} from "./NodeMirror.types";

export function createMirrorRouter() {
  const router = express.Router();

  router.post(
    "/mirror/join",
    (req: Request, res: Response) => {
      const payload = req.body as NodeJoinPayload;
      if (!payload?.nodeId || !payload?.name) {
        res.status(400).json({ error: "Missing nodeId or name" });
        return;
      }
      if (!Array.isArray(payload.capabilities) || typeof payload.expressive !== "object" || payload.expressive === null) {
        res.status(400).json({ error: "Missing or invalid capabilities/expressive in join payload" });
        return;
      }
      try {
        const registry = getNodeMirrorRegistry();
        const mirror = registry.handleJoin(payload);
        res.status(201).json({ nodeId: mirror.id, status: mirror.status, phase: mirror.lifecycle.phase });
      } catch (err: any) {
        console.error("[mirror] /mirror/join error:", err?.message);
        res.status(409).json({ error: err?.message ?? "Failed to join node" });
      }
    },
  );

  router.post(
    "/mirror/heartbeat",
    (req: Request, res: Response) => {
      try {
        const payload = req.body as NodeHeartbeatPayload;
        if (!payload?.nodeId) {
          res.status(400).json({ error: "Missing nodeId" });
          return;
        }
        const registry = getNodeMirrorRegistry();
        const mirror = registry.handleHeartbeat(payload);
        if (!mirror) {
          res.status(404).json({ error: `Node "${payload.nodeId}" not found` });
          return;
        }
        res.json({ nodeId: mirror.id, status: mirror.status, phase: mirror.lifecycle.phase });
      } catch (err: any) {
        console.error("[mirror] /mirror/heartbeat error:", err?.message);
        res.status(500).json({ error: err?.message ?? "Failed to process heartbeat" });
      }
    },
  );

  router.post(
    "/mirror/capabilities",
    (req: Request, res: Response) => {
      try {
        const payload = req.body as NodeCapSyncPayload;
        if (!payload?.nodeId) {
          res.status(400).json({ error: "Missing nodeId" });
          return;
        }
        const registry = getNodeMirrorRegistry();
        if (!registry.getMirror(payload.nodeId)) {
          res.status(404).json({ error: `Node "${payload.nodeId}" not found` });
          return;
        }
        const deltas = registry.handleCapSync(payload);
        res.json({ nodeId: payload.nodeId, deltaCount: deltas.length, deltas });
      } catch (err: any) {
        console.error("[mirror] /mirror/capabilities error:", err?.message);
        res.status(500).json({ error: err?.message ?? "Failed to sync capabilities" });
      }
    },
  );

  router.post(
    "/mirror/expressive",
    (req: Request, res: Response) => {
      try {
        const payload = req.body as NodeExpressiveSyncPayload;
        if (!payload?.nodeId) {
          res.status(400).json({ error: "Missing nodeId" });
          return;
        }
        const registry = getNodeMirrorRegistry();
        if (!registry.getMirror(payload.nodeId)) {
          res.status(404).json({ error: `Node "${payload.nodeId}" not found` });
          return;
        }
        const deltas = registry.handleExpressiveSync(payload);
        res.json({ nodeId: payload.nodeId, deltaCount: deltas.length, deltas });
      } catch (err: any) {
        console.error("[mirror] /mirror/expressive error:", err?.message);
        res.status(500).json({ error: err?.message ?? "Failed to sync expressive state" });
      }
    },
  );

  router.post(
    "/mirror/profile",
    (req: Request, res: Response) => {
      try {
        const payload = req.body as NodeProfileSyncPayload;
        if (!payload?.nodeId) {
          res.status(400).json({ error: "Missing nodeId" });
          return;
        }
        const registry = getNodeMirrorRegistry();
        if (!registry.getMirror(payload.nodeId)) {
          res.status(404).json({ error: `Node "${payload.nodeId}" not found` });
          return;
        }
        registry.handleProfileSync(payload);
        res.json({ nodeId: payload.nodeId, synced: true });
      } catch (err: any) {
        console.error("[mirror] /mirror/profile error:", err?.message);
        res.status(500).json({ error: err?.message ?? "Failed to sync profile" });
      }
    },
  );

  router.post(
    "/mirror/quarantine",
    (req: Request, res: Response) => {
      try {
        const { nodeId } = req.body as { nodeId: string };
        if (!nodeId) {
          res.status(400).json({ error: "Missing nodeId" });
          return;
        }
        const registry = getNodeMirrorRegistry();
        registry.handleQuarantine(nodeId);
        res.json({ nodeId, quarantined: true });
      } catch (err: any) {
        console.error("[mirror] /mirror/quarantine error:", err?.message);
        res.status(500).json({ error: err?.message ?? "Failed to quarantine node" });
      }
    },
  );

  router.post(
    "/mirror/detach",
    (req: Request, res: Response) => {
      try {
        const { nodeId } = req.body as { nodeId: string };
        if (!nodeId) {
          res.status(400).json({ error: "Missing nodeId" });
          return;
        }
        const registry = getNodeMirrorRegistry();
        registry.handleDetach(nodeId);
        res.json({ nodeId, detached: true });
      } catch (err: any) {
        console.error("[mirror] /mirror/detach error:", err?.message);
        res.status(500).json({ error: err?.message ?? "Failed to detach node" });
      }
    },
  );

  return router;
}
