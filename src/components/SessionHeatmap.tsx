import React, { useState } from 'react';
import { Clock, TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';
import { cn } from '../lib/utils';

// ── types ─────────────────────────────────────────────────────────────────────

interface SessionSlot {
  hour: number;          // 0–23 UTC
  winRate: number;       // 0–100
  trades: number;
  avgPips: number;
}

interface SessionBand {
  name: string;
  startHour: number;
  endHour: number;
  color: string;
  bg: string;
}

// ── constants ─────────────────────────────────────────────────────────────────

const SESSION_BANDS: SessionBand[] = [
  { name: 'Asia',     startHour: 0,  endHour: 8,  color: '#6366f1', bg: '#eef2ff' },
  { name: 'London',   startHour: 7,  endHour: 16, color: '#3d5af1', bg: '#eef0fd' },
  { name: 'NY Open',  startHour: 13, endHour: 21, color: '#00d4ff', bg: '#ecfeff' },
  { name: 'Overlap',  startHour: 13, endHour: 16, color: '#f59e0b', bg: '#fffbeb' },
];

// Mock 24-hour win rate data — swap with session_intelligence API
const MOCK_HOURLY: SessionSlot[] = Array.from({ length: 24 }, (_, h) => {
  const inLondon  = h >= 7  && h < 16;
  const inNY      = h >= 13 && h < 21;
  const inAsia    = h < 8;
  const inOverlap = h >= 13 && h < 16;

  let base = 40;
  if (inOverlap) base = 68;
  else if (inLondon) base = 62;
  else if (inNY) base = 58;
  else if (inAsia) base = 44;

  const winRate = Math.min(100, Math.max(0, base + (Math.sin(h * 0.7) * 10)));
  const trades  = inOverlap ? 12 : inLondon ? 9 : inNY ? 7 : inAsia ? 3 : 1;
  const avgPips = inOverlap ? 18 : inLondon ? 14 : inNY ? 11 : -3;

  return { hour: h, winRate: Math.round(winRate), trades, avgPips };
});

const MOCK_SESSION_STATS: Record<string, { winRate: number; trades: number; profitFactor: number; avgPips: number }> = {
  'London':  { winRate: 64, trades: 47, profitFactor: 2.1, avgPips: 14 },
  'NY Open': { winRate: 58, trades: 32, profitFactor: 1.7, avgPips: 11 },
  'Overlap': { winRate: 71, trades: 18, profitFactor: 2.6, avgPips: 19 },
  'Asia':    { winRate: 43, trades: 21, profitFactor: 0.9, avgPips: -3 },
};

// ── helpers ───────────────────────────────────────────────────────────────────

function winRateColor(wr: number): string {
  if (wr >= 65) return '#22c55e';
  if (wr >= 55) return '#f59e0b';
  if (wr >= 45) return '#94a3b8';
  return '#ef4444';
}

function winRateBg(wr: number): string {
  if (wr >= 65) return 'bg-green-500';
  if (wr >= 55) return 'bg-amber-400';
  if (wr >= 45) return 'bg-slate-300';
  return 'bg-red-400';
}

function formatHour(h: number): string {
  const ampm = h < 12 ? 'am' : 'pm';
  const display = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${display}${ampm}`;
}

// ── sub-components ────────────────────────────────────────────────────────────

function HeatCell({ slot, active, onClick }: {
  key?: React.Key;
  slot: SessionSlot;
  active: boolean;
  onClick: () => void;
}) {
  const height = Math.max(8, Math.round((slot.winRate / 100) * 48));
  return (
    <button
      onClick={onClick}
      className={cn(
        'relative flex flex-col items-center gap-0.5 group',
        active ? 'opacity-100' : 'opacity-70 hover:opacity-100'
      )}
    >
      {/* Bar */}
      <div className="w-5 bg-slate-100 rounded-t-sm flex items-end justify-center" style={{ height: 48 }}>
        <div
          className={cn('w-full rounded-t-sm transition-all duration-300', winRateBg(slot.winRate))}
          style={{ height }}
        />
      </div>
      {/* Hour label */}
      {slot.hour % 6 === 0 && (
        <span className="text-[7px] text-slate-400 font-medium">{formatHour(slot.hour)}</span>
      )}
      {/* Tooltip */}
      {active && (
        <div className="absolute -top-16 left-1/2 -translate-x-1/2 bg-[#1a1c3a] text-white rounded-lg px-2 py-1.5 text-[9px] z-10 whitespace-nowrap shadow-lg">
          <p className="font-black">{formatHour(slot.hour)} UTC</p>
          <p>WR: {slot.winRate}% · {slot.trades} trades</p>
          <p>{slot.avgPips >= 0 ? '+' : ''}{slot.avgPips} avg pips</p>
        </div>
      )}
    </button>
  );
}

function SessionBadge({ band, stats }: { key?: React.Key; band: SessionBand; stats: typeof MOCK_SESSION_STATS[string] }) {
  const isEdge = stats.winRate >= 60;
  return (
    <div className="flex items-center justify-between p-2 rounded-xl border" style={{ borderColor: band.color + '30', backgroundColor: band.bg }}>
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: band.color }} />
        <div>
          <p className="text-[10px] font-black text-[#1a1c3a]">{band.name}</p>
          <p className="text-[8px] text-slate-500">{stats.trades} trades · PF {stats.profitFactor.toFixed(1)}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-[11px] font-black" style={{ color: winRateColor(stats.winRate) }}>
          {stats.winRate}% WR
        </p>
        <p className={cn('text-[8px] font-black', stats.avgPips >= 0 ? 'text-green-600' : 'text-red-500')}>
          {stats.avgPips >= 0 ? '+' : ''}{stats.avgPips}p avg
        </p>
      </div>
    </div>
  );
}

// ── main export ───────────────────────────────────────────────────────────────

export function SessionHeatmap() {
  const [activeHour, setActiveHour] = useState<number | null>(null);
  const [showInfo, setShowInfo] = useState(false);

  const bestSession = Object.entries(MOCK_SESSION_STATS).reduce((best, [name, s]) =>
    s.trades >= 10 && s.winRate > (MOCK_SESSION_STATS[best]?.winRate ?? 0) ? name : best,
    'London'
  );

  const activeSlot = activeHour !== null ? MOCK_HOURLY[activeHour] : null;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Session Intelligence</p>
          <div className="flex items-center gap-2 mt-0.5">
            <Clock className="w-3.5 h-3.5 text-[#3d5af1]" />
            <h3 className="font-black text-sm text-[#1a1c3a]">24h Win-Rate Heatmap</h3>
          </div>
        </div>
        <button onClick={() => setShowInfo(v => !v)} className="p-1 rounded-lg border border-slate-100 text-slate-400 hover:bg-slate-50">
          <Info className="w-3.5 h-3.5" />
        </button>
      </div>

      {showInfo && (
        <div className="text-[10px] text-slate-500 bg-slate-50 rounded-xl p-3 border border-slate-100 leading-relaxed">
          Bars show historical win rate by UTC hour. Green ≥ 65%, amber 55-64%, red &lt; 45%.
          Click any bar to inspect that hour. All data from paper trading sessions — no live execution.
        </div>
      )}

      {/* Best session callout */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#eef0fd] border border-[#3d5af1]/20">
        <TrendingUp className="w-3.5 h-3.5 text-[#3d5af1] shrink-0" />
        <p className="text-[10px] font-black text-[#1a1c3a]">
          Best edge: <span className="text-[#3d5af1]">{bestSession}</span>
          {' '}— {MOCK_SESSION_STATS[bestSession].winRate}% WR · PF {MOCK_SESSION_STATS[bestSession].profitFactor.toFixed(1)}
        </p>
      </div>

      {/* Heatmap grid */}
      <div className="glass-card p-4">
        {/* Session band labels */}
        <div className="flex gap-2 flex-wrap mb-3">
          {SESSION_BANDS.map(band => (
            <div key={band.name} className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: band.color }} />
              <span className="text-[8px] text-slate-500 font-medium">
                {band.name} {band.startHour.toString().padStart(2,'0')}–{band.endHour.toString().padStart(2,'0')}z
              </span>
            </div>
          ))}
        </div>

        {/* Bars */}
        <div className="flex items-end gap-0.5 overflow-x-auto pb-1">
          {MOCK_HOURLY.map(slot => (
            <HeatCell
              key={slot.hour}
              slot={slot}
              active={activeHour === slot.hour}
              onClick={() => setActiveHour(activeHour === slot.hour ? null : slot.hour)}
            />
          ))}
        </div>

        {/* Win rate legend */}
        <div className="flex items-center gap-3 mt-3 pt-3 border-t border-slate-50">
          {[
            { label: '≥ 65%', cls: 'bg-green-500' },
            { label: '55–64%', cls: 'bg-amber-400' },
            { label: '45–54%', cls: 'bg-slate-300' },
            { label: '< 45%', cls: 'bg-red-400' },
          ].map(({ label, cls }) => (
            <div key={label} className="flex items-center gap-1">
              <div className={cn('w-2.5 h-2.5 rounded-sm', cls)} />
              <span className="text-[8px] text-slate-400 font-medium">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Active hour detail */}
      {activeSlot && (
        <div className="glass-card p-3 border border-[#3d5af1]/20">
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-wider mb-2">
            {formatHour(activeSlot.hour)} UTC Detail
          </p>
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: 'Win Rate', value: `${activeSlot.winRate}%`, color: winRateColor(activeSlot.winRate) },
              { label: 'Trades', value: activeSlot.trades.toString(), color: '#1a1c3a' },
              { label: 'Avg Pips', value: `${activeSlot.avgPips >= 0 ? '+' : ''}${activeSlot.avgPips}`, color: activeSlot.avgPips >= 0 ? '#22c55e' : '#ef4444' },
            ].map(({ label, value, color }) => (
              <div key={label} className="text-center p-2 bg-slate-50 rounded-lg">
                <p className="text-[8px] text-slate-400 font-medium mb-0.5">{label}</p>
                <p className="text-sm font-black" style={{ color }}>{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Session stats */}
      <div>
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-2">Per-Session Breakdown</p>
        <div className="space-y-2">
          {SESSION_BANDS.map(band => (
            <SessionBadge key={band.name} band={band} stats={MOCK_SESSION_STATS[band.name]} />
          ))}
        </div>
      </div>

      {/* Edge decay warning — shown when worst session trades drift negative */}
      {MOCK_SESSION_STATS['Asia'].winRate < 50 && (
        <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-50 border border-amber-200">
          <TrendingDown className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-[10px] font-black text-amber-800">Asia session edge decay detected</p>
            <p className="text-[9px] text-amber-600 font-medium">
              Win rate {MOCK_SESSION_STATS['Asia'].winRate}% — below 50% threshold.
              Consider pausing strategies during this session.
            </p>
          </div>
        </div>
      )}

      {/* Safety footer */}
      <p className="text-[9px] text-center text-slate-300 font-medium">
        Paper trading data only · NEXUS_DRY_RUN=true · No live execution
      </p>
    </div>
  );
}
