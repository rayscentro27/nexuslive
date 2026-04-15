import React from 'react';
import { 
  TrendingUp, 
  Play, 
  Pause, 
  RotateCcw, 
  Settings, 
  Activity, 
  ShieldCheck, 
  Zap,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Cpu,
  LineChart,
  ShieldCheck as ShieldCheckIcon
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdminTrading() {
  const strategies = [
    { name: 'Nexus Alpha v4', type: 'Scalping', winRate: '68.4%', profit: '+$12,480', status: 'active', load: 82 },
    { name: 'Funding Flow', type: 'Trend', winRate: '72.1%', profit: '+$8,920', status: 'active', load: 45 },
    { name: 'Credit Arb Bot', type: 'Arbitrage', winRate: '94.2%', profit: '+$3,150', status: 'paused', load: 0 },
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Trading Lab <span className="text-[#5B7CFA]">Admin</span></h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Monitor strategies, run backtests, and manage trading AI.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-6 py-2 rounded-xl bg-white border border-slate-200 text-[#1A2244] text-xs font-black uppercase tracking-widest hover:bg-slate-50 transition-all shadow-sm">
            Run Backtest
          </button>
          <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">
            Deploy Strategy
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Live Performance */}
        <div className="lg:col-span-8 space-y-8">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 space-y-6 shadow-sm relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-[#5B7CFA]/5 to-transparent rounded-full -mr-48 -mt-48 blur-3xl" />
            <div className="relative z-10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                    <Activity className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Live Performance</h3>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Live</span>
                  </div>
                  <span className="text-sm font-black text-[#1A2244]">+$24,550.00</span>
                </div>
              </div>

              <div className="h-64 bg-slate-50 rounded-2xl border border-slate-100 flex items-center justify-center relative overflow-hidden mt-6 shadow-inner">
                <div className="absolute inset-0 opacity-20">
                  <div className="w-full h-full" style={{ backgroundImage: 'radial-gradient(circle, #5B7CFA 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
                </div>
                <LineChart className="w-12 h-12 text-[#5B7CFA]/20" />
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest absolute bottom-4">Real-time market data stream</p>
              </div>

              <div className="grid grid-cols-3 gap-4 mt-6">
                {[
                  { label: 'Total Volume', value: '$1.2M', change: '+15%', trend: 'up' },
                  { label: 'Avg Win Rate', value: '74.2%', change: '+2.4%', trend: 'up' },
                  { label: 'Max Drawdown', value: '4.1%', change: '-0.5%', trend: 'down' },
                ].map((stat, i) => (
                  <div key={i} className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                    <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</p>
                    <div className="flex items-baseline justify-between mt-1">
                      <h4 className="text-lg font-black text-[#1A2244]">{stat.value}</h4>
                      <span className={cn(
                        "text-[8px] font-black uppercase tracking-widest",
                        stat.trend === 'up' ? "text-green-600" : "text-red-600"
                      )}>{stat.change}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Active Strategies */}
          <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
                  <Zap className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Active Strategies</h3>
              </div>
              <button className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest hover:text-[#4A6BEB] transition-colors">
                View All
              </button>
            </div>
            <div className="divide-y divide-slate-50">
              {strategies.map((strat, i) => (
                <div key={i} className="p-6 flex items-center justify-between hover:bg-slate-50/50 transition-all group">
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      "w-10 h-10 rounded-xl flex items-center justify-center",
                      strat.status === 'active' ? "bg-green-50 text-green-600" : "bg-slate-100 text-slate-400"
                    )}>
                      <BarChart3 className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-[#1A2244]">{strat.name}</h4>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">{strat.type}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-12">
                    <div className="text-right">
                      <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Win Rate</p>
                      <p className="text-xs font-black text-[#1A2244]">{strat.winRate}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Profit</p>
                      <p className="text-xs font-black text-green-600">{strat.profit}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="p-2 text-slate-400 hover:text-[#1A2244] hover:bg-slate-50 rounded-lg transition-all">
                        {strat.status === 'active' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                      </button>
                      <button className="p-2 text-slate-400 hover:text-[#1A2244] hover:bg-slate-50 rounded-lg transition-all">
                        <Settings className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Trading AI Control */}
        <div className="lg:col-span-4 space-y-8">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 space-y-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
                  <Cpu className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Trading AI</h3>
              </div>
              <span className="text-[10px] font-black text-green-600 uppercase tracking-widest">Optimized</span>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center text-[#5B7CFA] shadow-inner">
                  <Activity className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-xs font-black text-[#1A2244] uppercase tracking-widest">Neural Engine v2</h4>
                  <p className="text-[9px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">99.9% Uptime</p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-[8px] font-black text-slate-500 uppercase tracking-widest">
                  <span>Processing Power</span>
                  <span>84%</span>
                </div>
                <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-[#5B7CFA] w-[84%]" />
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">AI Parameters</h4>
              {[
                { label: 'Risk Tolerance', value: 'Moderate' },
                { label: 'Max Leverage', value: '10x' },
                { label: 'Auto-Approve', value: 'Enabled' },
              ].map((param, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="text-[10px] font-bold text-slate-500">{param.label}</span>
                  <span className="text-[10px] font-black text-[#1A2244] uppercase tracking-widest">{param.value}</span>
                </div>
              ))}
            </div>

            <button className="w-full py-3 rounded-xl bg-[#5B7CFA] text-white text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">
              Edit AI Prompts
            </button>
          </div>

          <div className="bg-white border border-slate-200 rounded-3xl p-6 space-y-6 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center text-green-600">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Risk Guard</h3>
            </div>
            <p className="text-[10px] text-slate-500 font-medium leading-relaxed">
              Real-time risk monitoring is active. System will auto-pause strategies if drawdown exceeds 5% in 24h.
            </p>
            <div className="flex items-center justify-between p-3 rounded-xl bg-green-50 border border-green-100">
              <span className="text-[10px] font-black text-green-600 uppercase tracking-widest">Status</span>
              <span className="text-[10px] font-black text-green-600 uppercase tracking-widest">Secured</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
