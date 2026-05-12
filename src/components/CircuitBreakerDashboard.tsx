import React, { useState, useEffect } from 'react';
import {
  ShieldAlert, ShieldCheck, AlertTriangle, Zap,
  RefreshCw, Clock, CheckCircle2, XCircle,
  TrendingDown, Activity, Power, PowerOff,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from './AuthProvider';

// ── types ─────────────────────────────────────────────────────────────────────

interface CircuitBreakerEvent {
  trigger_type: string;
  description: string;
  triggered_at: string;
  resolved: boolean;
  resolved_at?: string;
  resolved_by?: string;
  halt_all: boolean;
  auto_reset: boolean;
  trigger_value?: number;
  notes?: string;
}

interface CBStatus {
  any_active: boolean;
  halt_all: boolean;
  active_count: number;
  active_breakers: CircuitBreakerEvent[];
  recent_history: CircuitBreakerEvent[];
}

interface KillSwitchState {
  nexus_dry_run: string;
  live_trading: string;
  auto_trading: string;
  swarm_execution: string;
  kill_switch_status: 'safe' | 'WARNING';
}

// ── helpers ───────────────────────────────────────────────────────────────────

const TRIGGER_META: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  daily_loss_exceeded:    { label: 'Daily Loss Limit',    icon: TrendingDown, color: '#ef4444' },
  weekly_drawdown_exceeded:{ label: 'Weekly Drawdown',    icon: TrendingDown, color: '#ef4444' },
  consecutive_losses:     { label: 'Consecutive Losses',  icon: AlertTriangle, color: '#f59e0b' },
  volatility_spike:       { label: 'Volatility Spike',    icon: Activity,     color: '#f59e0b' },
  api_failure:            { label: 'API Failure',         icon: XCircle,      color: '#ef4444' },
  slippage_anomaly:       { label: 'Slippage Anomaly',    icon: AlertTriangle, color: '#ef4444' },
  abnormal_pnl:           { label: 'Abnormal P&L',        icon: AlertTriangle, color: '#ef4444' },
  operator_halt:          { label: 'Operator Halt',       icon: PowerOff,     color: '#6b7280' },
  market_gap:             { label: 'Market Gap',          icon: AlertTriangle, color: '#f59e0b' },
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}

// ── sub-components ────────────────────────────────────────────────────────────

function KillSwitchPanel({ state, onHalt, halting }: {
  state: KillSwitchState | null;
  onHalt: () => void;
  halting: boolean;
}) {
  const isSafe = !state || state.kill_switch_status === 'safe';
  return (
    <div className={cn(
      'glass-card p-4 border',
      isSafe ? 'border-green-200' : 'border-red-200 bg-red-50'
    )}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Kill Switch</p>
          <div className="flex items-center gap-2 mt-1">
            {isSafe
              ? <ShieldCheck className="w-4 h-4 text-green-500" />
              : <ShieldAlert className="w-4 h-4 text-red-500" />}
            <span className={cn('font-black text-sm', isSafe ? 'text-green-700' : 'text-red-700')}>
              {isSafe ? 'All Systems Safe' : '⚠️ Unsafe State Detected'}
            </span>
          </div>
        </div>
        <button
          onClick={onHalt}
          disabled={halting}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-red-600 text-[10px] font-black hover:bg-red-100 transition-colors disabled:opacity-50"
        >
          {halting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <PowerOff className="w-3.5 h-3.5" />}
          Emergency Halt
        </button>
      </div>
      {state && (
        <div className="grid grid-cols-2 gap-2">
          {[
            { label: 'Dry Run', value: state.nexus_dry_run },
            { label: 'Live Trading', value: state.live_trading },
            { label: 'Auto Trading', value: state.auto_trading },
            { label: 'Swarm Exec', value: state.swarm_execution },
          ].map(({ label, value }) => {
            const safe = value === 'true' && label === 'Dry Run' || value === 'false';
            return (
              <div key={label} className="flex items-center justify-between px-2 py-1 bg-white rounded-lg border border-slate-100">
                <span className="text-[9px] text-slate-500 font-medium">{label}</span>
                <span className={cn('text-[9px] font-black', safe ? 'text-green-600' : 'text-red-600')}>
                  {safe ? '✓' : '⚠️'} {value}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ActiveBreakerCard({ event, onReset, canReset }: {
  key?: React.Key;
  event: CircuitBreakerEvent;
  onReset: () => void;
  canReset: boolean;
}) {
  const meta = TRIGGER_META[event.trigger_type] ?? { label: event.trigger_type, icon: AlertTriangle, color: '#ef4444' };
  const Icon = meta.icon;

  return (
    <div className="p-4 rounded-xl border-2 bg-red-50 border-red-200 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 shrink-0" style={{ color: meta.color }} />
          <div>
            <p className="font-black text-sm text-red-700">{meta.label}</p>
            <p className="text-[10px] text-red-500 font-medium">{event.description}</p>
          </div>
        </div>
        <span className={cn(
          'px-2 py-0.5 rounded-full text-[8px] font-black uppercase',
          event.halt_all ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
        )}>
          {event.halt_all ? 'HALT ALL' : 'STRATEGY PAUSE'}
        </span>
      </div>
      <div className="text-[9px] text-red-500 flex items-center gap-1">
        <Clock className="w-3 h-3" />
        Fired: {formatTime(event.triggered_at)}
        {event.trigger_value != null && ` · Value: ${event.trigger_value}`}
      </div>
      {event.notes && <p className="text-[9px] text-red-600 font-medium">{event.notes}</p>}
      <div className="p-2 bg-white rounded-lg border border-red-200">
        <p className="text-[9px] text-red-700 font-medium">
          {event.auto_reset
            ? 'Will auto-reset when timer expires. No new entries until then.'
            : 'Manual operator reset required. Review the event before resetting.'}
        </p>
      </div>
      {canReset && (
        <button
          onClick={onReset}
          className="w-full py-2 rounded-lg bg-white border border-red-200 text-red-600 text-[10px] font-black flex items-center justify-center gap-1.5 hover:bg-red-50 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Reset Circuit Breaker (Operator)
        </button>
      )}
    </div>
  );
}

function HistoryRow({ event }: { key?: React.Key; event: CircuitBreakerEvent }) {
  const meta = TRIGGER_META[event.trigger_type] ?? { label: event.trigger_type, icon: AlertTriangle, color: '#ef4444' };
  return (
    <div className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
      {event.resolved
        ? <CheckCircle2 className="w-3.5 h-3.5 text-green-400 shrink-0" />
        : <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />}
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-bold text-[#1a1c3a] truncate">{meta.label}</p>
        <p className="text-[9px] text-slate-400 font-medium">{formatTime(event.triggered_at)}</p>
      </div>
      <span className={cn('text-[9px] font-black uppercase', event.resolved ? 'text-green-600' : 'text-red-500')}>
        {event.resolved ? `reset by ${event.resolved_by || 'auto'}` : 'active'}
      </span>
    </div>
  );
}

// ── mock state — wire to /api/admin/circuit-breakers in production ─────────────

const MOCK_CB_STATUS: CBStatus = {
  any_active: false,
  halt_all: false,
  active_count: 0,
  active_breakers: [],
  recent_history: [],
};

const MOCK_KS_STATE: KillSwitchState = {
  nexus_dry_run:    'true',
  live_trading:     'false',
  auto_trading:     'false',
  swarm_execution:  'false',
  kill_switch_status: 'safe',
};

// ── main export ───────────────────────────────────────────────────────────────

export function CircuitBreakerDashboard() {
  const { profile } = useAuth();
  const isAdmin = profile?.role === 'admin' || profile?.role === 'super_admin';

  const [cbStatus, setCbStatus] = useState<CBStatus>(MOCK_CB_STATUS);
  const [ksState] = useState<KillSwitchState>(MOCK_KS_STATE);
  const [halting, setHalting] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  async function handleEmergencyHalt() {
    if (!isAdmin) return;
    setHalting(true);
    // In production: POST /api/admin/kill-switch {"action":"halt"}
    await new Promise(r => setTimeout(r, 800));
    setHalting(false);
    alert('Emergency halt signal sent. Verify .env flags on server.');
  }

  function handleReset(event: CircuitBreakerEvent) {
    // In production: DELETE /api/admin/circuit-breakers with trigger_type
    setCbStatus(prev => ({
      ...prev,
      active_breakers: prev.active_breakers.filter(e => e.trigger_type !== event.trigger_type),
      active_count: Math.max(0, prev.active_count - 1),
      any_active: prev.active_count > 1,
    }));
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-[#1a1c3a] flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-[#3d5af1]" />
            Risk Control Dashboard
          </h2>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {lastRefresh.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
        <button
          onClick={() => setLastRefresh(new Date())}
          className="p-2 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Kill switch panel */}
      <KillSwitchPanel state={ksState} onHalt={handleEmergencyHalt} halting={halting} />

      {/* Active circuit breakers */}
      <div>
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-2">
          Circuit Breakers ({cbStatus.active_count} active)
        </p>
        {cbStatus.active_count === 0 ? (
          <div className="glass-card p-4 flex items-center gap-2 border border-green-200">
            <ShieldCheck className="w-5 h-5 text-green-500" />
            <div>
              <p className="font-bold text-sm text-green-700">All Clear — No Breakers Active</p>
              <p className="text-[10px] text-green-600 font-medium">Trading permitted within approved limits</p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {cbStatus.active_breakers.map((event, i) => (
              <ActiveBreakerCard
                key={i}
                event={event}
                onReset={() => handleReset(event)}
                canReset={isAdmin && !event.auto_reset}
              />
            ))}
          </div>
        )}
      </div>

      {/* Trigger reference */}
      <div className="glass-card overflow-hidden">
        <div className="p-3 border-b border-slate-100">
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Trigger Reference</p>
        </div>
        <div className="divide-y divide-slate-50">
          {Object.entries(TRIGGER_META).map(([key, meta]) => {
            const Icon = meta.icon;
            return (
              <div key={key} className="flex items-center gap-3 px-4 py-2">
                <Icon className="w-3.5 h-3.5 shrink-0" style={{ color: meta.color }} />
                <span className="text-[10px] font-bold text-slate-600 flex-1">{meta.label}</span>
                <span className={cn(
                  'text-[8px] font-black uppercase px-1.5 py-0.5 rounded',
                  key === 'daily_loss_exceeded' || key === 'weekly_drawdown_exceeded'
                    ? 'bg-red-50 text-red-500' : 'bg-amber-50 text-amber-500'
                )}>
                  {['api_failure','slippage_anomaly','abnormal_pnl','operator_halt'].includes(key) ? 'MANUAL RESET' : 'AUTO RESET'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent history */}
      {cbStatus.recent_history.length > 0 && (
        <div className="glass-card p-4">
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3">Recent Events</p>
          {cbStatus.recent_history.map((event, i) => (
            <HistoryRow key={i} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
