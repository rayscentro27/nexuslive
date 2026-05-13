/**
 * WorkforceOffice — Admin-only animated AI workforce visualization.
 * Shows all departments, workers, and live operational state.
 * Uses real data from provider_health and analytics_events.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'motion/react';
import { supabase } from '../../lib/supabase';
import { RefreshCw, Activity, Shield } from 'lucide-react';
import { DepartmentZone } from './DepartmentZone';
import { buildWorkforceState, type DepartmentStatus, type ResearchTicket } from './workforce_state_adapter';

interface ProviderHealth {
  provider_name: string;
  status: string;
  avg_latency_ms: number | null;
  last_checked_at: string | null;
}

interface AnalyticsEvent {
  feature: string | null;
  event_name: string | null;
  created_at: string;
}

function timeAgo(ts: string): string {
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export function WorkforceOffice() {
  const [departments, setDepartments] = useState<DepartmentStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date().toISOString());
  const [oppsCount, setOppsCount] = useState(0);
  const [openTickets, setOpenTickets] = useState(0);

  const load = useCallback(async () => {
    const [phRes, evRes, oppsRes, ticketRes] = await Promise.all([
      supabase
        .from('provider_health')
        .select('provider_name,status,avg_latency_ms,last_checked_at')
        .order('provider_name'),
      supabase
        .from('analytics_events')
        .select('feature,event_name,created_at')
        .order('created_at', { ascending: false })
        .limit(50),
      supabase
        .from('user_opportunities')
        .select('id', { count: 'exact', head: true }),
      supabase
        .from('research_requests')
        .select('id,department,status,priority,topic,created_at,completed_at')
        .in('status', ['submitted','queued','researching','needs_review'])
        .limit(50),
    ]);

    const providers = (phRes.data || []) as ProviderHealth[];
    const events = (evRes.data || []) as AnalyticsEvent[];
    const count = oppsRes.count || 0;
    const tickets = (ticketRes.data || []) as ResearchTicket[];

    setOppsCount(count);
    setOpenTickets(tickets.length);
    setDepartments(buildWorkforceState(providers, events, count, tickets));
    setLastRefresh(new Date().toISOString());
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 90_000);
    return () => clearInterval(t);
  }, [load]);

  const handleRefresh = () => { setRefreshing(true); void load(); };

  const totalWorkers = departments.reduce((s, d) => s + d.workers.length, 0);
  const activeWorkers = departments.reduce((s, d) => s + d.workers.filter(w => ['active', 'researching', 'analyzing'].includes(w.state)).length, 0);
  const warnWorkers = departments.reduce((s, d) => s + d.workers.filter(w => w.state === 'warning' || w.state === 'offline').length, 0);

  return (
    <div style={{ padding: '16px 20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: '#1a1c3a', margin: 0, marginBottom: 2 }}>
            🏢 AI Workforce Office
          </h2>
          <p style={{ fontSize: 12, color: '#8b8fa8', margin: 0 }}>
            Admin — real-time operational state
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '7px 14px', borderRadius: 10, border: '1px solid #e5e7eb',
            background: '#fff', color: '#3d5af1', fontWeight: 600, fontSize: 12, cursor: 'pointer',
          }}
        >
          <RefreshCw size={12} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
          Refresh
        </button>
      </div>

      {/* Summary bar */}
      {!loading && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}
        >
          {[
            { label: 'Total Workers', value: totalWorkers, color: '#6366f1', bg: '#eef0fd' },
            { label: 'Active', value: activeWorkers, color: '#22c55e', bg: '#f0fdf4' },
            { label: 'Needs Attention', value: warnWorkers, color: warnWorkers > 0 ? '#f59e0b' : '#9ca3af', bg: warnWorkers > 0 ? '#fffbeb' : '#f9fafb' },
            { label: 'Opportunities', value: oppsCount, color: '#7c3aed', bg: '#f5f3ff' },
            { label: 'Open Tickets', value: openTickets, color: openTickets > 0 ? '#d97706' : '#9ca3af', bg: openTickets > 0 ? '#fffbeb' : '#f9fafb' },
          ].map(s => (
            <div key={s.label} style={{
              flex: '1 1 80px', padding: '10px 12px', borderRadius: 12,
              background: s.bg, textAlign: 'center',
              border: `1px solid ${s.color}20`,
            }}>
              <p style={{ fontSize: 20, fontWeight: 800, color: s.color, margin: 0 }}>{s.value}</p>
              <p style={{ fontSize: 10, color: '#6b7280', margin: 0 }}>{s.label}</p>
            </div>
          ))}
        </motion.div>
      )}

      {/* Last sync */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 14 }}>
        <Activity size={12} color="#8b8fa8" />
        <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>
          Last synced {timeAgo(lastRefresh)} · auto-refreshes every 90s
        </p>
      </div>

      {/* Department zones */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} style={{ height: 64, borderRadius: 14, background: '#f3f4f6' }} />
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {departments.map((dept, i) => (
            <DepartmentZone
              key={dept.id}
              department={dept}
              defaultExpanded={i < 3}
            />
          ))}
        </div>
      )}

      {/* Safety footer */}
      <div style={{
        marginTop: 20, padding: '10px 14px', borderRadius: 12,
        background: '#f0fdf4', border: '1px solid #bbf7d0',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <Shield size={13} color="#16a34a" />
        <p style={{ fontSize: 11, color: '#16a34a', fontWeight: 700, margin: 0 }}>
          NEXUS_DRY_RUN=true · LIVE_TRADING=false · No broker execution · No auto social
        </p>
      </div>
    </div>
  );
}
