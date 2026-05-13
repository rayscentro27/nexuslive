import React, { useEffect, useState, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthProvider';
import { useAnalytics } from '../hooks/useAnalytics';
import { ChevronDown, ChevronUp, ArrowRight, ShieldCheck, Clock, Zap } from 'lucide-react';

interface Opportunity {
  id: string;
  opportunity_id: string;
  opportunity_name: string;
  category: string;
  feasibility_score: number;
  opportunity_score: number;
  startup_cost: number;
  risk_level: string;
  monetization_type: string;
  nexus_status: string;
  tested_by_nexus: boolean;
  max_amount: number | null;
  educational_summary: string | null;
  action_steps: string | null;
  failure_points: string | null;
  typical_timeline_days: number | null;
  source_url_hint: string | null;
  reasons: string | null;
}

const CATEGORY_COLORS: Record<string, { color: string; bg: string; emoji: string }> = {
  sba:       { color: '#2563eb', bg: '#dbeafe', emoji: '🏛️' },
  loan:      { color: '#7c3aed', bg: '#ede9fe', emoji: '💳' },
  credit:    { color: '#0d9488', bg: '#ccfbf1', emoji: '📈' },
  microloan: { color: '#d97706', bg: '#fef3c7', emoji: '💵' },
  grant:     { color: '#16a34a', bg: '#dcfce7', emoji: '🏆' },
  business:  { color: '#dc2626', bg: '#fee2e2', emoji: '🏢' },
  trading:   { color: '#6366f1', bg: '#e0e7ff', emoji: '📊' },
};

const STATUS_DISPLAY: Record<string, { label: string; color: string; icon: string }> = {
  validated:   { label: 'Nexus Validated',  color: '#16a34a', icon: '✅' },
  tested:      { label: 'Nexus Tested',     color: '#2563eb', icon: '🔬' },
  reviewing:   { label: 'Under Review',     color: '#d97706', icon: '🔍' },
  researching: { label: 'Researching',      color: '#6366f1', icon: '🧠' },
  pending:     { label: 'Pending',          color: '#6b7280', icon: '⏳' },
  flagged:     { label: 'Flagged',          color: '#dc2626', icon: '⚠️' },
};

const RISK_DISPLAY: Record<string, { label: string; color: string }> = {
  low:     { label: 'Low Risk',    color: '#16a34a' },
  medium:  { label: 'Medium Risk', color: '#d97706' },
  high:    { label: 'High Risk',   color: '#dc2626' },
  unknown: { label: 'Unknown',     color: '#6b7280' },
};

function ScoreMeter({ score, color }: { score: number; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 5, borderRadius: 5, background: '#e8e9f2', overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: 5, transition: 'width 0.5s ease' }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, color, minWidth: 28 }}>{score}%</span>
    </div>
  );
}

function OpportunityCard({ opp, onNavigate }: { opp: Opportunity; onNavigate?: (tab: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const { emit } = useAnalytics();

  const cat = CATEGORY_COLORS[opp.category] || { color: '#6b7280', bg: '#f3f4f6', emoji: '💡' };
  const status = STATUS_DISPLAY[opp.nexus_status] || STATUS_DISPLAY['pending'];
  const risk = RISK_DISPLAY[opp.risk_level] || RISK_DISPLAY['unknown'];

  let actionSteps: { step: string; description: string }[] = [];
  try { actionSteps = JSON.parse(opp.action_steps || '[]'); } catch {}

  const handleExpand = () => {
    setExpanded(e => !e);
    if (!expanded) {
      emit('opportunity_viewed', {
        event_name: 'opportunity_expanded',
        feature: 'opportunities',
        metadata: { opportunity_id: opp.opportunity_id, category: opp.category },
      });
    }
  };

  const handleAction = () => {
    emit('opportunity_action_clicked', {
      event_name: 'opportunity_action',
      feature: 'opportunities',
      metadata: { opportunity_id: opp.opportunity_id },
    });
    onNavigate?.(opp.source_url_hint || 'funding');
  };

  return (
    <div style={{
      background: '#fff',
      borderRadius: 14,
      border: '1px solid #e8e9f2',
      overflow: 'hidden',
      transition: 'box-shadow 0.2s',
    }}>
      {/* Card header */}
      <div
        onClick={handleExpand}
        style={{ padding: '14px 16px', cursor: 'pointer', display: 'flex', alignItems: 'flex-start', gap: 12 }}
      >
        {/* Category badge */}
        <div style={{
          width: 40, height: 40, borderRadius: 10, flexShrink: 0,
          background: cat.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20,
        }}>
          {cat.emoji}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: '#1a1c3a', margin: 0, lineHeight: 1.3 }}>
              {opp.opportunity_name}
            </p>
            <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
              {opp.tested_by_nexus && (
                <span style={{
                  fontSize: 10, fontWeight: 700, color: '#16a34a',
                  background: '#dcfce7', borderRadius: 6, padding: '2px 6px',
                  whiteSpace: 'nowrap',
                }}>✅ Nexus</span>
              )}
              <span style={{
                fontSize: 10, fontWeight: 700, color: risk.color,
                background: risk.color + '15', borderRadius: 6, padding: '2px 6px',
                whiteSpace: 'nowrap',
              }}>{risk.label}</span>
            </div>
          </div>

          {/* Scores row */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 6 }}>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 10, color: '#8b8fa8', marginBottom: 3 }}>Feasibility</p>
              <ScoreMeter score={opp.feasibility_score} color={cat.color} />
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 10, color: '#8b8fa8', marginBottom: 3 }}>Opportunity</p>
              <ScoreMeter score={opp.opportunity_score} color="#3d5af1" />
            </div>
          </div>

          {/* Meta row */}
          <div style={{ display: 'flex', gap: 10, fontSize: 11, color: '#8b8fa8' }}>
            {opp.max_amount ? (
              <span style={{ fontWeight: 600, color: '#22c55e' }}>
                Up to ${(opp.max_amount / 1000).toFixed(0)}k
              </span>
            ) : (
              <span>Credit building</span>
            )}
            {opp.typical_timeline_days && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                <Clock size={10} />
                {opp.typical_timeline_days}d timeline
              </span>
            )}
            <span style={{ color: status.color }}>{status.icon} {status.label}</span>
          </div>
        </div>

        <div style={{ flexShrink: 0, color: '#8b8fa8' }}>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div style={{ padding: '0 16px 16px', borderTop: '1px solid #f3f4f6' }}>
          {opp.educational_summary && (
            <div style={{ marginTop: 12 }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                What Nexus knows about this
              </p>
              <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.6, margin: 0 }}>
                {opp.educational_summary}
              </p>
            </div>
          )}

          {actionSteps.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
                Action Steps
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {actionSteps.map((s, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <div style={{
                      width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                      background: '#3d5af1', color: '#fff',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 10, fontWeight: 800,
                    }}>{s.step}</div>
                    <p style={{ fontSize: 13, color: '#374151', margin: 0, lineHeight: 1.5 }}>{s.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {opp.failure_points && (
            <div style={{ marginTop: 12, padding: '10px 12px', background: '#fff7ed', borderRadius: 10, border: '1px solid #fed7aa' }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: '#d97706', marginBottom: 4 }}>⚠️ Common Failure Points</p>
              <p style={{ fontSize: 12, color: '#92400e', margin: 0 }}>{opp.failure_points}</p>
            </div>
          )}

          <button
            onClick={handleAction}
            style={{
              marginTop: 14, width: '100%', padding: '10px 0',
              borderRadius: 10, border: 'none', cursor: 'pointer',
              background: 'linear-gradient(135deg, #3d5af1, #6366f1)',
              color: '#fff', fontWeight: 700, fontSize: 13,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}
          >
            <Zap size={13} /> Take Action <ArrowRight size={13} />
          </button>
        </div>
      )}
    </div>
  );
}

interface Props {
  onNavigate?: (tab: string) => void;
  limit?: number;
}

export function OpportunityDashboard({ onNavigate, limit = 7 }: Props) {
  const { user } = useAuth();
  const { emit } = useAnalytics();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const load = useCallback(async () => {
    if (!user) return;
    const { data } = await supabase
      .from('user_opportunities')
      .select('*')
      .eq('user_id', user.id)
      .order('opportunity_score', { ascending: false })
      .limit(limit);
    if (data) setOpportunities(data as Opportunity[]);
    setLoading(false);
  }, [user, limit]);

  useEffect(() => {
    void load();
    emit('page_view', { event_name: 'opportunities_viewed', feature: 'opportunities', page: '/opportunities' });
  }, [load]); // eslint-disable-line react-hooks/exhaustive-deps

  const categories: string[] = ['all', ...Array.from(new Set<string>(opportunities.map(o => o.category)))];
  const filtered: Opportunity[] = categoryFilter === 'all' ? opportunities : opportunities.filter(o => o.category === categoryFilter);

  const validated = opportunities.filter(o => o.nexus_status === 'validated' || o.tested_by_nexus).length;

  return (
    <div style={{ padding: '16px 20px' }}>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: '#1a1c3a', marginBottom: 3 }}>
          🔭 Your Opportunities
        </h1>
        <p style={{ fontSize: 14, color: '#8b8fa8' }}>
          Nexus researches, tests, and ranks opportunities so you don't have to.
        </p>
      </div>

      {/* Stats bar */}
      {!loading && opportunities.length > 0 && (
        <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
          {[
            { label: 'Matched', value: opportunities.length, color: '#3d5af1', bg: '#eef0fd' },
            { label: 'Nexus Validated', value: validated, color: '#16a34a', bg: '#dcfce7' },
            { label: 'Avg Feasibility', value: `${Math.round(opportunities.reduce((s, o) => s + o.feasibility_score, 0) / opportunities.length)}%`, color: '#d97706', bg: '#fef3c7' },
          ].map(s => (
            <div key={s.label} style={{
              flex: '1 1 90px', padding: '10px 12px', borderRadius: 12,
              background: s.bg, border: `1px solid ${s.color}20`,
              textAlign: 'center',
            }}>
              <p style={{ fontSize: 20, fontWeight: 800, color: s.color, margin: 0 }}>{s.value}</p>
              <p style={{ fontSize: 11, color: '#6b7280', margin: 0 }}>{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Category filter */}
      {categories.length > 2 && (
        <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
          {categories.map(cat => (
            <button key={cat} onClick={() => setCategoryFilter(cat)} style={{
              padding: '5px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600, cursor: 'pointer',
              background: categoryFilter === cat ? '#3d5af1' : '#f3f4f6',
              color: categoryFilter === cat ? '#fff' : '#6b7280',
              border: categoryFilter === cat ? '1px solid #3d5af1' : '1px solid #e5e7eb',
            }}>
              {cat === 'all' ? 'All' : cat.charAt(0).toUpperCase() + cat.slice(1)}
            </button>
          ))}
        </div>
      )}

      {/* Opportunity list */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[...Array(3)].map((_, i) => (
            <div key={i} style={{ height: 90, borderRadius: 14, background: '#f3f4f6' }} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div style={{
          padding: '32px 20px', textAlign: 'center',
          background: '#f9fafb', borderRadius: 14, border: '1px dashed #e5e7eb',
        }}>
          <p style={{ fontSize: 32, marginBottom: 8 }}>🔭</p>
          <p style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', marginBottom: 6 }}>
            Nexus is researching opportunities for you
          </p>
          <p style={{ fontSize: 13, color: '#8b8fa8' }}>
            Complete your profile to unlock personalized opportunity matching.
          </p>
          <button
            onClick={() => onNavigate?.('account')}
            style={{
              marginTop: 16, padding: '10px 24px', borderRadius: 10, border: 'none',
              background: '#3d5af1', color: '#fff', fontWeight: 700, fontSize: 13, cursor: 'pointer',
            }}
          >
            Complete Profile
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {filtered.map((opp, idx) => (
            <OpportunityCard key={opp.id || opp.opportunity_id || idx} opp={opp} onNavigate={onNavigate} />
          ))}
        </div>
      )}

      {/* Trust footer */}
      <div style={{
        marginTop: 20, padding: '12px 16px', borderRadius: 12,
        background: '#f0fdf4', border: '1px solid #bbf7d0',
        display: 'flex', alignItems: 'flex-start', gap: 10,
      }}>
        <ShieldCheck size={16} color="#16a34a" style={{ flexShrink: 0, marginTop: 1 }} />
        <div>
          <p style={{ fontSize: 12, fontWeight: 700, color: '#16a34a', margin: '0 0 2px' }}>
            Nexus Research Commitment
          </p>
          <p style={{ fontSize: 11, color: '#374151', margin: 0, lineHeight: 1.5 }}>
            Nexus investigates, simulates, and tests opportunities before surfacing them. We identify scams,
            evaluate realistic paths, and educate — so you carry less of the research burden alone.
          </p>
        </div>
      </div>
    </div>
  );
}
