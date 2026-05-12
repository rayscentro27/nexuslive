import React, { useState } from 'react';
import {
  TrendingUp, TrendingDown, Minus, Trophy, Shield, Zap,
  BarChart3, Clock, Target, ChevronRight, Play, Pause,
} from 'lucide-react';
import { cn } from '../lib/utils';

// ── types ─────────────────────────────────────────────────────────────────────

interface Strategy {
  id: string;
  name: string;
  version: string;
  market: string;
  timeframe: string;
  session: string;
  status: 'active' | 'paused' | 'review' | 'pending';
  phase: 'paper' | 'live' | 'backtest';
  winRate: number;
  profitFactor: number;
  totalTrades: number;
  weeklyReturn: number;
  drawdown: number;
  aiConfidence: number;
  streak: number;
  rank: number;
  rankChange: 'up' | 'down' | 'stable';
  edgeHealth: 'stable' | 'warning' | 'critical';
  backtestWinRate: number;
}

// ── mock data — replace with live Supabase query ──────────────────────────────

const MOCK_STRATEGIES: Strategy[] = [
  {
    id: 'london-breakout-v21',
    name: 'London Breakout',
    version: 'v2.1',
    market: 'EUR/USD',
    timeframe: '15m',
    session: 'London',
    status: 'active',
    phase: 'paper',
    winRate: 71,
    profitFactor: 2.3,
    totalTrades: 34,
    weeklyReturn: 4.2,
    drawdown: 8,
    aiConfidence: 68,
    streak: 4,
    rank: 1,
    rankChange: 'up',
    edgeHealth: 'stable',
    backtestWinRate: 73,
  },
  {
    id: 'spy-continuation',
    name: 'SPY Continuation',
    version: 'v1.0',
    market: 'SPY',
    timeframe: '5m',
    session: 'NY Open',
    status: 'active',
    phase: 'paper',
    winRate: 61,
    profitFactor: 1.6,
    totalTrades: 22,
    weeklyReturn: 1.8,
    drawdown: 5,
    aiConfidence: 72,
    streak: 2,
    rank: 2,
    rankChange: 'stable',
    edgeHealth: 'stable',
    backtestWinRate: 63,
  },
  {
    id: 'ny-momentum',
    name: 'NY Momentum',
    version: 'v1.2',
    market: 'GBP/USD',
    timeframe: '15m',
    session: 'NY Open',
    status: 'paused',
    phase: 'paper',
    winRate: 44,
    profitFactor: 0.9,
    totalTrades: 18,
    weeklyReturn: -0.4,
    drawdown: 12,
    aiConfidence: 41,
    streak: 0,
    rank: 3,
    rankChange: 'down',
    edgeHealth: 'warning',
    backtestWinRate: 60,
  },
];

// ── sub-components ────────────────────────────────────────────────────────────

const RANK_BADGE: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' };

function RankChange({ dir }: { dir: Strategy['rankChange'] }) {
  if (dir === 'up') return <TrendingUp className="w-3 h-3 text-green-500" />;
  if (dir === 'down') return <TrendingDown className="w-3 h-3 text-red-400" />;
  return <Minus className="w-3 h-3 text-slate-400" />;
}

function ProgressBar({ value, max = 100, color }: { value: number; max?: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

function EdgeBadge({ health }: { health: Strategy['edgeHealth'] }) {
  const map = {
    stable:   { label: 'Edge: STABLE',   cls: 'bg-green-50 text-green-700' },
    warning:  { label: 'Edge: WARNING',  cls: 'bg-amber-50 text-amber-700' },
    critical: { label: 'Edge: CRITICAL', cls: 'bg-red-50 text-red-700' },
  };
  const { label, cls } = map[health];
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider', cls)}>
      {label}
    </span>
  );
}

function PhaseBadge({ phase }: { phase: Strategy['phase'] }) {
  if (phase === 'paper') {
    return (
      <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-blue-50 text-blue-600">
        PAPER
      </span>
    );
  }
  if (phase === 'live') {
    return (
      <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-green-50 text-green-700">
        LIVE
      </span>
    );
  }
  return (
    <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-slate-100 text-slate-500">
      BACKTEST
    </span>
  );
}

function StatusDot({ status }: { status: Strategy['status'] }) {
  const cls =
    status === 'active'  ? 'bg-green-500 animate-pulse' :
    status === 'paused'  ? 'bg-amber-400' :
    status === 'review'  ? 'bg-purple-400' :
                           'bg-slate-300';
  return <span className={cn('inline-block w-2 h-2 rounded-full', cls)} />;
}

function StrategyCard({ strategy }: { key?: React.Key; strategy: Strategy }) {
  const [expanded, setExpanded] = useState(false);
  const tradeProgress = Math.min(100, (strategy.totalTrades / 30) * 100);
  const meetsMinimum = strategy.totalTrades >= 30;

  return (
    <div
      className={cn(
        'glass-card overflow-hidden transition-all duration-200',
        strategy.status === 'paused' && 'opacity-75'
      )}
    >
      {/* header row */}
      <div
        className="p-5 cursor-pointer"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="text-xl leading-none mt-0.5">
              {RANK_BADGE[strategy.rank] ?? <Trophy className="w-5 h-5 text-slate-400" />}
            </span>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-black text-[#1a1c3a] text-sm">
                  {strategy.name} <span className="text-slate-400 font-medium">{strategy.version}</span>
                </span>
                <StatusDot status={strategy.status} />
                <PhaseBadge phase={strategy.phase} />
              </div>
              <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-400 font-medium flex-wrap">
                <span>{strategy.market}</span>
                <span>·</span>
                <span>{strategy.timeframe}</span>
                <span>·</span>
                <span>{strategy.session}</span>
                <div className="flex items-center gap-0.5">
                  <RankChange dir={strategy.rankChange} />
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <EdgeBadge health={strategy.edgeHealth} />
            <ChevronRight
              className={cn('w-4 h-4 text-slate-300 transition-transform', expanded && 'rotate-90')}
            />
          </div>
        </div>

        {/* key metrics row */}
        <div className="grid grid-cols-4 gap-3 mt-4">
          <div>
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider mb-1">Win Rate</p>
            <p className={cn('text-base font-black', strategy.winRate >= 60 ? 'text-green-600' : strategy.winRate >= 50 ? 'text-amber-600' : 'text-red-500')}>
              {strategy.winRate}%
            </p>
            <ProgressBar value={strategy.winRate} color={strategy.winRate >= 60 ? '#22c55e' : strategy.winRate >= 50 ? '#f59e0b' : '#ef4444'} />
          </div>
          <div>
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider mb-1">P.Factor</p>
            <p className={cn('text-base font-black', strategy.profitFactor >= 1.5 ? 'text-green-600' : strategy.profitFactor >= 1.0 ? 'text-amber-600' : 'text-red-500')}>
              {strategy.profitFactor.toFixed(1)}x
            </p>
            <ProgressBar value={strategy.profitFactor * 40} color={strategy.profitFactor >= 1.5 ? '#22c55e' : '#f59e0b'} />
          </div>
          <div>
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider mb-1">Week</p>
            <p className={cn('text-base font-black', strategy.weeklyReturn >= 0 ? 'text-green-600' : 'text-red-500')}>
              {strategy.weeklyReturn >= 0 ? '+' : ''}{strategy.weeklyReturn}%
            </p>
            <ProgressBar value={Math.abs(strategy.weeklyReturn) * 20} color={strategy.weeklyReturn >= 0 ? '#22c55e' : '#ef4444'} />
          </div>
          <div>
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider mb-1">AI Conf.</p>
            <p className="text-base font-black text-[#8b5cf6]">{strategy.aiConfidence}%</p>
            <ProgressBar value={strategy.aiConfidence} color="#8b5cf6" />
          </div>
        </div>

        {/* progress to 30 trades */}
        <div className="mt-3">
          <div className="flex justify-between items-center mb-1">
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">
              Progress to review ({strategy.totalTrades}/30 trades)
            </span>
            {meetsMinimum && (
              <span className="text-[9px] font-black text-green-600 uppercase">✓ Minimum met</span>
            )}
          </div>
          <ProgressBar value={tradeProgress} color={meetsMinimum ? '#22c55e' : '#3d5af1'} />
        </div>
      </div>

      {/* expanded detail */}
      {expanded && (
        <div className="border-t border-slate-100 p-5 bg-slate-50/50 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center">
              <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Drawdown</p>
              <p className={cn('text-lg font-black', strategy.drawdown <= 8 ? 'text-[#1a1c3a]' : 'text-red-500')}>
                {strategy.drawdown}%
              </p>
            </div>
            <div className="text-center">
              <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Streak</p>
              <p className="text-lg font-black text-[#1a1c3a]">
                {strategy.streak > 0 ? `🔥 ${strategy.streak}` : '—'}
              </p>
            </div>
            <div className="text-center">
              <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider">vs Backtest</p>
              <p className={cn('text-lg font-black',
                Math.abs(strategy.winRate - strategy.backtestWinRate) <= 10 ? 'text-green-600' : 'text-amber-600'
              )}>
                {strategy.winRate - strategy.backtestWinRate >= 0 ? '+' : ''}{strategy.winRate - strategy.backtestWinRate}%
              </p>
            </div>
          </div>

          {strategy.edgeHealth === 'warning' && (
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-100">
              <p className="text-[10px] text-amber-700 font-semibold leading-relaxed">
                Win rate has dropped more than 15% below backtest baseline. Strategy automatically paused.
                Review last 10 trades before resuming.
              </p>
            </div>
          )}

          <div className="flex gap-2">
            <button className="flex-1 py-2 px-3 rounded-lg border border-slate-200 text-[11px] font-bold text-slate-600 flex items-center justify-center gap-1.5 hover:bg-white transition-colors">
              <BarChart3 className="w-3.5 h-3.5" />
              Run Backtest
            </button>
            <button className="flex-1 py-2 px-3 rounded-lg border border-slate-200 text-[11px] font-bold text-slate-600 flex items-center justify-center gap-1.5 hover:bg-white transition-colors">
              {strategy.status === 'active' ? (
                <><Pause className="w-3.5 h-3.5" /> Pause</>
              ) : (
                <><Play className="w-3.5 h-3.5" /> Resume</>
              )}
            </button>
            {meetsMinimum && (
              <button className="flex-1 py-2 px-3 rounded-lg bg-[#3d5af1] text-white text-[11px] font-bold flex items-center justify-center gap-1.5 hover:opacity-90 transition-opacity">
                <Shield className="w-3.5 h-3.5" />
                Request Approval
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── leaderboard header ────────────────────────────────────────────────────────

function LeaderboardHeader({ strategies }: { strategies: Strategy[] }) {
  const active = strategies.filter(s => s.status === 'active').length;
  const bestReturn = Math.max(...strategies.map(s => s.weeklyReturn));
  return (
    <div className="grid grid-cols-3 gap-4 mb-5">
      <div className="glass-card p-4 text-center">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider mb-1">Strategies</p>
        <p className="text-2xl font-black text-[#1a1c3a]">{strategies.length}</p>
        <p className="text-[10px] text-slate-400">{active} active</p>
      </div>
      <div className="glass-card p-4 text-center">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider mb-1">Best This Week</p>
        <p className="text-2xl font-black text-green-600">+{bestReturn}%</p>
        <p className="text-[10px] text-slate-400">{strategies.find(s => s.weeklyReturn === bestReturn)?.name}</p>
      </div>
      <div className="glass-card p-4 text-center">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider mb-1">Ready for Review</p>
        <p className="text-2xl font-black text-[#3d5af1]">
          {strategies.filter(s => s.totalTrades >= 30 && s.edgeHealth === 'stable').length}
        </p>
        <p className="text-[10px] text-slate-400">meet 30-trade minimum</p>
      </div>
    </div>
  );
}

// ── main export ───────────────────────────────────────────────────────────────

export function StrategyRegistry() {
  const [sortBy, setSortBy] = useState<'rank' | 'winRate' | 'return'>('rank');

  const sorted = [...MOCK_STRATEGIES].sort((a, b) => {
    if (sortBy === 'rank')    return a.rank - b.rank;
    if (sortBy === 'winRate') return b.winRate - a.winRate;
    return b.weeklyReturn - a.weeklyReturn;
  });

  return (
    <div className="p-6 space-y-4">
      {/* title */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-[#1a1c3a] flex items-center gap-2">
            <Trophy className="w-5 h-5 text-[#3d5af1]" />
            Strategy Registry
          </h2>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            Paper trading only · No live execution
          </p>
        </div>
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
          {(['rank', 'winRate', 'return'] as const).map(s => (
            <button
              key={s}
              onClick={() => setSortBy(s)}
              className={cn(
                'px-2.5 py-1 rounded-md text-[10px] font-bold transition-all',
                sortBy === s ? 'bg-white shadow-sm text-[#3d5af1]' : 'text-slate-500'
              )}
            >
              {s === 'rank' ? 'Rank' : s === 'winRate' ? 'Win %' : 'Return'}
            </button>
          ))}
        </div>
      </div>

      <LeaderboardHeader strategies={MOCK_STRATEGIES} />

      <div className="space-y-3">
        {sorted.map(s => <StrategyCard key={s.id} strategy={s} />)}
      </div>

      {/* paper mode banner */}
      <div className="p-4 rounded-xl border border-blue-100 bg-blue-50 flex items-start gap-3">
        <Zap className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
        <div>
          <p className="text-[11px] font-black text-blue-800">Paper Trading Mode Active</p>
          <p className="text-[10px] text-blue-600 font-medium mt-0.5">
            All strategies are simulated. No real funds at risk. Strategies require 30+ paper trades
            and human approval before any live execution discussion can begin.
          </p>
        </div>
      </div>
    </div>
  );
}
