import fs from "node:fs";
import path from "node:path";

export type LogLevel = "debug" | "info" | "warn" | "error";

const LEVEL_ORDER: Record<LogLevel, number> = { debug: 0, info: 1, warn: 2, error: 3 };

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  component: string;
  message: string;
  data?: any;
}

export interface LoggerConfig {
  level: LogLevel;
  console: boolean;
  file: boolean;
  filePath: string;
  maxFileSizeBytes: number;
  maxRotatedFiles: number;
}

const DEFAULT_CONFIG: LoggerConfig = {
  level: "info",
  console: true,
  file: false,
  filePath: path.resolve(process.cwd(), "daedalus.log"),
  maxFileSizeBytes: 10 * 1024 * 1024,
  maxRotatedFiles: 5,
};

export class DaedalusLogger {
  private config: LoggerConfig;
  private writeStream: fs.WriteStream | null = null;

  constructor(config: Partial<LoggerConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    if (this.config.file) {
      this.openStream();
    }
  }

  private openStream() {
    this.writeStream = fs.createWriteStream(this.config.filePath, { flags: "a" });
  }

  private rotate() {
    if (!this.writeStream) return;
    this.writeStream.end();

    for (let i = this.config.maxRotatedFiles - 1; i >= 1; i--) {
      const from = `${this.config.filePath}.${i}`;
      const to = `${this.config.filePath}.${i + 1}`;
      try {
        if (fs.existsSync(from)) fs.renameSync(from, to);
      } catch { /* best effort */ }
    }

    try {
      if (fs.existsSync(this.config.filePath)) {
        fs.renameSync(this.config.filePath, `${this.config.filePath}.1`);
      }
    } catch { /* best effort */ }

    this.openStream();
  }

  private shouldRotate(): boolean {
    try {
      if (!fs.existsSync(this.config.filePath)) return false;
      const stats = fs.statSync(this.config.filePath);
      return stats.size >= this.config.maxFileSizeBytes;
    } catch {
      return false;
    }
  }

  private write(entry: LogEntry) {
    if (LEVEL_ORDER[entry.level] < LEVEL_ORDER[this.config.level]) return;

    const line = JSON.stringify(entry);

    if (this.config.console) {
      const fn = entry.level === "error" ? console.error
        : entry.level === "warn" ? console.warn
        : console.log;
      fn(`[${entry.component}] ${entry.level.toUpperCase()}: ${entry.message}`, entry.data ?? "");
    }

    if (this.config.file && this.writeStream) {
      if (this.shouldRotate()) this.rotate();
      this.writeStream.write(line + "\n");
    }
  }

  log(level: LogLevel, component: string, message: string, data?: any) {
    this.write({
      timestamp: new Date().toISOString(),
      level,
      component,
      message,
      data,
    });
  }

  debug(component: string, message: string, data?: any) { this.log("debug", component, message, data); }
  info(component: string, message: string, data?: any) { this.log("info", component, message, data); }
  warn(component: string, message: string, data?: any) { this.log("warn", component, message, data); }
  error(component: string, message: string, data?: any) { this.log("error", component, message, data); }

  close() {
    this.writeStream?.end();
    this.writeStream = null;
  }
}

let singleton: DaedalusLogger | null = null;

export function getDaedalusLogger(config?: Partial<LoggerConfig>): DaedalusLogger {
  if (!singleton) {
    singleton = new DaedalusLogger(config);
  }
  return singleton;
}

export function resetDaedalusLogger(): void {
  singleton?.close();
  singleton = null;
}
