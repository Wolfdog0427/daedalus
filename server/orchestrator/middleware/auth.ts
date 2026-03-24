import { Request, Response, NextFunction } from "express";

const DAEDALUS_TOKEN = process.env.DAEDALUS_TOKEN ?? "daedalus-dev-token";

export function requireAuth(req: Request, res: Response, next: NextFunction): void {
  if (process.env.NODE_ENV === "test") {
    next();
    return;
  }

  const token =
    req.headers["x-daedalus-token"] ??
    req.headers["authorization"]?.replace("Bearer ", "") ??
    (req.query?.token as string | undefined);

  if (!token || token !== DAEDALUS_TOKEN) {
    res.status(401).json({ error: "Unauthorized: missing or invalid token" });
    return;
  }
  next();
}
