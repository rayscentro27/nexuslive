import React, { useEffect, useState } from 'react';
import {
  Activity, AlertTriangle, CheckCircle2, Clock, DollarSign,
  TrendingUp, MessageSquare, Zap, Cpu, FileText, RefreshCw, Loader2,
  Bell, ShieldAlert,
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { getSystemHealth, getTradingStatus } from '../../services/nexusApi';
import { OSSection, OSCard, StatusDot, Badge, MockLabel, timeAgo, NotConnectedLabel, EmptyState } from './shared';
import { useApprovalNotifier } from './useApprovalNotifier';
import type { SystemAlert, ApprovalItem, OsSection } from './types';

interface CommandCenterProps {
  onNavigate: (section: OsSection) => void;
}

interface SystemHealthResult {
  status?: string;
  [key: string]: unknown;
}

interface TradingStatusResult {
  engine?: {
    dry_run: boolean;
    live_trading: boolean;
    broker_type: string;
    broker_connected: boolean;
    signals_processed: number;
    active_positions: number;
    stage: string;
    updated_at: string;
  };
}

export function CommandCenter({ onNavigate }: CommandCenterProps) {
  const [alerts, setAlerts] = useState<SystemAlert[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalItem[]>([]);
  const [urgentNotifCount, setUrgentNotifCount] = useState(0);
  const [latestUrgentNotif, setLatestUrgentNotif] = useState<string | null>(null);
  const [health, setHealth] = useState<SystemHealthResult | null>(null);
  const [trading, setTrading] = useState<TradingStatusResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  async function load() {
    setLoading(true);
    try {
      const [alertsRes, approvalsRes] = await Promise.all([
        supabase
          .from('hermes_aggregates')
          .select('id,event_source,event_type,classification,aggregated_summary,created_at')
          .in('classification', ['critical_alert', 'actionable'])
          .order('created_at', { ascending: false })
          .limit(5),
        supabase
          .from('owner_approval_queue')
          .select('id,action_type,description,priority,status,requested_by,created_at')
          .eq('status', 'pending')
          .order('created_at', { ascending: false })
          .limit(8),
      ]);
      if (alertsRes.data) setAlerts(alertsRes.data as SystemAlert[]);
      if (approvalsRes.data) setPendingApprovals(approvalsRes.data as ApprovalItem[]);
    } catch (_) {}

    // Load urgent unread notifications
    try {
      const { data: notifData, count } = await supabase
        .from('notifications')
        .select('title', { count: 'exact' })
        .is('read_at', null)
        .is('dismissed_at', null)
        .gte('priority', 3)
        .order('created_at', { ascending: false })
        .limit(1);
      setUrgentNotifCount(count ?? 0);
      setLatestUrgentNotif(notifData?.[0]?.title ?? null);
    } catch (_) {}

    try {
      const h = await getSystemHealth();
      setHealth(h as SystemHealthResult);
    } catch (_) {
      setHealth(null);
    }

    try {
      const t = await getTradingStatus();
      setTrading(t as TradingStatusResult);
    } catch (_) {
      setTrading(null);
    }

    setLoading(false);
    setLastRefresh(new Date());
  }

  useEffect(() => { load(); }, []);

  const criticalAlerts = alerts.filter(a => a.classification === 'critical_alert');
  const actionableAlerts = alerts.filter(a => a.classification === 'actionable');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-[#1A2244]">Nexus OS <span className="text-[#5B7CFA]">Command Center</span></h1>
          <p className="text-slate-400 text-sm mt-0.5">
            Refreshed {timeAgo(lastRefresh.toISOString())} ·{' '}
            {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 transition-all disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
          Refresh
        </button>
      </div>

      {/* "Needs Ray" banner — shown when there are urgent items */}
      {(pendingApprovals.length > 0 || urgentNotifCount > 0 || criticalAlerts.length > 0) && (
        <NeedsRayCard
          pendingApprovals={pendingApprovals.length}
          criticalApprovals={pendingApprovals.filter(a => a.priority === 'urgent').length}
          urgentNotifs={urgentNotifCount}
          latestUrgentNotif={latestUrgentNotif}
          criticalAlerts={criticalAlerts.length}
          onApprovals={() => onNavigate('approvals')}
          onNotifications={() => onNavigate('notifications')}
        />
      )}

      {/* Status row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          icon={AlertTriangle}
          label="Blockers"
          value={criticalAlerts.length === 0 ? 'All Clear' : `${criticalAlerts.length} Alert${criticalAlerts.length > 1 ? 's' : ''}`}
          color={criticalAlerts.length > 0 ? 'red' : 'green'}
          sub="From Hermes aggregates"
        />
        <StatCard
          icon={CheckCircle2}
          label="Pending Approvals"
          value={String(pendingApprovals.length)}
          color={pendingApprovals.length > 0 ? 'amber' : 'green'}
          sub={`${pendingApprovals.filter(a => a.priority === 'urgent').length} urgent · owner_approval_queue`}
          onClick={() => onNavigate('approvals')}
        />
        <StatCard
          icon={TrendingUp}
          label="Trading Mode"
          value={trading?.engine?.dry_run ? 'Paper/Dry Run' : trading ? 'Live' : '—'}
          color={trading?.engine?.live_trading ? 'red' : 'green'}
          sub={trading ? `${trading.engine?.broker_type?.toUpperCase() ?? '?'} · ${trading.engine?.stage ?? '?'}` : 'Not connected'}
          onClick={() => onNavigate('trading')}
        />
        <StatCard
          icon={Bell}
          label="Urgent Notifications"
          value={String(urgentNotifCount)}
          color={urgentNotifCount > 0 ? 'red' : 'green'}
          sub={latestUrgentNotif ? latestUrgentNotif.slice(0, 30) : 'None unread'}
          onClick={() => onNavigate('notifications')}
        />
      </div>

      {/* Critical alerts */}
      {criticalAlerts.length > 0 && (
        <OSCard className="border-red-200 bg-red-50/40">
          <div className="px-5 py-4 border-b border-red-100 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <span className="text-[10px] font-black text-red-700 uppercase tracking-widest">Critical Alerts</span>
          </div>
          <div className="divide-y divide-red-100">
            {criticalAlerts.map(a => (
              <div key={a.id} className="px-5 py-3 flex items-start gap-3">
                <StatusDot status="offline" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-[#1A2244]">{a.event_type}</p>
                  <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{a.aggregated_summary ?? 'No summary'}</p>
                  <p className="text-[10px] text-slate-400 mt-1">Source: {a.event_source} · {timeAgo(a.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </OSCard>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Pending approvals preview */}
        <OSSection title="Approval Inbox" icon={CheckCircle2} action={
          <button onClick={() => onNavigate('approvals')} className="text-[10px] font-bold text-[#5B7CFA] hover:underline">
            View All
          </button>
        }>
          {loading ? (
            <LoadingRow />
          ) : pendingApprovals.length === 0 ? (
            <EmptyState icon={CheckCircle2} message="No pending approvals" />
          ) : (
            <div className="space-y-2">
              {pendingApprovals.slice(0, 3).map(a => (
                <div key={a.id} className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${a.priority === 'urgent' ? 'bg-red-500' : a.priority === 'normal' ? 'bg-blue-400' : 'bg-slate-300'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-[#1A2244] truncate">{a.action_type}</p>
                    <p className="text-[10px] text-slate-500 line-clamp-1 mt-0.5">{a.description}</p>
                    <p className="text-[10px] text-slate-400 mt-1">By {a.requested_by} · {timeAgo(a.created_at)}</p>
                  </div>
                </div>
              ))}
              {pendingApprovals.length > 3 && (
                <button onClick={() => onNavigate('approvals')} className="text-xs text-[#5B7CFA] font-bold mt-1 hover:underline">
                  +{pendingApprovals.length - 3} more
                </button>
              )}
            </div>
          )}
        </OSSection>

        {/* Actionable alerts */}
        <OSSection title="Hermes Alerts" icon={Zap} action={
          <Badge label={`${actionableAlerts.length} actionable`} variant={actionableAlerts.length > 0 ? 'warn' : 'success'} />
        }>
          {loading ? (
            <LoadingRow />
          ) : actionableAlerts.length === 0 && criticalAlerts.length === 0 ? (
            <EmptyState icon={Activity} message="No alerts from Hermes" />
          ) : (
            <div className="space-y-2">
              {[...criticalAlerts, ...actionableAlerts].slice(0, 4).map(a => (
                <div key={a.id} className="flex items-start gap-2 p-2 rounded-lg">
                  <StatusDot status={a.classification === 'critical_alert' ? 'offline' : 'limited'} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-[#1A2244]">{a.event_type}</p>
                    <p className="text-[10px] text-slate-500 line-clamp-1">{a.aggregated_summary}</p>
                    <p className="text-[10px] text-slate-400">{a.event_source} · {timeAgo(a.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </OSSection>

        {/* Trading status */}
        <OSSection title="Trading Ops" icon={TrendingUp} action={
          <button onClick={() => onNavigate('trading')} className="text-[10px] font-bold text-[#5B7CFA] hover:underline">Open</button>
        }>
          {loading ? <LoadingRow /> : trading?.engine ? (
            <div className="space-y-2">
              <InfoRow label="Mode" value={trading.engine.dry_run ? '📋 Paper / Dry Run — No real money' : '⚠️ LIVE'} />
              <InfoRow label="Broker" value={trading.engine.broker_type} />
              <InfoRow label="Connected" value={trading.engine.broker_connected ? 'Yes' : 'No'} />
              <InfoRow label="Active Positions" value={String(trading.engine.active_positions)} />
              <InfoRow label="Signals Processed" value={String(trading.engine.signals_processed)} />
              <InfoRow label="Last Updated" value={timeAgo(trading.engine.updated_at)} />
              <div className="mt-3 p-2 rounded-lg bg-green-50 border border-green-100">
                <p className="text-[10px] font-black text-green-700 uppercase tracking-widest">Safety: Live trading locked</p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <NotConnectedLabel />
              <p className="text-[11px] text-slate-400">Set NEXUS_API_URL env var to connect</p>
            </div>
          )}
        </OSSection>

        {/* What to do today */}
        <OSSection title="Today's Priority" icon={Clock} action={<MockLabel />}>
          <div className="space-y-2">
            {pendingApprovals.length > 0 && (
              <PriorityItem
                emoji="✅"
                text={`Review ${pendingApprovals.length} pending approval${pendingApprovals.length > 1 ? 's' : ''}`}
                onClick={() => onNavigate('approvals')}
              />
            )}
            <PriorityItem
              emoji="💬"
              text="Check Hermes for overnight recommendations"
              onClick={() => onNavigate('hermes-chat')}
            />
            <PriorityItem
              emoji="💰"
              text="Review revenue pipeline and affiliate status"
              onClick={() => onNavigate('revenue')}
            />
            <PriorityItem
              emoji="📈"
              text="Check paper trading performance and signals"
              onClick={() => onNavigate('trading')}
            />
            <PriorityItem
              emoji="🛠️"
              text="Verify provider/tool health status"
              onClick={() => onNavigate('tools')}
            />
          </div>
        </OSSection>

        {/* Quick actions */}
        <OSSection title="Quick Actions" icon={Zap}>
          <div className="grid grid-cols-2 gap-2">
            <QuickAction emoji="🤖" label="Ask Hermes" onClick={() => onNavigate('hermes-chat')} />
            <QuickAction emoji="📋" label="Approvals" onClick={() => onNavigate('approvals')} />
            <QuickAction emoji="💰" label="Revenue Hub" onClick={() => onNavigate('revenue')} />
            <QuickAction emoji="🧠" label="Knowledge" onClick={() => onNavigate('knowledge')} />
            <QuickAction emoji="✍️" label="Content Studio" onClick={() => onNavigate('content')} />
            <QuickAction emoji="🛠️" label="Tool Registry" onClick={() => onNavigate('tools')} />
          </div>
        </OSSection>

        {/* System info */}
        <OSSection title="System Info" icon={Cpu}>
          <div className="space-y-2">
            <InfoRow label="Hermes Gateway" value="127.0.0.1:8642" />
            <InfoRow label="Hermes Model" value="meta-llama/llama-3.3-70b (OpenRouter)" />
            <InfoRow label="Oracle VM" value="161.153.40.41" />
            <InfoRow label="Signal Port" value="5000" />
            <InfoRow label="Trading Config" value="DRY_RUN=true · LIVE=false" />
            <InfoRow label="Frontend" value="React 19 + Vite 6 + Supabase" />
          </div>
        </OSSection>
      </div>

      {/* "What happened while I was away" */}
      <OSSection title={`What Happened While You Were Away`} icon={MessageSquare}>
        {loading ? <LoadingRow /> : alerts.length === 0 && pendingApprovals.length === 0 ? (
          <p className="text-sm text-slate-500">No recent system events. Hermes is quiet.</p>
        ) : (
          <div className="space-y-1 text-sm text-slate-600">
            {criticalAlerts.length > 0 && (
              <p>🔴 <strong>{criticalAlerts.length} critical alert{criticalAlerts.length > 1 ? 's' : ''}</strong> from Hermes need attention.</p>
            )}
            {pendingApprovals.length > 0 && (
              <p>✅ <strong>{pendingApprovals.length} item{pendingApprovals.length > 1 ? 's' : ''}</strong> waiting for your approval.</p>
            )}
            {actionableAlerts.length > 0 && (
              <p>⚡ <strong>{actionableAlerts.length} actionable signal{actionableAlerts.length > 1 ? 's' : ''}</strong> from system agents.</p>
            )}
          </div>
        )}
      </OSSection>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color = 'default',
  onClick,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  color?: string;
  onClick?: () => void;
}) {
  const colorMap: Record<string, string> = {
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    amber: 'bg-amber-50 text-amber-600',
    blue: 'bg-blue-50 text-[#5B7CFA]',
    default: 'bg-slate-100 text-slate-500',
  };
  return (
    <OSCard
      className="p-4 flex items-center gap-3"
      onClick={onClick}
    >
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${colorMap[color] ?? colorMap.default}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest truncate">{label}</p>
        <p className="text-base font-black text-[#1A2244] leading-tight">{value}</p>
        {sub && <p className="text-[9px] text-slate-400 truncate mt-0.5">{sub}</p>}
      </div>
    </OSCard>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest shrink-0">{label}</span>
      <span className="text-xs font-semibold text-[#1A2244] text-right">{value}</span>
    </div>
  );
}

function PriorityItem({ emoji, text, onClick }: { emoji: string; text: string; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2 p-2.5 rounded-xl text-left hover:bg-slate-50 transition-colors group"
    >
      <span className="text-base shrink-0">{emoji}</span>
      <span className="text-xs font-semibold text-[#1A2244] group-hover:text-[#5B7CFA] transition-colors">{text}</span>
    </button>
  );
}

function QuickAction({ emoji, label, onClick }: { emoji: string; label: string; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 p-3 rounded-xl bg-slate-50 border border-slate-100 hover:bg-blue-50 hover:border-[#5B7CFA]/30 transition-all text-left group"
    >
      <span className="text-base">{emoji}</span>
      <span className="text-[11px] font-bold text-[#1A2244] group-hover:text-[#5B7CFA]">{label}</span>
    </button>
  );
}

function LoadingRow() {
  return (
    <div className="flex items-center justify-center py-6">
      <Loader2 className="w-5 h-5 animate-spin text-slate-300" />
    </div>
  );
}

function NeedsRayCard({
  pendingApprovals,
  criticalApprovals,
  urgentNotifs,
  latestUrgentNotif,
  criticalAlerts,
  onApprovals,
  onNotifications,
}: {
  pendingApprovals: number;
  criticalApprovals: number;
  urgentNotifs: number;
  latestUrgentNotif: string | null;
  criticalAlerts: number;
  onApprovals: () => void;
  onNotifications: () => void;
}) {
  const hasCritical = criticalApprovals > 0 || urgentNotifs > 0 || criticalAlerts > 0;
  return (
    <OSCard className={`border-2 ${hasCritical ? 'border-red-300 bg-red-50/30' : 'border-amber-200 bg-amber-50/20'}`}>
      <div className="p-4 flex items-start gap-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${hasCritical ? 'bg-red-100' : 'bg-amber-100'}`}>
          <ShieldAlert className={`w-5 h-5 ${hasCritical ? 'text-red-600' : 'text-amber-600'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-black ${hasCritical ? 'text-red-700' : 'text-amber-700'}`}>
            {hasCritical ? '🔴 Needs Ray — Critical Items' : '⚠️ Needs Ray — Items Awaiting Action'}
          </p>
          <div className="mt-1.5 space-y-0.5 text-xs text-slate-600">
            {criticalAlerts > 0 && (
              <p>• {criticalAlerts} critical alert{criticalAlerts > 1 ? 's' : ''} from Hermes</p>
            )}
            {pendingApprovals > 0 && (
              <p>• {pendingApprovals} pending approval{pendingApprovals > 1 ? 's' : ''}
                {criticalApprovals > 0 && <span className="text-red-600 font-bold"> ({criticalApprovals} urgent)</span>}
              </p>
            )}
            {urgentNotifs > 0 && (
              <p>• {urgentNotifs} urgent notification{urgentNotifs > 1 ? 's' : ''}
                {latestUrgentNotif && <span className="text-slate-400"> — {latestUrgentNotif.slice(0, 50)}</span>}
              </p>
            )}
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          {pendingApprovals > 0 && (
            <button
              onClick={onApprovals}
              className={`px-3 py-1.5 rounded-xl text-[10px] font-black text-white uppercase tracking-widest transition-all ${hasCritical ? 'bg-red-500 hover:bg-red-600' : 'bg-amber-500 hover:bg-amber-600'}`}
            >
              Approvals
            </button>
          )}
          {urgentNotifs > 0 && (
            <button
              onClick={onNotifications}
              className="px-3 py-1.5 rounded-xl text-[10px] font-black text-white uppercase tracking-widest bg-slate-700 hover:bg-slate-800 transition-all"
            >
              Notifications
            </button>
          )}
        </div>
      </div>
    </OSCard>
  );
}
