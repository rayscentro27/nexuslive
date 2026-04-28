/**
 * clients/supabase.js — Supabase wrapper with helpers.
 * Matches mac-mini-worker patterns.
 */

import { createClient } from '@supabase/supabase-js';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Load .env from nexus-ai root
function loadEnv() {
  try {
    const envPath = resolve(__dirname, '../../../../.env');
    const lines = readFileSync(envPath, 'utf-8').split('\n');
    const env = {};
    for (const line of lines) {
      if (!line || line.startsWith('#')) continue;
      const [key, ...rest] = line.split('=');
      if (key) env[key.trim()] = rest.join('=').trim();
    }
    return env;
  } catch {
    return {};
  }
}

const env = { ...loadEnv(), ...process.env };
const TRANSIENT_STATUS_CODES = new Set([408, 425, 429, 500, 502, 503, 504, 520, 522, 524]);
const RETRYABLE_METHODS = new Set(['GET', 'HEAD']);
const REQUEST_TIMEOUT_MS = 15_000;
const MAX_RETRIES = 2;

export function getEnv(key, def = null) {
  return env[key] ?? def;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function summarizeBody(body) {
  if (!body) return 'no response body';
  return body
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 160);
}

function normalizeErrorMessage(error) {
  return error?.message ?? String(error ?? 'unknown error');
}

function isTransientFetchErrorMessage(message) {
  const text = String(message ?? '').toLowerCase();
  return (
    text.includes('fetch failed')
    || text.includes('bad gateway')
    || text.includes('gateway timeout')
    || text.includes('internal server error')
    || text.includes('cloudflare')
    || text.includes('network')
    || text.includes('timed out')
    || text.includes('timeout')
  );
}

export function isTransientSupabaseError(error) {
  return isTransientFetchErrorMessage(normalizeErrorMessage(error));
}

async function resilientFetch(input, init = {}) {
  const method = (init.method ?? 'GET').toUpperCase();
  const retryable = RETRYABLE_METHODS.has(method);
  const attempts = retryable ? MAX_RETRIES + 1 : 1;
  let lastError = null;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(new Error(`Supabase request timed out after ${REQUEST_TIMEOUT_MS}ms`)), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(input, {
        ...init,
        signal: controller.signal,
      });
      clearTimeout(timeout);

      if (response.ok || !TRANSIENT_STATUS_CODES.has(response.status) || attempt === attempts) {
        if (!response.ok && TRANSIENT_STATUS_CODES.has(response.status) && attempt === attempts) {
          const body = await response.clone().text().catch(() => '');
          throw new Error(`Supabase transient ${response.status}: ${summarizeBody(body)}`);
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

  throw lastError ?? new Error('Supabase request failed');
}

const url = getEnv('SUPABASE_URL');
const key = getEnv('SUPABASE_KEY') || getEnv('SUPABASE_SERVICE_ROLE_KEY');

if (!url || !key) {
  process.stderr.write('FATAL: SUPABASE_URL and SUPABASE_KEY are required\n');
  process.exit(1);
}

export const db = createClient(url, key, {
  global: {
    fetch: resilientFetch,
  },
});

// ── Helpers ────────────────────────────────────────────────────────────────

export async function selectOne(table, filters) {
  const { data, error } = await db.from(table).select('*').match(filters).limit(1).single();
  if (error && error.code !== 'PGRST116') throw error;
  return data ?? null;
}

export async function insertRow(table, row) {
  const { data, error } = await db.from(table).insert(row).select().single();
  if (error) throw error;
  return data;
}

export async function upsertRow(table, row, onConflict) {
  const q = db.from(table).upsert(row, onConflict ? { onConflict } : undefined).select().single();
  const { data, error } = await q;
  if (error) throw error;
  return data;
}

export async function updateRow(table, match, updates) {
  const { error } = await db.from(table).update(updates).match(match);
  if (error) throw error;
}

export async function countRows(table, filters = '') {
  let q = db.from(table).select('*', { count: 'exact', head: true });
  if (filters) q = q.or(filters);
  const { count, error } = await q;
  if (error) throw error;
  return count ?? 0;
}
