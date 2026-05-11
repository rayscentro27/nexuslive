// ── Shared env loader for ai_workforce modules ────────────────────────────────
// Resolves .env relative to this file's location regardless of cwd.
// Import this as the FIRST import in any ai_workforce module.
// ─────────────────────────────────────────────────────────────────────────────

import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: resolve(__dirname, "../../.env") });

export {};
