import React, { useEffect, useState, useCallback } from 'react';
import {
  Bell, BellOff, CheckCheck, Loader2, Zap, AlertTriangle,
  TrendingUp, CheckCircle2, XCircle, Info, DollarSign, FileText,
  RefreshCw, Clock, Link,
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../AuthProvider';
import { Badge, timeAgo, EmptyState } from './shared';

interface NexusNotification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  body: string | null;
  action_url: string | null;
  action_label: string | null;
  priority: number;
  read_at: string | null;
  dismissed_at: string | null;
  created_at: string;
}

const TYPE_META: Record<string, {
  icon: React.ElementType;
  variant: 'danger' | 'warn' | 'info' | 'success' | 'default';
  category: string;
}> = {
  urgent:       { icon: AlertTriangle, variant: 'danger',  category: 'urgent' },
  action:       { icon: Zap,           variant: 'warn',    category: 'approval_needed' },
  ai:           { icon: Bell,          variant: 'info',    category: 'informational' },
  system:       { icon: Info,          variant: 'default', category: 'system_down' },
  trading:      { icon: TrendingUp,    variant: 'info',    category: 'trading_alert' },
  funding:      { icon: DollarSign,    variant: 'success', category: 'revenue_opportunity' },
  grant:        { icon: CheckCircle2,  variant: 'success', category: 'revenue_opportunity' },
  subscription: { icon: FileText,      variant: 'default', category: 'informational' },
  message:      { icon: Bell,          variant: 'info',    category: 'informational' },
};

const CATEGORIES = [
  'all',
  'approval_needed',
  'urgent',
  'trading_alert',
  'revenue_opportunity',
  'system_down',
  'informational',
];

function getCategory(type: string): string {
  return TYPE_META[type]?.category ?? 'informational';
}

export function NotificationCenter() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<NexusNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [readFilter, setReadFilter] = useState<'unread' | 'all'>('unread');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    const query = supabase
      .from('notifications')
      .select('*')
      .eq('user_id', user.id)
      .is('dismissed_at', null)
      .order('created_at', { ascending: false })
      .limit(100);

    if (readFilter === 'unread') query.is('read_at', null);

    const { data } = await query;
    setNotifications((data ?? []) as NexusNotification[]);
    setLoading(false);
  }, [user, readFilter]);

  useEffect(() => { load(); }, [load]);

  async function markRead(id: string) {
    await supabase
      .from('notifications')
      .update({ read_at: new Date().toISOString() })
      .eq('id', id);
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, read_at: new Date().toISOString() } : n),
    );
  }

  async function dismiss(id: string) {
    await supabase
      .from('notifications')
      .update({ dismissed_at: new Date().toISOString() })
      .eq('id', id);
    setNotifications(prev => prev.filter(n => n.id !== id));
  }

  async function markAllRead() {
    if (!user) return;
    await supabase
      .from('notifications')
      .update({ read_at: new Date().toISOString() })
      .eq('user_id', user.id)
      .is('read_at', null);
    setNotifications(prev =>
      prev.map(n => ({ ...n, read_at: n.read_at ?? new Date().toISOString() })),
    );
  }

  // Apply local filters
  const filtered = notifications.filter(n => {
    if (categoryFilter !== 'all' && getCategory(n.type) !== categoryFilter) return false;
    if (priorityFilter === 'high' && n.priority < 3) return false;
    if (priorityFilter === 'medium' && n.priority < 2) return false;
    return true;
  });

  const unreadCount = notifications.filter(n => !n.read_at).length;
  const urgentCount = notifications.filter(n => !n.read_at && n.priority >= 3).length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Notification <span className="text-[#5B7CFA]">Center</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
            {urgentCount > 0 && <span className="ml-2 text-red-500 font-bold">· {urgentCount} urgent</span>}
            {' '}· Supabase <code className="text-[10px]">notifications</code>
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 transition-all"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark all read
            </button>
          )}
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-500 text-xs font-bold hover:bg-slate-50 disabled:opacity-50 transition-all"
          >
            {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
          </button>
        </div>
      </div>

      {/* Filter row */}
      <div className="flex flex-col gap-2">
        {/* Read filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest shrink-0">Show:</span>
          {(['unread', 'all'] as const).map(f => (
            <button
              key={f}
              onClick={() => setReadFilter(f)}
              className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                readFilter === f
                  ? 'bg-[#5B7CFA] text-white'
                  : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Category filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest shrink-0">Category:</span>
          {CATEGORIES.map(c => (
            <button
              key={c}
              onClick={() => setCategoryFilter(c)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-bold whitespace-nowrap transition-all ${
                categoryFilter === c
                  ? 'bg-slate-700 text-white'
                  : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'
              }`}
            >
              {c.replace(/_/g, ' ')}
            </button>
          ))}
        </div>

        {/* Priority filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest shrink-0">Priority:</span>
          {(['all', 'high', 'medium'] as const).map(p => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all ${
                priorityFilter === p
                  ? 'bg-slate-700 text-white'
                  : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'
              }`}
            >
              {p === 'high' ? '🔴 High' : p === 'medium' ? '🟡 Medium' : 'All'}
            </button>
          ))}
        </div>
      </div>

      {/* Results count */}
      {(categoryFilter !== 'all' || priorityFilter !== 'all') && (
        <p className="text-xs text-slate-400">
          Showing {filtered.length} of {notifications.length} notifications
        </p>
      )}

      {/* Notifications list */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-slate-300" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={BellOff}
          message={
            categoryFilter !== 'all'
              ? `No ${categoryFilter.replace(/_/g, ' ')} notifications`
              : readFilter === 'unread'
              ? 'No unread notifications'
              : 'No notifications'
          }
        />
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm divide-y divide-slate-100">
          {filtered.map(n => (
            <NotifRow
              key={n.id}
              n={n}
              onRead={() => markRead(n.id)}
              onDismiss={() => dismiss(n.id)}
            />
          ))}
        </div>
      )}

      {/* Telegram bridge info */}
      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200">
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5">Telegram Bridge</p>
        <div className="space-y-1 text-xs text-slate-500">
          <p>Critical/urgent approvals → Telegram if <code>TELEGRAM_CRITICAL_ALERTS_ENABLED=true</code> (default: on).</p>
          <p>Normal approvals → Telegram if <code>TELEGRAM_APPROVAL_NOTIFICATIONS_ENABLED=true</code> (default: off).</p>
          <p>Low priority → Supabase notification only. No Telegram.</p>
          <p>Dedup window: 5 minutes per approval+status combination (via hermes_aggregates).</p>
        </div>
      </div>
    </div>
  );
}

function NotifRow({
  n, onRead, onDismiss,
}: {
  n: NexusNotification;
  onRead: () => void;
  onDismiss: () => void;
}) {
  const meta = TYPE_META[n.type] ?? { icon: Bell, variant: 'default' as const, category: 'informational' };
  const Icon = meta.icon;
  const variant = meta.variant;
  const isUnread = !n.read_at;
  const isUrgent = n.priority >= 3;
  const freshness = (() => {
    const diffMs = Date.now() - new Date(n.created_at).getTime();
    const diffM = Math.floor(diffMs / 60000);
    if (diffM < 60) return `${diffM}m ago`;
    const diffH = Math.floor(diffM / 60);
    if (diffH < 24) return `${diffH}h ago`;
    return `${Math.floor(diffH / 24)}d ago`;
  })();

  return (
    <div
      className={`flex items-start gap-3 px-5 py-4 transition-colors cursor-pointer ${
        isUrgent && isUnread ? 'bg-red-50/40' : isUnread ? 'bg-blue-50/30' : 'bg-white'
      } hover:bg-slate-50/60`}
      onClick={onRead}
    >
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
          variant === 'danger'  ? 'bg-red-50 text-red-500' :
          variant === 'warn'   ? 'bg-amber-50 text-amber-500' :
          variant === 'success' ? 'bg-green-50 text-green-500' :
          'bg-blue-50 text-[#5B7CFA]'
        }`}
      >
        <Icon className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className={`text-sm ${isUnread ? 'font-bold' : 'font-semibold'} text-[#1A2244]`}>
                {n.title}
              </p>
              <Badge label={n.type} variant={variant} />
              {isUrgent && <Badge label="Urgent" variant="danger" />}
            </div>
            {n.body && <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{n.body}</p>}
          </div>
          <div className="shrink-0 flex items-center gap-1.5">
            {isUnread && <div className="w-2 h-2 rounded-full bg-[#5B7CFA]" />}
            <button
              onClick={e => { e.stopPropagation(); onDismiss(); }}
              className="p-1 rounded-lg text-slate-300 hover:text-red-400 hover:bg-red-50 transition-colors"
              title="Dismiss"
            >
              <XCircle className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3 mt-1.5 flex-wrap">
          <div className="flex items-center gap-1 text-[10px] text-slate-400">
            <Clock className="w-3 h-3" />
            <span>{freshness}</span>
          </div>
          <span className="text-[10px] text-slate-300">·</span>
          <span className="text-[10px] text-slate-400">
            Priority: {n.priority >= 3 ? '🔴 High' : n.priority >= 2 ? '🟡 Medium' : '🟢 Low'}
          </span>
          {n.action_url && (
            <>
              <span className="text-[10px] text-slate-300">·</span>
              <a
                href={n.action_url}
                onClick={e => e.stopPropagation()}
                className="flex items-center gap-0.5 text-[10px] text-[#5B7CFA] font-bold hover:underline"
              >
                <Link className="w-2.5 h-2.5" />
                {n.action_label ?? 'View'}
              </a>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
