import React, { useCallback, useEffect, useState } from 'react';
import { useAnalytics } from '../hooks/useAnalytics';
import { useAuth } from './AuthProvider';
import { supabase } from '../lib/supabase';
import {
  Zap, TrendingUp, TrendingDown, Target, Shield,
  CheckCircle2, XCircle, Clock, BarChart3, Calendar,
} from 'lucide-react';
import { cn } from '../lib/utils';

// ── DB row types ──────────────────────────────────────────────────────────────

interface PaperRun {
  id: string;
  symbol: string | null;
  strategy_id: string | null;
  strategy_type: string | null;
  status: 'running' | 'finished' | 'error';
  started_at: string;
  finished_at: string | null;
}

interface ReplayResult {
  id: string;
  symbol: string | null;
  strategy_id: string | null;
  replay_outcome: string;
  pnl_r: number | null;
  pnl_pct: number | null;
  hit_take_profit: boolean | null;
  hit_stop_loss: boolean | null;
  created_at: string;
}

// ── types ─────────────────────────────────────────────────────────────────────

interface PaperTrade {
  id: string;
  strategyId: string;
  strategyName: string;
  market: string;
  direction: 'long' | 'short';
  entryPrice: number;
  stopLoss: number;
  takeProfit: number;
  exitPrice?: number;
  sizeLots: number;
  pnlPips?: number;
  pnlUsd?: number;
  openedAt: string;
  closedAt?: string;
  status: 'open' | 'closed' | 'tp_hit' | 'stopped';
  exitReason?: 'tp' | 'sl' | 'trailing' | 'manual';
  session: string;
  aiConfidence: number;
}

interface ArenaStats {
  balance: number;
  startBalance: number;
  todayPnlUsd: number;
  todayPnlPct: number;
  weekTrades: number;
  weekWins: number;
  weekPnlUsd: number;
  weekPnlPct: number;
  profitFactor: number;
}

// ── constants ─────────────────────────────────────────────────────────────────

const DEMO_START = 10000;
const R_VALUE = 100; // 1R = $100 for demo sizing

// ── DB → display mappers ──────────────────────────────────────────────────────

function mapRun(r: PaperRun): PaperTrade {
  return {
    id: r.id,
    strategyId: r.strategy_id ?? 'unknown',
    strategyName: (r.strategy_id ?? 'Session').replace(/_/g, ' '),
    market: r.symbol ?? 'Pending',
    direction: 'long',
    entryPrice: 0,
    stopLoss: 0,
    takeProfit: 0,
    sizeLots: 0.01,
    openedAt: r.started_at,
    status: 'open',
    session: 'Replay',
    aiConfidence: 50,
  };
}

function mapResult(r: ReplayResult): PaperTrade {
  const pnlR = r.pnl_r ?? 0;
  return {
    id: r.id,
    strategyId: r.strategy_id ?? 'unknown',
    strategyName: (r.strategy_id ?? 'Strategy').replace(/_/g, ' '),
    market: r.symbol ?? 'Unknown',
    direction: 'long',
    entryPrice: 0,
    stopLoss: 0,
    takeProfit: 0,
    sizeLots: 0.01,
    pnlPips: Math.round(pnlR * 20),
    pnlUsd: Math.round(pnlR * R_VALUE),
    openedAt: r.created_at,
    closedAt: r.created_at,
    status: r.hit_take_profit ? 'tp_hit' : r.hit_stop_loss ? 'stopped' : 'closed',
    exitReason: r.hit_take_profit ? 'tp' : r.hit_stop_loss ? 'sl' : undefined,
    session: 'Replay',
    aiConfidence: 50,
  };
}

function computeStats(results: ReplayResult[]): ArenaStats {
  if (results.length === 0) {
    return {
      balance: DEMO_START, startBalance: DEMO_START,
      todayPnlUsd: 0, todayPnlPct: 0,
      weekTrades: 0, weekWins: 0, weekPnlUsd: 0, weekPnlPct: 0,
      profitFactor: 0,
    };
  }
  const wins = results.filter(r => r.hit_take_profit);
  const losses = results.filter(r => r.hit_stop_loss);
  const totalR = results.reduce((s, r) => s + (r.pnl_r ?? 0), 0);
  const balance = DEMO_START + totalR * R_VALUE;
  const today = new Date().toISOString().slice(0, 10);
  const todayResults = results.filter(r => r.created_at.slice(0, 10) === today);
  const todayR = todayResults.reduce((s, r) => s + (r.pnl_r ?? 0), 0);
  const winR = wins.reduce((s, r) => s + (r.pnl_r ?? 0), 0);
  const lossR = Math.abs(losses.reduce((s, r) => s + (r.pnl_r ?? 0), 0));
  return {
    balance: Math.round(balance),
    startBalance: DEMO_START,
    todayPnlUsd: Math.round(todayR * R_VALUE),
    todayPnlPct: parseFloat((todayR * R_VALUE / DEMO_START * 100).toFixed(2)),
    weekTrades: results.length,
    weekWins: wins.length,
    weekPnlUsd: Math.round(totalR * R_VALUE),
    weekPnlPct: parseFloat(((balance - DEMO_START) / DEMO_START * 100).toFixed(2)),
    profitFactor: lossR > 0 ? parseFloat((winR / lossR).toFixed(2)) : winR > 0 ? 99 : 0,
  };
}

// ── sub-components ────────────────────────────────────────────────────────────

function PnlFlash({ value, isCurrency = true }: { value: number; isCurrency?: boolean }) {
  const pos = value >= 0;
  return (
    <span className={cn('font-black tabular-nums', pos ? 'text-green-600' : 'text-red-500')}>
      {pos ? '+' : ''}{isCurrency ? `$${Math.abs(value).toFixed(0)}` : `${value.toFixed(1)}`}
    </span>
  );
}

function TPProgress({ trade }: { trade: PaperTrade }) {
  if (trade.direction === 'long') {
    const range = trade.takeProfit - trade.entryPrice;
    const current = (trade.pnlPips || 0) / 10;
    const pct = Math.max(0, Math.min(100, (current / range) * 100));
    return (
      <div className="flex items-center gap-1.5">
        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-green-400 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-[9px] text-slate-400 font-medium shrink-0">TP {Math.round(pct)}%</span>
      </div>
    );
  }
  const range = trade.entryPrice - trade.takeProfit;
  const current = Math.abs(trade.pnlPips || 0) / 10;
  const pct = Math.max(0, Math.min(100, (current / range) * 100));
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-500', (trade.pnlPips || 0) < 0 ? 'bg-red-400' : 'bg-green-400')}
          style={{ width: `${Math.abs(pct)}%` }}
        />
      </div>
      <span className="text-[9px] text-slate-400 font-medium shrink-0">
        {(trade.pnlPips || 0) >= 0 ? `TP ${Math.round(pct)}%` : `SL risk`}
      </span>
    </div>
  );
}

function OpenTradeRow({ trade }: { key?: React.Key; trade: PaperTrade }) {
  const pips = trade.pnlPips || 0;
  const isPos = pips >= 0;

  function elapsed(iso: string) {
    const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
    if (mins < 60) return `${mins}m`;
    return `${Math.floor(mins / 60)}h ${mins % 60}m`;
  }

  return (
    <div className="p-4 border border-slate-100 rounded-xl bg-white space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            {trade.direction === 'long'
              ? <TrendingUp className="w-3.5 h-3.5 text-green-500" />
              : <TrendingDown className="w-3.5 h-3.5 text-red-400" />}
            <span className="font-black text-sm text-[#1a1c3a]">{trade.market}</span>
            <span className={cn(
              'px-1.5 py-0.5 rounded text-[8px] font-black uppercase',
              trade.direction === 'long' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'
            )}>
              {trade.direction}
            </span>
          </div>
          <div className="flex items-center gap-1 text-[9px] text-slate-400">
            <Zap className="w-2.5 h-2.5 text-[#00d4ff]" />
            <span className="animate-pulse">active</span>
          </div>
        </div>
        <div className="text-right">
          <span className={cn('font-black tabular-nums', isPos ? 'text-green-600' : 'text-red-500')}>
            {isPos ? '+' : ''}{pips} pips
          </span>
        </div>
      </div>
      <div className="text-[9px] text-slate-400 font-medium flex gap-3">
        <span>Entry {trade.entryPrice.toFixed(trade.market.includes('JPY') ? 2 : 5)}</span>
        <span>SL {trade.stopLoss.toFixed(trade.market.includes('JPY') ? 2 : 5)}</span>
        <span>TP {trade.takeProfit.toFixed(trade.market.includes('JPY') ? 2 : 5)}</span>
        <span className="ml-auto flex items-center gap-0.5">
          <Clock className="w-2.5 h-2.5" />
          {elapsed(trade.openedAt)}
        </span>
      </div>
      <TPProgress trade={trade} />
      <div className="text-[9px] text-slate-400 flex gap-3">
        <span>{trade.strategyName}</span>
        <span>·</span>
        <span>{trade.session} session</span>
        <span>·</span>
        <span className="text-[#8b5cf6]">AI {trade.aiConfidence}%</span>
      </div>
    </div>
  );
}

function ClosedTradeRow({ trade }: { key?: React.Key; trade: PaperTrade }) {
  const pips = trade.pnlPips || 0;
  const isPos = pips >= 0;
  const icon = trade.exitReason === 'tp'
    ? <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
    : <XCircle className="w-4 h-4 text-red-400 shrink-0" />;

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-slate-50 last:border-0">
      {icon}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 text-xs font-bold text-[#1a1c3a]">
          <span>{trade.market}</span>
          <span className={cn('text-[8px] font-black uppercase', trade.direction === 'long' ? 'text-green-600' : 'text-red-500')}>
            {trade.direction}
          </span>
        </div>
        <p className="text-[9px] text-slate-400 font-medium">
          {trade.session} · {trade.strategyName} ·{' '}
          {trade.exitReason === 'tp' ? 'TP hit' : 'SL hit'}
        </p>
      </div>
      <span className={cn('font-black text-sm tabular-nums', isPos ? 'text-green-600' : 'text-red-500')}>
        {isPos ? '+' : ''}{pips}p
      </span>
    </div>
  );
}

function WeeklyStats({ stats }: { stats: ArenaStats }) {
  const winRate = Math.round((stats.weekWins / stats.weekTrades) * 100);
  return (
    <div className="glass-card p-5 space-y-3">
      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">This Week</p>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-2xl font-black text-green-600">
            +${stats.weekPnlUsd.toLocaleString()}
          </p>
          <p className="text-[10px] text-slate-400 font-medium">+{stats.weekPnlPct}% return</p>
        </div>
        <div>
          <p className="text-2xl font-black text-[#1a1c3a]">{stats.weekTrades}</p>
          <p className="text-[10px] text-slate-400 font-medium">trades ({stats.weekWins}W / {stats.weekTrades - stats.weekWins}L)</p>
        </div>
      </div>
      <div className="space-y-1.5">
        <div className="flex justify-between text-[10px]">
          <span className="text-slate-500 font-medium">Win Rate</span>
          <span className={cn('font-black', winRate >= 60 ? 'text-green-600' : winRate >= 50 ? 'text-amber-600' : 'text-red-500')}>
            {winRate}%
          </span>
        </div>
        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div className="h-full rounded-full bg-green-400" style={{ width: `${winRate}%` }} />
        </div>
        <div className="flex justify-between text-[10px]">
          <span className="text-slate-500 font-medium">Profit Factor</span>
          <span className="font-black text-green-600">{stats.profitFactor}x</span>
        </div>
      </div>
    </div>
  );
}

// ── main export ───────────────────────────────────────────────────────────────

export function PaperTradingArena() {
  const { user } = useAuth();
  const { emit } = useAnalytics();
  const [tab, setTab] = useState<'live' | 'journal' | 'stats'>('live');
  const [loading, setLoading] = useState(true);
  const [runs, setRuns] = useState<PaperRun[]>([]);
  const [results, setResults] = useState<ReplayResult[]>([]);

  useEffect(() => {
    emit('page_view', { event_name: 'paper_trading_arena_viewed', feature: 'trading', page: '/trading' });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(async () => {
    setLoading(true);
    const [{ data: runData }, { data: resultData }] = await Promise.all([
      supabase.from('paper_trade_runs').select('id,symbol,strategy_id,strategy_type,status,started_at,finished_at')
        .order('started_at', { ascending: false }).limit(50),
      supabase.from('replay_results').select('id,symbol,strategy_id,replay_outcome,pnl_r,pnl_pct,hit_take_profit,hit_stop_loss,created_at')
        .order('created_at', { ascending: false }).limit(100),
    ]);
    setRuns((runData ?? []) as PaperRun[]);
    setResults((resultData ?? []) as ReplayResult[]);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const openTrades = runs.filter(r => r.status === 'running').map(mapRun);
  const closedTrades = results.map(mapResult);
  const stats = computeStats(results);
  const totalPct = ((stats.balance - stats.startBalance) / stats.startBalance) * 100;
  void user; // user context available for future RLS-gated queries

  return (
    <div className="p-6 space-y-4">
      {/* header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-[#1a1c3a] flex items-center gap-2">
            <Zap className="w-5 h-5 text-[#00d4ff]" />
            Paper Trading Arena
            <span className="px-2 py-0.5 rounded-full text-[8px] font-black uppercase bg-amber-50 text-amber-600 border border-amber-200 tracking-wider">
              DEMO / SIMULATED
            </span>
          </h2>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            Simulated · No real funds · Demo data only
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-black text-[#1a1c3a]">
            ${stats.balance.toLocaleString()}
          </p>
          <p className={cn('text-[11px] font-black', totalPct >= 0 ? 'text-green-600' : 'text-red-500')}>
            {totalPct >= 0 ? '+' : ''}{totalPct.toFixed(1)}% all time
          </p>
        </div>
      </div>

      {/* today stat */}
      <div className="glass-card p-4 flex items-center justify-between">
        <div>
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Today</p>
          <div className="flex items-baseline gap-2 mt-1">
            <PnlFlash value={stats.todayPnlUsd} />
            <span className={cn('text-sm font-bold', stats.todayPnlPct >= 0 ? 'text-green-500' : 'text-red-400')}>
              {stats.todayPnlPct >= 0 ? '+' : ''}{stats.todayPnlPct.toFixed(2)}%
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-slate-400 font-medium">
          <div className="text-center">
            <p className="font-black text-[#1a1c3a] text-sm">{openTrades.length}</p>
            <p>open</p>
          </div>
          <div className="text-center">
            <p className="font-black text-[#1a1c3a] text-sm">{closedTrades.length}</p>
            <p>closed today</p>
          </div>
        </div>
      </div>

      {/* tabs */}
      <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
        {(['live', 'journal', 'stats'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              'flex-1 py-1.5 rounded-md text-[10px] font-bold transition-all capitalize',
              tab === t ? 'bg-white shadow-sm text-[#3d5af1]' : 'text-slate-500'
            )}
          >
            {t === 'live' ? 'Live Trades' : t === 'journal' ? 'Recent Closes' : 'Stats'}
          </button>
        ))}
      </div>

      {/* tab content */}
      {tab === 'live' && (
        <div className="space-y-3">
          {openTrades.length === 0 ? (
            <div className="glass-card p-8 text-center">
              <Target className="w-8 h-8 text-slate-200 mx-auto mb-2" />
              <p className="text-sm font-bold text-slate-400">No open positions</p>
              <p className="text-[10px] text-slate-400 font-medium mt-0.5">
                Waiting for signal quality to meet entry threshold
              </p>
            </div>
          ) : (
            openTrades.map(t => <OpenTradeRow key={t.id} trade={t} />)
          )}
        </div>
      )}

      {tab === 'journal' && (
        <div className="glass-card overflow-hidden">
          {closedTrades.length === 0 ? (
            <div className="p-8 text-center">
              <BarChart3 className="w-8 h-8 text-slate-200 mx-auto mb-2" />
              <p className="text-sm font-bold text-slate-400">No closed trades yet</p>
            </div>
          ) : (
            <div className="p-4">
              {closedTrades.map(t => <ClosedTradeRow key={t.id} trade={t} />)}
            </div>
          )}
        </div>
      )}

      {tab === 'stats' && <WeeklyStats stats={stats} />}

      {/* safety footer */}
      <div className="flex items-center gap-2 p-3 rounded-xl bg-blue-50 border border-blue-100">
        <Shield className="w-4 h-4 text-blue-500 shrink-0" />
        <p className="text-[10px] text-blue-700 font-medium">
          Paper mode active · Simulated PnL · No real money · TRADING_LIVE_EXECUTION_ENABLED=false
        </p>
      </div>
    </div>
  );
}
