import React, { useEffect, useState, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { Activity, Cpu, Wifi, WifiOff, Minus } from 'lucide-react';

interface ProviderHealth {
  provider_name: string;
  status: string;
  avg_latency_ms: number | null;
  last_checked_at: string | null;
}

interface AnalyticsEvent {
  event_type: string;
  event_name: string | null;
  feature: string | null;
  created_at: string;
}

const WORKER_DISPLAY: Record<string, { label: string; emoji: string }> = {
  ollama:       { label: 'Local LLM',     emoji: '🧠' },
  groq:         { label: 'Groq Cloud',    emoji: '⚡' },
  openrouter:   { label: 'OpenRouter',    emoji: '🔀' },
  claude_cli:   { label: 'Claude CLI',    emoji: '🤖' },
  codex:        { label: 'Codex',         emoji: '📝' },
  opencode:     { label: 'OpenCode',      emoji: '💻' },
  notebooklm:   { label: 'NotebookLM',   emoji: '📚' },
};

function StatusDot({ status }: { status: string }) {
  const color = status === 'online' ? '#22c55e' : status === 'degraded' ? '#f59e0b' : '#ef4444';
  return (
    <div style={{
      width: 8, height: 8, borderRadius: '50%', background: color,
      boxShadow: status === 'online' ? `0 0 6px ${color}` : 'none',
      flexShrink: 0,
    }} />
  );
}

function timeAgo(ts: string): string {
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export function LiveActivityFeed() {
  const [providers, setProviders] = useState<ProviderHealth[]>([]);
  const [events, setEvents] = useState<AnalyticsEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const [phRes, evRes] = await Promise.all([
      supabase.from('provider_health').select('provider_name,status,avg_latency_ms,last_checked_at').order('provider_name'),
      supabase.from('analytics_events')
        .select('event_type,event_name,feature,created_at')
        .order('created_at', { ascending: false })
        .limit(8),
    ]);
    if (phRes.data) setProviders(phRes.data as ProviderHealth[]);
    if (evRes.data) setEvents(evRes.data as AnalyticsEvent[]);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 60_000);
    return () => clearInterval(t);
  }, [load]);

  const online  = providers.filter(p => p.status === 'online').length;
  const offline = providers.filter(p => p.status === 'offline').length;
  const degraded = providers.filter(p => p.status === 'degraded').length;

  return (
    <div className="glass-card" style={{ padding: 18 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Cpu size={16} color="#3d5af1" />
          <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>AI Workforce</h3>
        </div>
        <div style={{ display: 'flex', gap: 8, fontSize: 11 }}>
          {online > 0 && <span style={{ color: '#22c55e', fontWeight: 700 }}>🟢 {online}</span>}
          {degraded > 0 && <span style={{ color: '#f59e0b', fontWeight: 700 }}>🟡 {degraded}</span>}
          {offline > 0 && <span style={{ color: '#ef4444', fontWeight: 700 }}>🔴 {offline}</span>}
        </div>
      </div>

      {/* Provider grid */}
      {loading ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {[...Array(6)].map((_, i) => (
            <div key={i} style={{ flex: '1 1 calc(50% - 4px)', height: 36, borderRadius: 8, background: '#f3f4f6', animation: 'pulse 1.5s infinite' }} />
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {providers.map(p => {
            const info = WORKER_DISPLAY[p.provider_name] || { label: p.provider_name, emoji: '⚙️' };
            return (
              <div key={p.provider_name} style={{
                flex: '1 1 calc(50% - 4px)',
                display: 'flex', alignItems: 'center', gap: 7,
                background: p.status === 'online' ? '#f0fdf4' : p.status === 'degraded' ? '#fffbeb' : '#fef2f2',
                borderRadius: 10, padding: '7px 10px',
                border: `1px solid ${p.status === 'online' ? '#bbf7d0' : p.status === 'degraded' ? '#fde68a' : '#fecaca'}`,
              }}>
                <StatusDot status={p.status} />
                <span style={{ fontSize: 14 }}>{info.emoji}</span>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontSize: 11, fontWeight: 700, color: '#1a1c3a', margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {info.label}
                  </p>
                  {p.avg_latency_ms != null && (
                    <p style={{ fontSize: 10, color: '#8b8fa8', margin: 0 }}>{p.avg_latency_ms}ms</p>
                  )}
                </div>
              </div>
            );
          })}
          {providers.length === 0 && (
            <p style={{ fontSize: 12, color: '#8b8fa8', padding: '4px 0' }}>
              No provider health data yet — run provider_health_worker.
            </p>
          )}
        </div>
      )}

      {/* Live activity events */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
          <Activity size={13} color="#8b8fa8" />
          <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
            Live Activity
          </p>
        </div>
        {events.length === 0 ? (
          <p style={{ fontSize: 12, color: '#8b8fa8' }}>No activity yet today.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {events.map((ev, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{
                  width: 6, height: 6, borderRadius: '50%', background: '#3d5af1',
                  flexShrink: 0, opacity: 0.6 + (8 - i) * 0.05,
                }} />
                <span style={{ flex: 1, fontSize: 12, color: '#1a1c3a', fontWeight: 500 }}>
                  {ev.event_name || ev.event_type}
                  {ev.feature && <span style={{ color: '#8b8fa8', fontWeight: 400 }}> · {ev.feature}</span>}
                </span>
                <span style={{ fontSize: 10, color: '#8b8fa8', flexShrink: 0 }}>{timeAgo(ev.created_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
