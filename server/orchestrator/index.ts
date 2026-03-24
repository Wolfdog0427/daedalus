import express from "express";
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

  return app;
};
