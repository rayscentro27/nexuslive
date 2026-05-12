import React, { useState } from 'react';
import {
  Shield, Zap, CheckCircle2, ChevronRight, Activity,
  TrendingUp, DollarSign, BarChart3, AlertCircle, Lock,
} from 'lucide-react';
import { cn } from '../lib/utils';

// ── types ─────────────────────────────────────────────────────────────────────

interface DemoProvider {
  id: string;
  name: string;
  description: string;
  available: boolean;
  comingSoon?: boolean;
  balance?: number;
}

interface DemoAccount {
  provider: string;
  balance: number;
  equity: number;
  buyingPower: number;
  activeStrategy: string | null;
  connectedAt: string;
}

// ── constants ─────────────────────────────────────────────────────────────────

const PROVIDERS: DemoProvider[] = [
  {
    id: 'nexus_sim',
    name: 'Nexus Simulated Account',
    description: 'Built-in paper trading engine. No signup required. Start immediately.',
    available: true,
    balance: 10_000,
  },
  {
    id: 'oanda_demo',
    name: 'OANDA Demo Account',
    description: 'Connect your OANDA practice account (API key required).',
    available: false,
    comingSoon: true,
  },
  {
    id: 'tradingview_paper',
    name: 'TradingView Paper',
    description: 'Sync paper trades from TradingView (webhook integration).',
    available: false,
    comingSoon: true,
  },
  {
    id: 'ninjatrader_sim',
    name: 'NinjaTrader Sim',
    description: 'NinjaTrader simulation account integration.',
    available: false,
    comingSoon: true,
  },
  {
    id: 'webull_paper',
    name: 'Webull Paper',
    description: 'Webull paper trading account sync.',
    available: false,
    comingSoon: true,
  },
];

// ── sub-components ────────────────────────────────────────────────────────────

function ProviderCard({
  provider,
  selected,
  onSelect,
}: {
  key?: React.Key;
  provider: DemoProvider;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={() => provider.available && onSelect()}
      disabled={!provider.available}
      className={cn(
        'w-full text-left p-4 rounded-xl border transition-all',
        selected
          ? 'border-[#3d5af1] bg-[#eef0fd]'
          : provider.available
          ? 'border-slate-200 bg-white hover:border-[#3d5af1]/50 hover:bg-slate-50'
          : 'border-slate-100 bg-slate-50 cursor-not-allowed opacity-60'
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn(
          'w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
          selected ? 'bg-[#3d5af1]' : provider.available ? 'bg-slate-100' : 'bg-slate-100'
        )}>
          {provider.available
            ? <Zap className={cn('w-4 h-4', selected ? 'text-white' : 'text-slate-500')} />
            : <Lock className="w-4 h-4 text-slate-300" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-sm text-[#1a1c3a]">{provider.name}</span>
            {provider.comingSoon && (
              <span className="px-1.5 py-0.5 rounded text-[8px] font-black uppercase bg-amber-50 text-amber-600">
                Coming Soon
              </span>
            )}
            {provider.available && (
              <span className="px-1.5 py-0.5 rounded text-[8px] font-black uppercase bg-green-50 text-green-600">
                Available
              </span>
            )}
          </div>
          <p className="text-[10px] text-slate-500 font-medium mt-0.5 leading-relaxed">
            {provider.description}
          </p>
        </div>
        {selected && <CheckCircle2 className="w-4 h-4 text-[#3d5af1] shrink-0 mt-0.5" />}
      </div>
    </button>
  );
}

function ConnectedBadge({ account }: { account: DemoAccount }) {
  return (
    <div className="space-y-3">
      {/* Demo mode banner */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-50 border border-blue-100">
        <Shield className="w-3.5 h-3.5 text-blue-500 shrink-0" />
        <p className="text-[10px] text-blue-700 font-black uppercase tracking-wider">
          Demo Mode Only — No Real Money Trades
        </p>
      </div>

      {/* Account stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="glass-card p-3 text-center">
          <p className="text-[8px] font-black text-slate-400 uppercase tracking-wider mb-1">Balance</p>
          <p className="text-lg font-black text-[#1a1c3a]">${account.balance.toLocaleString()}</p>
        </div>
        <div className="glass-card p-3 text-center">
          <p className="text-[8px] font-black text-slate-400 uppercase tracking-wider mb-1">Equity</p>
          <p className="text-lg font-black text-green-600">${account.equity.toLocaleString()}</p>
        </div>
        <div className="glass-card p-3 text-center">
          <p className="text-[8px] font-black text-slate-400 uppercase tracking-wider mb-1">Buying Power</p>
          <p className="text-lg font-black text-[#3d5af1]">${account.buyingPower.toLocaleString()}</p>
        </div>
      </div>

      <div className="glass-card p-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-[#00d4ff] animate-pulse" />
          <span className="text-[10px] font-bold text-slate-600">
            {account.activeStrategy ? `Active: ${account.activeStrategy}` : 'No strategy active'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          <span className="text-[9px] text-green-600 font-bold">LIVE DEMO</span>
        </div>
      </div>
    </div>
  );
}

// ── main export ───────────────────────────────────────────────────────────────

export function DemoAccountConnect({
  onConnected,
}: {
  onConnected?: (account: DemoAccount) => void;
}) {
  const [selectedProvider, setSelectedProvider] = useState<string>('nexus_sim');
  const [connecting, setConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [account, setAccount] = useState<DemoAccount | null>(null);

  const provider = PROVIDERS.find(p => p.id === selectedProvider);

  async function handleConnect() {
    if (!provider?.available || connecting) return;
    setConnecting(true);

    // Simulate connection handshake (replace with real API call)
    await new Promise(r => setTimeout(r, 1200));

    const demoAccount: DemoAccount = {
      provider: selectedProvider,
      balance: provider.balance ?? 10_000,
      equity: (provider.balance ?? 10_000) * 1.0,
      buyingPower: (provider.balance ?? 10_000) * 30, // 30:1 leverage for forex
      activeStrategy: null,
      connectedAt: new Date().toISOString(),
    };

    setAccount(demoAccount);
    setConnected(true);
    setConnecting(false);
    onConnected?.(demoAccount);
  }

  if (connected && account) {
    return (
      <div className="p-6 space-y-4">
        <div>
          <h2 className="text-lg font-black text-[#1a1c3a] flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[#3d5af1]" />
            Demo Account Connected
          </h2>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            {PROVIDERS.find(p => p.id === account.provider)?.name}
          </p>
        </div>
        <ConnectedBadge account={account} />
        <button
          onClick={() => { setConnected(false); setAccount(null); }}
          className="w-full py-2 rounded-xl border border-slate-200 text-[11px] font-bold text-slate-500 hover:bg-slate-50 transition-colors"
        >
          Disconnect Demo Account
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-black text-[#1a1c3a] flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-[#3d5af1]" />
          Connect Demo Account
        </h2>
        <p className="text-[11px] text-slate-400 font-medium mt-0.5">
          Paper trading only — no real money at any point
        </p>
      </div>

      {/* Safety reminder */}
      <div className="flex items-center gap-2 p-3 rounded-xl bg-blue-50 border border-blue-100">
        <Shield className="w-4 h-4 text-blue-500 shrink-0" />
        <p className="text-[10px] text-blue-700 font-medium">
          Demo Mode Only — No Real Money Trades. All results are simulated.
        </p>
      </div>

      {/* Provider selection */}
      <div className="space-y-2">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Select Platform</p>
        {PROVIDERS.map(p => (
          <ProviderCard
            key={p.id}
            provider={p}
            selected={selectedProvider === p.id}
            onSelect={() => setSelectedProvider(p.id)}
          />
        ))}
      </div>

      {/* Connect button */}
      <button
        onClick={handleConnect}
        disabled={!provider?.available || connecting}
        className={cn(
          'w-full py-3 rounded-xl font-black text-sm flex items-center justify-center gap-2 transition-all',
          provider?.available && !connecting
            ? 'bg-[#3d5af1] text-white hover:opacity-90 active:scale-[0.98]'
            : 'bg-slate-100 text-slate-400 cursor-not-allowed'
        )}
      >
        {connecting ? (
          <>
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Connecting...
          </>
        ) : (
          <>
            <Zap className="w-4 h-4" />
            Connect {provider?.available ? provider.name : 'Demo Account'}
            <ChevronRight className="w-4 h-4" />
          </>
        )}
      </button>

      <p className="text-center text-[9px] text-slate-400 font-medium">
        TRADING_LIVE_EXECUTION_ENABLED=false · Simulated trades only
      </p>
    </div>
  );
}
