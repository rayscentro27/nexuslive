import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, TrendingDown,
  Clock,
  Zap,
  ChevronRight,
  Play,
  MessageSquare,
  BarChart3,
  Bot,
  CheckCircle2,
  Plus, Loader2, X, AlertCircle,
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
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthProvider';

// ─── Paper Trading ─────────────────────────────────────────────────────────────

interface PaperAccount {
  id: string;
  balance: number;
  initial_balance: number;
}

interface PaperTrade {
  id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  status: string;
  pnl: number | null;
  opened_at: string;
  closed_at: string | null;
  notes: string | null;
}

interface TradeForm {
  symbol: string;
  direction: 'long' | 'short';
  entry_price: string;
  quantity: string;
  notes: string;
}

const EMPTY_TRADE: TradeForm = { symbol: '', direction: 'long', entry_price: '', quantity: '1', notes: '' };

function PaperTradingTab() {
  const { user } = useAuth();
  const [account,    setAccount]    = useState<PaperAccount | null>(null);
  const [trades,     setTrades]     = useState<PaperTrade[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [showForm,   setShowForm]   = useState(false);
  const [form,       setForm]       = useState<TradeForm>(EMPTY_TRADE);
  const [saving,     setSaving]     = useState(false);
  const [closingId,  setClosingId]  = useState<string | null>(null);
  const [closePrice, setClosePrice] = useState('');

  const load = useCallback(async () => {
    if (!user) return;
    // Get or create account
    let { data: acct } = await supabase
      .from('paper_trading_accounts')
      .select('*')
      .eq('user_id', user.id)
      .maybeSingle();

    if (!acct) {
      const { data: created } = await supabase
        .from('paper_trading_accounts')
        .insert({ user_id: user.id })
        .select()
        .single();
      acct = created;
    }

    const { data: tradeData } = await supabase
      .from('paper_trades')
      .select('*')
      .eq('user_id', user.id)
      .order('opened_at', { ascending: false });

    setAccount(acct as PaperAccount);
    setTrades((tradeData ?? []) as PaperTrade[]);
    setLoading(false);
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const openTrade = async () => {
    if (!user || !account || !form.symbol || !form.entry_price) return;
    setSaving(true);
    await supabase.from('paper_trades').insert({
      user_id:     user.id,
      account_id:  account.id,
      symbol:      form.symbol.toUpperCase(),
      direction:   form.direction,
      entry_price: parseFloat(form.entry_price),
      quantity:    parseFloat(form.quantity) || 1,
      notes:       form.notes || null,
      status:      'open',
    });
    setSaving(false);
    setShowForm(false);
    setForm(EMPTY_TRADE);
    load();
  };

  const closeTrade = async (trade: PaperTrade) => {
    if (!closePrice) return;
    const exit = parseFloat(closePrice);
    const direction = trade.direction === 'long' ? 1 : -1;
    const pnl = (exit - trade.entry_price) * trade.quantity * direction;
    const newBalance = (account?.balance ?? 0) + pnl;

    await Promise.all([
      supabase.from('paper_trades').update({
        exit_price:  exit,
        status:      'closed',
        pnl:         pnl,
        closed_at:   new Date().toISOString(),
      }).eq('id', trade.id),
      supabase.from('paper_trading_accounts').update({ balance: newBalance }).eq('id', account!.id),
    ]);

    setClosingId(null);
    setClosePrice('');
    load();
  };

  const openTrades  = trades.filter(t => t.status === 'open');
  const closedTrades = trades.filter(t => t.status === 'closed');
  const totalPnl    = closedTrades.reduce((s, t) => s + (t.pnl ?? 0), 0);
  const winRate     = closedTrades.length > 0
    ? Math.round((closedTrades.filter(t => (t.pnl ?? 0) > 0).length / closedTrades.length) * 100)
    : 0;

  if (loading) return (
    <div style={{ padding: 48, textAlign: 'center' }}>
      <Loader2 size={28} color="#3d5af1" style={{ animation: 'spin 1s linear infinite', margin: '0 auto' }} />
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Disclaimer */}
      <div style={{ padding: '10px 14px', borderRadius: 12, background: '#fffbeb', border: '1px solid #fde68a', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <AlertCircle size={14} color="#f59e0b" style={{ flexShrink: 0, marginTop: 1 }} />
        <p style={{ fontSize: 12, color: '#92400e', margin: 0 }}>
          This is a paper (simulated) trading account. No real money is involved. Prices are entered manually and are not live market data.
        </p>
      </div>

      {/* Account stats */}
      {account && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {[
            { label: 'Balance',    value: `$${account.balance.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: '#1a1c3a' },
            { label: 'Total P&L',  value: (totalPnl >= 0 ? '+$' : '-$') + Math.abs(totalPnl).toLocaleString(undefined, { maximumFractionDigits: 0 }), color: totalPnl >= 0 ? '#22c55e' : '#ef4444' },
            { label: 'Win Rate',   value: closedTrades.length ? `${winRate}%` : '—', color: winRate >= 60 ? '#22c55e' : '#f59e0b' },
            { label: 'Open Trades', value: openTrades.length, color: '#3d5af1' },
          ].map(m => (
            <div key={m.label} className="glass-card" style={{ padding: '14px 16px' }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: m.color }}>{m.value}</div>
              <div style={{ fontSize: 11, color: '#8b8fa8', fontWeight: 600, marginTop: 2 }}>{m.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* New trade button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={() => setShowForm(v => !v)}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 16px', borderRadius: 12, border: 'none', background: '#3d5af1', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
        >
          <Plus size={14} /> Open Trade
        </button>
      </div>

      {/* Open trade form */}
      {showForm && (
        <div className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 800, color: '#1a1c3a', margin: '0 0 16px' }}>New Paper Trade</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 12 }}>
            {[
              { label: 'Symbol', field: 'symbol', placeholder: 'AAPL' },
              { label: 'Entry Price', field: 'entry_price', placeholder: '150.00' },
              { label: 'Quantity', field: 'quantity', placeholder: '10' },
            ].map(f => (
              <div key={f.field}>
                <label style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', display: 'block', marginBottom: 4, textTransform: 'uppercase' }}>{f.label}</label>
                <input
                  type={f.field === 'symbol' ? 'text' : 'number'}
                  value={form[f.field as keyof TradeForm]}
                  onChange={e => setForm(p => ({ ...p, [f.field]: e.target.value }))}
                  placeholder={f.placeholder}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1.5px solid #e8e9f2', fontSize: 13, color: '#1a1c3a', outline: 'none', boxSizing: 'border-box' }}
                />
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            {(['long', 'short'] as const).map(d => (
              <button
                key={d}
                onClick={() => setForm(p => ({ ...p, direction: d }))}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 8, border: `1.5px solid ${form.direction === d ? (d === 'long' ? '#22c55e' : '#ef4444') : '#e8e9f2'}`,
                  background: form.direction === d ? (d === 'long' ? '#f0fdf4' : '#fef2f2') : '#fff',
                  color: form.direction === d ? (d === 'long' ? '#16a34a' : '#dc2626') : '#8b8fa8',
                  fontSize: 13, fontWeight: 700, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                }}
              >
                {d === 'long' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                {d === 'long' ? 'Long' : 'Short'}
              </button>
            ))}
          </div>
          <input
            type="text"
            value={form.notes}
            onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
            placeholder="Notes (optional)"
            style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1.5px solid #e8e9f2', fontSize: 13, color: '#1a1c3a', outline: 'none', marginBottom: 12, boxSizing: 'border-box' }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setShowForm(false)} style={{ flex: 1, padding: '9px 0', borderRadius: 8, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 13, fontWeight: 700, color: '#8b8fa8', cursor: 'pointer' }}>Cancel</button>
            <button onClick={openTrade} disabled={saving} style={{ flex: 2, padding: '9px 0', borderRadius: 8, border: 'none', background: '#3d5af1', fontSize: 13, fontWeight: 700, color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              {saving ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <CheckCircle2 size={14} />}
              {saving ? 'Opening…' : 'Open Trade'}
            </button>
          </div>
        </div>
      )}

      {/* Open trades */}
      {openTrades.length > 0 && (
        <div className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 800, color: '#1a1c3a', margin: '0 0 12px' }}>Open Positions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {openTrades.map(t => (
              <div key={t.id} style={{ padding: '12px 14px', borderRadius: 12, border: '1px solid #e8e9f2', display: 'flex', alignItems: 'center', gap: 12, background: '#f7f8ff' }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: t.direction === 'long' ? '#f0fdf4' : '#fef2f2', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {t.direction === 'long'
                    ? <TrendingUp size={18} color="#22c55e" />
                    : <TrendingDown size={18} color="#ef4444" />
                  }
                </div>
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 14, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>{t.symbol}</p>
                  <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>
                    {t.direction.toUpperCase()} · Qty {t.quantity} · Entry ${t.entry_price.toLocaleString()}
                  </p>
                </div>
                {closingId === t.id ? (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input
                      type="number"
                      value={closePrice}
                      onChange={e => setClosePrice(e.target.value)}
                      placeholder="Exit price"
                      style={{ width: 100, padding: '6px 8px', borderRadius: 8, border: '1.5px solid #e8e9f2', fontSize: 12 }}
                    />
                    <button onClick={() => closeTrade(t)} style={{ padding: '6px 12px', borderRadius: 8, border: 'none', background: '#22c55e', color: '#fff', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>Close</button>
                    <button onClick={() => { setClosingId(null); setClosePrice(''); }} style={{ padding: '6px 8px', borderRadius: 8, border: '1.5px solid #e8e9f2', background: '#fff', cursor: 'pointer' }}><X size={12} color="#8b8fa8" /></button>
                  </div>
                ) : (
                  <button onClick={() => setClosingId(t.id)} style={{ padding: '7px 14px', borderRadius: 8, border: 'none', background: '#3d5af1', color: '#fff', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>Close</button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Closed trades */}
      {closedTrades.length > 0 && (
        <div className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 800, color: '#1a1c3a', margin: '0 0 12px' }}>Trade History</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {closedTrades.map(t => {
              const pnl = t.pnl ?? 0;
              return (
                <div key={t.id} style={{ padding: '10px 14px', borderRadius: 10, border: '1px solid #e8e9f2', display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>
                      {t.symbol} <span style={{ fontSize: 11, color: '#8b8fa8', fontWeight: 400 }}>{t.direction}</span>
                    </p>
                    <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>
                      ${t.entry_price} → ${t.exit_price ?? '—'} · Qty {t.quantity}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: 14, fontWeight: 800, color: pnl >= 0 ? '#22c55e' : '#ef4444', margin: 0 }}>
                      {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
                    </p>
                    <p style={{ fontSize: 10, color: '#8b8fa8', margin: 0 }}>{new Date(t.closed_at ?? '').toLocaleDateString()}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {trades.length === 0 && !showForm && (
        <div style={{ padding: 40, textAlign: 'center', background: '#fff', borderRadius: 16, border: '1px solid #e8e9f2' }}>
          <BarChart3 size={28} color="#c7d2fe" style={{ margin: '0 auto 12px' }} />
          <p style={{ fontSize: 14, color: '#8b8fa8' }}>No trades yet. Open your first paper trade to get started.</p>
        </div>
      )}
    </div>
  );
}

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
  const [activeSection, setActiveSection] = useState<'lab' | 'paper'>('lab');

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

      {/* Section switcher */}
      <div className="flex gap-2 bg-slate-100 rounded-xl p-1 w-fit shrink-0">
        {[{ key: 'lab', label: 'Research Lab' }, { key: 'paper', label: 'Paper Account' }].map(s => (
          <button
            key={s.key}
            onClick={() => setActiveSection(s.key as 'lab' | 'paper')}
            className={cn(
              "px-5 py-2 rounded-lg text-xs font-bold transition-all",
              activeSection === s.key ? "bg-white text-[#1A2244] shadow-sm" : "text-slate-500 hover:text-[#1A2244]"
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {activeSection === 'paper' ? (
        <div className="flex-1 overflow-y-auto scrollbar-hide pr-1">
          <PaperTradingTab />
        </div>
      ) : (

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
      )}
    </div>
  );
}
