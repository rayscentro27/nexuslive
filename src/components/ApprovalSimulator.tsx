import React, { useState, useEffect } from 'react';
import { TrendingUp, AlertCircle, CheckCircle2, ArrowRight, Loader2, Info } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthProvider';
import { getCreditReport } from '../lib/db';

interface LenderRule {
  id: string;
  lender_name: string;
  product_type: string;
  min_score: number | null;
  max_utilization: number | null;
  estimated_limit_min: number | null;
  estimated_limit_max: number | null;
}

interface SimResult {
  lender: LenderRule;
  approval_odds: number;
  limit_range: string;
  risk_factors: string[];
  improvements: string[];
}

function oddsColor(odds: number) {
  if (odds >= 75) return { color: '#22c55e', bg: '#f0fdf4' };
  if (odds >= 50) return { color: '#f59e0b', bg: '#fffbeb' };
  return { color: '#ef4444', bg: '#fef2f2' };
}

function OddsGauge({ value }: { value: number }) {
  const { color } = oddsColor(value);
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (value / 100) * circumference;
  return (
    <div style={{ position: 'relative', width: 100, height: 100 }}>
      <svg viewBox="0 0 100 100" style={{ width: 100, height: 100, transform: 'rotate(-90deg)' }}>
        <circle cx="50" cy="50" r="40" fill="none" stroke="#e8e9f2" strokeWidth="10" />
        <circle cx="50" cy="50" r="40" fill="none" stroke={color} strokeWidth="10"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.5s ease' }} strokeLinecap="round" />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: 22, fontWeight: 800, color }}>{value}%</span>
        <span style={{ fontSize: 10, color: '#8b8fa8', fontWeight: 600 }}>odds</span>
      </div>
    </div>
  );
}

export function ApprovalSimulator({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const { user } = useAuth();
  const [lenders, setLenders] = useState<LenderRule[]>([]);
  const [results, setResults] = useState<SimResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [simulated, setSimulated] = useState(false);
  const [creditScore, setCreditScore] = useState<number | null>(null);
  const [utilization, setUtilization] = useState<number | null>(null);

  useEffect(() => {
    const fetchAll = async () => {
      const [{ data: lr }, reportResult] = await Promise.all([
        supabase.from('lender_rules').select('*').eq('is_active', true),
        user ? getCreditReport(user.id) : Promise.resolve({ data: null, error: null }),
      ]);
      setLenders((lr ?? []) as LenderRule[]);
      setCreditScore(reportResult.data?.score ?? null);
      setUtilization(reportResult.data?.utilization_percent ?? null);
      setLoading(false);
    };
    fetchAll();
  }, [user]);

  const runSimulation = async () => {
    const score = creditScore ?? 680;
    const util = utilization ?? 30;

    const simResults: SimResult[] = lenders.map(lender => {
      let odds = 50;
      const factors: string[] = [];
      const improvements: string[] = [];

      if (lender.min_score) {
        if (score >= lender.min_score + 50) odds += 25;
        else if (score >= lender.min_score) odds += 10;
        else {
          odds -= 30;
          factors.push(`Score ${score} below minimum ${lender.min_score}`);
          improvements.push(`Improve credit score to ${lender.min_score}+`);
        }
      }

      if (lender.max_utilization) {
        if (util <= 10) odds += 15;
        else if (util <= lender.max_utilization) odds += 5;
        else {
          odds -= 20;
          factors.push(`Utilization ${util}% above max ${lender.max_utilization}%`);
          improvements.push(`Reduce utilization below ${lender.max_utilization}%`);
        }
      }

      odds = Math.max(5, Math.min(95, odds));

      const limitMin = lender.estimated_limit_min;
      const limitMax = lender.estimated_limit_max;
      const limitRange = limitMin && limitMax
        ? `$${(limitMin / 1000).toFixed(0)}k – $${(limitMax / 1000).toFixed(0)}k`
        : 'Varies';

      return { lender, approval_odds: odds, limit_range: limitRange, risk_factors: factors, improvements };
    });

    simResults.sort((a, b) => b.approval_odds - a.approval_odds);
    setResults(simResults);
    setSimulated(true);

    // Persist each result to approval_simulations
    if (user) {
      const rows = simResults.map(r => ({
        user_id: user.id,
        lender_name: r.lender.lender_name,
        product_type: r.lender.product_type,
        approval_odds: r.approval_odds,
        estimated_limit_min: r.lender.estimated_limit_min,
        estimated_limit_max: r.lender.estimated_limit_max,
        credit_score_used: score,
        utilization_used: util,
        risk_factors: r.risk_factors,
        improvements: r.improvements,
      }));
      await supabase.from('approval_simulations').insert(rows);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
        <Loader2 size={24} color="#3d5af1" style={{ animation: 'spin 1s linear infinite' }} />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Approval Simulator</h2>
        <p style={{ fontSize: 14, color: '#8b8fa8', marginTop: 4 }}>
          See estimated approval odds for various lenders based on your credit profile.
        </p>
      </div>

      {/* Disclaimer */}
      <div style={{ padding: '12px 16px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 12, marginBottom: 20, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
        <AlertCircle size={16} color="#f59e0b" style={{ flexShrink: 0, marginTop: 1 }} />
        <p style={{ fontSize: 12, color: '#92400e', margin: 0, lineHeight: 1.5 }}>
          <strong>Educational Estimate Only.</strong> Approval odds are estimates based on general lender criteria and your current credit profile. They are not actual pre-approvals and do not guarantee approval. Apply only when you believe you are ready.
        </p>
      </div>

      {/* Profile summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
        <div className="glass-card" style={{ padding: 16 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', margin: '0 0 4px', textTransform: 'uppercase' }}>Your Credit Score</p>
          <p style={{ fontSize: 28, fontWeight: 800, color: creditScore ? '#1a1c3a' : '#c7d2fe', margin: 0 }}>
            {creditScore ?? 'No report'}
          </p>
          {!creditScore && <p style={{ fontSize: 12, color: '#8b8fa8', margin: '4px 0 0' }}>Upload credit report to simulate</p>}
        </div>
        <div className="glass-card" style={{ padding: 16 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', margin: '0 0 4px', textTransform: 'uppercase' }}>Utilization</p>
          <p style={{ fontSize: 28, fontWeight: 800, color: utilization !== null ? (utilization <= 10 ? '#22c55e' : utilization <= 30 ? '#f59e0b' : '#ef4444') : '#c7d2fe', margin: 0 }}>
            {utilization !== null ? `${utilization}%` : '—'}
          </p>
          {utilization !== null && utilization > 30 && (
            <p style={{ fontSize: 12, color: '#ef4444', margin: '4px 0 0' }}>High — reduce to &lt;30% for better odds</p>
          )}
        </div>
      </div>

      {!simulated ? (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <TrendingUp size={40} color="#c7d2fe" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: 18, fontWeight: 700, color: '#1a1c3a', marginBottom: 8 }}>Run Your Simulation</h3>
          <p style={{ fontSize: 14, color: '#8b8fa8', marginBottom: 24 }}>
            We'll estimate your approval odds across {lenders.length} lender products.
          </p>
          <button
            onClick={runSimulation}
            style={{
              padding: '14px 32px', borderRadius: 14, border: 'none',
              background: 'linear-gradient(135deg, #3d5af1, #6366f1)',
              color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer',
              boxShadow: '0 4px 16px rgba(61,90,241,0.3)',
              display: 'inline-flex', alignItems: 'center', gap: 10,
            }}
          >
            <TrendingUp size={18} /> Run Simulation
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: 17, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Simulation Results</h3>
            <button onClick={runSimulation} style={{ padding: '7px 14px', borderRadius: 10, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 12, fontWeight: 700, color: '#3d5af1', cursor: 'pointer' }}>
              Re-run
            </button>
          </div>

          {results.map(result => {
            const { color, bg } = oddsColor(result.approval_odds);
            return (
              <div key={result.lender.id} className="glass-card" style={{ padding: 20, display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                <OddsGauge value={result.approval_odds} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <h4 style={{ fontSize: 16, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>{result.lender.lender_name}</h4>
                    <span style={{ padding: '3px 10px', borderRadius: 20, background: bg, color, fontSize: 12, fontWeight: 700 }}>
                      {result.approval_odds >= 75 ? 'High' : result.approval_odds >= 50 ? 'Medium' : 'Low'} Chance
                    </span>
                  </div>
                  <p style={{ fontSize: 13, color: '#8b8fa8', margin: '0 0 8px' }}>{result.lender.product_type} · Est. {result.limit_range}</p>

                  {result.risk_factors.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      {result.risk_factors.map((f, i) => (
                        <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 3 }}>
                          <AlertCircle size={12} color="#ef4444" />
                          <span style={{ fontSize: 12, color: '#dc2626' }}>{f}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {result.improvements.length > 0 && (
                    <div>
                      {result.improvements.map((imp, i) => (
                        <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 3 }}>
                          <TrendingUp size={12} color="#22c55e" />
                          <span style={{ fontSize: 12, color: '#16a34a' }}>{imp}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {result.risk_factors.length === 0 && (
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 10 }}>
                      <CheckCircle2 size={12} color="#22c55e" />
                      <span style={{ fontSize: 12, color: '#16a34a' }}>Profile meets basic requirements</span>
                    </div>
                  )}
                  <button
                    onClick={() => onNavigate?.('funding')}
                    style={{
                      marginTop: 8, padding: '7px 14px', borderRadius: 10, border: 'none',
                      background: result.approval_odds >= 50 ? '#3d5af1' : '#f1f5f9',
                      color: result.approval_odds >= 50 ? '#fff' : '#8b8fa8',
                      fontSize: 12, fontWeight: 700, cursor: 'pointer',
                      display: 'inline-flex', alignItems: 'center', gap: 6,
                    }}
                  >
                    Apply Now <ArrowRight size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
