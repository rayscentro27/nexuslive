/**
 * NexusIntelligencePanel — "What Nexus Learned Today" live intelligence feed.
 * Shows recently approved knowledge, research queue activity, trending concepts,
 * and ingestion activity. Pulls from Supabase in real time.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { supabase } from '../lib/supabase';
import { Brain, BookOpen, Activity, ChevronRight } from 'lucide-react';

interface KnowledgeItem {
  id: string;
  domain: string;
  title: string;
  quality_score: number;
  approved_at: string | null;
  created_at: string;
}

interface ResearchTicket {
  id: string;
  department: string;
  topic: string;
  status: string;
  created_at: string;
}

interface TranscriptItem {
  id: string;
  title: string;
  domain: string;
  source_type: string | null;
  created_at: string;
}

interface IngestionSummary {
  notebooklm: number;
  email: number;
  playlist: number;
  other: number;
}

interface CentralSnapshot {
  knowledge?: { learned_recent?: Array<{ title: string; domain: string; quality_score: number; created_at: string }> };
  opportunities?: { recent_count?: number };
  grants?: { recent_count?: number };
  worker_activity?: { feature_counts?: Record<string, number> };
}

const DOMAIN_EMOJI: Record<string, string> = {
  trading: '📈',
  grants: '🏛️',
  funding: '💼',
  business: '🚀',
  credit: '💳',
  marketing: '📣',
  operations: '⚡',
  default: '💡',
};

const DEPT_LABEL: Record<string, string> = {
  trading_intelligence: 'Trading',
  grants_research: 'Grants',
  funding_intelligence: 'Funding',
  business_opportunities: 'Business',
  credit_research: 'Credit',
  marketing_intelligence: 'Marketing',
  operations: 'Operations',
};

function timeAgo(ts: string): string {
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function PulseDot({ color = '#3d5af1', size = 6 }: { color?: string; size?: number }) {
  return (
    <div style={{ position: 'relative', width: size + 8, height: size + 8, flexShrink: 0 }}>
      <motion.div
        animate={{ scale: [1, 1.8, 1], opacity: [0.7, 0, 0.7] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute', inset: 0, borderRadius: '50%',
          background: color, opacity: 0.3,
        }}
      />
      <div style={{
        position: 'absolute',
        top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        width: size, height: size, borderRadius: '50%', background: color,
      }} />
    </div>
  );
}

interface Props {
  compact?: boolean;
  onNavigate?: (tab: string) => void;
}

export function NexusIntelligencePanel({ compact = false, onNavigate }: Props) {
  const [knowledge, setKnowledge] = useState<KnowledgeItem[]>([]);
  const [tickets, setTickets] = useState<ResearchTicket[]>([]);
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'learned' | 'queue' | 'ingestion'>('learned');
  const [snapshot, setSnapshot] = useState<CentralSnapshot | null>(null);

  const load = useCallback(async () => {
    let centralSnapshot: CentralSnapshot | null = null;
    try {
      const statusRes = await fetch('/api/admin/ai-ops/status', { credentials: 'include' });
      if (statusRes.ok) {
        const payload = await statusRes.json();
        centralSnapshot = payload?.data?.central_operational_snapshot || payload?.central_operational_snapshot || null;
      }
    } catch {
      centralSnapshot = null;
    }

    const [kiRes, tkRes, trRes] = await Promise.all([
      supabase
        .from('knowledge_items')
        .select('id,domain,title,quality_score,approved_at,created_at')
        .order('created_at', { ascending: false })
        .limit(8),
      supabase
        .from('research_requests')
        .select('id,department,topic,status,created_at')
        .in('status', ['submitted', 'queued', 'researching', 'needs_review'])
        .order('created_at', { ascending: false })
        .limit(6),
      supabase
        .from('transcript_queue')
        .select('id,title,domain,source_type,created_at')
        .order('created_at', { ascending: false })
        .limit(5),
    ]);
    if (kiRes.data) setKnowledge(kiRes.data as KnowledgeItem[]);
    if (tkRes.data) setTickets(tkRes.data as ResearchTicket[]);
    if (trRes.data) setTranscripts(trRes.data as TranscriptItem[]);
    setSnapshot(centralSnapshot);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 60_000);
    return () => clearInterval(t);
  }, [load]);

  const totalActivity = knowledge.length + tickets.length + transcripts.length;
  const learnedToday = knowledge.filter(item =>
    item.approved_at && Date.now() - new Date(item.approved_at).getTime() < 24 * 60 * 60 * 1000
  ).length;

  const queueByStatus = tickets.reduce<Record<string, number>>((acc, ticket) => {
    acc[ticket.status] = (acc[ticket.status] ?? 0) + 1;
    return acc;
  }, {});

  const ingestionSummary = transcripts.reduce<IngestionSummary>((acc, tr) => {
    const sourceType = (tr.source_type || '').toLowerCase();
    if (sourceType.includes('notebooklm')) {
      acc.notebooklm += 1;
    } else if (sourceType.includes('email')) {
      acc.email += 1;
    } else if (sourceType.includes('youtube') || sourceType.includes('playlist')) {
      acc.playlist += 1;
    } else {
      acc.other += 1;
    }
    return acc;
  }, { notebooklm: 0, email: 0, playlist: 0, other: 0 });

  const trendingTopics = Object.entries(snapshot?.worker_activity?.feature_counts || {})
    .filter(([k]) => k !== 'unknown')
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  const TABS = [
    { id: 'learned' as const, label: 'Learned', count: knowledge.length, icon: Brain },
    { id: 'queue' as const, label: 'Queue', count: tickets.length, icon: Activity },
    { id: 'ingestion' as const, label: 'Sources', count: transcripts.length, icon: BookOpen },
  ];

  return (
    <div className="glass-card" style={{
      padding: compact ? '12px 14px' : '16px 18px',
      background: 'linear-gradient(135deg, #0f0f1a 0%, #1a1c3a 100%)',
      border: '1px solid rgba(61,90,241,0.25)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: 'rgba(61,90,241,0.2)',
            border: '1px solid rgba(61,90,241,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Brain size={14} color="#7b9bf8" />
          </div>
          <div>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: '#e8eaf6', margin: 0 }}>
              Nexus Intelligence
            </h3>
            <p style={{ fontSize: 10, color: '#6b7280', margin: 0 }}>
              {loading ? 'Loading...' : `${totalActivity} active signals${learnedToday > 0 ? ` · ${learnedToday} learned today` : ''}`}
            </p>
            {!loading && (
              <p style={{ fontSize: 9, color: '#64748b', margin: '2px 0 0' }}>
                {`Opportunities ${snapshot?.opportunities?.recent_count || 0} · Grants ${snapshot?.grants?.recent_count || 0}`}
              </p>
            )}
          </div>
        </div>
        {!loading && totalActivity > 0 && (
          <PulseDot color="#3d5af1" size={7} />
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
        {TABS.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                flex: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                padding: '5px 6px',
                borderRadius: 7,
                border: isActive ? '1px solid rgba(61,90,241,0.5)' : '1px solid rgba(255,255,255,0.06)',
                background: isActive ? 'rgba(61,90,241,0.2)' : 'rgba(255,255,255,0.04)',
                color: isActive ? '#7b9bf8' : '#6b7280',
                fontSize: 10,
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={10} />
              {tab.label}
              {tab.count > 0 && (
                <span style={{
                  background: isActive ? '#3d5af1' : 'rgba(255,255,255,0.1)',
                  color: isActive ? '#fff' : '#9ca3af',
                  borderRadius: 4,
                  padding: '1px 5px',
                  fontSize: 9,
                  fontWeight: 700,
                }}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {[...Array(3)].map((_, i) => (
              <div key={i} style={{
                height: 32, borderRadius: 8, background: 'rgba(255,255,255,0.05)',
                marginBottom: 6,
                animation: 'pulse 1.5s infinite',
              }} />
            ))}
          </motion.div>
        ) : activeTab === 'learned' ? (
          <motion.div key="learned" initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
            {knowledge.length === 0 ? (
              <p style={{ fontSize: 11, color: '#6b7280', padding: '4px 0' }}>
                No knowledge items yet — approve proposed records in Admin → Tickets.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {trendingTopics.length > 0 && (
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {trendingTopics.map(([topic, count]) => (
                      <span key={topic} style={{ fontSize: 9, color: '#94a3b8', border: '1px solid rgba(148,163,184,0.25)', borderRadius: 999, padding: '1px 6px' }}>
                        {topic}: {count}
                      </span>
                    ))}
                  </div>
                )}
                {knowledge.slice(0, compact ? 3 : 6).map(item => (
                  <div key={item.id} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '6px 8px', borderRadius: 8,
                    background: item.quality_score >= 70
                      ? 'rgba(34,197,94,0.08)'
                      : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${item.quality_score >= 70 ? 'rgba(34,197,94,0.2)' : 'rgba(255,255,255,0.06)'}`,
                  }}>
                    <span style={{ fontSize: 14, flexShrink: 0 }}>
                      {DOMAIN_EMOJI[item.domain] || DOMAIN_EMOJI.default}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 11, fontWeight: 600, color: '#d1d5db', margin: 0,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.title.replace(/^\[Proposed\]\s*/i, '')}
                      </p>
                      <p style={{ fontSize: 9, color: '#6b7280', margin: 0 }}>
                        {item.domain} · score {item.quality_score} · {timeAgo(item.created_at)}
                      </p>
                    </div>
                    <div style={{
                      fontSize: 9, fontWeight: 700,
                      color: item.quality_score >= 70 ? '#22c55e' : '#f59e0b',
                      flexShrink: 0,
                    }}>
                      {item.quality_score >= 70 ? 'LIVE' : 'PENDING'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        ) : activeTab === 'queue' ? (
          <motion.div key="queue" initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
            {tickets.length === 0 ? (
              <p style={{ fontSize: 11, color: '#6b7280', padding: '4px 0' }}>
                No active research tickets.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{
                  display: 'flex',
                  gap: 6,
                  flexWrap: 'wrap',
                  marginBottom: 2,
                }}>
                  {Object.entries(queueByStatus).slice(0, 4).map(([status, count]) => (
                    <span
                      key={status}
                      style={{
                        fontSize: 9,
                        color: '#94a3b8',
                        border: '1px solid rgba(148,163,184,0.25)',
                        background: 'rgba(148,163,184,0.08)',
                        borderRadius: 999,
                        padding: '1px 6px',
                      }}
                    >
                      {status}: {count}
                    </span>
                  ))}
                </div>
                {tickets.slice(0, compact ? 3 : 6).map(ticket => {
                  const isActive = ['researching', 'needs_review'].includes(ticket.status);
                  return (
                    <div key={ticket.id} style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '6px 8px', borderRadius: 8,
                      background: isActive ? 'rgba(124,58,237,0.1)' : 'rgba(255,255,255,0.04)',
                      border: `1px solid ${isActive ? 'rgba(124,58,237,0.25)' : 'rgba(255,255,255,0.06)'}`,
                    }}>
                      {isActive ? (
                        <PulseDot color="#7c3aed" size={5} />
                      ) : (
                        <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#4b5563', flexShrink: 0, margin: '0 4px' }} />
                      )}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontSize: 11, fontWeight: 600, color: '#d1d5db', margin: 0,
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {ticket.topic}
                        </p>
                        <p style={{ fontSize: 9, color: '#6b7280', margin: 0 }}>
                          {DEPT_LABEL[ticket.department] || ticket.department} · {ticket.status}
                        </p>
                      </div>
                      <span style={{ fontSize: 9, color: '#6b7280', flexShrink: 0 }}>
                        {timeAgo(ticket.created_at)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </motion.div>
        ) : (
          <motion.div key="ingestion" initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }}>
            {transcripts.length === 0 ? (
              <p style={{ fontSize: 11, color: '#6b7280', padding: '4px 0' }}>
                No ingested sources yet — run notebooklm_ingest_adapter or email intake.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: compact ? '1fr 1fr' : 'repeat(4, minmax(0, 1fr))',
                  gap: 6,
                }}>
                  {[
                    ['NotebookLM', ingestionSummary.notebooklm],
                    ['Email', ingestionSummary.email],
                    ['Playlist', ingestionSummary.playlist],
                    ['Other', ingestionSummary.other],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      style={{
                        borderRadius: 7,
                        border: '1px solid rgba(255,255,255,0.08)',
                        background: 'rgba(255,255,255,0.03)',
                        padding: '5px 6px',
                      }}
                    >
                      <p style={{ margin: 0, fontSize: 9, color: '#94a3b8' }}>{label}</p>
                      <p style={{ margin: 0, fontSize: 12, fontWeight: 700, color: '#e5e7eb' }}>{value}</p>
                    </div>
                  ))}
                </div>
                {transcripts.map(tr => (
                  <div key={tr.id} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '6px 8px', borderRadius: 8,
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}>
                    <span style={{ fontSize: 12 }}>📥</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 11, fontWeight: 600, color: '#d1d5db', margin: 0,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {tr.title || 'Untitled source'}
                      </p>
                      <p style={{ fontSize: 9, color: '#6b7280', margin: 0 }}>
                        {tr.domain} · {(tr.source_type || 'unknown').replace('_', ' ')} · {timeAgo(tr.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer CTA */}
      {!loading && !compact && (
        <button
          onClick={() => onNavigate?.('opportunities')}
          style={{
            marginTop: 10,
            width: '100%',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
            padding: '7px 0',
            borderRadius: 8,
            border: '1px solid rgba(61,90,241,0.3)',
            background: 'rgba(61,90,241,0.1)',
            color: '#7b9bf8',
            fontSize: 11, fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          View All Intelligence <ChevronRight size={11} />
        </button>
      )}
    </div>
  );
}
