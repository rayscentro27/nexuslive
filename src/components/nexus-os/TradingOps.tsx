import React, { useEffect, useState } from 'react';
import {
  TrendingUp, TrendingDown, ShieldCheck, AlertTriangle, Activity,
  Lock, Loader2, RefreshCw, BarChart3, FileText, Clock,
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { getTradingStatus } from '../../services/nexusApi';
import { OSSection, OSCard, Badge, StatusDot, timeAgo, EmptyState, NotConnectedLabel } from './shared';
import type { PaperTrade } from './types';

interface TradingStatusData {
  engine?: {
    dry_run: boolean;
    live_trading: boolean;
    broker_type: string;
    broker_connected: boolean;
    signals_processed: number;
    active_positions: number;
    last_signal: Record<string, unknown> | null;
    last_result: Record<string, unknown> | null;
    stage: string;
    updated_at: string;
  };
  recent_paper_trades?: Array<{
    id: string;
    symbol: string;
    entry_status: 'open' | 'closed';
    thesis: string;
    opened_at: string;
    closed_at: string | null;
  }>;
  signal_review_tail?: string[];
}

export function TradingOps() {
  const [status, setStatus] = useState<TradingStatusData | null>(null);
  const [paperTrades, setPaperTrades] = useState<PaperTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setApiError(null);

    // Try live nexus API status
    try {
      const s = await getTradingStatus();
      setStatus(s as TradingStatusData);
    } catch (err) {
      setApiError(String(err));
      setStatus(null);
    }

    // Load from Supabase paper_trade_journal
    try {
      const { data } = await supabase
        .from('paper_trade_journal')
        .select('id,strategy_id,market,direction,entry_date,entry_price,stop_loss,exit_price,paper_pnl_usd,result_r,status,thesis,lesson,created_at')
        .order('entry_date', { ascending: false })
        .limit(20);
      if (data) setPaperTrades(data as unknown as PaperTrade[]);
    } catch (_) {}

    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  const openTrades = paperTrades.filter(t => !t.exit_price);
  const closedTrades = paperTrades.filter(t => t.exit_price);
  const winningTrades = closedTrades.filter(t => (t.paper_pnl_usd ?? 0) > 0);
  const winRate = closedTrades.length > 0
    ? Math.round((winningTrades.length / closedTrades.length) * 100)
    : null;
  const totalPnl = closedTrades.reduce((s, t) => s + (t.paper_pnl_usd ?? 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Trading <span className="text-[#5B7CFA]">Operations</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Paper/research mode only · Supabase paper_trade_journal + Nexus API
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

      {/* Safety lock banner */}
      <div className="p-4 rounded-2xl bg-green-50 border border-green-200 flex items-center gap-3">
        <Lock className="w-5 h-5 text-green-600 shrink-0" />
        <div>
          <p className="text-sm font-black text-green-700">Live Trading: LOCKED</p>
          <p className="text-xs text-green-600 mt-0.5">
            NEXUS_DRY_RUN=true · TRADING_LIVE_EXECUTION_ENABLED=false · No real money at risk.
            Live trading requires explicit approval before any config change.
          </p>
        </div>
      </div>

      {/* Engine status */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <EngineCard
          icon={Activity}
          label="Engine Mode"
          value={status?.engine ? (status.engine.dry_run ? 'Paper / Dry Run' : '⚠️ LIVE') : 'Not reached'}
          color={status?.engine?.dry_run !== false ? 'green' : 'red'}
        />
        <EngineCard
          icon={ShieldCheck}
          label="Broker"
          value={status?.engine?.broker_type?.toUpperCase() ?? '—'}
          color="blue"
          sub={status?.engine?.broker_connected ? 'Connected' : 'Disconnected'}
        />
        <EngineCard
          icon={BarChart3}
          label="Signals Processed"
          value={status?.engine ? String(status.engine.signals_processed) : '—'}
          color="purple"
        />
        <EngineCard
          icon={Activity}
          label="Active Positions"
          value={status?.engine ? String(status.engine.active_positions) : '—'}
          color="amber"
        />
      </div>

      {apiError && (
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500">
          <p className="font-bold text-slate-700 mb-1">Nexus API not reachable</p>
          <p>Set <code>NEXUS_API_URL</code> env var. Data below is from Supabase paper_trade_journal only.</p>
          <p className="font-mono text-[10px] mt-1 text-slate-400">{apiError}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Paper trade stats */}
        <OSSection title="Paper Trade Stats" icon={BarChart3} action={
          paperTrades.length === 0 ? undefined : <Badge label={`${paperTrades.length} trades`} variant="info" />
        }>
          {loading ? <LoadingRow /> : paperTrades.length === 0 ? (
            <EmptyState icon={BarChart3} message="No paper trades in journal yet" />
          ) : (
            <div className="space-y-2">
              <StatRow label="Total Trades" value={String(paperTrades.length)} />
              <StatRow label="Open Trades" value={String(openTrades.length)} />
              <StatRow label="Closed Trades" value={String(closedTrades.length)} />
              <StatRow
                label="Win Rate"
                value={winRate !== null ? `${winRate}%` : 'N/A'}
                color={winRate !== null && winRate >= 50 ? 'green' : 'red'}
              />
              <StatRow
                label="Total Paper P&L"
                value={`$${totalPnl.toFixed(2)}`}
                color={totalPnl >= 0 ? 'green' : 'red'}
              />
              <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-100 text-[10px] text-slate-400 italic">
                Paper P&L only. No real money. Research and simulation.
              </div>
            </div>
          )}
        </OSSection>

        {/* Nexus engine detail */}
        <OSSection title="Engine Status" icon={Activity}>
          {status?.engine ? (
            <div className="space-y-2">
              <StatRow label="Stage" value={status.engine.stage} />
              <StatRow label="Last Updated" value={timeAgo(status.engine.updated_at)} />
              {status.engine.last_signal && (
                <div>
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Last Signal</p>
                  <pre className="text-[10px] font-mono bg-slate-50 border border-slate-100 rounded-xl p-2 overflow-x-auto text-slate-600">
                    {JSON.stringify(status.engine.last_signal, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              <NotConnectedLabel />
              <p className="text-xs text-slate-400">Connect Nexus backend: set NEXUS_API_URL in Netlify env.</p>
            </div>
          )}
        </OSSection>

        {/* Signal review tail */}
        {status?.signal_review_tail && status.signal_review_tail.length > 0 && (
          <OSSection title="Signal Review Log" icon={FileText}>
            <div className="space-y-1 font-mono text-[11px] text-slate-600 max-h-40 overflow-y-auto">
              {status.signal_review_tail.map((line, i) => (
                <p key={i} className="leading-relaxed">{line}</p>
              ))}
            </div>
          </OSSection>
        )}

        {/* Recent paper trades */}
        <OSSection title="Recent Paper Trades" icon={TrendingUp}>
          {loading ? <LoadingRow /> : paperTrades.length === 0 ? (
            <EmptyState icon={TrendingUp} message="No trades yet" />
          ) : (
            <div className="space-y-2">
              {paperTrades.slice(0, 6).map(t => (
                <TradeRow key={t.id} trade={t} />
              ))}
            </div>
          )}
        </OSSection>
      </div>

      {/* Config info */}
      <OSSection title="Configuration" icon={ShieldCheck}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="space-y-1.5">
            <ConfigRow label="Broker" value="Oanda Practice (fxpractice)" />
            <ConfigRow label="Account" value="101-001-27557105-003" />
            <ConfigRow label="Signal Port" value="5000" />
            <ConfigRow label="Pairs" value="EUR/USD, GBP/USD, USD/JPY" />
          </div>
          <div className="space-y-1.5">
            <ConfigRow label="live_trading" value="false" highlight="safe" />
            <ConfigRow label="NEXUS_DRY_RUN" value="true" highlight="safe" />
            <ConfigRow label="auto_trading" value="false" highlight="safe" />
            <ConfigRow label="max_trades_per_day" value="5" />
          </div>
        </div>
        <div className="mt-4 p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
          <p className="text-[10px] text-amber-700 font-medium">
            API key in trading_config.json is labeled ROTATE_THIS_KEY. Rotate before any real use.
            Do not enable live_trading without a full review and explicit approval.
          </p>
        </div>
      </OSSection>
    </div>
  );
}

function EngineCard({
  icon: Icon,
  label,
  value,
  sub,
  color = 'blue',
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  const colorMap: Record<string, string> = {
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
    blue: 'bg-blue-50 text-[#5B7CFA]',
    purple: 'bg-purple-50 text-purple-600',
    amber: 'bg-amber-50 text-amber-600',
  };
  return (
    <OSCard className="p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${colorMap[color] ?? colorMap.blue}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
        <p className="text-sm font-black text-[#1A2244] leading-tight">{value}</p>
        {sub && <p className="text-[9px] text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </OSCard>
  );
}

function StatRow({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: 'green' | 'red';
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{label}</span>
      <span
        className={`text-xs font-bold ${
          color === 'green' ? 'text-green-600' : color === 'red' ? 'text-red-500' : 'text-[#1A2244]'
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function TradeRow({ trade }: { trade: PaperTrade }) {
  const pnl = trade.paper_pnl_usd;
  const isOpen = !trade.exit_price;
  return (
    <div className="flex items-center gap-3 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
      <div className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 ${
        trade.direction === 'long' ? 'bg-green-50' : 'bg-red-50'
      }`}>
        {trade.direction === 'long'
          ? <TrendingUp className="w-3 h-3 text-green-500" />
          : <TrendingDown className="w-3 h-3 text-red-500" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-bold text-[#1A2244]">{trade.market} · {trade.direction?.toUpperCase()}</p>
        <p className="text-[10px] text-slate-400">{trade.entry_date} · {trade.strategy_id}</p>
      </div>
      <div className="text-right">
        {isOpen ? (
          <Badge label="Open" variant="info" />
        ) : pnl !== null && pnl !== undefined ? (
          <span className={`text-xs font-black ${pnl >= 0 ? 'text-green-600' : 'text-red-500'}`}>
            {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
          </span>
        ) : (
          <span className="text-xs text-slate-400">Closed</span>
        )}
      </div>
    </div>
  );
}

function ConfigRow({ label, value, highlight }: { label: string; value: string; highlight?: 'safe' | 'warn' }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest font-mono">{label}</span>
      <span className={`text-xs font-bold font-mono ${
        highlight === 'safe' ? 'text-green-600' : highlight === 'warn' ? 'text-amber-500' : 'text-[#1A2244]'
      }`}>{value}</span>
    </div>
  );
}

function LoadingRow() {
  return (
    <div className="flex items-center justify-center py-6">
      <Loader2 className="w-5 h-5 animate-spin text-slate-300" />
    </div>
  );
}
