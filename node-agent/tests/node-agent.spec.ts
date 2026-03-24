import { NodeAgent } from "../src/NodeAgent";
import { createMockTransport } from "../src/NodeAgent.transport";
import type { NodeAgentConfig } from "../src/NodeAgent.config";
import { IDLE_LIFECYCLE_STATE } from "../src/NodeAgent.lifecycle";

function mkConfig(overrides: Partial<NodeAgentConfig> = {}): NodeAgentConfig {
  return {
    nodeId: "test-node",
    nodeName: "Test Node",
    kind: "mobile",
    model: "TestDevice",
    os: "android",
    osVersion: "15",
    operatorId: "op-test",
    orchestratorUrl: "http://localhost:4000",
    heartbeatIntervalMs: 100,
    expressiveSyncIntervalMs: 200,
    capabilities: [
      { name: "vision", value: "enabled", enabled: true },
    ],
    ...overrides,
  };
}

describe("NodeAgent", () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  test("starts in idle phase", () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);
    expect(agent.getPhase()).toBe("idle");
  });

  test("start joins then activates", async () => {
    const transport = createMockTransport({
      "POST /daedalus/mirror/join": () => ({ ok: true }),
    });
    const agent = new NodeAgent(mkConfig(), transport);
    await agent.start();
    expect(agent.getPhase()).toBe("active");
    agent.stop();
  });

  test("start calls join endpoint", async () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);
    await agent.start();
    const joinCall = transport.calls.find(c => c.path === "/daedalus/mirror/join");
    expect(joinCall).toBeDefined();
    expect(joinCall!.method).toBe("POST");
    agent.stop();
  });

  test("heartbeat starts after join", async () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);
    await agent.start();

    jest.advanceTimersByTime(100);
    const hbCalls = transport.calls.filter(c => c.path === "/daedalus/mirror/heartbeat");
    expect(hbCalls.length).toBeGreaterThan(0);
    agent.stop();
  });

  test("stop ceases heartbeat", async () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);
    await agent.start();
    agent.stop();

    const countBefore = transport.calls.length;
    jest.advanceTimersByTime(500);
    expect(transport.calls.length).toBe(countBefore);
  });

  test("syncCapabilities sends capabilities", async () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);
    await agent.start();
    await agent.syncCapabilities();

    const capCalls = transport.calls.filter(c => c.path === "/daedalus/mirror/caps");
    expect(capCalls.length).toBeGreaterThanOrEqual(1);
    agent.stop();
  });

  test("syncProfile sends profile", async () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);
    await agent.start();
    await agent.syncProfile();

    const profileCalls = transport.calls.filter(c => c.path === "/daedalus/mirror/profile");
    expect(profileCalls.length).toBeGreaterThanOrEqual(1);
    agent.stop();
  });

  test("syncExpressive sends expressive state", async () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);
    await agent.start();
    await agent.syncExpressive();

    const exprCalls = transport.calls.filter(c => c.path === "/daedalus/mirror/expressive");
    expect(exprCalls.length).toBeGreaterThanOrEqual(1);
    agent.stop();
  });

  test("expressive state can be modified", async () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);
    await agent.start();

    agent.expressive.setPosture("sentinel");
    expect(agent.expressive.getState().posture).toBe("sentinel");

    agent.expressive.setGlow({ level: "high", intensity: 0.9 });
    expect(agent.expressive.getState().glow.level).toBe("high");
    agent.stop();
  });

  test("capabilities can be registered", async () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);
    await agent.start();

    agent.capabilities.registerCap({ name: "audio", value: "enabled", enabled: true });
    expect(agent.capabilities.getCaps()).toHaveLength(2);
    agent.stop();
  });

  test("capabilities can negotiate with remote", () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);

    const result = agent.capabilities.negotiate([
      { name: "vision", value: "enabled", enabled: true },
      { name: "other", value: "enabled", enabled: true },
    ]);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("vision");
  });

  test("lifecycle listeners fire on phase changes", async () => {
    const transport = createMockTransport();
    const agent = new NodeAgent(mkConfig(), transport);
    const phases: string[] = [];
    agent.lifecycle.onStateChange(s => phases.push(s.phase));

    await agent.start();
    expect(phases).toContain("joining");
    expect(phases).toContain("active");
    agent.stop();
  });
});
