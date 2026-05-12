import React, { useState, useEffect } from 'react';
import {
  ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2,
  Zap, TrendingDown, Activity, RefreshCw, Clock,
} from 'lucide-react';
import { cn } from '../lib/utils';

// ── types ─────────────────────────────────────────────────────────────────────

interface RiskState {
  accountHealth: number;           // 0-100
  dailyLossUsed: number;           // %
  dailyLossLimit: number;          // %
  weeklyDrawdown: number;          // %
  weeklyDrawdownLimit: number;     // %
  openPositions: number;
  maxPositions: number;
  circuitBreakers: CircuitBreakerEvent[];
  riskScore: number;               // 0-100
  riskLabel: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  newsBlackout: boolean;
  sessionActive: boolean;
  currentSession: string;
}

interface CircuitBreakerEvent {
  id: string;
  triggerType: string;
  triggeredAt: string;
  resolved: boolean;
  notes?: string;
}

interface RiskLayer {
  id: number;
  name: string;
  status: 'pass' | 'block' | 'warn';
  detail: string;
}

// ── mock state — replace with live Supabase/API query ──────────────────────────

const MOCK_RISK: RiskState = {
  accountHealth: 78,
  dailyLossUsed: 0.9,
  dailyLossLimit: 2.0,
  weeklyDrawdown: 1.2,
  weeklyDrawdownLimit: 5.0,
  openPositions: 2,
  maxPositions: 4,
  circuitBreakers: [],
  riskScore: 22,
  riskLabel: 'LOW',
  newsBlackout: false,
  sessionActive: true,
  currentSession: 'London',
};

const MOCK_LAYERS: RiskLayer[] = [
  { id: 1,  name: 'Market Filter',   status: 'pass',  detail: 'EUR/USD, GBP/USD approved' },
  { id: 2,  name: 'Session Filter',  status: 'pass',  detail: 'London session — active' },
  { id: 3,  name: 'News Filter',     status: 'pass',  detail: 'No high-impact news in 30min' },
  { id: 4,  name: 'Volatility',      status: 'pass',  detail: 'ATR within normal range' },
  { id: 5,  name: 'Position Check',  status: 'pass',  detail: '2 of 4 positions used' },
  { id: 6,  name: 'Daily P&L',       status: 'pass',  detail: '-0.9% of -2.0% limit' },
  { id: 7,  name: 'Weekly Drawdown', status: 'pass',  detail: '-1.2% of -5.0% limit' },
  { id: 8,  name: 'Streak Check',    status: 'pass',  detail: 'No consecutive loss streak' },
  { id: 9,  name: 'Slippage Check',  status: 'pass',  detail: 'Paper mode — simulated' },
  { id: 10, name: 'Circuit Breaker', status: 'pass',  detail: 'No breaker active' },
];

// ── sub-components ────────────────────────────────────────────────────────────

function HealthGauge({ value }: { value: number }) {
  const color =
    value >= 70 ? '#22c55e' :
    value >= 40 ? '#f59e0b' : '#ef4444';
  const label =
    value >= 70 ? 'NOMINAL' :
    value >= 40 ? 'ELEVATED' : 'CRITICAL';

  return (
    <div className="glass-card p-5">
      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3">Account Health</p>
      <div className="flex items-end gap-3 mb-3">
        <span className="text-4xl font-black" style={{ color }}>{value}%</span>
        <span className="text-sm font-black pb-1" style={{ color }}>{label}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000"
          style={{ width: `${value}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function RiskScoreBadge({ score, label }: { score: number; label: RiskState['riskLabel'] }) {
  const map = {
    LOW:      { color: '#22c55e', bg: 'bg-green-50', border: 'border-green-200' },
    MODERATE: { color: '#f59e0b', bg: 'bg-amber-50', border: 'border-amber-200' },
    HIGH:     { color: '#ef4444', bg: 'bg-red-50',   border: 'border-red-200' },
    CRITICAL: { color: '#ef4444', bg: 'bg-red-50',   border: 'border-red-200' },
  };
  const { color, bg, border } = map[label];
  return (
    <div className={cn('glass-card p-5 border', border, bg)}>
      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3">Risk Score</p>
      <div className="flex items-end gap-3 mb-3">
        <span className="text-4xl font-black" style={{ color }}>{score}</span>
        <span className="text-sm font-black pb-1" style={{ color }}>{label}</span>
      </div>
      <p className="text-[10px] text-slate-500 font-medium">
        {label === 'LOW' && 'Trade approved at full size'}
        {label === 'MODERATE' && 'Trade approved at reduced size'}
        {label === 'HIGH' && 'Requires AI confirmation'}
        {label === 'CRITICAL' && 'Trade blocked — circuit breaker active'}
      </p>
    </div>
  );
}

function LimitBar({ label, used, limit, color }: { label: string; used: number; limit: number; color: string }) {
  const pct = Math.min(100, (used / limit) * 100);
  const proximityColor =
    pct >= 80 ? '#ef4444' :
    pct >= 60 ? '#f59e0b' : color;

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-[10px] font-bold text-slate-600">{label}</span>
        <span className="text-[10px] font-black" style={{ color: proximityColor }}>
          {used.toFixed(1)}% <span className="text-slate-400 font-medium">of {limit}%</span>
        </span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: proximityColor }}
        />
      </div>
    </div>
  );
}

function LayerStatus({ layers }: { layers: RiskLayer[] }) {
  const [expanded, setExpanded] = useState(false);
  const blocking = layers.filter(l => l.status === 'block').length;
  const warning  = layers.filter(l => l.status === 'warn').length;

  return (
    <div className="glass-card overflow-hidden">
      <button
        className="w-full p-5 flex items-center justify-between text-left"
        onClick={() => setExpanded(e => !e)}
      >
        <div>
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Risk Engine Layers</p>
          <div className="flex items-center gap-2">
            <span className="text-sm font-black text-[#1a1c3a]">10 Layers Active</span>
            {blocking === 0 && warning === 0 && (
              <span className="flex items-center gap-1 text-green-600 text-[10px] font-bold">
                <CheckCircle2 className="w-3.5 h-3.5" /> All clear
              </span>
            )}
            {blocking > 0 && (
              <span className="flex items-center gap-1 text-red-500 text-[10px] font-bold">
                <ShieldAlert className="w-3.5 h-3.5" /> {blocking} blocking
              </span>
            )}
            {warning > 0 && (
              <span className="flex items-center gap-1 text-amber-500 text-[10px] font-bold">
                <AlertTriangle className="w-3.5 h-3.5" /> {warning} warning
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-0.5">
          {layers.map(l => (
            <div
              key={l.id}
              className="w-2 h-4 rounded-sm"
              style={{
                backgroundColor:
                  l.status === 'pass'  ? '#22c55e' :
                  l.status === 'warn'  ? '#f59e0b' : '#ef4444',
              }}
            />
          ))}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-100">
          {layers.map(l => (
            <div key={l.id} className="flex items-center gap-3 px-5 py-2.5 border-b border-slate-50 last:border-0">
              <div
                className="w-1.5 h-1.5 rounded-full shrink-0"
                style={{
                  backgroundColor:
                    l.status === 'pass'  ? '#22c55e' :
                    l.status === 'warn'  ? '#f59e0b' : '#ef4444',
                }}
              />
              <span className="text-[10px] font-bold text-slate-600 w-32 shrink-0">
                [{l.id}] {l.name}
              </span>
              <span className="text-[10px] text-slate-400 font-medium">{l.detail}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CircuitBreakerPanel({ events }: { events: CircuitBreakerEvent[] }) {
  const active = events.filter(e => !e.resolved);

  if (active.length === 0) {
    return (
      <div className="glass-card p-5">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3">Circuit Breakers</p>
        <div className="flex items-center gap-2 text-green-600">
          <ShieldCheck className="w-5 h-5" />
          <span className="font-bold text-sm">None active — all clear</span>
        </div>
        <p className="text-[10px] text-slate-400 font-medium mt-2">
          Circuit breakers fire unconditionally and require manual operator reset.
          No automated reset is possible.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card border border-red-200 bg-red-50 p-5">
      <p className="text-[9px] font-black text-red-400 uppercase tracking-widest mb-3">
        🚨 Circuit Breaker Active
      </p>
      {active.map(ev => (
        <div key={ev.id} className="space-y-2">
          <p className="text-sm font-black text-red-700">{ev.triggerType}</p>
          <p className="text-[10px] text-red-500 font-medium">
            Fired: {new Date(ev.triggeredAt).toLocaleString()}
          </p>
          {ev.notes && (
            <p className="text-[10px] text-red-600">{ev.notes}</p>
          )}
          <div className="p-3 bg-white rounded-lg border border-red-200 text-[10px] text-red-700 font-medium">
            No new entries accepted. Open positions maintained. Operator manual reset required.
          </div>
        </div>
      ))}
    </div>
  );
}

// ── main export ───────────────────────────────────────────────────────────────

export function RiskControlCenter() {
  const [risk] = useState<RiskState>(MOCK_RISK);
  const [layers] = useState<RiskLayer[]>(MOCK_LAYERS);
  const [lastUpdate] = useState(new Date());

  return (
    <div className="p-6 space-y-4">
      {/* title */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-[#1a1c3a] flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-[#3d5af1]" />
            Risk Control Center
          </h2>
          <p className="text-[11px] text-slate-400 font-medium mt-0.5 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Updated {lastUpdate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={cn(
            'px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5',
            risk.sessionActive ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-500'
          )}>
            <Activity className="w-3 h-3" />
            {risk.sessionActive ? risk.currentSession : 'Closed'}
          </div>
          {risk.newsBlackout && (
            <div className="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-amber-50 text-amber-700 flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3" />
              News Blackout
            </div>
          )}
        </div>
      </div>

      {/* top gauge row */}
      <div className="grid grid-cols-2 gap-4">
        <HealthGauge value={risk.accountHealth} />
        <RiskScoreBadge score={risk.riskScore} label={risk.riskLabel} />
      </div>

      {/* circuit breakers */}
      <CircuitBreakerPanel events={risk.circuitBreakers} />

      {/* limit bars */}
      <div className="glass-card p-5 space-y-4">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Risk Utilization</p>
        <LimitBar
          label="Daily Loss"
          used={risk.dailyLossUsed}
          limit={risk.dailyLossLimit}
          color="#3d5af1"
        />
        <LimitBar
          label="Weekly Drawdown"
          used={risk.weeklyDrawdown}
          limit={risk.weeklyDrawdownLimit}
          color="#3d5af1"
        />
        <div className="flex justify-between items-center pt-1">
          <span className="text-[10px] font-bold text-slate-600">Open Positions</span>
          <div className="flex gap-1">
            {Array.from({ length: risk.maxPositions }).map((_, i) => (
              <div
                key={i}
                className={cn('w-5 h-5 rounded-md', i < risk.openPositions ? 'bg-[#3d5af1]' : 'bg-slate-100')}
              />
            ))}
            <span className="text-[10px] text-slate-400 font-medium ml-1 self-center">
              {risk.openPositions}/{risk.maxPositions}
            </span>
          </div>
        </div>
      </div>

      {/* layer status */}
      <LayerStatus layers={layers} />

      {/* hardcoded safety footer */}
      <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider mb-2">Hardcoded Limits — Cannot Be Overridden</p>
        <div className="grid grid-cols-2 gap-1">
          {[
            'No trades during news blackout',
            'No leverage beyond approved limit',
            'No execution outside approved sessions',
            'Circuit breaker override requires operator',
            'No automated circuit breaker reset',
            'No position size increase mid-trade',
          ].map(r => (
            <div key={r} className="flex items-start gap-1.5">
              <Zap className="w-2.5 h-2.5 text-[#3d5af1] shrink-0 mt-0.5" />
              <span className="text-[9px] text-slate-500 font-medium leading-tight">{r}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
