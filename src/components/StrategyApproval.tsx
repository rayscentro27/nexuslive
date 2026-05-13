import React, { useState } from 'react';
import { useAnalytics } from '../hooks/useAnalytics';
import {
  Shield, CheckCircle2, Clock, AlertTriangle, Zap,
  TrendingUp, Target, Play, Pause, X, ChevronDown, ChevronUp,
} from 'lucide-react';
import { cn } from '../lib/utils';

// ── types ─────────────────────────────────────────────────────────────────────

export interface RiskProfile {
  maxRiskPctPerTrade: number;    // % of account
  maxDailyLossPct: number;       // % of account
  maxWeeklyDrawdownPct: number;  // % of account
  maxOpenTrades: number;
  stopLossRequired: boolean;
  takeProfitRequired: boolean;
  allowedSessions: string[];
  autoPauseAfterLosses: number;  // consecutive losses before pause
  volatilityProtection: boolean;
}

export interface StrategyApprovalRecord {
  id: string;
  strategyId: string;
  strategyName: string;
  market: string;
  approvedBy: string;
  approvedAt: string;
  riskProfile: RiskProfile;
  allowedSessions: string[];
  status: 'approved' | 'paused' | 'revoked';
}

interface StrategyOption {
  id: string;
  name: string;
  market: string;
  timeframe: string;
  riskLevel: 'Low' | 'Medium' | 'High';
  aiConfidence: number;
  backtestWinRate: number;
  maxDrawdown: number;
  bestSession: string;
  edgeHealth: 'stable' | 'warning' | 'critical';
  demoReady: boolean;
}

// ── mock strategies ───────────────────────────────────────────────────────────

const STRATEGIES: StrategyOption[] = [
  {
    id: 'london_breakout',
    name: 'London Breakout',
    market: 'EUR/USD',
    timeframe: '15m',
    riskLevel: 'Medium',
    aiConfidence: 71,
    backtestWinRate: 68,
    maxDrawdown: 8,
    bestSession: 'London',
    edgeHealth: 'stable',
    demoReady: true,
  },
  {
    id: 'spy_trend',
    name: 'SPY Trend Continuation',
    market: 'SPY',
    timeframe: '5m',
    riskLevel: 'Medium',
    aiConfidence: 64,
    backtestWinRate: 61,
    maxDrawdown: 10,
    bestSession: 'NY Open',
    edgeHealth: 'stable',
    demoReady: true,
  },
  {
    id: 'btc_structure',
    name: 'BTC/ETH Trend Structure',
    market: 'BTC/USD',
    timeframe: '1h',
    riskLevel: 'High',
    aiConfidence: 58,
    backtestWinRate: 55,
    maxDrawdown: 15,
    bestSession: 'Asia / NY',
    edgeHealth: 'warning',
    demoReady: true,
  },
  {
    id: 'purple_cloud',
    name: 'Purple Cloud Trend System',
    market: 'Multi',
    timeframe: '4h',
    riskLevel: 'Low',
    aiConfidence: 74,
    backtestWinRate: 72,
    maxDrawdown: 6,
    bestSession: 'London',
    edgeHealth: 'stable',
    demoReady: true,
  },
  {
    id: 'futures_reversal',
    name: 'Futures Morning Reversal',
    market: 'ES/NQ',
    timeframe: '5m',
    riskLevel: 'High',
    aiConfidence: 61,
    backtestWinRate: 57,
    maxDrawdown: 12,
    bestSession: 'NY Open',
    edgeHealth: 'stable',
    demoReady: true,
  },
  {
    id: 'options_watchlist',
    name: 'High-IV Options Watchlist',
    market: 'Options',
    timeframe: 'Daily',
    riskLevel: 'High',
    aiConfidence: 55,
    backtestWinRate: 52,
    maxDrawdown: 18,
    bestSession: 'NY Open',
    edgeHealth: 'warning',
    demoReady: false,
  },
];

const SESSIONS = ['London', 'NY Open', 'Asia', 'Overlap', 'All Day'];

const DEFAULT_RISK: RiskProfile = {
  maxRiskPctPerTrade: 1.0,
  maxDailyLossPct: 2.0,
  maxWeeklyDrawdownPct: 5.0,
  maxOpenTrades: 3,
  stopLossRequired: true,
  takeProfitRequired: true,
  allowedSessions: ['London', 'NY Open'],
  autoPauseAfterLosses: 3,
  volatilityProtection: true,
};

// ── sub-components ────────────────────────────────────────────────────────────

function RiskBadge({ level }: { level: 'Low' | 'Medium' | 'High' }) {
  const cls = { Low: 'bg-green-50 text-green-700', Medium: 'bg-amber-50 text-amber-700', High: 'bg-red-50 text-red-600' }[level];
  return <span className={cn('px-2 py-0.5 rounded-full text-[8px] font-black uppercase tracking-wider', cls)}>{level}</span>;
}

function EdgeBadge({ health }: { health: StrategyOption['edgeHealth'] }) {
  const cls = health === 'stable' ? 'bg-green-50 text-green-700' : health === 'warning' ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-600';
  return <span className={cn('px-2 py-0.5 rounded-full text-[8px] font-black uppercase tracking-wider', cls)}>{health}</span>;
}

function StrategyCard({
  strategy,
  selected,
  onSelect,
}: {
  key?: React.Key;
  strategy: StrategyOption;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={() => strategy.demoReady && onSelect()}
      disabled={!strategy.demoReady}
      className={cn(
        'w-full text-left p-4 rounded-xl border transition-all',
        selected ? 'border-[#3d5af1] bg-[#eef0fd]' :
        strategy.demoReady ? 'border-slate-200 bg-white hover:border-[#3d5af1]/50' :
        'border-slate-100 bg-slate-50 opacity-60 cursor-not-allowed'
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <p className="font-black text-[13px] text-[#1a1c3a]">{strategy.name}</p>
          <p className="text-[9px] text-slate-400 font-medium">{strategy.market} · {strategy.timeframe} · {strategy.bestSession}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {!strategy.demoReady && <span className="text-[8px] font-black text-slate-400 uppercase">Not Ready</span>}
          <EdgeBadge health={strategy.edgeHealth} />
          <RiskBadge level={strategy.riskLevel} />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <p className="text-[8px] text-slate-400 font-medium">Backtest WR</p>
          <p className="text-sm font-black text-green-600">{strategy.backtestWinRate}%</p>
        </div>
        <div>
          <p className="text-[8px] text-slate-400 font-medium">AI Confidence</p>
          <p className="text-sm font-black text-[#8b5cf6]">{strategy.aiConfidence}%</p>
        </div>
        <div>
          <p className="text-[8px] text-slate-400 font-medium">Max Drawdown</p>
          <p className={cn('text-sm font-black', strategy.maxDrawdown <= 10 ? 'text-[#1a1c3a]' : 'text-red-500')}>
            {strategy.maxDrawdown}%
          </p>
        </div>
      </div>
      {selected && (
        <div className="mt-2 flex items-center gap-1 text-[#3d5af1]">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span className="text-[10px] font-black">Selected for approval</span>
        </div>
      )}
    </button>
  );
}

function RiskGuardrails({ risk, onChange }: { risk: RiskProfile; onChange: (r: RiskProfile) => void }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="glass-card overflow-hidden">
      <button
        className="w-full p-4 flex items-center justify-between text-left"
        onClick={() => setExpanded(e => !e)}
      >
        <div>
          <p className="font-black text-sm text-[#1a1c3a] flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#3d5af1]" />
            Risk Guardrails
          </p>
          <p className="text-[10px] text-slate-400 font-medium mt-0.5">
            {risk.maxRiskPctPerTrade}% per trade · {risk.maxDailyLossPct}% daily · {risk.maxOpenTrades} max positions
          </p>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>
      {expanded && (
        <div className="border-t border-slate-100 p-4 space-y-4">
          {[
            { label: 'Risk Per Trade', key: 'maxRiskPctPerTrade' as const, min: 0.5, max: 3.0, step: 0.5, suffix: '%' },
            { label: 'Max Daily Loss', key: 'maxDailyLossPct' as const, min: 1.0, max: 5.0, step: 0.5, suffix: '%' },
            { label: 'Max Weekly Drawdown', key: 'maxWeeklyDrawdownPct' as const, min: 2.0, max: 10.0, step: 1.0, suffix: '%' },
            { label: 'Max Open Trades', key: 'maxOpenTrades' as const, min: 1, max: 6, step: 1, suffix: '' },
            { label: 'Auto-Pause After N Losses', key: 'autoPauseAfterLosses' as const, min: 2, max: 6, step: 1, suffix: '' },
          ].map(({ label, key, min, max, step, suffix }) => (
            <div key={key}>
              <div className="flex justify-between mb-1">
                <label className="text-[10px] font-bold text-slate-600">{label}</label>
                <span className="text-[10px] font-black text-[#3d5af1]">{risk[key]}{suffix}</span>
              </div>
              <input
                type="range" min={min} max={max} step={step}
                value={risk[key] as number}
                onChange={e => onChange({ ...risk, [key]: parseFloat(e.target.value) })}
                className="w-full h-1.5 rounded-full accent-[#3d5af1]"
              />
            </div>
          ))}

          <div>
            <p className="text-[10px] font-bold text-slate-600 mb-2">Allowed Sessions</p>
            <div className="flex flex-wrap gap-1.5">
              {SESSIONS.map(s => (
                <button
                  key={s}
                  onClick={() => {
                    const has = risk.allowedSessions.includes(s);
                    onChange({ ...risk, allowedSessions: has ? risk.allowedSessions.filter(x => x !== s) : [...risk.allowedSessions, s] });
                  }}
                  className={cn(
                    'px-2.5 py-1 rounded-full text-[9px] font-black border transition-all',
                    risk.allowedSessions.includes(s)
                      ? 'bg-[#3d5af1] text-white border-[#3d5af1]'
                      : 'bg-white text-slate-500 border-slate-200'
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-4">
            {[
              { key: 'stopLossRequired' as const, label: 'SL Required' },
              { key: 'takeProfitRequired' as const, label: 'TP Required' },
              { key: 'volatilityProtection' as const, label: 'Volatility Guard' },
            ].map(({ key, label }) => (
              <label key={key} className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={risk[key] as boolean}
                  onChange={e => onChange({ ...risk, [key]: e.target.checked })}
                  className="w-3 h-3 rounded accent-[#3d5af1]"
                />
                <span className="text-[10px] font-bold text-slate-600">{label}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── main export ───────────────────────────────────────────────────────────────

export function StrategyApproval({
  onApproved,
}: {
  onApproved?: (record: StrategyApprovalRecord) => void;
}) {
  const { emit } = useAnalytics();
  const [step, setStep] = useState<'select' | 'configure' | 'confirm' | 'done'>('select');
  const [selectedId, setSelectedId] = useState<string>('london_breakout');
  const [risk, setRisk] = useState<RiskProfile>(DEFAULT_RISK);
  const [approvalRecord, setApprovalRecord] = useState<StrategyApprovalRecord | null>(null);

  const strategy = STRATEGIES.find(s => s.id === selectedId);

  function handleApprove() {
    if (!strategy) return;
    const record: StrategyApprovalRecord = {
      id: crypto.randomUUID(),
      strategyId: strategy.id,
      strategyName: strategy.name,
      market: strategy.market,
      approvedBy: 'operator',
      approvedAt: new Date().toISOString(),
      riskProfile: { ...risk },
      allowedSessions: [...risk.allowedSessions],
      status: 'approved',
    };
    setApprovalRecord(record);
    setStep('done');
    onApproved?.(record);
    emit('strategy_approved', { event_name: 'strategy_approved', feature: 'trading', metadata: { strategy_id: record.strategyId, strategy_name: record.strategyName } });
  }

  if (step === 'done' && approvalRecord) {
    return (
      <div className="p-6 space-y-4">
        <div className="text-center py-4">
          <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-3" />
          <h2 className="text-lg font-black text-[#1a1c3a]">Strategy Approved</h2>
          <p className="text-[11px] text-slate-400 font-medium mt-1">
            {approvalRecord.strategyName} is now active for demo trading
          </p>
        </div>
        <div className="glass-card p-4 space-y-2">
          <div className="grid grid-cols-2 gap-3 text-[10px]">
            <div>
              <p className="text-slate-400 font-medium">Strategy</p>
              <p className="font-black text-[#1a1c3a]">{approvalRecord.strategyName}</p>
            </div>
            <div>
              <p className="text-slate-400 font-medium">Market</p>
              <p className="font-black text-[#1a1c3a]">{approvalRecord.market}</p>
            </div>
            <div>
              <p className="text-slate-400 font-medium">Risk Per Trade</p>
              <p className="font-black text-[#3d5af1]">{approvalRecord.riskProfile.maxRiskPctPerTrade}%</p>
            </div>
            <div>
              <p className="text-slate-400 font-medium">Approved At</p>
              <p className="font-black text-[#1a1c3a]">
                {new Date(approvalRecord.approvedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
          </div>
          <div>
            <p className="text-[10px] text-slate-400 font-medium mb-1">Allowed Sessions</p>
            <div className="flex flex-wrap gap-1">
              {approvalRecord.allowedSessions.map(s => (
                <span key={s} className="px-2 py-0.5 rounded-full text-[8px] font-black bg-[#3d5af1] text-white">{s}</span>
              ))}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setStep('select'); setApprovalRecord(null); }}
            className="flex-1 py-2.5 rounded-xl border border-slate-200 text-[11px] font-bold text-slate-600"
          >
            Change Strategy
          </button>
          <button
            onClick={() => {
              setApprovalRecord(prev => prev ? { ...prev, status: 'paused' } : null);
            }}
            className="flex-1 py-2.5 rounded-xl bg-amber-50 border border-amber-200 text-[11px] font-bold text-amber-700"
          >
            Pause Strategy
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-[#1a1c3a] flex items-center gap-2">
            <Target className="w-5 h-5 text-[#3d5af1]" />
            Strategy Approval
          </h2>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
            You approve once — demo trades automatically within your limits
          </p>
        </div>
        <div className="flex gap-1">
          {(['select', 'configure', 'confirm'] as const).map((s, i) => (
            <div key={s} className={cn('w-2 h-2 rounded-full', step === s ? 'bg-[#3d5af1]' : i < ['select','configure','confirm'].indexOf(step) ? 'bg-green-400' : 'bg-slate-200')} />
          ))}
        </div>
      </div>

      {/* Step 1: Select strategy */}
      {step === 'select' && (
        <>
          <div className="space-y-2">
            {STRATEGIES.map(s => (
              <StrategyCard key={s.id} strategy={s} selected={selectedId === s.id} onSelect={() => setSelectedId(s.id)} />
            ))}
          </div>
          <button
            onClick={() => setStep('configure')}
            disabled={!strategy?.demoReady}
            className="w-full py-3 rounded-xl bg-[#3d5af1] text-white font-black text-sm flex items-center justify-center gap-2 disabled:opacity-50"
          >
            Configure Risk Guardrails
            <ChevronDown className="w-4 h-4 rotate-[-90deg]" />
          </button>
        </>
      )}

      {/* Step 2: Configure risk */}
      {step === 'configure' && (
        <>
          <div className="glass-card p-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[#3d5af1] shrink-0" />
            <span className="font-bold text-sm text-[#1a1c3a]">{strategy?.name}</span>
            <span className="text-[10px] text-slate-400 ml-auto">{strategy?.market}</span>
          </div>
          <RiskGuardrails risk={risk} onChange={setRisk} />
          <div className="flex gap-2">
            <button onClick={() => setStep('select')} className="px-4 py-2.5 rounded-xl border border-slate-200 text-[11px] font-bold text-slate-600">Back</button>
            <button onClick={() => setStep('confirm')} className="flex-1 py-2.5 rounded-xl bg-[#3d5af1] text-white font-black text-[11px]">
              Review & Approve
            </button>
          </div>
        </>
      )}

      {/* Step 3: Confirm */}
      {step === 'confirm' && (
        <>
          <div className="glass-card p-4 space-y-3">
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Approval Summary</p>
            <div className="grid grid-cols-2 gap-3 text-[10px]">
              <div><p className="text-slate-400">Strategy</p><p className="font-black text-[#1a1c3a]">{strategy?.name}</p></div>
              <div><p className="text-slate-400">Market</p><p className="font-black text-[#1a1c3a]">{strategy?.market}</p></div>
              <div><p className="text-slate-400">Risk/Trade</p><p className="font-black text-[#3d5af1]">{risk.maxRiskPctPerTrade}%</p></div>
              <div><p className="text-slate-400">Daily Limit</p><p className="font-black text-red-500">{risk.maxDailyLossPct}%</p></div>
              <div><p className="text-slate-400">Max Positions</p><p className="font-black text-[#1a1c3a]">{risk.maxOpenTrades}</p></div>
              <div><p className="text-slate-400">Auto-Pause</p><p className="font-black text-[#1a1c3a]">After {risk.autoPauseAfterLosses} losses</p></div>
            </div>
            <div>
              <p className="text-[10px] text-slate-400 font-medium mb-1">Approved Sessions</p>
              <div className="flex flex-wrap gap-1">
                {risk.allowedSessions.map(s => (
                  <span key={s} className="px-2 py-0.5 rounded-full text-[8px] font-black bg-[#3d5af1] text-white">{s}</span>
                ))}
              </div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-amber-50 border border-amber-100 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <p className="text-[10px] text-amber-700 font-medium">
              By approving, you authorize demo trading within these exact boundaries.
              The system will automatically pause if any limit is reached.
              This is demo trading only — no real money.
            </p>
          </div>

          <div className="flex gap-2">
            <button onClick={() => setStep('configure')} className="px-4 py-3 rounded-xl border border-slate-200 text-[11px] font-bold text-slate-600">Back</button>
            <button
              onClick={handleApprove}
              className="flex-1 py-3 rounded-xl bg-[#3d5af1] text-white font-black text-sm flex items-center justify-center gap-2"
            >
              <CheckCircle2 className="w-4 h-4" />
              Approve Strategy for Demo Trading
            </button>
          </div>
        </>
      )}
    </div>
  );
}
