export interface Logger {
  info(message: string, meta?: Record<string, any>): void;
  debug(message: string, meta?: Record<string, any>): void;
  warn(message: string, meta?: Record<string, any>): void;
  error(message: string, meta?: Record<string, any>): void;
}

export function createLogger(): Logger {
  function log(level: string, message: string, meta?: Record<string, any>) {
    console.log(
      JSON.stringify({
        level,
        message,
        meta: meta ?? {},
        at: new Date().toISOString(),
      }),
    );
  }

  return {
    info: (m, meta) => log('info', m, meta),
    debug: (m, meta) => log('debug', m, meta),
    warn: (m, meta) => log('warn', m, meta),
    error: (m, meta) => log('error', m, meta),
  };
}
