/**
 * supabase.js — Supabase client + helpers.
 */

import { createClient } from '@supabase/supabase-js';
import { config }       from './config.js';

const TRANSIENT_STATUS_CODES = new Set([408, 425, 429, 500, 502, 503, 504, 520, 522, 524]);
const RETRYABLE_METHODS = new Set(['GET', 'HEAD']);
const REQUEST_TIMEOUT_MS = 15_000;
const MAX_RETRIES = 2;

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

export const db = createClient(config.supabaseUrl, config.supabaseKey, {
  global: {
    fetch: resilientFetch,
  },
});

export async function insertRow(table, row) {
  const { data, error } = await db.from(table).insert(row).select().single();
  if (error) throw error;
  return data;
}

export async function upsertRow(table, row, onConflict) {
  const { data, error } = await db
    .from(table)
    .upsert(row, onConflict ? { onConflict } : undefined)
    .select().single();
  if (error) throw error;
  return data;
}
