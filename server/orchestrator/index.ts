import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import { daedalusRouter, getStrategyService } from "./daedalusRouter";
import { requireAuth } from "./middleware/auth";
import { rateLimit } from "./middleware/rateLimit";
import { getNodeMirrorRegistry } from "./mirror/NodeMirror";
import { governanceService } from "./governance/GovernanceService";

const TICK_INTERVAL_MS = parseInt(process.env.DAEDALUS_TICK_MS ?? "5000", 10);

let tickTimer: ReturnType<typeof setInterval> | null = null;

export const createOrchestratorApp = () => {
  const app = express();

  const allowedOrigins = process.env.DAEDALUS_CORS_ORIGINS;
  app.use(cors({
    origin: allowedOrigins ? allowedOrigins.split(",").map(s => s.trim()) : true,
    credentials: true,
  }));
  app.use(express.json({ limit: "1mb" }));

  app.get("/health", (_req, res) => {
    res.json({ status: "ok", service: "daedalus-orchestrator", timestamp: new Date().toISOString() });
  });

  app.use("/daedalus", rateLimit(), requireAuth, daedalusRouter);

  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    if (status !== 500) {
      res.status(status).json({ error: err.message });
      return;
    }
    console.error("[daedalus] Unhandled route error:", err.message, err.stack);
    res.status(500).json({
      error: "Internal server error",
      message: process.env.NODE_ENV === "production" ? undefined : err.message,
    });
  });

  if (!tickTimer) {
    tickTimer = setInterval(() => {
      try { getStrategyService().evaluate(); }
      catch (e: any) { console.error("[daedalus] evaluate() error:", e?.message); }

      try { getNodeMirrorRegistry().sweepStaleHeartbeats?.(); }
      catch (e: any) { console.error("[daedalus] sweepStaleHeartbeats error:", e?.message); }

      try { governanceService.sweepExpired?.(); }
      catch (e: any) { console.error("[daedalus] sweepExpired error:", e?.message); }
    }, TICK_INTERVAL_MS);
  }

  return app;
};
