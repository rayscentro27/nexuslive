import React, { useState, useEffect, useCallback } from 'react';
import { supabase } from '../../lib/supabase';

interface ResearchTicket {
  id: string;
  user_id: string | null;
  department: string;
  request_type: string;
  priority: string;
  topic: string;
  original_question: string;
  status: string;
  confidence_gap: number | null;
  estimated_completion_hours: number | null;
  assigned_worker: string | null;
  risk_level: string;
  research_summary: string | null;
  recommended_action: string | null;
  client_visible_status: string;
  notify_user_when_ready: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

const DEPT_LABELS: Record<string, string> = {
  trading_intelligence:  '📈 Trading',
  grants_research:       '🏛️ Grants',
  funding_intelligence:  '💼 Funding',
  business_opportunities:'🚀 Business',
  credit_research:       '💳 Credit',
  marketing_intelligence:'📣 Marketing',
  operations:            '🎯 Operations',
};

const STATUS_COLORS: Record<string, string> = {
  submitted:    '#6b7280',
  queued:       '#2563eb',
  researching:  '#7c3aed',
  needs_review: '#d97706',
  completed:    '#059669',
  rejected:     '#dc2626',
  archived:     '#9ca3af',
};

const PRIORITY_COLORS: Record<string, string> = {
  urgent: '#dc2626',
  high:   '#ea580c',
  normal: '#2563eb',
  low:    '#6b7280',
};

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const h = Math.floor(diff / 3_600_000);
  const m = Math.floor((diff % 3_600_000) / 60_000);
  if (h > 48) return `${Math.floor(h / 24)}d ago`;
  if (h > 0) return `${h}h ${m}m ago`;
  return `${m}m ago`;
}

function isOverdue(ticket: ResearchTicket): boolean {
  if (['completed', 'rejected', 'archived'].includes(ticket.status)) return false;
  const est = ticket.estimated_completion_hours ?? 24;
  const ageH = (Date.now() - new Date(ticket.created_at).getTime()) / 3_600_000;
  return ageH > est;
}

type FilterStatus = 'open' | 'completed' | 'all';

export function ResearchTicketBoard() {
  const [tickets, setTickets] = useState<ResearchTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterDept, setFilterDept] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('open');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const load = useCallback(async () => {
    setLoading(true);
    try {
      let q = supabase
        .from('research_requests')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);

      if (filterStatus === 'open') {
        q = q.in('status', ['submitted', 'queued', 'researching', 'needs_review']);
      } else if (filterStatus === 'completed') {
        q = q.in('status', ['completed', 'rejected', 'archived']);
      }
      if (filterDept !== 'all') {
        q = q.eq('department', filterDept);
      }

      const { data, error } = await q;
      if (error) throw error;
      setTickets((data as ResearchTicket[]) ?? []);
      setLastRefresh(new Date());
    } catch (err) {
      console.error('ResearchTicketBoard load error:', err);
    } finally {
      setLoading(false);
    }
  }, [filterDept, filterStatus]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 60_000);
    return () => clearInterval(interval);
  }, [load]);

  const openCount = tickets.filter(t => ['submitted','queued','researching','needs_review'].includes(t.status)).length;
  const overdueCount = tickets.filter(isOverdue).length;
  const depts = ['all', ...Object.keys(DEPT_LABELS)];

  return (
    <div style={{ padding: '16px', fontFamily: 'system-ui, sans-serif' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#111827' }}>
            📋 Research Ticket Board
          </h2>
          <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
            {openCount} open · {overdueCount > 0 ? <span style={{ color: '#dc2626' }}>{overdueCount} overdue · </span> : null}
            Refreshed {timeAgo(lastRefresh.toISOString())}
          </div>
        </div>
        <button
          onClick={load}
          style={{ background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: 6, padding: '6px 12px', cursor: 'pointer', fontSize: 13 }}
        >
          ↻ Refresh
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {(['open', 'completed', 'all'] as FilterStatus[]).map(s => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            style={{
              padding: '4px 12px', borderRadius: 20, fontSize: 12, cursor: 'pointer',
              background: filterStatus === s ? '#111827' : '#f3f4f6',
              color: filterStatus === s ? '#fff' : '#374151',
              border: filterStatus === s ? '1px solid #111827' : '1px solid #d1d5db',
            }}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
        <div style={{ width: 1, background: '#e5e7eb', margin: '0 4px' }} />
        <select
          value={filterDept}
          onChange={e => setFilterDept(e.target.value)}
          style={{ fontSize: 12, padding: '4px 8px', borderRadius: 6, border: '1px solid #d1d5db', background: '#f9fafb' }}
        >
          {depts.map(d => (
            <option key={d} value={d}>
              {d === 'all' ? 'All Departments' : DEPT_LABELS[d] ?? d}
            </option>
          ))}
        </select>
      </div>

      {/* Ticket list */}
      {loading && <div style={{ color: '#6b7280', fontSize: 13 }}>Loading tickets…</div>}
      {!loading && tickets.length === 0 && (
        <div style={{ textAlign: 'center', padding: 32, color: '#9ca3af', fontSize: 14 }}>
          No tickets found.
        </div>
      )}
      {!loading && tickets.map(ticket => {
        const overdue = isOverdue(ticket);
        const isOpen = expanded === ticket.id;
        return (
          <div
            key={ticket.id}
            style={{
              background: '#fff',
              border: `1px solid ${overdue ? '#fca5a5' : '#e5e7eb'}`,
              borderRadius: 10,
              marginBottom: 10,
              overflow: 'hidden',
              boxShadow: overdue ? '0 0 0 2px rgba(239,68,68,0.1)' : undefined,
            }}
          >
            {/* Row */}
            <div
              onClick={() => setExpanded(isOpen ? null : ticket.id)}
              style={{ padding: '12px 16px', cursor: 'pointer', display: 'flex', gap: 12, alignItems: 'flex-start' }}
            >
              {/* Priority dot */}
              <div style={{
                width: 10, height: 10, borderRadius: '50%', marginTop: 5, flexShrink: 0,
                background: PRIORITY_COLORS[ticket.priority] ?? '#6b7280',
              }} />

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 12, color: '#6b7280' }}>{DEPT_LABELS[ticket.department] ?? ticket.department}</span>
                  <span style={{
                    fontSize: 11, padding: '1px 8px', borderRadius: 10,
                    background: STATUS_COLORS[ticket.status] + '20',
                    color: STATUS_COLORS[ticket.status],
                    border: `1px solid ${STATUS_COLORS[ticket.status]}40`,
                    fontWeight: 600,
                  }}>
                    {ticket.status}
                  </span>
                  {overdue && (
                    <span style={{ fontSize: 11, color: '#dc2626', fontWeight: 600 }}>⚠️ overdue</span>
                  )}
                </div>
                <div style={{ fontWeight: 600, fontSize: 14, marginTop: 2, color: '#111827', wordBreak: 'break-word' }}>
                  {ticket.topic}
                </div>
                <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
                  {timeAgo(ticket.created_at)}
                  {ticket.confidence_gap != null && ` · ${ticket.confidence_gap}% confidence gap`}
                  {ticket.assigned_worker && ` · ${ticket.assigned_worker}`}
                </div>
              </div>

              <div style={{ fontSize: 16, color: '#9ca3af', flexShrink: 0 }}>
                {isOpen ? '▲' : '▼'}
              </div>
            </div>

            {/* Expanded detail */}
            {isOpen && (
              <div style={{ padding: '0 16px 16px', borderTop: '1px solid #f3f4f6' }}>
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>
                    Original Question
                  </div>
                  <div style={{ fontSize: 13, color: '#374151', background: '#f9fafb', borderRadius: 6, padding: '8px 12px' }}>
                    {ticket.original_question}
                  </div>
                </div>

                {ticket.research_summary && (
                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>
                      Research Summary
                    </div>
                    <div style={{ fontSize: 13, color: '#374151', background: '#f0fdf4', borderRadius: 6, padding: '8px 12px', borderLeft: '3px solid #059669' }}>
                      {ticket.research_summary}
                    </div>
                  </div>
                )}

                {ticket.recommended_action && (
                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>
                      Recommended Action
                    </div>
                    <div style={{ fontSize: 13, color: '#374151' }}>{ticket.recommended_action}</div>
                  </div>
                )}

                <div style={{ display: 'flex', gap: 16, marginTop: 12, flexWrap: 'wrap' }}>
                  {[
                    ['Risk', ticket.risk_level],
                    ['Priority', ticket.priority],
                    ['Est. Hours', ticket.estimated_completion_hours != null ? `${ticket.estimated_completion_hours}h` : '—'],
                    ['Type', ticket.request_type],
                    ['Notify', ticket.notify_user_when_ready ? 'Yes' : 'No'],
                  ].map(([label, val]) => (
                    <div key={label}>
                      <div style={{ fontSize: 10, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 1 }}>{label}</div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>{val}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Safety footer */}
      <div style={{ marginTop: 20, padding: '8px 12px', background: '#f9fafb', borderRadius: 6, fontSize: 11, color: '#6b7280', textAlign: 'center' }}>
        🔒 Research tickets are read-only for display · No automated actions taken from this board
      </div>
    </div>
  );
}
