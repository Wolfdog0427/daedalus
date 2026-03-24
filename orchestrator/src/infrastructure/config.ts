export interface OrchestratorConfig {
  env: string;
  http: {
    port: number;
  };
}

export function loadConfig(): OrchestratorConfig {
  const env = process.env.NODE_ENV ?? 'development';
  const port = Number(process.env.ORCHESTRATOR_PORT ?? 4000);

  return {
    env,
    http: {
      port,
    },
  };
}
