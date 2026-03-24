import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import { daedalusRouter } from "./daedalusRouter";
import { requireAuth } from "./middleware/auth";
import { rateLimit } from "./middleware/rateLimit";

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

  return app;
};
