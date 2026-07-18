import { Request, Response, NextFunction } from "express";

// ─── Request Logger Middleware ────────────────────────────────────────────────
export function requestLogger(req: Request, _res: Response, next: NextFunction) {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
}

// ─── Auth Middleware (placeholder — replace with real JWT/Supabase auth) ──────
export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    res.status(401).json({ error: "Unauthorized — missing or invalid token" });
    return;
  }

  // TODO: Verify JWT token with Supabase or your auth provider
  // const token = authHeader.split(" ")[1];
  // const { data, error } = await supabase.auth.getUser(token);
  // if (error) { res.status(401).json({ error: "Invalid token" }); return; }
  // req.user = data.user;

  next();
}

// ─── Validate Request Body Middleware ────────────────────────────────────────
export function validateBody(
  requiredFields: string[]
): (req: Request, res: Response, next: NextFunction) => void {
  return (req: Request, res: Response, next: NextFunction) => {
    const missing = requiredFields.filter((f) => !(f in req.body));
    if (missing.length > 0) {
      res.status(400).json({
        error: `Missing required fields: ${missing.join(", ")}`,
      });
      return;
    }
    next();
  };
}
