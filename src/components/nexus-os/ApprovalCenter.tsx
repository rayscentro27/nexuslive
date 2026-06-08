import React, { useEffect, useState, useCallback } from 'react';
import {
  CheckCircle2, XCircle, MessageSquare, Clock, AlertTriangle,
  ChevronDown, ChevronUp, Loader2, Filter, Bell, BellOff,
  Eye, History, RefreshCw,
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { OSSection, Badge, PriorityBadge, timeAgo, EmptyState } from './shared';
import { useApprovalNotifier } from './useApprovalNotifier';
import type { ApprovalItem } from './types';

interface ApprovalEvent {
  id: string;
  approval_id: string;
  event_type: string;
  changed_by: string | null;
  comment: string | null;
  telegram_sent: boolean;
  created_at: string;
}

const ACTION_TYPE_RISK: Record<string, string> = {
  bulk_outreach:     'critical',
  email_outreach:    'high',
  ad_spend:          'critical',
  live_trading:      'critical',
  credential_change: 'critical',
  rls_change:        'critical',
  schema_change:     'high',
  budget_change:     'high',
  content_publish:   'medium',
  deploy_code:       'medium',
  affiliate_activate:'medium',
  client_message:    'medium',
};

// Keyword fallback so naming variants (publish_content vs content_publish,
// apply_affiliate_program vs affiliate_activate, update_broker_credentials vs
// credential_change, …) are still classified correctly — not silently 'low'.
function riskLevel(actionType: string): string {
  if (ACTION_TYPE_RISK[actionType]) return ACTION_TYPE_RISK[actionType];
  const a = (actionType || '').toLowerCase();
  if (/live[_-]?trad|broker|ad[_-]?spend|outreach|credential|rls|payment|stripe|wire|charge/.test(a)) return 'critical';
  if (/publish|post|affiliate|deploy|schema|migrat|budget|email|newsletter|social|submit|client/.test(a)) return 'high';
  if (/content|draft|message|review/.test(a)) return 'medium';
  return 'low';
}

// External / real-world impact → require an explicit confirm before approving.
function needsConfirm(actionType: string): boolean {
  const r = riskLevel(actionType);
  return r === 'high' || r === 'critical';
}

export function ApprovalCenter() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [events, setEvents] = useState<Record<string, ApprovalEvent[]>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('pending');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [historyOpen, setHistoryOpen] = useState<Set<string>>(new Set());
  const [acting, setActing] = useState<string | null>(null);
  const [confirmApprove, setConfirmApprove] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, string>>({});
  const [notifyResults, setNotifyResults] = useState<Record<string, string>>({});
  const { notify } = useApprovalNotifier();

  const load = useCallback(async () => {
    setLoading(true);
    const query = supabase
      .from('owner_approval_queue')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(60);

    if (filter !== 'all') {
      query.eq('status', filter);
    }

    const { data } = await query;
    const loaded = (data ?? []) as ApprovalItem[];
    setItems(loaded);

    // Load history events for all items in batch
    if (loaded.length > 0) {
      const ids = loaded.map(i => i.id);
      const { data: evData } = await supabase
        .from('nexus_os_approval_events')
        .select('*')
        .in('approval_id', ids)
        .order('created_at', { ascending: true });

      if (evData) {
        const byId: Record<string, ApprovalEvent[]> = {};
        (evData as ApprovalEvent[]).forEach(ev => {
          if (!byId[ev.approval_id]) byId[ev.approval_id] = [];
          byId[ev.approval_id].push(ev);
        });
        setEvents(byId);
      }
    }

    setLoading(false);
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  // Write a "viewed" event when an item is expanded for the first time
  async function markViewed(item: ApprovalItem) {
    const itemEvents = events[item.id] ?? [];
    const alreadyViewed = itemEvents.some(e => e.event_type === 'viewed');
    if (alreadyViewed) return;

    const { data } = await supabase
      .from('nexus_os_approval_events')
      .insert({
        approval_id: item.id,
        event_type: 'viewed',
        changed_by: 'ray',
        comment: null,
        telegram_sent: false,
      })
      .select()
      .single();

    if (data) {
      setEvents(prev => ({
        ...prev,
        [item.id]: [...(prev[item.id] ?? []), data as ApprovalEvent],
      }));
    }
  }

  async function act(item: ApprovalItem, status: 'approved' | 'rejected' | 'needs_edits') {
    // Two-step confirm for external/real-world-impact approvals. First click on a
    // high/critical item arms the confirm; it must be clicked again to proceed.
    // Internal/free (low/medium) items stay one-click.
    if (status === 'approved' && needsConfirm(item.action_type) && confirmApprove !== item.id) {
      setConfirmApprove(item.id);
      return;
    }
    setConfirmApprove(null);
    setActing(item.id);
    const { error } = await supabase
      .from('owner_approval_queue')
      .update({
        status,
        review_notes: comments[item.id] ?? null,
        reviewed_at: new Date().toISOString(),
      })
      .eq('id', item.id);

    if (!error) {
      setItems(prev =>
        prev.map(i =>
          i.id === item.id
            ? { ...i, status, review_notes: comments[item.id] ?? null }
            : i,
        ),
      );

      // Fire notification (non-blocking)
      const result = await notify({
        approval_id:  item.id,
        action_type:  item.action_type,
        description:  item.description,
        priority:     item.priority,
        status,
        requested_by: item.requested_by,
        review_notes: comments[item.id],
      });

      const msg = result.telegram_sent
        ? '📱 Telegram notified'
        : result.telegram_skipped_reason
        ? `Telegram: ${result.telegram_skipped_reason}`
        : 'Notification logged';
      setNotifyResults(prev => ({ ...prev, [item.id]: msg }));
    }
    setActing(null);
  }

  function toggleExpand(item: ApprovalItem) {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(item.id)) {
        next.delete(item.id);
      } else {
        next.add(item.id);
        markViewed(item);
      }
      return next;
    });
  }

  function toggleHistory(id: string) {
    setHistoryOpen(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const pendingCount = items.filter(i => i.status === 'pending').length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Approval <span className="text-[#5B7CFA]">Center</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            {pendingCount} pending · <code className="text-[10px]">owner_approval_queue</code> · history tracked
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 disabled:opacity-50 transition-all"
          >
            {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            Refresh
          </button>
          {(['all', 'pending', 'approved', 'rejected'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                filter === f
                  ? 'bg-[#5B7CFA] text-white shadow'
                  : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Telegram status */}
      <TelegramStatusBanner />

      {/* Items */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-slate-300" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState icon={CheckCircle2} message={`No ${filter === 'all' ? '' : filter} approvals`} />
      ) : (
        <div className="space-y-3">
          {items.map(item => (
            <ApprovalCard
              key={item.id}
              item={item}
              itemEvents={events[item.id] ?? []}
              expanded={expanded.has(item.id)}
              historyOpen={historyOpen.has(item.id)}
              onToggle={() => toggleExpand(item)}
              onToggleHistory={() => toggleHistory(item.id)}
              acting={acting === item.id}
              confirmArmed={confirmApprove === item.id}
              comment={comments[item.id] ?? ''}
              onCommentChange={v => setComments(prev => ({ ...prev, [item.id]: v }))}
              onApprove={() => act(item, 'approved')}
              onReject={() => act(item, 'rejected')}
              onNeedsChanges={() => act(item, 'needs_edits')}
              notifyResult={notifyResults[item.id] ?? ''}
            />
          ))}
        </div>
      )}

      {/* Safety note */}
      <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-50 border border-amber-200">
        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-700 font-medium">
          Approval actions update status in Supabase and log history. Telegram is notified based on priority
          and policy gates. No live trading, publishing, outreach, or risky actions are executed by this UI.
          A backend executor is required for downstream action execution.
        </p>
      </div>
    </div>
  );
}

function TelegramStatusBanner() {
  return (
    <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200">
      <Bell className="w-4 h-4 text-slate-400 shrink-0" />
      <div className="flex-1 text-xs text-slate-500">
        <span className="font-bold text-slate-600">Telegram notifications: </span>
        <span>Critical/urgent approvals → Telegram (if TELEGRAM_BOT_TOKEN + TELEGRAM_CRITICAL_ALERTS_ENABLED=true). </span>
        <span>Normal approvals → set TELEGRAM_APPROVAL_NOTIFICATIONS_ENABLED=true to enable. </span>
        <span>Low priority → Supabase notification only.</span>
      </div>
    </div>
  );
}

function ApprovalCard({
  item, itemEvents, expanded, historyOpen, onToggle, onToggleHistory,
  acting, confirmArmed, comment, onCommentChange, onApprove, onReject, onNeedsChanges, notifyResult,
}: {
  item: ApprovalItem;
  itemEvents: ApprovalEvent[];
  expanded: boolean;
  historyOpen: boolean;
  onToggle: () => void;
  onToggleHistory: () => void;
  acting: boolean;
  confirmArmed: boolean;
  comment: string;
  onCommentChange: (v: string) => void;
  onApprove: () => void;
  onReject: () => void;
  onNeedsChanges: () => void;
  notifyResult: string;
}) {
  const risk = riskLevel(item.action_type);
  const isPending = item.status === 'pending';
  const wasViewed = itemEvents.some(e => e.event_type === 'viewed');
  const wasNotified = itemEvents.some(e => e.event_type === 'notified');
  const telegramSent = itemEvents.some(e => e.telegram_sent);

  const borderColor =
    risk === 'critical' ? 'border-red-300' :
    risk === 'high'     ? 'border-orange-200' :
    risk === 'medium'   ? 'border-amber-200' :
    'border-slate-200';

  return (
    <div className={`bg-white rounded-2xl border ${borderColor} shadow-sm overflow-hidden`}>
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-50/50 transition-colors"
      >
        <StatusIcon status={item.status} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-black text-[#1A2244]">{item.action_type}</p>
            <PriorityBadge priority={item.priority} />
            <RiskBadgeLocal level={risk} />
            <StatusBadge status={item.status} />
            {wasViewed && <Eye className="w-3 h-3 text-slate-400" title="Viewed by Ray" />}
            {telegramSent && <span className="text-[10px] text-blue-500 font-bold">📱 TG</span>}
          </div>
          <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{item.description}</p>
          <p className="text-[10px] text-slate-400 mt-1">
            By {item.requested_by} · {timeAgo(item.created_at)}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {itemEvents.length > 0 && (
            <span className="text-[10px] text-slate-400 font-bold">{itemEvents.length} events</span>
          )}
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4 space-y-4">
          {/* Description */}
          <div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Description</p>
            <p className="text-sm text-slate-700">{item.description}</p>
          </div>

          {/* Payload */}
          {item.payload && Object.keys(item.payload).length > 0 && (
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Payload</p>
              <pre className="text-xs bg-slate-50 border border-slate-200 rounded-xl p-3 overflow-x-auto text-slate-600 max-h-32">
                {JSON.stringify(item.payload, null, 2)}
              </pre>
            </div>
          )}

          {/* Review notes */}
          {item.review_notes && (
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Review Notes</p>
              <p className="text-sm text-slate-600">{item.review_notes}</p>
            </div>
          )}

          {/* Comment input */}
          {isPending && (
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Your Comment (optional)</p>
              <textarea
                value={comment}
                onChange={e => onCommentChange(e.target.value)}
                placeholder="Add reason or note..."
                rows={2}
                className="w-full resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B7CFA]/20 focus:border-[#5B7CFA]/40"
              />
            </div>
          )}

          {/* Action buttons */}
          {isPending && (
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={onApprove}
                disabled={acting}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-white text-xs font-black disabled:opacity-50 transition-all shadow-sm ${
                  confirmArmed ? 'bg-red-600 hover:bg-red-700 ring-2 ring-red-300' : 'bg-green-500 hover:bg-green-600'
                }`}
                title={confirmArmed ? 'External/real-world impact — click again to confirm' : undefined}
              >
                {acting ? <Loader2 className="w-3 h-3 animate-spin" />
                  : confirmArmed ? <AlertTriangle className="w-3 h-3" />
                  : <CheckCircle2 className="w-3 h-3" />}
                {confirmArmed ? 'Confirm approve (external impact)' : 'Approve'}
              </button>
              {confirmArmed && (
                <span className="text-[10px] text-red-600 font-semibold">
                  This {risk}-risk action has real-world impact — click again to approve.
                </span>
              )}
              <button
                onClick={onReject}
                disabled={acting}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-red-500 text-white text-xs font-black hover:bg-red-600 disabled:opacity-50 transition-all shadow-sm"
              >
                {acting ? <Loader2 className="w-3 h-3 animate-spin" /> : <XCircle className="w-3 h-3" />}
                Reject
              </button>
              <button
                onClick={onNeedsChanges}
                disabled={acting}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-600 text-xs font-black hover:bg-slate-50 disabled:opacity-50 transition-all"
              >
                <MessageSquare className="w-3 h-3" />
                Needs Changes
              </button>
            </div>
          )}

          {/* Notify result feedback */}
          {notifyResult && (
            <p className="text-[10px] text-slate-500 italic">{notifyResult}</p>
          )}

          {/* History toggle */}
          {itemEvents.length > 0 && (
            <button
              onClick={onToggleHistory}
              className="flex items-center gap-1.5 text-xs font-bold text-[#5B7CFA] hover:underline"
            >
              <History className="w-3.5 h-3.5" />
              {historyOpen ? 'Hide' : 'Show'} history ({itemEvents.length} events)
            </button>
          )}

          {/* History timeline */}
          {historyOpen && itemEvents.length > 0 && (
            <div className="space-y-2 pt-1">
              {itemEvents.map(ev => (
                <div key={ev.id} className="flex items-start gap-2.5 text-xs">
                  <div className="w-4 h-4 rounded-full bg-slate-100 flex items-center justify-center shrink-0 mt-0.5">
                    <HistoryEventDot eventType={ev.event_type} />
                  </div>
                  <div className="flex-1">
                    <p className="font-bold text-[#1A2244]">
                      {ev.event_type}
                      {ev.changed_by && <span className="font-normal text-slate-400 ml-1">by {ev.changed_by}</span>}
                      {ev.telegram_sent && <span className="ml-1 text-blue-500">📱</span>}
                    </p>
                    {ev.comment && <p className="text-slate-500 text-[11px] mt-0.5">{ev.comment}</p>}
                    <p className="text-[10px] text-slate-400 mt-0.5">{timeAgo(ev.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function HistoryEventDot({ eventType }: { eventType: string }) {
  const colors: Record<string, string> = {
    created:      'bg-blue-400',
    notified:     'bg-indigo-400',
    viewed:       'bg-slate-400',
    approved:     'bg-green-500',
    rejected:     'bg-red-500',
    needs_changes:'bg-amber-400',
    completed:    'bg-green-600',
    failed:       'bg-red-600',
    comment:      'bg-slate-300',
  };
  return <div className={`w-2 h-2 rounded-full ${colors[eventType] ?? 'bg-slate-200'}`} />;
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'approved') return <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0" />;
  if (status === 'rejected') return <XCircle className="w-5 h-5 text-red-500 shrink-0" />;
  if (status === 'needs_edits') return <MessageSquare className="w-5 h-5 text-amber-500 shrink-0" />;
  return <Clock className="w-5 h-5 text-blue-400 animate-pulse shrink-0" />;
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'approved')   return <Badge label="Approved" variant="success" />;
  if (status === 'rejected')   return <Badge label="Rejected" variant="danger" />;
  if (status === 'needs_edits') return <Badge label="Needs Changes" variant="warn" />;
  return <Badge label="Pending" variant="info" />;
}

function RiskBadgeLocal({ level }: { level: string }) {
  if (level === 'critical') return <Badge label="Critical Risk" variant="danger" />;
  if (level === 'high')     return <Badge label="High Risk" variant="danger" />;
  if (level === 'medium')   return <Badge label="Medium Risk" variant="warn" />;
  return <Badge label="Low Risk" variant="success" />;
}
