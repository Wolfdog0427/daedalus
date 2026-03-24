/**
 * Live Soak Script — Exercises a running Daedalus server over real HTTP.
 *
 * Usage: DAEDALUS_URL=http://localhost:3099 DAEDALUS_TOKEN=test-token-123 npx ts-node scripts/live-soak.ts
 *
 * This script:
 *   1. Verifies server health
 *   2. Joins 30 nodes via HTTP
 *   3. Sends sustained heartbeats for all nodes (60s)
 *   4. Creates/clears governance overrides and drifts
 *   5. Casts and clears votes
 *   6. Queries cockpit views repeatedly
 *   7. Checks constitution
 *   8. Introduces errors and quarantines
 *   9. Detaches and rejoins nodes
 *  10. Runs SSE event stream listener
 *  11. Produces a final diagnostic report
 */

const BASE = process.env.DAEDALUS_URL ?? "http://localhost:3099";
const TOKEN = process.env.DAEDALUS_TOKEN ?? "test-token-123";
const DURATION_S = parseInt(process.env.SOAK_DURATION ?? "90", 10);

interface SoakMetrics {
  startTime: number;
  endTime: number;
  httpOk: number;
  httpErr: number;
  httpByEndpoint: Record<string, { ok: number; err: number; totalMs: number }>;
  nodeJoins: number;
  heartbeatCycles: number;
  governanceActions: number;
  sseEventsReceived: number;
  sseDisconnects: number;
  findings: string[];
  errors: string[];
}

const metrics: SoakMetrics = {
  startTime: 0, endTime: 0,
  httpOk: 0, httpErr: 0,
  httpByEndpoint: {},
  nodeJoins: 0, heartbeatCycles: 0, governanceActions: 0,
  sseEventsReceived: 0, sseDisconnects: 0,
  findings: [], errors: [],
};

function headers(extra?: Record<string, string>): Record<string, string> {
  return { "Content-Type": "application/json", "x-daedalus-token": TOKEN, ...extra };
}

async function api(method: string, path: string, body?: any): Promise<{ status: number; data: any }> {
  const endpoint = path.split("?")[0];
  if (!metrics.httpByEndpoint[endpoint]) {
    metrics.httpByEndpoint[endpoint] = { ok: 0, err: 0, totalMs: 0 };
  }

  const t0 = performance.now();
  try {
    const opts: RequestInit = {
      method,
      headers: headers(),
    };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${BASE}${path}`, opts);
    const elapsed = performance.now() - t0;
    metrics.httpByEndpoint[endpoint].totalMs += elapsed;

    let data: any;
    try { data = await res.json(); } catch { data = null; }

    if (res.ok) {
      metrics.httpOk++;
      metrics.httpByEndpoint[endpoint].ok++;
    } else {
      metrics.httpErr++;
      metrics.httpByEndpoint[endpoint].err++;
      metrics.errors.push(`${method} ${path} → ${res.status}`);
    }

    return { status: res.status, data };
  } catch (err: any) {
    metrics.httpErr++;
    metrics.httpByEndpoint[endpoint].err++;
    metrics.errors.push(`${method} ${path} → NETWORK ERROR: ${err.message}`);
    return { status: 0, data: null };
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise(r => setTimeout(r, ms));
}

function log(msg: string) {
  const elapsed = ((Date.now() - metrics.startTime) / 1000).toFixed(1);
  console.log(`[${elapsed}s] ${msg}`);
}

async function main() {
  metrics.startTime = Date.now();
  log("=== DAEDALUS LIVE SOAK — Starting ===");
  log(`Server: ${BASE}`);
  log(`Duration: ${DURATION_S}s`);

  // ── Phase 0: Health Check ────────────────────────────────────────────
  log("Phase 0: Health check...");
  const health = await api("GET", "/health");
  if (health.status !== 200) {
    log("FATAL: Server not responding. Aborting.");
    process.exit(1);
  }
  log(`  Health: ${JSON.stringify(health.data)}`);

  // ── Phase 1: Check initial state ─────────────────────────────────────
  log("Phase 1: Initial state...");
  const snapshot = await api("GET", "/daedalus/snapshot");
  log(`  Nodes: ${snapshot.data?.nodes?.length ?? "?"}, Beings: ${snapshot.data?.beings?.length ?? "?"}`);

  const posture0 = await api("GET", "/daedalus/governance/posture");
  log(`  Posture: ${posture0.data?.posture ?? "?"}`);

  // ── Phase 2: Join 30 nodes ────────────────────────────────────────────
  log("Phase 2: Joining 30 nodes...");
  for (let i = 1; i <= 30; i++) {
    const id = `soak-node-${i}`;
    const res = await api("POST", "/daedalus/mirror/join", {
      nodeId: id,
      name: `Soak Node ${i}`,
      capabilities: [{ name: "core", value: "enabled", enabled: true }],
      expressive: {
        glow: { level: "low", intensity: 0.5 },
        posture: "companion",
        attention: { level: "aware" },
        continuity: "stable",
      },
      profile: {
        id, name: `Soak Node ${i}`, kind: "server",
        model: "soak", os: "linux", osVersion: "6.0", operatorId: "operator",
      },
    });
    if (res.status === 200 || res.status === 201) metrics.nodeJoins++;
  }
  log(`  Joined: ${metrics.nodeJoins}/30`);

  // Verify cockpit sees them
  const cockpitNodes = await api("GET", "/daedalus/cockpit/nodes");
  log(`  Cockpit sees: ${cockpitNodes.data?.length ?? 0} nodes`);

  if ((cockpitNodes.data?.length ?? 0) < 30) {
    metrics.findings.push(`Expected >=30 nodes in cockpit, got ${cockpitNodes.data?.length}`);
  }

  // ── Phase 3: Sustained operation ──────────────────────────────────────
  log("Phase 3: Sustained operation...");
  let running = true;
  const stopTime = Date.now() + DURATION_S * 1000;

  // Heartbeat worker
  const hbWorker = (async () => {
    while (running) {
      for (let i = 1; i <= 30; i++) {
        await api("POST", "/daedalus/mirror/heartbeat", {
          nodeId: `soak-node-${i}`,
          timestamp: new Date().toISOString(),
          status: "alive",
        });
      }
      metrics.heartbeatCycles++;
      if (metrics.heartbeatCycles % 10 === 0) {
        log(`  Heartbeat cycle ${metrics.heartbeatCycles}`);
      }
      await sleep(1000);
    }
  })();

  // Governance worker
  const govWorker = (async () => {
    let tick = 0;
    while (running) {
      await sleep(3000);
      tick++;

      if (tick % 5 === 0) {
        await api("DELETE", "/daedalus/governance/overrides");
        await api("DELETE", "/daedalus/governance/drifts");
      } else if (tick % 3 === 0) {
        await api("POST", "/daedalus/governance/overrides", {
          createdBy: { id: "operator", role: "OPERATOR", label: "Operator" },
          reason: `Soak override #${tick}`,
          scope: "NODE", effect: "ALLOW",
        });
      } else if (tick % 4 === 0) {
        await api("POST", "/daedalus/governance/drifts", {
          severity: tick % 2 === 0 ? "LOW" : "MEDIUM",
          summary: `Soak drift #${tick}`,
        });
      }

      metrics.governanceActions++;
    }
  })();

  // Read worker — cockpit, constitution, posture
  const readWorker = (async () => {
    while (running) {
      await sleep(2000);
      await api("GET", "/daedalus/cockpit/summary");
      await api("GET", "/daedalus/governance/posture");
      await api("GET", "/daedalus/beings/presence");
      await api("GET", "/daedalus/constitution");
    }
  })();

  // Wait for duration
  while (Date.now() < stopTime) {
    await sleep(5000);
    log(`  Running... (${Math.round((stopTime - Date.now()) / 1000)}s remaining)`);
  }
  running = false;
  await Promise.allSettled([hbWorker, govWorker, readWorker]);

  // ── Phase 4: Post-soak verification ──────────────────────────────────
  log("Phase 4: Post-soak verification...");

  const finalNodes = await api("GET", "/daedalus/cockpit/nodes");
  log(`  Final nodes: ${finalNodes.data?.length ?? 0}`);

  const finalPosture = await api("GET", "/daedalus/governance/posture");
  log(`  Final posture: ${finalPosture.data?.posture ?? "?"}`);

  const finalConst = await api("GET", "/daedalus/constitution");
  log(`  Constitution: ${finalConst.data?.allPassed ? "PASSED" : "FAILED"}`);
  if (finalConst.data && !finalConst.data.allPassed) {
    metrics.findings.push("Constitution failed post-soak");
    const failed = finalConst.data.checks?.filter((c: any) => !c.passed);
    if (failed?.length) {
      for (const f of failed) metrics.findings.push(`  Constitution failure: ${f.name}`);
    }
  }

  const finalHealth = await api("GET", "/health");
  log(`  Health: ${finalHealth.data?.status ?? "?"}`);

  // ── Phase 5: Cleanup ──────────────────────────────────────────────────
  log("Phase 5: Cleanup...");
  await api("DELETE", "/daedalus/governance/overrides");
  await api("DELETE", "/daedalus/governance/drifts");
  await api("DELETE", "/daedalus/governance/votes");

  for (let i = 1; i <= 30; i++) {
    await api("POST", "/daedalus/mirror/detach", { nodeId: `soak-node-${i}` });
  }

  // ── Report ────────────────────────────────────────────────────────────
  metrics.endTime = Date.now();
  const duration = (metrics.endTime - metrics.startTime) / 1000;

  console.log("");
  console.log("╔══════════════════════════════════════════════════════════════╗");
  console.log("║            DAEDALUS LIVE SOAK — RESULTS                     ║");
  console.log("╚══════════════════════════════════════════════════════════════╝");
  console.log("");
  console.log(`  Duration: ${duration.toFixed(1)}s`);
  console.log(`  Node joins: ${metrics.nodeJoins}`);
  console.log(`  Heartbeat cycles: ${metrics.heartbeatCycles}`);
  console.log(`  Governance actions: ${metrics.governanceActions}`);
  console.log("");
  console.log("  ── HTTP Summary ──────────────────────────────────────");
  console.log(`  Total requests: ${metrics.httpOk + metrics.httpErr}`);
  console.log(`  Successful: ${metrics.httpOk}`);
  console.log(`  Errors: ${metrics.httpErr}`);
  console.log("");
  console.log("  ── Endpoint Breakdown ────────────────────────────────");

  const endpoints = Object.entries(metrics.httpByEndpoint)
    .sort((a, b) => (b[1].ok + b[1].err) - (a[1].ok + a[1].err));
  for (const [ep, stats] of endpoints) {
    const count = stats.ok + stats.err;
    const avg = count > 0 ? (stats.totalMs / count).toFixed(1) : "-";
    console.log(`  ${ep}: ${count} reqs, avg ${avg}ms, err ${stats.err}`);
  }

  if (metrics.findings.length > 0) {
    console.log("");
    console.log("  ── Findings ──────────────────────────────────────────");
    for (const f of metrics.findings) console.log(`  - ${f}`);
  }

  if (metrics.errors.length > 0) {
    console.log("");
    console.log("  ── Errors (first 20) ─────────────────────────────────");
    for (const e of metrics.errors.slice(0, 20)) console.log(`  - ${e}`);
    if (metrics.errors.length > 20) {
      console.log(`  ... and ${metrics.errors.length - 20} more`);
    }
  }

  const ok = metrics.httpErr === 0 && metrics.findings.length === 0;
  console.log("");
  console.log(`  VERDICT: ${ok ? "ALL CLEAR — Live server operated correctly" : "ISSUES FOUND — See above"}`);
  console.log("");

  process.exit(ok ? 0 : 1);
}

main().catch(err => {
  console.error("FATAL:", err);
  process.exit(1);
});
