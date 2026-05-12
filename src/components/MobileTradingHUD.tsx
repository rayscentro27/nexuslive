import React, { useState } from 'react';
import {
  Zap, TrendingUp, TrendingDown, Shield, Target,
  ChevronRight, Activity, AlertTriangle,
} from 'lucide-react';
import { cn } from '../lib/utils';

// ── types ─────────────────────────────────────────────────────────────────────

interface HUDTrade {
  id: string;
  market: string;
  direction: 'long' | 'short';
  pnlPips: number;
  tpProgress: number;  // 0–100
  session: string;
}

interface HUDMetrics {
  balance: number;
  todayPct: number;
  weekPct: number;
  riskUsedPct: number;
  openTrades: number;
  maxTrades: number;
  riskLabel: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  circuitBreaker: boolean;
}

// ── mock data — swap with live API ────────────────────────────────────────────

const MOCK_METRICS: HUDMetrics = {
  balance: 10847,
  todayPct: 0.32,
  weekPct: 4.2,
  riskUsedPct: 45,
  openTrades: 2,
  maxTrades: 4,
  riskLabel: 'LOW',
  circuitBreaker: false,
};

const MOCK_TRADES: HUDTrade[] = [
  { id: 't1', market: 'EUR/USD', direction: 'long',  pnlPips: 28, tpProgress: 42, session: 'London' },
  { id: 't2', market: 'GBP/JPY', direction: 'short', pnlPips: -8, tpProgress: 12, session: 'London' },
];

// ── sub-components ────────────────────────────────────────────────────────────

function RiskPill({ label }: { label: HUDMetrics['riskLabel'] }) {
  const cls = {
    LOW:      'bg-green-50 text-green-700',
    MODERATE: 'bg-amber-50 text-amber-700',
    HIGH:     'bg-red-50 text-red-600',
    CRITICAL: 'bg-red-100 text-red-700',
  }[label];
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider', cls)}>
      {label}
    </span>
  );
}

function MiniTradeCard({ trade }: { trade: HUDTrade }) {
  const pos = trade.pnlPips >= 0;
  return (
    <div className="flex items-center gap-3 py-2 px-3 bg-white rounded-xl border border-slate-100">
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        {trade.direction === 'long'
          ? <TrendingUp className="w-3.5 h-3.5 text-green-500 shrink-0" />
          : <TrendingDown className="w-3.5 h-3.5 text-red-400 shrink-0" />}
        <span className="font-black text-[11px] text-[#1a1c3a] truncate">{trade.market}</span>
        <span className={cn(
          'text-[8px] font-black uppercase px-1 py-0.5 rounded shrink-0',
          trade.direction === 'long' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'
        )}>
          {trade.direction}
        </span>
      </div>
      {/* TP progress mini bar */}
      <div className="flex items-center gap-1.5 shrink-0">
        <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={cn('h-full rounded-full', pos ? 'bg-green-400' : 'bg-red-400')}
            style={{ width: `${Math.abs(trade.tpProgress)}%` }}
          />
        </div>
        <span className={cn('font-black text-[11px] tabular-nums w-12 text-right', pos ? 'text-green-600' : 'text-red-500')}>
          {pos ? '+' : ''}{trade.pnlPips}p
        </span>
      </div>
    </div>
  );
}

// ── main HUD ──────────────────────────────────────────────────────────────────

export function MobileTradingHUD({ onExpand }: { onExpand?: () => void }) {
  const [metrics] = useState<HUDMetrics>(MOCK_METRICS);
  const [trades] = useState<HUDTrade[]>(MOCK_TRADES);
  const todayPos = metrics.todayPct >= 0;

  if (metrics.circuitBreaker) {
    return (
      <div className="mx-4 mb-3 p-3 rounded-xl bg-red-50 border border-red-200 flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-black text-red-700">Circuit Breaker Active</p>
          <p className="text-[9px] text-red-500">No new entries. Operator reset required.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-4 mb-3 space-y-2">
      {/* Top HUD bar */}
      <div
        className="flex items-center gap-3 p-3 rounded-xl bg-white border border-slate-100"
        onClick={onExpand}
      >
        {/* Balance + today */}
        <div className="flex-1 min-w-0">
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Paper Balance</p>
          <div className="flex items-baseline gap-1.5 mt-0.5">
            <span className="text-base font-black text-[#1a1c3a]">
              ${metrics.balance.toLocaleString()}
            </span>
            <span className={cn('text-[10px] font-black', todayPos ? 'text-green-600' : 'text-red-500')}>
              {todayPos ? '+' : ''}{metrics.todayPct.toFixed(2)}%
            </span>
          </div>
        </div>

        {/* Risk gauge */}
        <div className="shrink-0 text-center">
          <div className="relative w-10 h-10">
            <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="14" fill="none" stroke="#f1f5f9" strokeWidth="3" />
              <circle
                cx="18" cy="18" r="14" fill="none"
                stroke={metrics.riskUsedPct > 80 ? '#ef4444' : metrics.riskUsedPct > 60 ? '#f59e0b' : '#22c55e'}
                strokeWidth="3"
                strokeDasharray={`${metrics.riskUsedPct * 0.879} 87.9`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <Shield className="w-3.5 h-3.5 text-[#3d5af1]" />
            </div>
          </div>
          <RiskPill label={metrics.riskLabel} />
        </div>

        {/* Open trades count */}
        <div className="shrink-0 text-center">
          <div className="flex gap-0.5 mb-1">
            {Array.from({ length: metrics.maxTrades }).map((_, i) => (
              <div
                key={i}
                className={cn('w-2.5 h-5 rounded-sm', i < metrics.openTrades ? 'bg-[#3d5af1]' : 'bg-slate-100')}
              />
            ))}
          </div>
          <p className="text-[8px] text-slate-400 font-medium">
            {metrics.openTrades}/{metrics.maxTrades}
          </p>
        </div>

        <ChevronRight className="w-4 h-4 text-slate-300 shrink-0" />
      </div>

      {/* Live trades compact */}
      {trades.length > 0 && (
        <div className="space-y-1.5">
          {trades.map(t => <MiniTradeCard key={t.id} trade={t} />)}
        </div>
      )}

      {trades.length === 0 && (
        <div className="flex items-center gap-2 px-3 py-2 bg-white rounded-xl border border-slate-100">
          <Activity className="w-3.5 h-3.5 text-[#00d4ff] animate-pulse" />
          <span className="text-[10px] text-slate-400 font-medium">
            Scanning for signals · {metrics.riskLabel} risk environment
          </span>
        </div>
      )}

      {/* Week stat pill */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-white rounded-xl border border-slate-100">
        <span className="text-[9px] text-slate-400 font-medium">This week</span>
        <span className={cn('font-black text-[11px]', metrics.weekPct >= 0 ? 'text-green-600' : 'text-red-500')}>
          {metrics.weekPct >= 0 ? '+' : ''}{metrics.weekPct}%
        </span>
        <span className="text-[9px] text-slate-300">·</span>
        <span className="text-[9px] text-slate-400 font-medium flex items-center gap-1">
          <Zap className="w-2.5 h-2.5 text-[#00d4ff]" />
          PAPER MODE
        </span>
      </div>
    </div>
  );
}
