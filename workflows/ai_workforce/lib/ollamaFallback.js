/**
 * ollamaFallback.js — Netcup Ollama fallback for ai_workforce JS workers.
 *
 * Calls the Netcup ARM64 server via SSH tunnel (localhost:11555 → remote:11434).
 * Import this after env.js so process.env is populated from root .env.
 *
 * SSH tunnel (run once per session):
 *   ssh -N -L 11555:localhost:11434 root@v2202604354135454731.luckysrv.de
 *
 * Env vars consumed:
 *   OLLAMA_FALLBACK_URL    (default: http://localhost:11555/api/generate)
 *   OLLAMA_FALLBACK_MODEL  (default: llama3.2:3b)
 *   HERMES_FALLBACK_ENABLED (default: true)
 *
 * Usage:
 *   import { runOllamaFallback, isOllamaAvailable } from "../lib/ollamaFallback.js";
 *
 *   const result = await runOllamaFallback("Summarize: ...");
 *   if (result.success) console.log(result.response);
 */

const OLLAMA_FALLBACK_URL   = process.env.OLLAMA_FALLBACK_URL   ?? "http://localhost:11555/api/generate";
const OLLAMA_FALLBACK_MODEL = process.env.OLLAMA_FALLBACK_MODEL ?? "llama3.2:3b";
const HERMES_FALLBACK_ENABLED = (process.env.HERMES_FALLBACK_ENABLED ?? "true") !== "false"
  && (process.env.HERMES_FALLBACK_ENABLED ?? "true") !== "0";

const DEFAULT_TIMEOUT_MS = 60_000;

/**
 * @typedef {Object} OllamaResult
 * @property {"netcup_ollama"} source
 * @property {string} model
 * @property {string|null} response
 * @property {true} fallback_used
 * @property {boolean} success
 * @property {string|null} error
 */

/**
 * POST a prompt to the Netcup Ollama instance.
 *
 * @param {string} prompt
 * @param {{ timeoutMs?: number }} [opts]
 * @returns {Promise<OllamaResult>}
 */
export async function runOllamaFallback(prompt, { timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  /** @type {OllamaResult} */
  const base = { source: "netcup_ollama", model: OLLAMA_FALLBACK_MODEL, fallback_used: true };

  if (!HERMES_FALLBACK_ENABLED) {
    console.debug("[ollamaFallback] Skipped — HERMES_FALLBACK_ENABLED=false");
    return { ...base, response: null, success: false, error: "HERMES_FALLBACK_ENABLED=false" };
  }

  console.log(`[ollamaFallback] Triggered → ${OLLAMA_FALLBACK_URL}`);

  try {
    const res = await fetch(OLLAMA_FALLBACK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: OLLAMA_FALLBACK_MODEL, prompt, stream: false }),
      signal: AbortSignal.timeout(timeoutMs),
    });

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      const err = `HTTP ${res.status}: ${body.slice(0, 120)}`;
      console.error(`[ollamaFallback] ${err}`);
      return { ...base, response: null, success: false, error: err };
    }

    const data = await res.json();
    const response = (data?.response ?? "").trim();

    if (!response) {
      console.warn("[ollamaFallback] Empty response from model");
      return { ...base, response: null, success: false, error: "Empty response from model" };
    }

    console.log(`[ollamaFallback] Success (${response.length} chars)`);
    return { ...base, response, success: true, error: null };

  } catch (err) {
    const isTimeout = err?.name === "TimeoutError" || err?.name === "AbortError";
    const msg = isTimeout ? `Timeout after ${timeoutMs}ms` : (err?.message ?? String(err));
    console.error(`[ollamaFallback] ${isTimeout ? "Timeout" : "Error"}: ${msg}`);
    return { ...base, response: null, success: false, error: msg };
  }
}

/**
 * Quick reachability check — resolves true if the tunnel endpoint responds.
 *
 * @param {{ timeoutMs?: number }} [opts]
 * @returns {Promise<boolean>}
 */
export async function isOllamaAvailable({ timeoutMs = 3_000 } = {}) {
  const base = OLLAMA_FALLBACK_URL.replace(/\/api\/generate$/, "");
  try {
    const res = await fetch(`${base}/api/tags`, {
      signal: AbortSignal.timeout(timeoutMs),
    });
    return res.ok;
  } catch {
    return false;
  }
}
