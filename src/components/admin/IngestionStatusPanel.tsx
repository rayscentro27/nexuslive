/**
 * IngestionStatusPanel — Admin visibility into email and playlist ingestion.
 * Shows recent transcript_queue items with status, source, and timestamps.
 * Answers: "Did Nexus process the latest email? What was ingested?"
 */
import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { supabase } from '../../lib/supabase';
import { Inbox, RefreshCw, CheckCircle2, AlertCircle, Clock, Mail, Youtube } from 'lucide-react';

interface IngestItem {
  id: string;
  title: string;
  domain: string;
  status: string;
  source_url: string | null;
  channel_name: string | null;
  playlist_id: string | null;
  trust_score: number | null;
  created_at: string;
}

const STATUS_CONFIG: Record<string, { color: string; bg: string; icon: string; label: string }> = {
  processed:        { color: '#16a34a', bg: '#f0fdf4', icon: '✅', label: 'Processed' },
  ready:            { color: '#2563eb', bg: '#eff6ff', icon: '📋', label: 'Ready' },
  needs_transcript: { color: '#7c3aed', bg: '#f5f3ff', icon: '🎤', label: 'Needs Transcript' },
  needs_review:     { color: '#d97706', bg: '#fffbeb', icon: '👁️', label: 'Needs Review' },
  pending:          { color: '#6b7280', bg: '#f9fafb', icon: '⏳', label: 'Pending' },
  failed:           { color: '#dc2626', bg: '#fef2f2', icon: '❌', label: 'Failed' },
  duplicate:        { color: '#9ca3af', bg: '#f9fafb', icon: '🔁', label: 'Duplicate' },
};

const DOMAIN_EMOJI: Record<string, string> = {
  trading: '📈',
  grants: '🏛️',
  funding: '💼',
  business: '🚀',
  credit: '💳',
  marketing: '📣',
  default: '📄',
};

function timeAgo(ts: string): string {
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function SourceIcon({ item }: { item: IngestItem }) {
  if (item.source_url?.includes('youtube.com') || item.source_url?.includes('youtu.be')) {
    return <Youtube size={12} color="#dc2626" />;
  }
  if (item.channel_name?.toLowerCase().includes('email') || item.source_url?.includes('mailto')) {
    return <Mail size={12} color="#6b7280" />;
  }
  return <Inbox size={12} color="#6b7280" />;
}

export function IngestionStatusPanel() {
  const [items, setItems] = useState<IngestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [domainFilter, setDomainFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [lastRefresh, setLastRefresh] = useState(new Date().toISOString());

  const load = useCallback(async () => {
    const { data } = await supabase
      .from('transcript_queue')
      .select('id,title,domain,status,source_url,channel_name,playlist_id,trust_score,created_at')
      .order('created_at', { ascending: false })
      .limit(50);

    setItems((data || []) as IngestItem[]);
    setLastRefresh(new Date().toISOString());
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 60_000);
    return () => clearInterval(t);
  }, [load]);

  const handleRefresh = () => { setRefreshing(true); void load(); };

  const domains: string[] = ['all', ...(Array.from(new Set(items.map(i => i.domain))) as string[]).filter(Boolean)];
  const statuses: string[] = ['all', ...(Array.from(new Set(items.map(i => i.status))) as string[]).filter(Boolean)];

  const filtered = items.filter(item => {
    const domainMatch = domainFilter === 'all' || item.domain === domainFilter;
    const statusMatch = statusFilter === 'all' || item.status === statusFilter;
    return domainMatch && statusMatch;
  });

  const counts = {
    total: items.length,
    processed: items.filter(i => i.status === 'processed').length,
    failed: items.filter(i => i.status === 'failed').length,
    pending: items.filter(i => ['pending', 'needs_transcript', 'needs_review'].includes(i.status)).length,
  };

  return (
    <div style={{ padding: '16px 20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: '#1a1c3a', margin: 0, marginBottom: 2 }}>
            📥 Ingestion Status
          </h2>
          <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>
            Email, playlist, and transcript source tracking
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

      {/* Summary chips */}
      {!loading && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
          {[
            { label: 'Total', value: counts.total, color: '#6366f1', bg: '#eef0fd' },
            { label: 'Processed', value: counts.processed, color: '#16a34a', bg: '#f0fdf4' },
            { label: 'Pending', value: counts.pending, color: '#d97706', bg: '#fffbeb' },
            { label: 'Failed', value: counts.failed, color: counts.failed > 0 ? '#dc2626' : '#9ca3af', bg: counts.failed > 0 ? '#fef2f2' : '#f9fafb' },
          ].map(s => (
            <div key={s.label} style={{
              flex: '1 1 60px', padding: '8px 10px', borderRadius: 10,
              background: s.bg, textAlign: 'center', border: `1px solid ${s.color}20`,
            }}>
              <p style={{ fontSize: 17, fontWeight: 800, color: s.color, margin: 0, lineHeight: 1 }}>{s.value}</p>
              <p style={{ fontSize: 9, color: '#6b7280', margin: '2px 0 0', fontWeight: 600, textTransform: 'uppercase' }}>{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Last sync */}
      <p style={{ fontSize: 11, color: '#9ca3af', marginBottom: 12 }}>
        Synced {timeAgo(lastRefresh)} · auto-refresh 60s · {filtered.length} items
      </p>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        <select
          value={domainFilter}
          onChange={e => setDomainFilter(e.target.value)}
          style={{ flex: 1, padding: '6px 10px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12, background: '#fff', color: '#374151' }}
        >
          {domains.map(d => (
            <option key={d} value={d}>{d === 'all' ? 'All Domains' : d.charAt(0).toUpperCase() + d.slice(1)}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          style={{ flex: 1, padding: '6px 10px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 12, background: '#fff', color: '#374151' }}
        >
          {statuses.map(s => (
            <option key={s} value={s}>{s === 'all' ? 'All Statuses' : (STATUS_CONFIG[s]?.label || s)}</option>
          ))}
        </select>
      </div>

      {/* Items */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {[...Array(5)].map((_, i) => (
            <div key={i} style={{ height: 52, borderRadius: 10, background: '#f3f4f6', animation: 'pulse 1.5s infinite' }} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '30px 0' }}>
          <Inbox size={32} color="#d1d5db" style={{ margin: '0 auto 8px' }} />
          <p style={{ fontSize: 13, color: '#9ca3af' }}>No ingestion items found.</p>
          <p style={{ fontSize: 11, color: '#d1d5db', marginTop: 4 }}>
            Run hermes_email_knowledge_intake.py or playlist_ingest_worker.py to populate.
          </p>
        </div>
      ) : (
        <AnimatePresence>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {filtered.map((item, idx) => {
              const cfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.pending;
              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.03 }}
                  style={{
                    padding: '9px 12px', borderRadius: 10,
                    background: cfg.bg,
                    border: `1px solid ${cfg.color}25`,
                    display: 'flex', alignItems: 'center', gap: 10,
                  }}
                >
                  <span style={{ fontSize: 14 }}>
                    {DOMAIN_EMOJI[item.domain] || DOMAIN_EMOJI.default}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: '#1a1c3a', margin: 0,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.title || item.source_url || 'Untitled source'}
                    </p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 2 }}>
                      <SourceIcon item={item} />
                      <span style={{ fontSize: 10, color: '#6b7280' }}>
                        {item.domain}{item.channel_name ? ` · ${item.channel_name}` : ''}
                        {item.trust_score != null ? ` · trust ${item.trust_score}` : ''}
                      </span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{
                      display: 'inline-flex', alignItems: 'center', gap: 3,
                      padding: '2px 7px', borderRadius: 6,
                      background: `${cfg.color}15`, color: cfg.color,
                      fontSize: 10, fontWeight: 700,
                    }}>
                      {cfg.icon} {cfg.label}
                    </div>
                    <p style={{ fontSize: 9, color: '#9ca3af', margin: '3px 0 0', textAlign: 'right' }}>
                      {timeAgo(item.created_at)}
                    </p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </AnimatePresence>
      )}
    </div>
  );
}
