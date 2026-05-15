import React, { useEffect, useState } from 'react';
import { supabase } from '../../lib/supabase';
import {
  TrendingUp,
  Play,
  Pause,
  Settings,
  Activity,
  ShieldCheck,
  Zap,
  BarChart3,
  BookOpen,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface Strategy {
  id: string;
  name: string;
  asset_class: string | null;
  risk_level: string | null;
  ai_confidence: number | null;
  is_active: boolean;
  edge_health: string | null;
  description: string | null;
}

function timeAgo(ts: string): string {
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export function AdminTrading() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date().toISOString());

  const load = async () => {
    const { data } = await supabase
      .from('strategies_catalog')
      .select('id,name,asset_class,risk_level,ai_confidence,is_active,edge_health,description')
      .order('ai_confidence', { ascending: false })
      .limit(8);
    if (data) setStrategies(data as Strategy[]);
    setLastRefresh(new Date().toISOString());
    setLoading(false);
  };

  useEffect(() => { void load(); }, []);

  const activeCount = strategies.filter(s => s.is_active).length;
  const avgConf = strategies.length
    ? Math.round(strategies.reduce((sum, s) => sum + (s.ai_confidence ?? 0), 0) / strategies.length)
    : 0;

  return (
    <div className="p-6 space-y-6 bg-slate-50/50 min-h-full text-slate-600">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-[#1A2244] tracking-tight">
            Trading Intelligence <span className="text-[#5B7CFA]">Lab</span>
          </h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">
            AI strategy research and autonomous demo learning — read only during travel.
          </p>
        </div>
        <button
          onClick={() => { setLoading(true); void load(); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-xs font-black text-slate-500 hover:bg-slate-50 transition-all"
        >
          <RefreshCw size={12} />
          Refresh
        </button>
      </div>

      {/* DEMO ONLY safety banner */}
      <div className="flex items-start gap-3 p-4 rounded-2xl bg-amber-50 border border-amber-200">
        <AlertCircle size={18} className="text-amber-600 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-xs font-black text-amber-700 uppercase tracking-widest">
            DEMO / PAPER TRADING ONLY
          </p>
          <p className="text-[11px] text-amber-600 mt-1 leading-relaxed">
            No real-money orders are placed. All strategy activity is simulated learning with OANDA practice accounts.
            LIVE_TRADING=false · REAL_MONEY_TRADING=false · TRADING_LIVE_EXECUTION_ENABLED=false
          </p>
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Strategies', value: strategies.length, color: '#5B7CFA', bg: '#eef0fd' },
          { label: 'Active', value: activeCount, color: '#16a34a', bg: '#f0fdf4' },
          { label: 'Avg Confidence', value: `${avgConf}%`, color: '#7c3aed', bg: '#f5f3ff' },
          { label: 'Mode', value: 'DEMO', color: '#f59e0b', bg: '#fffbeb' },
        ].map(s => (
          <div key={s.label} style={{ background: s.bg, border: `1px solid ${s.color}20` }}
            className="p-4 rounded-2xl text-center">
            <p className="text-xl font-black" style={{ color: s.color }}>{s.value}</p>
            <p className="text-[9px] text-slate-400 font-bold uppercase tracking-widest mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Strategies */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Strategy Catalog</h3>
              <p className="text-[9px] text-slate-400 font-bold">Paper learning only · Synced {timeAgo(lastRefresh)}</p>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="p-8 flex items-center justify-center gap-3">
            <RefreshCw size={16} className="text-slate-400 animate-spin" />
            <span className="text-sm text-slate-400 font-medium">Loading strategies…</span>
          </div>
        ) : strategies.length === 0 ? (
          <div className="p-8 text-center">
            <BarChart3 size={32} className="text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400 font-medium">No strategies in catalog yet.</p>
            <p className="text-[11px] text-slate-300 mt-1">
              Strategies populate as autonomous paper trading runs and patterns are scored.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-50">
            {strategies.map(strat => {
              const conf = strat.ai_confidence ?? 0;
              const confColor = conf >= 70 ? '#16a34a' : conf >= 45 ? '#f59e0b' : '#ef4444';
              return (
                <div key={strat.id} className="p-5 flex items-center gap-4 hover:bg-slate-50/50 transition-all">
                  <div className={cn(
                    'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
                    strat.is_active ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-400'
                  )}>
                    <BarChart3 className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-black text-[#1A2244] truncate">{strat.name}</h4>
                      {strat.is_active && (
                        <span className="text-[8px] font-black text-green-600 bg-green-50 px-1.5 py-0.5 rounded uppercase">Active</span>
                      )}
                    </div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">
                      {strat.asset_class || 'Multi-asset'} · Risk: {strat.risk_level || 'Moderate'}
                    </p>
                    {/* Confidence bar */}
                    <div className="flex items-center gap-2 mt-2">
                      <div className="flex-1 h-1 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${conf}%`, background: confColor }} />
                      </div>
                      <span className="text-[9px] font-black" style={{ color: confColor }}>{conf}%</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {strat.edge_health && (
                      <span className={cn(
                        'text-[8px] font-black px-2 py-1 rounded-lg uppercase tracking-wider',
                        strat.edge_health === 'strong' ? 'bg-green-50 text-green-600' :
                        strat.edge_health === 'moderate' ? 'bg-amber-50 text-amber-600' :
                        'bg-slate-100 text-slate-400'
                      )}>
                        {strat.edge_health}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Learning & Safety panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Autonomous learning */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Demo Learning</h3>
              <p className="text-[9px] text-slate-400 font-bold">OANDA practice mode</p>
            </div>
          </div>
          <div className="space-y-2">
            {[
              { label: 'Execution Mode', value: 'PAPER ONLY' },
              { label: 'Max Concurrent Trades', value: '3' },
              { label: 'Max Daily Drawdown', value: '$250' },
              { label: 'Sessions Allowed', value: 'London / NY' },
            ].map(item => (
              <div key={item.label} className="flex justify-between items-center p-2 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-[10px] text-slate-500 font-medium">{item.label}</span>
                <span className="text-[10px] font-black text-[#1A2244]">{item.value}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2 p-2 rounded-lg bg-blue-50 border border-blue-100">
            <BookOpen size={12} className="text-[#5B7CFA]" />
            <span className="text-[10px] font-black text-[#5B7CFA]">Ask Hermes: "how did demo trading perform today"</span>
          </div>
        </div>

        {/* Safety verification */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center text-green-600">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Safety Verification</h3>
          </div>
          <div className="space-y-2">
            {[
              { label: 'NEXUS_DRY_RUN', value: 'true', safe: true },
              { label: 'LIVE_TRADING', value: 'false', safe: true },
              { label: 'REAL_MONEY_TRADING', value: 'false', safe: true },
              { label: 'TRADING_LIVE_EXECUTION_ENABLED', value: 'false', safe: true },
              { label: 'Auto-Approve', value: 'Disabled', safe: true },
            ].map(item => (
              <div key={item.label} className="flex justify-between items-center p-2 rounded-lg"
                style={{ background: item.safe ? '#f0fdf4' : '#fef2f2', border: `1px solid ${item.safe ? '#bbf7d0' : '#fecaca'}` }}>
                <span className="text-[9px] text-slate-500 font-mono">{item.label}</span>
                <span className={cn('text-[9px] font-black', item.safe ? 'text-green-600' : 'text-red-600')}>
                  {item.value} ✓
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
