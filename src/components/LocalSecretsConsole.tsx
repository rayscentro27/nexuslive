import React, { useEffect, useState, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { Shield, RefreshCw } from 'lucide-react';

interface ProviderHealth {
  provider_name: string;
  status: string;
  avg_latency_ms: number | null;
  last_checked_at: string | null;
  notes: string | null;
}

const SERVICE_DISPLAY: Record<string, { label: string; emoji: string; keyHint: string }> = {
  ollama:       { label: 'Ollama (Local LLM)',   emoji: '🧠', keyHint: 'localhost:11555' },
  groq:         { label: 'Groq API',             emoji: '⚡', keyHint: 'GROQ_API_KEY ****' },
  openrouter:   { label: 'OpenRouter',           emoji: '🔀', keyHint: 'OPENROUTER_API_KEY ****' },
  claude_cli:   { label: 'Claude CLI',           emoji: '🤖', keyHint: 'claude binary' },
  codex:        { label: 'OpenAI Codex',         emoji: '📝', keyHint: 'codex binary' },
  opencode:     { label: 'OpenCode',             emoji: '💻', keyHint: 'opencode binary' },
  notebooklm:   { label: 'NotebookLM',           emoji: '📚', keyHint: 'notebooklm.google.com' },
};

const STATIC_SERVICES = [
  { key: 'supabase',  label: 'Supabase',         emoji: '🗄️', keyHint: 'SUPABASE_URL ****' },
  { key: 'telegram',  label: 'Telegram Bot',     emoji: '✈️', keyHint: 'TELEGRAM_BOT_TOKEN ****' },
  { key: 'stripe',    label: 'Stripe',           emoji: '💳', keyHint: 'STRIPE_SECRET_KEY ****' },
];

function statusColor(status: string): string {
  return status === 'online' ? '#22c55e' : status === 'degraded' ? '#f59e0b' : '#ef4444';
}

function StatusPill({ status }: { status: string }) {
  const color = statusColor(status);
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: `${color}18`, color,
      borderRadius: 8, padding: '3px 9px',
      fontSize: 11, fontWeight: 700,
      border: `1px solid ${color}30`,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block' }} />
      {status}
    </span>
  );
}

function timeSince(ts: string | null): string {
  if (!ts) return '—';
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

interface Props {
  isAdmin?: boolean;
}

export function LocalSecretsConsole({ isAdmin = false }: Props) {
  const [providers, setProviders] = useState<ProviderHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const { data } = await supabase
      .from('provider_health')
      .select('provider_name,status,avg_latency_ms,last_checked_at,notes')
      .order('provider_name');
    if (data) setProviders(data as ProviderHealth[]);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => { void load(); }, [load]);

  const handleRefresh = () => { setRefreshing(true); void load(); };

  if (!isAdmin) {
    return (
      <div className="glass-card" style={{ padding: 18, textAlign: 'center', color: '#8b8fa8' }}>
        <Shield size={24} style={{ margin: '0 auto 8px' }} />
        <p style={{ fontSize: 13 }}>Admin access required.</p>
      </div>
    );
  }

  const providerMap = Object.fromEntries(providers.map(p => [p.provider_name, p]));

  return (
    <div className="glass-card" style={{ padding: 18 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Shield size={15} color="#3d5af1" />
          <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>Service Connections</h3>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            background: 'none', border: '1px solid #e8e9f2', borderRadius: 8,
            padding: '5px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
            fontSize: 12, color: '#3d5af1', fontWeight: 600,
          }}
        >
          <RefreshCw size={12} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
          Refresh
        </button>
      </div>

      <p style={{ fontSize: 11, color: '#8b8fa8', marginBottom: 12, padding: '6px 10px', background: '#fef3c7', borderRadius: 8, border: '1px solid #fde68a' }}>
        🔒 Showing connection status only — no actual key values are displayed or stored here.
      </p>

      {/* AI Provider rows */}
      <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
        AI Providers
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
        {Object.entries(SERVICE_DISPLAY).map(([key, info]) => {
          const ph = providerMap[key];
          const status = ph?.status || 'unknown';
          return (
            <div key={key} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '9px 12px', borderRadius: 10,
              background: '#f9fafb', border: '1px solid #e8e9f2',
            }}>
              <span style={{ fontSize: 18 }}>{info.emoji}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{info.label}</p>
                <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>
                  {info.keyHint}
                  {ph?.avg_latency_ms != null && ` · ${ph.avg_latency_ms}ms`}
                </p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
                <StatusPill status={status} />
                {ph?.last_checked_at && (
                  <span style={{ fontSize: 10, color: '#8b8fa8' }}>{timeSince(ph.last_checked_at)}</span>
                )}
              </div>
            </div>
          );
        })}
        {loading && (
          <p style={{ fontSize: 12, color: '#8b8fa8' }}>Loading provider health…</p>
        )}
        {!loading && providers.length === 0 && (
          <p style={{ fontSize: 12, color: '#8b8fa8' }}>
            No data yet — run provider_health_worker to populate.
          </p>
        )}
      </div>

      {/* Static services */}
      <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
        Platform Services
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {STATIC_SERVICES.map(svc => (
          <div key={svc.key} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '9px 12px', borderRadius: 10,
            background: '#f9fafb', border: '1px solid #e8e9f2',
          }}>
            <span style={{ fontSize: 18 }}>{svc.emoji}</span>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{svc.label}</p>
              <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>{svc.keyHint}</p>
            </div>
            <StatusPill status="online" />
          </div>
        ))}
      </div>

      {/* Safety footer */}
      <div style={{
        marginTop: 14, padding: '8px 12px', borderRadius: 10,
        background: '#f0fdf4', border: '1px solid #bbf7d0',
        fontSize: 11, color: '#16a34a',
      }}>
        🔒 NEXUS_DRY_RUN=true · LIVE_TRADING=false · No real-money execution
      </div>
    </div>
  );
}
