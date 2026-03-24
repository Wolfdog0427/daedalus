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
    },
  );

  router.post(
    "/mirror/capabilities",
    (req: Request, res: Response) => {
      const payload = req.body as NodeCapSyncPayload;
      if (!payload?.nodeId) {
        res.status(400).json({ error: "Missing nodeId" });
        return;
      }
      const registry = getNodeMirrorRegistry();
      const deltas = registry.handleCapSync(payload);
      res.json({ nodeId: payload.nodeId, deltaCount: deltas.length, deltas });
    },
  );

  router.post(
    "/mirror/expressive",
    (req: Request, res: Response) => {
      const payload = req.body as NodeExpressiveSyncPayload;
      if (!payload?.nodeId) {
        res.status(400).json({ error: "Missing nodeId" });
        return;
      }
      const registry = getNodeMirrorRegistry();
      const deltas = registry.handleExpressiveSync(payload);
      res.json({ nodeId: payload.nodeId, deltaCount: deltas.length, deltas });
    },
  );

  router.post(
    "/mirror/profile",
    (req: Request, res: Response) => {
      const payload = req.body as NodeProfileSyncPayload;
      if (!payload?.nodeId) {
        res.status(400).json({ error: "Missing nodeId" });
        return;
      }
      const registry = getNodeMirrorRegistry();
      registry.handleProfileSync(payload);
      res.json({ nodeId: payload.nodeId, synced: true });
    },
  );

  router.post(
    "/mirror/quarantine",
    (req: Request, res: Response) => {
      const { nodeId } = req.body as { nodeId: string };
      if (!nodeId) {
        res.status(400).json({ error: "Missing nodeId" });
        return;
      }
      const registry = getNodeMirrorRegistry();
      registry.handleQuarantine(nodeId);
      res.json({ nodeId, quarantined: true });
    },
  );

  router.post(
    "/mirror/detach",
    (req: Request, res: Response) => {
      const { nodeId } = req.body as { nodeId: string };
      if (!nodeId) {
        res.status(400).json({ error: "Missing nodeId" });
        return;
      }
      const registry = getNodeMirrorRegistry();
      registry.handleDetach(nodeId);
      res.json({ nodeId, detached: true });
    },
  );

  return router;
}
