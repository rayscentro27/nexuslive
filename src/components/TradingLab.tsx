import React from 'react';
import { 
  TrendingUp, 
  Clock, 
  Zap, 
  ChevronRight, 
  Play, 
  MessageSquare,
  BarChart3,
  Bot,
  CheckCircle2
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';

const performanceData = [
  { name: 'Mon', pnl: 2400 },
  { name: 'Tue', pnl: 1398 },
  { name: 'Wed', pnl: 9800 },
  { name: 'Thu', pnl: 3908 },
  { name: 'Fri', pnl: 4800 },
  { name: 'Sat', pnl: 3800 },
  { name: 'Sun', pnl: 4300 },
];

const backtestResults = [
  { strategy: 'Momentum Reversal', trades: 220, winRate: '70%', stability: 4, pnl: '$12,450', status: 'Approved' },
  { strategy: 'Pullback Buy', trades: 134, winRate: '66%', stability: 5, pnl: '$8,740', status: 'Approved' },
  { strategy: 'Pre-Earnings Momentum', trades: 90, winRate: '72%', stability: 3, pnl: '$5,305', status: 'Promoted' },
];

export function TradingLab() {
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto h-full flex flex-col">
      <div className="space-y-0.5 shrink-0">
        <h2 className="text-2xl font-bold text-[#1A2244]">Trading Lab</h2>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 px-1.5 py-0.5 rounded-lg bg-slate-100 text-slate-700 text-[8px] font-bold uppercase tracking-widest">
            <CheckCircle2 className="w-2.5 h-2.5" /> Education Mode
          </span>
          <span className="flex items-center gap-1.5 px-1.5 py-0.5 rounded-lg bg-green-100 text-green-700 text-[8px] font-bold uppercase tracking-widest">
            <CheckCircle2 className="w-2.5 h-2.5" /> Paper Trading
          </span>
        </div>
        <p className="text-xs text-slate-500 font-medium mt-1">Learn, backtest, and simulate trading strategies.</p>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide space-y-6 pr-1">
        {/* Performance Snapshot */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-[#1A2244]">Performance Snapshot</h3>
              <span className="text-[10px] text-slate-400 font-medium">Backtest and simulate strategies.</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="glass-panel p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Win Rate (30d)</p>
                  <ChevronRight className="w-2.5 h-2.5 text-slate-300" />
                </div>
                <div className="space-y-0.5">
                  <p className="text-2xl font-bold text-[#1A2244]">67%</p>
                  <p className="text-[10px] font-bold text-green-600 flex items-center gap-1">
                    <TrendingUp className="w-2.5 h-2.5" /> +2.5%
                  </p>
                </div>
                <div className="h-10">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={performanceData}>
                      <Area type="monotone" dataKey="pnl" stroke="#5B7CFA" fill="#5B7CFA" fillOpacity={0.1} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <button className="w-full py-1.5 bg-slate-50 text-slate-600 font-bold text-[8px] rounded-lg border border-slate-100 hover:bg-slate-100 transition-all">Journal</button>
              </div>

              <div className="glass-panel p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">P&L (30d)</p>
                  <ChevronRight className="w-2.5 h-2.5 text-slate-300" />
                </div>
                <div className="space-y-0.5">
                  <p className="text-2xl font-bold text-[#1A2244]">+$4,570</p>
                  <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">(Demo)</p>
                </div>
                <div className="h-10">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={performanceData}>
                      <Bar dataKey="pnl" fill="#5B7CFA" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <button className="w-full py-1.5 bg-slate-50 text-slate-600 font-bold text-[8px] rounded-lg border border-slate-100 hover:bg-slate-100 transition-all">Journal</button>
              </div>

              <div className="glass-panel p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Trades (30d)</p>
                  <ChevronRight className="w-2.5 h-2.5 text-slate-300" />
                </div>
                <div className="space-y-0.5">
                  <p className="text-2xl font-bold text-[#1A2244]">32</p>
                  <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Active</p>
                </div>
                <div className="flex items-center gap-2 pt-2">
                  <div className="w-1.5 h-1.5 bg-[#5B7CFA] rounded-full animate-pulse" />
                  <span className="text-[8px] font-bold text-[#5B7CFA] uppercase tracking-widest">Weekly progress</span>
                </div>
                <button className="w-full py-1.5 bg-slate-50 text-slate-600 font-bold text-[8px] rounded-lg border border-slate-100 hover:bg-slate-100 transition-all">Journal</button>
              </div>
            </div>
          </div>

          {/* AI Insights */}
          <div className="glass-card p-6 space-y-4 relative overflow-hidden">
            <div className="absolute -top-4 -right-4 w-24 h-24 opacity-10">
              <BotAvatar type="trading" size="lg" className="bg-transparent shadow-none" />
            </div>
            <div className="flex items-center justify-between relative z-10">
              <h3 className="text-sm font-bold text-[#1A2244]">AI Insights</h3>
              <button className="text-[8px] font-bold text-[#5B7CFA] uppercase tracking-widest hover:underline">All</button>
            </div>
            
            <div className="glass-panel p-4 flex flex-col items-center text-center space-y-3 relative z-10">
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center">
                <Bot className="w-6 h-6 text-[#5B7CFA]" />
              </div>
              <div className="space-y-0.5">
                <p className="text-xs font-bold text-[#1A2244]">Best Strategy</p>
                <p className="text-[10px] text-slate-500 font-medium">Momentum Reversal (72%)</p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-[8px] font-bold text-[#1A2244] uppercase tracking-widest">Market Conditions</p>
              <div className="p-3 glass-panel bg-slate-50/50 border-slate-100">
                <p className="text-[10px] text-slate-600 leading-relaxed font-medium">
                  Increased volatility detected - consider breakout strategies.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Strategy Ideas */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-[#1A2244]">Strategy Ideas</h3>
            <button className="text-[10px] font-bold text-[#5B7CFA] hover:underline">View All</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="glass-card p-5 space-y-4 group hover:border-slate-300 transition-all">
              <div className="flex items-center justify-between">
                <span className="px-1.5 py-0.5 rounded-md bg-blue-50 text-[#5B7CFA] text-[8px] font-bold uppercase tracking-widest">In Testing</span>
                <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">ID: 88</span>
              </div>
              <div className="space-y-0.5">
                <h4 className="text-base font-bold text-[#1A2244]">Momentum Reversal</h4>
                <p className="text-2xl font-black text-[#1A2244]">88%</p>
                <p className="text-[10px] font-bold text-green-600 flex items-center gap-1">
                  <TrendingUp className="w-2.5 h-2.5" /> +12% vs last week
                </p>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-[10px] text-slate-500 font-medium">220 trades</span>
                </div>
                <div className="flex gap-2">
                  <button className="bg-[#5B7CFA] text-white py-1.5 px-4 text-[8px] font-bold rounded-lg shadow-lg shadow-blue-500/10 hover:bg-[#4A6BEB] transition-all">Try Demo</button>
                  <button className="p-1.5 bg-slate-50 text-slate-400 rounded-lg border border-slate-100 hover:bg-slate-100 transition-all"><MessageSquare className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            </div>

            <div className="glass-card p-5 space-y-4 group hover:border-slate-300 transition-all">
              <div className="flex items-center justify-between">
                <span className="px-1.5 py-0.5 rounded-md bg-blue-50 text-[#5B7CFA] text-[8px] font-bold uppercase tracking-widest">In Testing</span>
                <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">ID: 85</span>
              </div>
              <div className="space-y-0.5">
                <h4 className="text-base font-bold text-[#1A2244]">Morning Breakout</h4>
                <p className="text-2xl font-black text-[#1A2244]">85%</p>
                <p className="text-[10px] font-bold text-green-600 flex items-center gap-1">
                  <TrendingUp className="w-2.5 h-2.5" /> +8% vs last week
                </p>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-[10px] text-slate-500 font-medium">124 trades</span>
                </div>
                <div className="flex gap-2">
                  <button className="bg-[#5B7CFA] text-white py-1.5 px-4 text-[8px] font-bold rounded-lg shadow-lg shadow-blue-500/10 hover:bg-[#4A6BEB] transition-all">Try Demo</button>
                  <button className="p-1.5 bg-slate-50 text-slate-400 rounded-lg border border-slate-100 hover:bg-slate-100 transition-all"><MessageSquare className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Backtest Results Table */}
        <div className="glass-card overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#1A2244]">Backtest Results</h3>
            <div className="flex gap-4">
              <button className="text-[10px] font-bold text-[#5B7CFA] border-b-2 border-[#5B7CFA] pb-0.5 uppercase tracking-widest">Strategies</button>
              <button className="text-[10px] font-bold text-slate-400 hover:text-[#5B7CFA] transition-colors uppercase tracking-widest">Watchlist</button>
              <button className="text-[10px] font-bold text-slate-400 hover:text-[#5B7CFA] transition-colors uppercase tracking-widest">Journal</button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50/50 text-left">
                  <th className="px-4 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest">Strategy</th>
                  <th className="px-4 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest">Trades</th>
                  <th className="px-4 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest">Win %</th>
                  <th className="px-4 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest">Stability</th>
                  <th className="px-4 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest">P&L (60d)</th>
                  <th className="px-4 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest">Status</th>
                  <th className="px-4 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {backtestResults.map((res, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/30 transition-colors group">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                        <span className="text-xs font-bold text-[#1A2244]">{res.strategy}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600 font-medium">{res.trades}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 font-medium">{res.winRate}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-0.5">
                        {[...Array(5)].map((_, i) => (
                          <div key={i} className={cn("w-1.5 h-1.5 rounded-full", i < res.stability ? "bg-amber-400" : "bg-slate-100")} />
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs font-black text-green-600">{res.pnl}</td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        "px-1.5 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-widest",
                        res.status === 'Approved' ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-700"
                      )}>
                        {res.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button className="p-1 text-slate-300 hover:text-[#5B7CFA] hover:bg-blue-50 rounded-md transition-all">
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
