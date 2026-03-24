import express from "express";
import cors from "cors";
import { recordHeartbeat, recordJoin, listNodes } from "./presenceState";

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 4001;

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "daedalus-presence-server" });
});

app.post("/heartbeat", (req, res) => {
  const body = req.body ?? {};
  if (!body.nodeId) {
    return res.status(400).json({ error: "nodeId required" });
  }
  const node = recordHeartbeat({
    nodeId: body.nodeId,
    label: body.label ?? "unknown",
    platform: body.platform ?? "unknown",
    deviceType: body.deviceType ?? "unknown",
    operator: body.operator ?? "unknown",
    timestamp: body.timestamp ?? new Date().toISOString()
  });
  res.json({ ok: true, node });
});

app.post("/join", (req, res) => {
  const body = req.body ?? {};
  if (!body.nodeId) {
    return res.status(400).json({ error: "nodeId required" });
  }
  const node = recordJoin({
    nodeId: body.nodeId,
    label: body.label ?? "unknown",
    platform: body.platform ?? "unknown",
    deviceType: body.deviceType ?? "unknown",
    operator: body.operator ?? "unknown",
    requestedAt: body.requestedAt ?? new Date().toISOString()
  });
  res.json({ ok: true, node });
});

app.get("/nodes", (_req, res) => {
  res.json({ nodes: listNodes() });
});

app.listen(PORT, () => {
  console.log(`Daedalus presence server listening on :${PORT}`);
});
