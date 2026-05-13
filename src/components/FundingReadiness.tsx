import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, ShieldCheck, Building2, CreditCard, Landmark, Lock,
  CheckCircle2, AlertCircle, Circle, RefreshCw, Loader2, ChevronRight,
  Info,
} from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthProvider';
import { getCreditReport, getBusinessEntity } from '../lib/db';
import { useAnalytics } from '../hooks/useAnalytics';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Snapshot {
  id: string;
  overall_score: number;
  personal_credit: number | null;
  utilization: number | null;
  tradelines: number | null;
  business_foundation: number | null;
  business_credit: number | null;
  bank_behavior: number | null;
  risk_control: number | null;
  calculated_at: string;
}

interface Factor {
  key: keyof Omit<Snapshot, 'id' | 'overall_score' | 'calculated_at'>;
  label: string;
  icon: React.ReactNode;
  weight: number; // max points
  tip: string;
  action: string;
  actionTab?: string;
}

// ─── Gauge ────────────────────────────────────────────────────────────────────

function ScoreGauge({ score }: { score: number }) {
  const radius = 72;
  const circ = Math.PI * radius; // half-circle
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const dash = pct * circ;

  const color = score >= 75 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444';
  const label = score >= 75 ? 'Strong' : score >= 50 ? 'Building' : 'Needs Work';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg width={180} height={100} viewBox="0 0 180 100">
        {/* track */}
        <path
          d="M 18 90 A 72 72 0 0 1 162 90"
          fill="none" stroke="#e8e9f2" strokeWidth={16} strokeLinecap="round"
        />
        {/* fill */}
        <path
          d="M 18 90 A 72 72 0 0 1 162 90"
          fill="none" stroke={color} strokeWidth={16} strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
        <text x={90} y={82} textAnchor="middle" fontSize={32} fontWeight={800} fill="#1a1c3a">{score}</text>
      </svg>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: -8 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: 1 }}>out of 100</span>
        <span style={{ fontSize: 11, fontWeight: 800, color, background: color + '18', padding: '2px 8px', borderRadius: 20 }}>{label}</span>
      </div>
    </div>
  );
}

// ─── Factor Row ───────────────────────────────────────────────────────────────

function FactorRow({
  factor, value, onNavigate,
}: {
  factor: Factor;
  value: number | null;
  onNavigate?: (tab: string) => void;
}) {
  const pct = value != null ? Math.round((value / factor.weight) * 100) : null;
  const statusColor = pct == null ? '#8b8fa8' : pct >= 75 ? '#22c55e' : pct >= 40 ? '#f59e0b' : '#ef4444';

  return (
    <div style={{
      background: '#fff', borderRadius: 14, padding: '16px 18px',
      border: '1px solid #e8e9f2', display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: '#f0f1ff', display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#3d5af1',
          }}>
            {factor.icon}
          </div>
          <div>
            <p style={{ fontSize: 14, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>{factor.label}</p>
            <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>{factor.tip}</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {pct == null ? (
            <span style={{ fontSize: 11, color: '#8b8fa8', fontWeight: 600 }}>Not scored</span>
          ) : (
            <span style={{ fontSize: 16, fontWeight: 800, color: statusColor }}>
              {value}/{factor.weight}
            </span>
          )}
          {factor.actionTab && (
            <button
              onClick={() => onNavigate?.(factor.actionTab!)}
              style={{
                width: 28, height: 28, borderRadius: 8, border: 'none',
                background: '#f0f1ff', color: '#3d5af1', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <ChevronRight size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 6, background: '#f0f1ff', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 99,
          width: `${pct ?? 0}%`,
          background: statusColor,
          transition: 'width 0.8s ease',
        }} />
      </div>

      {(pct == null || pct < 75) && (
        <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0, display: 'flex', alignItems: 'center', gap: 4 }}>
          <Info size={10} style={{ flexShrink: 0 }} />
          {factor.action}
        </p>
      )}
    </div>
  );
}

// ─── Factors Config ───────────────────────────────────────────────────────────

const FACTORS: Factor[] = [
  {
    key: 'personal_credit',
    label: 'Personal Credit Score',
    icon: <ShieldCheck size={18} />,
    weight: 20,
    tip: 'FICO score above 680 preferred by most lenders',
    action: 'Upload your credit report or dispute negative items to improve this score.',
    actionTab: 'credit',
  },
  {
    key: 'utilization',
    label: 'Credit Utilization',
    icon: <CreditCard size={18} />,
    weight: 15,
    tip: 'Keep utilization below 10% for best odds',
    action: 'Pay down balances or request a credit limit increase.',
    actionTab: 'credit',
  },
  {
    key: 'tradelines',
    label: 'Tradelines',
    icon: <TrendingUp size={18} />,
    weight: 15,
    tip: 'Number of positive open accounts reporting',
    action: 'Add vendor tradelines or become an authorized user.',
    actionTab: 'business-setup',
  },
  {
    key: 'business_foundation',
    label: 'Business Foundation',
    icon: <Building2 size={18} />,
    weight: 20,
    tip: 'Entity, EIN, DUNS, NAICS — all 6 fields matter',
    action: 'Complete your business entity profile to raise this factor.',
    actionTab: 'business-setup',
  },
  {
    key: 'business_credit',
    label: 'Business Credit Profile',
    icon: <Landmark size={18} />,
    weight: 15,
    tip: 'Paydex, Experian, Equifax business scores',
    action: 'Establish DUNS and apply to net-30 vendor accounts.',
    actionTab: 'business-setup',
  },
  {
    key: 'bank_behavior',
    label: 'Bank Behavior',
    icon: <CheckCircle2 size={18} />,
    weight: 10,
    tip: '3–6 months of average daily balance above $1k',
    action: 'Log your monthly bank snapshots to track your behavior score.',
    actionTab: 'bank-behavior',
  },
  {
    key: 'risk_control',
    label: 'Risk Control',
    icon: <Lock size={18} />,
    weight: 5,
    tip: 'No recent NSF, no collections, no judgments',
    action: 'Resolve any collections or judgments before applying.',
  },
];

// ─── Main Component ───────────────────────────────────────────────────────────

export function FundingReadiness({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const { user } = useAuth();
  const { emit } = useAnalytics();
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);

  const loadSnapshot = useCallback(async () => {
    if (!user) return;
    const { data } = await supabase
      .from('funding_readiness_snapshots')
      .select('*')
      .eq('user_id', user.id)
      .order('calculated_at', { ascending: false })
      .limit(1)
      .maybeSingle();
    setSnapshot(data as Snapshot | null);
    setLoading(false);
  }, [user]);

  useEffect(() => { loadSnapshot(); }, [loadSnapshot]);
  useEffect(() => {
    if (user) emit('page_view', { event_name: 'funding_readiness_viewed', feature: 'funding', page: '/funding' });
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  const recalculate = async () => {
    if (!user) return;
    setRecalculating(true);

    // Pull live data to compute scores
    const [creditRes, entityRes] = await Promise.all([
      getCreditReport(user.id),
      getBusinessEntity(user.id),
    ]);

    const credit = creditRes.data;
    const entity = entityRes.data;

    // Personal credit: 0-20 based on FICO
    const fico = credit?.score ?? 0;
    const personal_credit = fico >= 750 ? 20 : fico >= 700 ? 16 : fico >= 680 ? 12 : fico >= 620 ? 8 : fico > 0 ? 4 : null;

    // Utilization: 0-15
    const util = credit?.utilization_percent ?? null;
    const utilization = util == null ? null : util <= 10 ? 15 : util <= 20 ? 11 : util <= 30 ? 7 : 3;

    // Tradelines: infer from debt/score presence (no open_accounts field)
    const tradelines = credit ? (fico >= 680 ? 12 : fico >= 620 ? 8 : 4) : null;

    // Business foundation: 0-20 based on filled entity fields
    const entityFields = entity ? [
      entity.business_name, entity.entity_type, entity.ein,
      entity.formation_state, entity.naics_code, entity.duns_number,
    ].filter(Boolean).length : 0;
    const business_foundation = entity ? Math.round((entityFields / 6) * 20) : null;

    // Business credit: 0-15
    const [{ data: bizCredit }, { data: bankSnap }] = await Promise.all([
      supabase.from('business_credit_profiles').select('paydex_score, experian_score, equifax_score').eq('user_id', user.id).maybeSingle(),
      supabase.from('bank_behavior_snapshots').select('bank_readiness_score').eq('user_id', user.id).order('snapshot_month', { ascending: false }).limit(1).maybeSingle(),
    ]);
    const scores = [bizCredit?.paydex_score, bizCredit?.experian_score, bizCredit?.equifax_score].filter((s): s is number => s != null);
    const business_credit = scores.length === 0 ? null : Math.round((scores.reduce((a, b) => a + b, 0) / scores.length / 100) * 15);

    // Bank behavior: 0-10 from most recent bank_behavior_snapshots row
    const rawBankScore = (bankSnap as any)?.bank_readiness_score ?? null;
    const bank_behavior: number | null = rawBankScore != null ? Math.round((rawBankScore / 100) * 10) : null;

    // Risk control: use score as proxy (no negative_accounts field in schema)
    const risk_control = credit ? (fico >= 700 ? 5 : fico >= 620 ? 3 : 1) : null;

    const factors = { personal_credit, utilization, tradelines, business_foundation, business_credit, bank_behavior, risk_control };
    const summed = Object.values(factors).reduce<number>((a, v) => a + (v ?? 0), 0);
    const overall_score = Math.min(100, summed);

    const { data: saved } = await supabase
      .from('funding_readiness_snapshots')
      .insert({ user_id: user.id, overall_score, ...factors })
      .select()
      .single();

    setSnapshot(saved as Snapshot);
    setRecalculating(false);
  };

  const score = snapshot?.overall_score ?? 0;

  return (
    <div style={{ padding: 24, maxWidth: 720, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Funding Readiness</h1>
          <p style={{ fontSize: 13, color: '#8b8fa8', marginTop: 4 }}>
            Your score across 7 factors lenders evaluate before approving funding.
          </p>
        </div>
        <button
          onClick={recalculate}
          disabled={recalculating || loading}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '9px 16px', borderRadius: 12, border: 'none',
            background: '#3d5af1', color: '#fff', fontSize: 13, fontWeight: 700,
            cursor: recalculating ? 'not-allowed' : 'pointer',
            opacity: recalculating ? 0.7 : 1,
          }}
        >
          {recalculating ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <RefreshCw size={14} />}
          {recalculating ? 'Calculating…' : 'Recalculate'}
        </button>
      </div>

      {loading ? (
        <div style={{ padding: 60, textAlign: 'center' }}>
          <Loader2 size={28} color="#3d5af1" style={{ animation: 'spin 1s linear infinite', margin: '0 auto' }} />
        </div>
      ) : (
        <>
          {/* Score card */}
          <div style={{
            background: 'linear-gradient(135deg, #3d5af1 0%, #6d5af1 100%)',
            borderRadius: 20, padding: '28px 24px 20px', marginBottom: 20,
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
          }}>
            <ScoreGauge score={score} />
            {snapshot && (
              <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.6)', margin: 0 }}>
                Last calculated {new Date(snapshot.calculated_at).toLocaleDateString()}
              </p>
            )}
            {!snapshot && (
              <div style={{ marginTop: 8, padding: '10px 16px', background: 'rgba(255,255,255,0.12)', borderRadius: 12, textAlign: 'center' }}>
                <p style={{ fontSize: 13, color: '#fff', margin: 0, fontWeight: 600 }}>
                  Tap "Recalculate" to generate your first readiness score.
                </p>
              </div>
            )}
          </div>

          {/* Quick summary bar */}
          {snapshot && (
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 20,
            }}>
              {[
                { label: 'Strong', count: FACTORS.filter(f => (snapshot[f.key] ?? 0) / f.weight >= 0.75).length, color: '#22c55e' },
                { label: 'Building', count: FACTORS.filter(f => { const v = snapshot[f.key]; return v != null && v / f.weight >= 0.4 && v / f.weight < 0.75; }).length, color: '#f59e0b' },
                { label: 'Needs Work', count: FACTORS.filter(f => { const v = snapshot[f.key]; return v == null || v / f.weight < 0.4; }).length, color: '#ef4444' },
              ].map(s => (
                <div key={s.label} style={{
                  background: '#fff', borderRadius: 14, padding: '14px 16px',
                  border: '1px solid #e8e9f2', textAlign: 'center',
                }}>
                  <div style={{ fontSize: 24, fontWeight: 800, color: s.color }}>{s.count}</div>
                  <div style={{ fontSize: 11, color: '#8b8fa8', fontWeight: 600 }}>{s.label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Factor rows */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {FACTORS.map(factor => (
              <FactorRow
                key={factor.key}
                factor={factor}
                value={snapshot ? (snapshot[factor.key] as number | null) : null}
                onNavigate={onNavigate}
              />
            ))}
          </div>

          {/* Disclaimer */}
          <div style={{
            marginTop: 20, padding: '12px 16px', borderRadius: 14,
            background: '#fffbeb', border: '1px solid #fde68a',
            display: 'flex', gap: 10, alignItems: 'flex-start',
          }}>
            <AlertCircle size={16} color="#f59e0b" style={{ flexShrink: 0, marginTop: 1 }} />
            <p style={{ fontSize: 12, color: '#92400e', margin: 0, lineHeight: 1.5 }}>
              This readiness score is educational and calculated from the information you've entered.
              It does not guarantee funding approval or represent a formal lender assessment.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
