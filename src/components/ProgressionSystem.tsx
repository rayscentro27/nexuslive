import React from 'react';
import { Lock, CheckCircle2, Star, Zap, TrendingUp } from 'lucide-react';

interface Level {
  level: number;
  name: string;
  emoji: string;
  minScore: number;
  color: string;
  bgColor: string;
  perks: string[];
}

const LEVELS: Level[] = [
  { level: 1, name: 'Starter',      emoji: '🌱', minScore: 0,   color: '#6b7280', bgColor: '#f3f4f6', perks: ['Dashboard access', 'Credit upload'] },
  { level: 2, name: 'Builder',      emoji: '🔨', minScore: 25,  color: '#2563eb', bgColor: '#dbeafe', perks: ['Funding roadmap', 'Action center'] },
  { level: 3, name: 'Strategist',   emoji: '🧠', minScore: 50,  color: '#7c3aed', bgColor: '#ede9fe', perks: ['Opportunity intelligence', 'Grant finder'] },
  { level: 4, name: 'Operator',     emoji: '⚙️', minScore: 70,  color: '#0d9488', bgColor: '#ccfbf1', perks: ['Trading lab', 'AI strategy builder'] },
  { level: 5, name: 'Nexus Elite',  emoji: '🚀', minScore: 90,  color: '#d97706', bgColor: '#fef3c7', perks: ['Priority AI workforce', 'Full automation'] },
];

function computeLevel(score: number): { current: Level; next: Level | null; progress: number } {
  let current = LEVELS[0];
  for (const l of LEVELS) {
    if (score >= l.minScore) current = l;
  }
  const nextIdx = LEVELS.indexOf(current) + 1;
  const next = nextIdx < LEVELS.length ? LEVELS[nextIdx] : null;
  const progress = next
    ? Math.round(((score - current.minScore) / (next.minScore - current.minScore)) * 100)
    : 100;
  return { current, next, progress };
}

interface Props {
  score: number;
  onNavigate?: (tab: string) => void;
}

export function ProgressionSystem({ score, onNavigate }: Props) {
  const { current, next, progress } = computeLevel(score);

  return (
    <div className="glass-card" style={{ padding: 18 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', marginBottom: 2 }}>
            {current.emoji} Level {current.level} — {current.name}
          </h3>
          <p style={{ fontSize: 12, color: '#8b8fa8', margin: 0 }}>
            Readiness score: <strong style={{ color: current.color }}>{score}/100</strong>
          </p>
        </div>
        <div style={{
          background: current.bgColor,
          color: current.color,
          borderRadius: 12,
          padding: '6px 12px',
          fontSize: 13,
          fontWeight: 700,
          border: `1.5px solid ${current.color}30`,
        }}>
          L{current.level}
        </div>
      </div>

      {/* Progress bar */}
      {next && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 11, color: '#8b8fa8' }}>
              Progress to {next.emoji} {next.name}
            </span>
            <span style={{ fontSize: 11, fontWeight: 700, color: current.color }}>{progress}%</span>
          </div>
          <div style={{ height: 6, borderRadius: 6, background: '#e8e9f2', overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${progress}%`,
              background: `linear-gradient(90deg, ${current.color}, ${next.color})`,
              borderRadius: 6,
              transition: 'width 0.6s ease',
            }} />
          </div>
          <p style={{ fontSize: 11, color: '#8b8fa8', marginTop: 5 }}>
            {next.minScore - score} more points to unlock {next.name}
          </p>
        </div>
      )}

      {/* Unlocked perks */}
      <div style={{ marginBottom: 14 }}>
        <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
          Unlocked
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {current.perks.map(perk => (
            <div key={perk} style={{
              display: 'flex', alignItems: 'center', gap: 4,
              background: current.bgColor, color: current.color,
              borderRadius: 8, padding: '4px 9px', fontSize: 12, fontWeight: 600,
            }}>
              <CheckCircle2 size={11} />
              {perk}
            </div>
          ))}
        </div>
      </div>

      {/* Level ladder */}
      <div style={{ display: 'flex', gap: 4 }}>
        {LEVELS.map(l => {
          const unlocked = score >= l.minScore;
          const active = l.level === current.level;
          return (
            <div key={l.level} style={{
              flex: 1,
              height: 4,
              borderRadius: 4,
              background: unlocked ? l.color : '#e8e9f2',
              boxShadow: active ? `0 0 8px ${l.color}88` : 'none',
              transition: 'background 0.3s',
            }} />
          );
        })}
      </div>

      {/* CTA */}
      {next && (
        <button
          onClick={() => onNavigate?.('action-center')}
          style={{
            marginTop: 14,
            width: '100%',
            padding: '9px 0',
            borderRadius: 10,
            background: `linear-gradient(135deg, ${current.color}, ${next.color})`,
            color: '#fff',
            fontWeight: 700,
            fontSize: 13,
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <Zap size={14} />
          Level up to {next.name}
        </button>
      )}
      {!next && (
        <div style={{
          marginTop: 14,
          textAlign: 'center',
          padding: '10px 0',
          borderRadius: 10,
          background: '#fef3c7',
          color: '#d97706',
          fontWeight: 700,
          fontSize: 13,
        }}>
          <Star size={14} style={{ display: 'inline', marginRight: 4 }} />
          Max level reached — Operator status!
        </div>
      )}
    </div>
  );
}
