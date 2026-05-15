/**
 * WorkforceOffice — Admin animated AI workforce visualization.
 * Shows departments, workers, live research tickets, ingestion activity, and live ops feed.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { supabase } from '../../lib/supabase';
import { RefreshCw, Activity, Shield, Brain, Inbox, Clock, Radio } from 'lucide-react';
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

interface IngestEvent {
  id: string;
  title: string;
  domain: string;
  status?: string;
  created_at: string;
}

interface KnowledgeEvent {
  id: string;
  title: string;
  status: string;
  quality_score: number | null;
  created_at: string;
}

interface OpsEvent {
  id: string;
  label: string;
  sublabel: string;
  icon: string;
  color: string;
  ts: string;
  type: 'research' | 'knowledge' | 'ingestion' | 'activity';
}

function timeAgo(ts: string): string {
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

function PulseRing({ color = '#3d5af1', size = 10 }: { color?: string; size?: number }) {
  return (
    <div style={{ position: 'relative', width: size + 8, height: size + 8, flexShrink: 0 }}>
      <motion.div
        animate={{ scale: [1, 1.7, 1], opacity: [0.6, 0, 0.6] }}
        transition={{ duration: 2, repeat: Infinity }}
        style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: color, opacity: 0.3 }}
      />
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        transform: 'translate(-50%,-50%)',
        width: size, height: size, borderRadius: '50%', background: color,
      }} />
    </div>
  );
}

const DEPT_LABEL: Record<string, string> = {
  trading_intelligence: 'Trading',
  grants_research: 'Grants',
  funding_intelligence: 'Funding',
  business_opportunities: 'Business',
  credit_research: 'Credit',
  marketing_intelligence: 'Marketing',
  operations: 'Operations',
};

const STATUS_COLOR: Record<string, string> = {
  researching: '#7c3aed',
  needs_review: '#f59e0b',
  queued: '#3d5af1',
  submitted: '#6b7280',
};

function IngestRow({ item, idx, color, icon }: { item: IngestEvent; idx: number; color: string; icon: string }) {
  const label = item.title || item.domain || 'Source';
  const shortLabel = label.length > 50 ? label.slice(0, 50) + '…' : label;
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.04 }}
      style={{
        padding: '8px 12px', borderRadius: 9,
        background: '#f9fafb', border: `1px solid ${color}20`,
        display: 'flex', alignItems: 'center', gap: 9,
      }}
    >
      <span style={{ fontSize: 14 }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 11, fontWeight: 600, color: '#1a1c3a', margin: 0,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {shortLabel}
        </p>
        <p style={{ fontSize: 9, color: '#6b7280', margin: 0 }}>{item.domain}</p>
      </div>
      <span style={{ fontSize: 9, color: '#9ca3af', flexShrink: 0 }}>{timeAgo(item.created_at)}</span>
    </motion.div>
  );
}

function buildOpsEvents(
  tickets: ResearchTicket[],
  knowledge: KnowledgeEvent[],
  ingest: IngestEvent[],
  events: AnalyticsEvent[],
): OpsEvent[] {
  const out: OpsEvent[] = [];
  const STATUS_ICON: Record<string, string> = {
    researching: '🔬', needs_review: '👁️', submitted: '📋', queued: '⏳',
  };
  for (const t of tickets.slice(0, 8)) {
    out.push({
      id: `t-${t.id}`, type: 'research',
      label: t.topic.length > 48 ? t.topic.slice(0, 48) + '…' : t.topic,
      sublabel: `Research · ${t.status.replace(/_/g, ' ')}`,
      icon: STATUS_ICON[t.status] || '📋',
      color: t.status === 'researching' ? '#7c3aed' : t.status === 'needs_review' ? '#f59e0b' : '#3d5af1',
      ts: t.created_at,
    });
  }
  for (const k of knowledge.slice(0, 6)) {
    const isApproved = k.status === 'approved';
    out.push({
      id: `k-${k.id}`, type: 'knowledge',
      label: k.title.length > 48 ? k.title.slice(0, 48) + '…' : k.title,
      sublabel: `Knowledge · ${k.status}${k.quality_score ? ` · q=${k.quality_score}` : ''}`,
      icon: isApproved ? '✅' : k.status === 'proposed' ? '⏳' : '📚',
      color: isApproved ? '#16a34a' : '#6b7280',
      ts: k.created_at,
    });
  }
  for (const i of ingest.slice(0, 5)) {
    const statusIcon = i.status === 'ready' ? '📥' : i.status === 'needs_transcript' ? '⌛' : '📄';
    out.push({
      id: `i-${i.id}`, type: 'ingestion',
      label: (i.title || i.domain || 'Source').slice(0, 48),
      sublabel: `Ingestion · ${i.status || 'queued'} · ${i.domain}`,
      icon: statusIcon,
      color: '#0d9488',
      ts: i.created_at,
    });
  }
  for (const e of events.slice(0, 4)) {
    if (!e.event_name && !e.feature) continue;
    out.push({
      id: `e-${e.created_at}`, type: 'activity',
      label: e.event_name || e.feature || 'User event',
      sublabel: `Activity · ${e.feature || 'platform'}`,
      icon: '📊',
      color: '#6366f1',
      ts: e.created_at,
    });
  }
  return out.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime()).slice(0, 18);
}

export function WorkforceOffice() {
  const [departments, setDepartments] = useState<DepartmentStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date().toISOString());
  const [oppsCount, setOppsCount] = useState(0);
  const [openTickets, setOpenTickets] = useState(0);
  const [tickets, setAllTickets] = useState<ResearchTicket[]>([]);
  const [ingestFeed, setIngestFeed] = useState<IngestEvent[]>([]);
  const [opsEvents, setOpsEvents] = useState<OpsEvent[]>([]);
  const [activePanel, setActivePanel] = useState<'workforce' | 'research' | 'ingestion' | 'liveops'>('workforce');

  const load = useCallback(async () => {
    const [phRes, evRes, oppsRes, ticketRes, transcriptRes, knowledgeRes] = await Promise.all([
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
        .in('status', ['submitted', 'queued', 'researching', 'needs_review'])
        .order('created_at', { ascending: false })
        .limit(50),
      supabase
        .from('transcript_queue')
        .select('id,title,domain,status,created_at')
        .order('created_at', { ascending: false })
        .limit(12),
      supabase
        .from('knowledge_items')
        .select('id,title,status,quality_score,created_at')
        .in('status', ['approved', 'proposed'])
        .order('created_at', { ascending: false })
        .limit(10),
    ]);

    const providers = (phRes.data || []) as ProviderHealth[];
    const events = (evRes.data || []) as AnalyticsEvent[];
    const count = oppsRes.count || 0;
    const tkts = (ticketRes.data || []) as ResearchTicket[];
    const ingest = (transcriptRes.data || []) as IngestEvent[];
    const knowledge = (knowledgeRes.data || []) as KnowledgeEvent[];

    setOppsCount(count);
    setOpenTickets(tkts.length);
    setAllTickets(tkts);
    setIngestFeed(ingest);
    setOpsEvents(buildOpsEvents(tkts, knowledge, ingest, events));
    setDepartments(buildWorkforceState(providers, events, count, tkts));
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
  const researchingCount = tickets.filter(t => t.status === 'researching').length;
  const reviewCount = tickets.filter(t => t.status === 'needs_review').length;
  const overdueCount = tickets.filter(t => {
    const age = (Date.now() - new Date(t.created_at).getTime()) / 3600000;
    return age > 24 && ['submitted', 'queued', 'researching'].includes(t.status);
  }).length;

  const PANELS = [
    { id: 'workforce' as const, label: 'Workforce', icon: Brain, count: activeWorkers },
    { id: 'research' as const, label: 'Research', icon: Clock, count: openTickets },
    { id: 'ingestion' as const, label: 'Ingestion', icon: Inbox, count: ingestFeed.length },
    { id: 'liveops' as const, label: 'Live Ops', icon: Radio, count: opsEvents.length },
  ];

  return (
    <div style={{ padding: '14px 18px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <h2 style={{ fontSize: 19, fontWeight: 800, color: '#1a1c3a', margin: 0, marginBottom: 2 }}>
            🏢 AI Workforce Office
          </h2>
          <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>
            Admin — real-time operational intelligence
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '6px 12px', borderRadius: 10, border: '1px solid #e5e7eb',
            background: '#fff', color: '#3d5af1', fontWeight: 600, fontSize: 12, cursor: 'pointer',
          }}
        >
          <RefreshCw size={11} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
          Refresh
        </button>
      </div>

      {/* Summary bar */}
      {!loading && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}
        >
          {[
            { label: 'Workers', value: totalWorkers, color: '#6366f1', bg: '#eef0fd' },
            { label: 'Active', value: activeWorkers, color: '#22c55e', bg: '#f0fdf4' },
            { label: 'Researching', value: researchingCount, color: '#7c3aed', bg: '#f5f3ff' },
            { label: 'Review Ready', value: reviewCount, color: reviewCount > 0 ? '#f59e0b' : '#9ca3af', bg: reviewCount > 0 ? '#fffbeb' : '#f9fafb' },
            { label: 'Overdue', value: overdueCount, color: overdueCount > 0 ? '#ef4444' : '#9ca3af', bg: overdueCount > 0 ? '#fef2f2' : '#f9fafb' },
            { label: 'Opportunities', value: oppsCount, color: '#7c3aed', bg: '#f5f3ff' },
          ].map(s => (
            <div key={s.label} style={{
              flex: '1 1 70px', padding: '8px 10px', borderRadius: 10,
              background: s.bg, textAlign: 'center',
              border: `1px solid ${s.color}20`,
            }}>
              <p style={{ fontSize: 18, fontWeight: 800, color: s.color, margin: 0, lineHeight: 1 }}>{s.value}</p>
              <p style={{ fontSize: 9, color: '#6b7280', margin: '2px 0 0', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{s.label}</p>
            </div>
          ))}
        </motion.div>
      )}

      {/* Sync timestamp */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 12 }}>
        <motion.div
          animate={{ opacity: [1, 0.4, 1] }}
          transition={{ duration: 3, repeat: Infinity }}
          style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }}
        />
        <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>
          Synced {timeAgo(lastRefresh)} · auto-refresh 90s
        </p>
      </div>

      {/* Panel tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
        {PANELS.map(p => {
          const Icon = p.icon;
          const isActive = activePanel === p.id;
          return (
            <button
              key={p.id}
              onClick={() => setActivePanel(p.id)}
              style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
                padding: '7px 0', borderRadius: 10,
                border: isActive ? '1.5px solid #3d5af1' : '1px solid #e5e7eb',
                background: isActive ? '#eef0fd' : '#fff',
                color: isActive ? '#3d5af1' : '#6b7280',
                fontSize: 12, fontWeight: 700, cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              <Icon size={12} />
              {p.label}
              {p.count > 0 && (
                <span style={{
                  background: isActive ? '#3d5af1' : '#f3f4f6',
                  color: isActive ? '#fff' : '#6b7280',
                  borderRadius: 5, padding: '1px 5px', fontSize: 9, fontWeight: 700,
                }}>
                  {p.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Panel content */}
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[...Array(4)].map((_, i) => (
                <div key={i} style={{ height: 56, borderRadius: 12, background: '#f3f4f6', animation: 'pulse 1.5s infinite' }} />
              ))}
            </div>
          </motion.div>
        ) : activePanel === 'workforce' ? (
          <motion.div key="workforce" initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {departments.map((dept, i) => (
                <DepartmentZone key={dept.id} department={dept} defaultExpanded={i < 3} />
              ))}
            </div>
          </motion.div>
        ) : activePanel === 'research' ? (
          <motion.div key="research" initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
            {tickets.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center' }}>
                <p style={{ fontSize: 13, color: '#8b8fa8' }}>No active research tickets.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {tickets.map(ticket => {
                  const isActive = ['researching', 'needs_review'].includes(ticket.status);
                  const color = STATUS_COLOR[ticket.status] || '#6b7280';
                  return (
                    <motion.div
                      key={ticket.id}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      style={{
                        padding: '10px 12px', borderRadius: 10,
                        background: isActive ? `${color}08` : '#f9fafb',
                        border: `1px solid ${isActive ? `${color}25` : '#e5e7eb'}`,
                        display: 'flex', alignItems: 'center', gap: 10,
                      }}
                    >
                      {isActive ? (
                        <PulseRing color={color} size={7} />
                      ) : (
                        <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#d1d5db', flexShrink: 0, margin: '0 4px' }} />
                      )}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a', margin: 0,
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {ticket.topic}
                        </p>
                        <p style={{ fontSize: 10, color: '#6b7280', margin: 0 }}>
                          {DEPT_LABEL[ticket.department] || ticket.department}
                        </p>
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <p style={{ fontSize: 11, fontWeight: 700, color, margin: 0, textTransform: 'capitalize' }}>
                          {ticket.status.replace('_', ' ')}
                        </p>
                        <p style={{ fontSize: 9, color: '#9ca3af', margin: 0 }}>
                          {timeAgo(ticket.created_at)}
                        </p>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </motion.div>
        ) : activePanel === 'ingestion' ? (
          <motion.div key="ingestion" initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
            {ingestFeed.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center' }}>
                <p style={{ fontSize: 13, color: '#8b8fa8' }}>No ingested sources yet.</p>
                <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>
                  Run playlist_ingest_worker or hermes_email_knowledge_intake.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {(() => {
                  const ready = ingestFeed.filter(i => i.status === 'ready');
                  const pending = ingestFeed.filter(i => i.status !== 'ready');
                  return (
                    <>
                      {ready.length > 0 && (
                        <div style={{ fontSize: 10, fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>
                          ✅ Ready ({ready.length})
                        </div>
                      )}
                      {ready.map((item, idx) => (
                        <IngestRow key={item.id} item={item} idx={idx} color="#16a34a" icon="📥" />
                      ))}
                      {pending.length > 0 && (
                        <div style={{ fontSize: 10, fontWeight: 700, color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: ready.length > 0 ? 8 : 0, marginBottom: 2 }}>
                          ⌛ Awaiting Transcript ({pending.length})
                        </div>
                      )}
                      {pending.slice(0, 6).map((item, idx) => (
                        <IngestRow key={item.id} item={item} idx={idx} color="#f59e0b" icon="⌛" />
                      ))}
                      {pending.length > 6 && (
                        <p style={{ fontSize: 11, color: '#9ca3af', textAlign: 'center', margin: '4px 0 0' }}>
                          +{pending.length - 6} more awaiting transcript
                        </p>
                      )}
                    </>
                  );
                })()}
              </div>
            )}
          </motion.div>
        ) : (
          <motion.div key="liveops" initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
              <motion.div
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1.8, repeat: Infinity }}
                style={{ width: 7, height: 7, borderRadius: '50%', background: '#3d5af1' }}
              />
              <span style={{ fontSize: 11, fontWeight: 700, color: '#3d5af1' }}>LIVE OPS FEED</span>
              <span style={{ fontSize: 10, color: '#9ca3af', marginLeft: 'auto' }}>{opsEvents.length} events</span>
            </div>
            {opsEvents.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center' }}>
                <p style={{ fontSize: 13, color: '#8b8fa8' }}>No operational events yet.</p>
                <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>Events appear as research, ingestion, and knowledge activity flows in.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                {opsEvents.map((ev, idx) => (
                  <motion.div
                    key={ev.id}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    style={{
                      padding: '8px 10px', borderRadius: 9,
                      background: `${ev.color}08`,
                      border: `1px solid ${ev.color}20`,
                      display: 'flex', alignItems: 'center', gap: 9,
                    }}
                  >
                    <span style={{ fontSize: 14, flexShrink: 0 }}>{ev.icon}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 11, fontWeight: 700, color: '#1a1c3a', margin: 0,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {ev.label}
                      </p>
                      <p style={{ fontSize: 9, color: '#6b7280', margin: 0 }}>{ev.sublabel}</p>
                    </div>
                    <span style={{ fontSize: 9, color: '#9ca3af', flexShrink: 0, textAlign: 'right' }}>
                      {timeAgo(ev.ts)}
                    </span>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Safety footer */}
      <div style={{
        marginTop: 16, padding: '8px 12px', borderRadius: 10,
        background: '#f0fdf4', border: '1px solid #bbf7d0',
        display: 'flex', alignItems: 'center', gap: 7,
        flexWrap: 'wrap',
      }}>
        <Shield size={12} color="#16a34a" />
        <p style={{ fontSize: 10, color: '#16a34a', fontWeight: 700, margin: 0 }}>
          DRY_RUN=true · LIVE_TRADING=false · DEMO trading only · No broker execution · No auto social
        </p>
      </div>
    </div>
  );
}
