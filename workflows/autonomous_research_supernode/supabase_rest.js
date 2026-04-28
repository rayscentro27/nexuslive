import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

const TRANSIENT_STATUS_CODES = new Set([408, 425, 429, 500, 502, 503, 504, 520, 522, 524]);
const RETRYABLE_METHODS = new Set(["GET", "HEAD"]);
const REQUEST_TIMEOUT_MS = 15_000;
const MAX_RETRIES = 2;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function summarizeBody(body) {
  if (!body) return "no response body";
  return body
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 160);
}

function normalizeErrorMessage(error) {
  return error?.message ?? String(error ?? "unknown error");
}

function isTransientFetchErrorMessage(message) {
  const text = String(message ?? "").toLowerCase();
  return (
    text.includes("fetch failed") ||
    text.includes("bad gateway") ||
    text.includes("gateway timeout") ||
    text.includes("internal server error") ||
    text.includes("cloudflare") ||
    text.includes("network") ||
    text.includes("timed out") ||
    text.includes("timeout")
  );
}

export function isTransientSupabaseError(error) {
  return isTransientFetchErrorMessage(normalizeErrorMessage(error));
}

function serviceHeaders(extra = {}) {
  return {
    apikey: SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json",
    ...extra,
  };
}

async function supabaseFetch(path, init = {}) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  }

  const method = (init.method ?? "GET").toUpperCase();
  const retryable = RETRYABLE_METHODS.has(method);
  const attempts = retryable ? MAX_RETRIES + 1 : 1;
  let lastError = null;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(new Error(`Supabase request timed out after ${REQUEST_TIMEOUT_MS}ms`)),
      REQUEST_TIMEOUT_MS,
    );

    try {
      const response = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
        ...init,
        signal: controller.signal,
        headers: serviceHeaders(init.headers ?? {}),
      });
      clearTimeout(timeout);

      if (response.ok || !TRANSIENT_STATUS_CODES.has(response.status) || attempt === attempts) {
        if (!response.ok) {
          const body = await response.clone().text().catch(() => "");
          const prefix = TRANSIENT_STATUS_CODES.has(response.status) ? "Supabase transient" : "Supabase";
          throw new Error(`${prefix} ${method} ${path}: ${response.status} ${summarizeBody(body)}`);
        }
        return response;
      }

      await sleep(250 * attempt);
    } catch (error) {
      clearTimeout(timeout);
      lastError = error;

      if (!retryable || attempt === attempts || !isTransientSupabaseError(error)) {
        throw error;
      }

      await sleep(250 * attempt);
    }
  }

  throw lastError ?? new Error("Supabase request failed");
}

export async function supabaseInsert(path, rows, { prefer = "return=representation" } = {}) {
  const response = await supabaseFetch(path, {
    method: "POST",
    headers: {
      Prefer: prefer,
    },
    body: JSON.stringify(Array.isArray(rows) ? rows : [rows]),
  });
  return response.json();
}
