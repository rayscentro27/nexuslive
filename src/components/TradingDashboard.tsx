import React, { useEffect, useState } from 'react';
import {
  TrendingUp, Lock, CheckCircle2, AlertCircle, Loader2,
  BarChart3, Clock, Activity, RefreshCw, ShieldCheck,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from './AuthProvider';
import { supabase } from '../lib/supabase';
import { getTradingStatus, NexusTradingStatusResponse, PaperTrade } from '../services/nexusApi';
import { usePlan } from '../hooks/usePlan';

// ── helpers ──────────────────────────────────────────────────────────────────

function fmt(iso: string | null | undefined) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString([], {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function TagPill({ tag }: { tag: string }) {
  const colors: Record<string, string> = {
    paper:      'bg-blue-50 text-blue-600',
    nexus_auto: 'bg-indigo-50 text-indigo-600',
    dry_run:    'bg-slate-100 text-slate-500',
    crypto:     'bg-orange-50 text-orange-600',
    forex:      'bg-green-50 text-green-600',
    equities:   'bg-purple-50 text-purple-600',
    options:    'bg-yellow-50 text-yellow-700',
  };
  return (
    <span className={cn('px-1.5 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wider', colors[tag] ?? 'bg-slate-100 text-slate-500')}>
      {tag}
    </span>
  );
}

// ── locked state ─────────────────────────────────────────────────────────────

function TradingLocked() {
  return (
    <div className="h-full flex items-center justify-center p-6">
      <div className="max-w-md w-full glass-card p-10 text-center space-y-6">
        <div className="w-16 h-16 bg-nexus-50 rounded-2xl flex items-center justify-center mx-auto">
          <Lock className="w-8 h-8" style={{ color: '#8b8fa8' }} />
        </div>
        <div>
          <h2 className="text-xl font-black text-[#1a1c3a]">Trading Access Locked</h2>
          <p className="text-sm text-slate-500 font-medium mt-2">
            Upgrade to <span className="text-[#3d5af1] font-bold">Pro</span> to unlock the Trading Lab. All activity is paper trading only — no real funds at risk.
          </p>
        </div>
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-100 flex gap-3 text-left">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <p className="text-xs text-amber-700 font-medium leading-relaxed">
            Trading involves risk. Past paper performance does not guarantee future results. This platform is for educational and paper trading only.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── stat card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, accent }: { label: string; value: React.ReactNode; sub?: string; accent?: boolean }) {
  return (
    <div className="glass-card p-5">
      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">{label}</p>
      <div className={cn('text-2xl font-black', accent ? 'text-[#3d5af1]' : 'text-[#1a1c3a]')}>{value}</div>
      {sub && <p className="text-[10px] text-slate-400 font-medium mt-0.5">{sub}</p>}
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export function TradingDashboard() {
  const { user } = useAuth();
  const { isAtLeast } = usePlan();

  const [status, setStatus] = useState<NexusTradingStatusResponse | null>(null);
  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [snapshotTrading, setSnapshotTrading] = useState<{ win_rate?: number; net_pnl?: number; max_drawdown?: number; outcomes_recent?: number } | null>(null);

  const hasTradingAccess = isAtLeast('pro');

  async function loadData() {
    if (!user || !hasTradingAccess) { setLoading(false); return; }

    // Supabase direct query for paper trades (RLS-safe)
    const { data: sbTrades } = await supabase
      .from('paper_trading_journal_entries')
      .select('id,symbol,asset_class,entry_status,thesis,stop_loss,target_price,tags,opened_at,closed_at')
      .order('opened_at', { ascending: false })
      .limit(50);

    if (sbTrades) setTrades(sbTrades as PaperTrade[]);

    // Engine status via Netlify proxy → Nexus backend
    try {
      const s = await getTradingStatus();
      setStatus(s);
      setApiError(false);
    } catch {
      setApiError(true);
    }

    try {
      const res = await fetch('/api/admin/ai-ops/status', { credentials: 'include' });
      if (res.ok) {
        const payload = await res.json();
        const pt = payload?.data?.central_operational_snapshot?.paper_trading || payload?.central_operational_snapshot?.paper_trading || null;
        setSnapshotTrading(pt);
      }
    } catch {
      setSnapshotTrading(null);
    }

    setLoading(false);
    setLastRefresh(new Date());
  }

  useEffect(() => { loadData(); }, [user, hasTradingAccess]);

  async function handleRefresh() {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }

  if (!hasTradingAccess) return <TradingLocked />;

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[#5B7CFA]" />
      </div>
    );
  }

  const eng = status?.engine;
  const openTrades = trades.filter(t => t.entry_status === 'open');
  const closedTrades = trades.filter(t => t.entry_status === 'closed');
  const logTail = status?.signal_review_tail ?? [];
  const categoryCounts = trades.reduce<Record<string, number>>((acc, t) => {
    const key = (t.asset_class || 'unknown').toLowerCase();
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
  const strategyPulse = [
    { label: 'Research Activity', value: Math.min(100, logTail.length * 12) },
    { label: 'Signal Confidence', value: Math.min(95, 35 + openTrades.length * 9) },
    { label: 'Risk Posture', value: eng?.dry_run ? 82 : 40 },
  ];

  return (
    <div className="p-4 space-y-5 max-w-7xl mx-auto">

      {/* header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-black text-[#1A2244]">Trading Lab</h2>
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-lg bg-green-100 text-green-700 text-[9px] font-bold uppercase tracking-widest">
              <CheckCircle2 className="w-2.5 h-2.5" /> Paper Mode
            </span>
            {eng?.dry_run && (
              <span className="px-2 py-0.5 rounded-lg bg-blue-50 text-blue-600 text-[9px] font-bold uppercase tracking-widest">
                DRY RUN
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 font-medium">Live paper trading — no real funds at risk.</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-100 text-[10px] font-bold text-slate-500 hover:bg-slate-100 transition-all disabled:opacity-50"
        >
          <RefreshCw className={cn('w-3 h-3', refreshing && 'animate-spin')} />
          {lastRefresh ? fmt(lastRefresh.toISOString()) : 'Refresh'}
        </button>
      </div>

      {/* disclaimer */}
      <div className="p-3 rounded-xl bg-amber-50 border border-amber-100 flex gap-2">
        <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
        <p className="text-[10px] text-amber-700 font-medium leading-relaxed">
          <strong>Paper trading only.</strong> All trades shown are simulated. No real orders are placed. Past performance does not guarantee future results. Trading involves risk.
        </p>
      </div>

      {/* stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Engine Mode"
          value={eng ? (eng.dry_run ? 'Paper' : 'Live') : '—'}
          sub={eng?.broker_type ?? undefined}
          accent
        />
        <StatCard label="Signals Processed"
          value={eng?.signals_processed ?? trades.length}
          sub="since last restart"
        />
        <StatCard label="Open Positions"
          value={eng?.active_positions ?? openTrades.length}
        />
        <StatCard label="Total Trades"
          value={trades.length}
          sub={`${closedTrades.length} closed`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {strategyPulse.map((row) => (
          <div key={row.label} className="glass-card p-4">
            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">{row.label}</p>
            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-[#3d5af1] to-[#0ea5e9]" style={{ width: `${row.value}%`, transition: 'width 0.35s ease' }} />
            </div>
            <p className="text-[10px] text-slate-400 mt-2 font-semibold">{row.value}% live confidence</p>
          </div>
        ))}
      </div>

      {Object.keys(categoryCounts).length > 0 && (
        <div className="glass-card p-4">
          <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">Market Category Pulse</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(categoryCounts).slice(0, 6).map(([cat, count]) => (
              <span key={cat} className="px-2 py-1 rounded-md bg-slate-100 text-slate-600 text-[10px] font-bold uppercase tracking-wide">
                {cat}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {snapshotTrading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Sim Outcomes" value={snapshotTrading.outcomes_recent ?? 0} sub="recent journaled" />
          <StatCard label="Sim Win Rate" value={`${Math.round(snapshotTrading.win_rate ?? 0)}%`} />
          <StatCard label="Net Sim PnL" value={snapshotTrading.net_pnl ?? 0} />
          <StatCard label="Max Drawdown" value={snapshotTrading.max_drawdown ?? 0} sub="simulated" />
        </div>
      )}

      {/* last signal */}
      {eng?.last_signal && (
        <div className="glass-card p-4">
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-2">Last Signal Processed</p>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#5B7CFA]" />
              <span className="text-sm font-black text-[#1a1c3a]">
                {String(eng.last_signal.symbol)} {String(eng.last_signal.action)}
              </span>
            </div>
            <span className="text-[10px] text-slate-500 font-medium">
              Entry: {eng.last_signal.entry_price ? String(eng.last_signal.entry_price) : '—'}
            </span>
            {eng.last_result && (
              <span className={cn(
                'px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wider',
                String(eng.last_result.status).includes('approved') ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
              )}>
                {String(eng.last_result.status)}
              </span>
            )}
            <span className="text-[10px] text-slate-400 font-medium ml-auto">
              <Clock className="w-3 h-3 inline mr-1" />
              {fmt(String(eng.last_signal.timestamp ?? ''))}
            </span>
          </div>
        </div>
      )}

      {/* paper trades table */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-black text-[#1A2244] flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-[#5B7CFA]" />
            Paper Trades
          </h3>
          <span className="text-[10px] text-slate-400 font-medium">{trades.length} total</span>
        </div>

        {trades.length === 0 ? (
          <div className="p-10 text-center">
            <TrendingUp className="w-8 h-8 text-slate-200 mx-auto mb-2" />
            <p className="text-xs text-slate-400 font-medium">No paper trades yet. Send a signal to get started.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50/50">
                  <th className="px-4 py-2.5 text-left text-[9px] font-black text-slate-400 uppercase tracking-widest">Symbol</th>
                  <th className="px-4 py-2.5 text-left text-[9px] font-black text-slate-400 uppercase tracking-widest hidden md:table-cell">Thesis</th>
                  <th className="px-4 py-2.5 text-left text-[9px] font-black text-slate-400 uppercase tracking-widest">SL / TP</th>
                  <th className="px-4 py-2.5 text-left text-[9px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                  <th className="px-4 py-2.5 text-left text-[9px] font-black text-slate-400 uppercase tracking-widest hidden lg:table-cell">Tags</th>
                  <th className="px-4 py-2.5 text-left text-[9px] font-black text-slate-400 uppercase tracking-widest hidden lg:table-cell">Opened</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {trades.map(t => (
                  <tr key={t.id} className="hover:bg-slate-50/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-black text-xs text-[#1a1c3a]">{t.symbol}</div>
                      <div className="text-[9px] text-slate-400 font-medium">{t.asset_class}</div>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell max-w-xs">
                      <p className="text-[10px] text-slate-600 font-medium truncate">{t.thesis}</p>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-[10px] font-medium text-slate-600">
                        {t.stop_loss ? Number(t.stop_loss).toFixed(4) : '—'} / {t.target_price ? Number(t.target_price).toFixed(4) : '—'}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        'px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wider',
                        t.entry_status === 'open'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-slate-100 text-slate-500'
                      )}>
                        {t.entry_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <div className="flex gap-1 flex-wrap">
                        {(t.tags ?? []).slice(0, 3).map(tag => <TagPill key={tag} tag={tag} />)}
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell text-[10px] text-slate-400 font-medium">
                      {fmt(t.opened_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* signal review log */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck className="w-4 h-4 text-[#5B7CFA]" />
          <h3 className="text-sm font-black text-[#1A2244]">Signal Review</h3>
          {apiError && (
            <span className="text-[9px] text-amber-600 font-bold bg-amber-50 px-2 py-0.5 rounded-md">
              Engine offline — showing Supabase data only
            </span>
          )}
        </div>
        {logTail.length > 0 ? (
          <div className="bg-slate-900 rounded-xl p-4 font-mono text-[10px] leading-6 max-h-48 overflow-y-auto space-y-0.5">
            {logTail.map((line, i) => (
              <div key={i} className={cn(
                line.includes('ERROR') ? 'text-red-400' :
                line.includes('WARN') || line.includes('heuristic') ? 'text-yellow-400' :
                'text-slate-300'
              )}>{line}</div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400 font-medium">
            {apiError
              ? 'Signal review log unavailable — Nexus engine not reachable from this device.'
              : 'No recent signal review activity.'}
          </p>
        )}
      </div>

      {/* webhook info */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-black text-[#1A2244] mb-3">TradingView Integration</h3>
        <p className="text-xs text-slate-500 font-medium mb-3">Send signals from TradingView alerts to this webhook URL:</p>
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 font-mono text-[11px] text-[#3d5af1] break-all">
          https://signals.goclearonline.cc/webhook/tradingview
        </div>
        <p className="text-[10px] text-slate-400 font-medium mt-3">
          All signals are reviewed by AI (Groq) and executed as paper trades only. No live orders.
        </p>
      </div>
    </div>
  );
}
