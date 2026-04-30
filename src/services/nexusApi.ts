/**
 * Nexus backend API calls.
 * Proxied through Netlify function /.netlify/functions/nexus-api which
 * forwards to the Nexus control center (NEXUS_API_URL env var on Netlify).
 */

import { supabase } from '../lib/supabase';

const PROXY = '/.netlify/functions/nexus-api';

async function nexusFetch(path: string, options?: RequestInit) {
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token ?? '';

  const url = `${PROXY}?path=${encodeURIComponent(path)}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error(`Nexus API ${path} → ${res.status}`);
  return res.json();
}

export interface NexusEngineStatus {
  dry_run: boolean;
  live_trading: boolean;
  broker_type: string;
  broker_connected: boolean;
  signals_processed: number;
  active_positions: number;
  last_signal: Record<string, unknown> | null;
  last_result: Record<string, unknown> | null;
  stage: string;
  updated_at: string;
}

export interface NexusTradingStatusResponse {
  engine: NexusEngineStatus;
  recent_paper_trades: PaperTrade[];
  signal_review_tail: string[];
}

export interface PaperTrade {
  id: string;
  symbol: string;
  asset_class: string;
  entry_status: 'open' | 'closed';
  thesis: string;
  stop_loss: number | null;
  target_price: number | null;
  tags: string[];
  opened_at: string;
  closed_at: string | null;
}

export async function getTradingStatus(): Promise<NexusTradingStatusResponse> {
  return nexusFetch('/api/trading/status');
}

export async function getReadinessProfile() {
  return nexusFetch('/api/readiness/profile');
}

export async function getReadinessTasks() {
  return nexusFetch('/api/readiness/tasks');
}

export async function getFundingOverview() {
  return nexusFetch('/api/funding/overview');
}

export async function getFundingStrategy() {
  return nexusFetch('/api/funding/strategy');
}

export async function getSystemHealth() {
  return nexusFetch('/api/health');
}
