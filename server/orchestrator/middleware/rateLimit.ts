import { Request, Response, NextFunction } from "express";

interface RateBucket {
  count: number;
  resetAt: number;
}

const buckets = new Map<string, RateBucket>();

const DEFAULT_WINDOW_MS = 60_000;
const DEFAULT_MAX_REQUESTS = 300;

const SWEEP_INTERVAL = 5 * 60_000;
let lastSweep = Date.now();

function sweep(now: number) {
  if (now - lastSweep < SWEEP_INTERVAL) return;
  lastSweep = now;
  for (const [key, bucket] of buckets) {
    if (now > bucket.resetAt) buckets.delete(key);
  }
}

export interface RateLimitOptions {
  windowMs?: number;
  maxRequests?: number;
}

export function rateLimit(opts: RateLimitOptions = {}) {
  const windowMs = opts.windowMs ?? DEFAULT_WINDOW_MS;
  const max = opts.maxRequests ?? DEFAULT_MAX_REQUESTS;

  return (req: Request, res: Response, next: NextFunction): void => {
    if (process.env.NODE_ENV === "test") {
      next();
      return;
    }

    const now = Date.now();
    sweep(now);

    const key = req.ip ?? req.socket.remoteAddress ?? "unknown";
    let bucket = buckets.get(key);

    if (!bucket || now > bucket.resetAt) {
      bucket = { count: 0, resetAt: now + windowMs };
      buckets.set(key, bucket);
    }

    bucket.count++;

    res.setHeader("X-RateLimit-Limit", String(max));
    res.setHeader("X-RateLimit-Remaining", String(Math.max(0, max - bucket.count)));
    res.setHeader("X-RateLimit-Reset", String(Math.ceil(bucket.resetAt / 1000)));

    if (bucket.count > max) {
      res.status(429).json({
        error: "Too many requests — rate limit exceeded",
        retryAfterMs: bucket.resetAt - now,
      });
      return;
    }

    next();
  };
}

export function resetRateLimits(): void {
  buckets.clear();
}
