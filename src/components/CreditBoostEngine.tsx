import React, { useState, useEffect } from 'react';
import {
  Home, Users, TrendingDown, CreditCard, Building, ArrowRight,
  CheckCircle2, Plus, Info, Star, Clock, DollarSign, Zap, X, Loader2
} from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthProvider';

interface BoostOpportunity {
  id: string;
  name: string;
  category: string;
  description: string | null;
  impact_score_min: number | null;
  impact_score_max: number | null;
  impact_fundability: number | null;
  estimated_timeline: string | null;
  cost_estimate: string | null;
  providers: any;
}

interface BoostAction {
  id: string;
  opportunity_id: string | null;
  name: string;
  status: string;
  in_action_center: boolean;
}

interface RentProvider {
  id: string;
  name: string;
  description: string | null;
  monthly_cost: number | null;
  bureaus: string[] | null;
  website_url: string | null;
  how_it_works: string | null;
}

const CATEGORY_ICONS: Record<string, React.ElementType> = {
  rent_reporting: Home,
  authorized_user: Users,
  utilization: TrendingDown,
  credit_builder: CreditCard,
  tradeline: Building,
  dispute: Star,
};

const CATEGORY_COLORS: Record<string, { bg: string; color: string; border: string }> = {
  rent_reporting: { bg: '#f0fdf4', color: '#16a34a', border: '#bbf7d0' },
  authorized_user: { bg: '#eff6ff', color: '#1d4ed8', border: '#bfdbfe' },
  utilization:    { bg: '#fefce8', color: '#854d0e', border: '#fde047' },
  credit_builder: { bg: '#fdf4ff', color: '#7c3aed', border: '#e9d5ff' },
  tradeline:      { bg: '#fff7ed', color: '#c2410c', border: '#fed7aa' },
  dispute:        { bg: '#eef0fd', color: '#3d5af1', border: '#c7d2fe' },
};

function RentKharmaModal({ onClose, onAddToPlan }: { onClose: () => void; onAddToPlan: (name: string) => void }) {
  const [providers, setProviders] = useState<RentProvider[]>([]);
  const [step, setStep] = useState<'overview' | 'providers' | 'checklist'>('overview');
  const [selectedProvider, setSelectedProvider] = useState<RentProvider | null>(null);

  useEffect(() => {
    supabase.from('rent_reporting_providers').select('*').then(({ data }) => {
      if (data) setProviders(data as RentProvider[]);
    });
  }, []);

  const checklist = [
    'You are currently renting (not owning)',
    'Your landlord agrees to verify rent payments',
    'You have 6+ months of rental history',
    'Your landlord can provide payment receipts or bank statements',
    'You have a valid checking or savings account',
  ];

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 500, background: 'rgba(26,28,58,0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ background: '#fff', borderRadius: 20, width: '100%', maxWidth: 560, maxHeight: '85vh', overflowY: 'auto', boxShadow: '0 20px 60px rgba(60,80,180,0.2)' }}>
        <div style={{ padding: '20px 24px', borderBottom: '1px solid #f0f0f8', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Rent Reporting</h2>
            <p style={{ fontSize: 13, color: '#8b8fa8', margin: '3px 0 0' }}>Build credit with monthly rent payments</p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8' }}><X size={18} /></button>
        </div>
        <div style={{ padding: 24 }}>
          {/* Tabs */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            {['overview', 'providers', 'checklist'].map(t => (
              <button key={t} onClick={() => setStep(t as any)}
                style={{
                  padding: '7px 14px', borderRadius: 20, fontSize: 13, fontWeight: 700,
                  border: '1.5px solid', cursor: 'pointer',
                  background: step === t ? '#3d5af1' : '#fff',
                  color: step === t ? '#fff' : '#3d5af1',
                  borderColor: step === t ? '#3d5af1' : '#c7d2fe',
                }}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>
            ))}
          </div>

          {step === 'overview' && (
            <div>
              <div style={{ padding: 16, background: '#f0fdf4', borderRadius: 12, border: '1px solid #bbf7d0', marginBottom: 16 }}>
                <p style={{ fontSize: 14, color: '#16a34a', fontWeight: 700, margin: '0 0 6px' }}>How It Works</p>
                <p style={{ fontSize: 13, color: '#166534', lineHeight: 1.6, margin: 0 }}>
                  Rent reporting services report your monthly rent payments to one or more credit bureaus. Since payment history is 35% of your FICO score, consistent on-time rent payments can significantly boost your credit score over time — especially if you have a thin file.
                </p>
              </div>
              <div style={{ padding: 16, background: '#eff6ff', borderRadius: 12, border: '1px solid #bfdbfe', marginBottom: 16 }}>
                <p style={{ fontSize: 14, color: '#1d4ed8', fontWeight: 700, margin: '0 0 6px' }}>Landlord Verification</p>
                <p style={{ fontSize: 13, color: '#1e40af', lineHeight: 1.6, margin: 0 }}>
                  Most providers require landlord participation or bank statement verification. Some services like LevelCredit allow you to connect your bank account to automatically verify rent payments without landlord involvement.
                </p>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div style={{ padding: 14, background: '#fafbff', borderRadius: 12, border: '1px solid #e8e9f2' }}>
                  <p style={{ fontSize: 12, fontWeight: 700, color: '#8b8fa8', margin: '0 0 4px' }}>IMPACT</p>
                  <p style={{ fontSize: 18, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>+10 to +40 pts</p>
                  <p style={{ fontSize: 12, color: '#8b8fa8', margin: '2px 0 0' }}>Credit score boost</p>
                </div>
                <div style={{ padding: 14, background: '#fafbff', borderRadius: 12, border: '1px solid #e8e9f2' }}>
                  <p style={{ fontSize: 12, fontWeight: 700, color: '#8b8fa8', margin: '0 0 4px' }}>TIMELINE</p>
                  <p style={{ fontSize: 18, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>1–3 months</p>
                  <p style={{ fontSize: 12, color: '#8b8fa8', margin: '2px 0 0' }}>To see results</p>
                </div>
              </div>
            </div>
          )}

          {step === 'providers' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {providers.length === 0 ? (
                <div style={{ padding: 24, textAlign: 'center' }}>
                  <Loader2 size={20} color="#3d5af1" style={{ animation: 'spin 1s linear infinite', margin: '0 auto 8px' }} />
                  <p style={{ fontSize: 13, color: '#8b8fa8' }}>Loading providers...</p>
                </div>
              ) : providers.map(p => (
                <div key={p.id}
                  style={{
                    padding: 16, borderRadius: 14, border: `2px solid ${selectedProvider?.id === p.id ? '#3d5af1' : '#e8e9f2'}`,
                    background: selectedProvider?.id === p.id ? '#eef0fd' : '#fff',
                    cursor: 'pointer',
                  }}
                  onClick={() => setSelectedProvider(selectedProvider?.id === p.id ? null : p)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <p style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{p.name}</p>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#3d5af1' }}>
                      {p.monthly_cost === 0 ? 'Free' : `$${p.monthly_cost}/mo`}
                    </span>
                  </div>
                  <p style={{ fontSize: 13, color: '#8b8fa8', margin: '0 0 8px' }}>{p.description}</p>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {(p.bureaus ?? []).map(b => (
                      <span key={b} style={{ padding: '3px 8px', background: '#f0fdf4', color: '#16a34a', borderRadius: 20, fontSize: 11, fontWeight: 700 }}>{b}</span>
                    ))}
                  </div>
                  {selectedProvider?.id === p.id && p.how_it_works && (
                    <p style={{ fontSize: 12, color: '#3d5af1', marginTop: 10, padding: '8px 12px', background: '#f0f4ff', borderRadius: 8 }}>
                      {p.how_it_works}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {step === 'checklist' && (
            <div>
              <p style={{ fontSize: 14, color: '#8b8fa8', marginBottom: 16 }}>Make sure you meet these requirements before starting:</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {checklist.map((item, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <CheckCircle2 size={18} color="#22c55e" style={{ flexShrink: 0, marginTop: 1 }} />
                    <p style={{ fontSize: 14, color: '#1a1c3a', margin: 0 }}>{item}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
            <button onClick={onClose}
              style={{ flex: 1, padding: '11px 0', borderRadius: 12, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 14, fontWeight: 700, color: '#8b8fa8', cursor: 'pointer' }}>
              Close
            </button>
            <button onClick={() => { onAddToPlan('Rent Reporting'); onClose(); }}
              style={{ flex: 2, padding: '11px 0', borderRadius: 12, border: 'none', background: '#3d5af1', fontSize: 14, fontWeight: 700, color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <Zap size={15} /> Add to Action Center
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function BoostCard({ opp, action, onAddToPlan, onLearnMore }: {
  opp: BoostOpportunity;
  action: BoostAction | undefined;
  onAddToPlan: (opp: BoostOpportunity) => void;
  onLearnMore: (opp: BoostOpportunity) => void;
}) {
  const Icon = CATEGORY_ICONS[opp.category] ?? Star;
  const colors = CATEGORY_COLORS[opp.category] ?? CATEGORY_COLORS.dispute;
  const isActive = action?.status === 'active' || action?.status === 'completed';
  const inPlan = action?.in_action_center;

  return (
    <div style={{
      padding: 20, borderRadius: 16, background: '#fff',
      border: `1.5px solid ${isActive ? colors.border : '#e8e9f2'}`,
      boxShadow: '0 2px 8px rgba(60,80,180,0.06)',
      display: 'flex', flexDirection: 'column', gap: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ width: 42, height: 42, borderRadius: 12, background: colors.bg, color: colors.color, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Icon size={20} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{opp.name}</h3>
            {isActive && (
              <span style={{ padding: '3px 10px', borderRadius: 20, background: '#f0fdf4', color: '#16a34a', fontSize: 11, fontWeight: 700 }}>Active</span>
            )}
          </div>
          <p style={{ fontSize: 13, color: '#8b8fa8', margin: '3px 0 0', lineHeight: 1.4 }}>{opp.description}</p>
        </div>
      </div>

      {/* Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        <div style={{ padding: '8px 10px', background: '#fafbff', borderRadius: 10, border: '1px solid #f0f0f8' }}>
          <p style={{ fontSize: 10, fontWeight: 700, color: '#8b8fa8', margin: '0 0 2px', textTransform: 'uppercase' }}>Score Impact</p>
          <p style={{ fontSize: 13, fontWeight: 800, color: colors.color, margin: 0 }}>+{opp.impact_score_min}–{opp.impact_score_max} pts</p>
        </div>
        <div style={{ padding: '8px 10px', background: '#fafbff', borderRadius: 10, border: '1px solid #f0f0f8' }}>
          <p style={{ fontSize: 10, fontWeight: 700, color: '#8b8fa8', margin: '0 0 2px', textTransform: 'uppercase' }}>Timeline</p>
          <p style={{ fontSize: 13, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>{opp.estimated_timeline ?? '—'}</p>
        </div>
        <div style={{ padding: '8px 10px', background: '#fafbff', borderRadius: 10, border: '1px solid #f0f0f8' }}>
          <p style={{ fontSize: 10, fontWeight: 700, color: '#8b8fa8', margin: '0 0 2px', textTransform: 'uppercase' }}>Cost</p>
          <p style={{ fontSize: 13, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>{opp.cost_estimate ?? '—'}</p>
        </div>
      </div>

      {/* Fundability impact bar */}
      {opp.impact_fundability && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Fundability Impact</span>
            <span style={{ fontSize: 12, fontWeight: 800, color: colors.color }}>+{opp.impact_fundability}%</span>
          </div>
          <div style={{ height: 5, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden' }}>
            <div style={{ width: `${opp.impact_fundability}%`, height: '100%', background: colors.color, borderRadius: 10 }} />
          </div>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={() => onLearnMore(opp)}
          style={{ flex: 1, padding: '9px 0', borderRadius: 10, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 13, fontWeight: 700, color: '#3d5af1', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
          <Info size={13} /> See Options
        </button>
        <button
          onClick={() => !inPlan && onAddToPlan(opp)}
          disabled={!!inPlan}
          style={{
            flex: 1, padding: '9px 0', borderRadius: 10, border: 'none',
            background: inPlan ? '#f0fdf4' : '#3d5af1',
            color: inPlan ? '#22c55e' : '#fff',
            fontSize: 13, fontWeight: 700, cursor: inPlan ? 'default' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          }}>
          {inPlan ? <><CheckCircle2 size={13} /> In Plan</> : <><Plus size={13} /> Add to Plan</>}
        </button>
      </div>
    </div>
  );
}

export function CreditBoostEngine() {
  const { user } = useAuth();
  const [opportunities, setOpportunities] = useState<BoostOpportunity[]>([]);
  const [actions, setActions] = useState<BoostAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRentModal, setShowRentModal] = useState(false);
  const [selectedOpp, setSelectedOpp] = useState<BoostOpportunity | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    Promise.all([
      supabase.from('credit_boost_opportunities').select('*').eq('is_active', true).order('sort_order'),
      user ? supabase.from('credit_boost_actions').select('*').eq('user_id', user.id) : Promise.resolve({ data: [] }),
    ]).then(([{ data: opps }, { data: acts }]) => {
      setOpportunities((opps ?? []) as BoostOpportunity[]);
      setActions((acts ?? []) as BoostAction[]);
      setLoading(false);
    });
  }, [user]);

  const addToPlan = async (opp: BoostOpportunity) => {
    if (!user) return;
    setSaving(opp.id);
    const { data } = await supabase.from('credit_boost_actions').upsert({
      user_id: user.id,
      opportunity_id: opp.id,
      name: opp.name,
      status: 'considering',
      in_action_center: true,
    }, { onConflict: 'user_id,opportunity_id' }).select().single();

    if (data) {
      setActions(prev => {
        const existing = prev.find(a => a.opportunity_id === opp.id);
        if (existing) return prev.map(a => a.opportunity_id === opp.id ? { ...a, in_action_center: true } : a);
        return [...prev, data as BoostAction];
      });

      // Create task
      await supabase.from('tasks').insert({
        user_id: user.id,
        title: `Start: ${opp.name}`,
        description: opp.description,
        category: 'credit',
        status: 'pending',
        priority: 2,
        readiness_impact: opp.impact_fundability ?? 5,
        is_primary: false,
      });
    }
    setSaving(null);
  };

  const learnMore = (opp: BoostOpportunity) => {
    if (opp.category === 'rent_reporting') { setShowRentModal(true); return; }
    setSelectedOpp(opp);
  };

  const filtered = filter === 'all' ? opportunities : opportunities.filter(o => o.category === filter);
  const categories = ['all', ...Array.from(new Set(opportunities.map(o => o.category)))];
  const categoryLabels: Record<string, string> = {
    all: 'All', rent_reporting: 'Rent', authorized_user: 'Auth User',
    utilization: 'Utilization', credit_builder: 'Credit Builder',
    tradeline: 'Tradelines', dispute: 'Disputes',
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
        <h2 style={{ fontSize: 22, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Credit Boost Engine</h2>
        <p style={{ fontSize: 14, color: '#8b8fa8', marginTop: 4 }}>
          Strategic actions to improve your credit score and fundability.
        </p>
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, overflowX: 'auto', paddingBottom: 4 }}>
        {categories.map(cat => (
          <button key={cat} onClick={() => setFilter(cat)}
            style={{
              padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 700,
              border: '1.5px solid', cursor: 'pointer', whiteSpace: 'nowrap',
              background: filter === cat ? '#3d5af1' : '#fff',
              color: filter === cat ? '#fff' : '#3d5af1',
              borderColor: filter === cat ? '#3d5af1' : '#c7d2fe',
            }}>{categoryLabels[cat] ?? cat}</button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', background: '#fff', borderRadius: 16, border: '1px solid #e8e9f2' }}>
          <Star size={28} color="#c7d2fe" style={{ margin: '0 auto 12px' }} />
          <p style={{ fontSize: 14, color: '#8b8fa8' }}>No opportunities available yet.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
          {filtered.map(opp => (
            <BoostCard
              key={opp.id}
              opp={opp}
              action={actions.find(a => a.opportunity_id === opp.id)}
              onAddToPlan={addToPlan}
              onLearnMore={learnMore}
            />
          ))}
        </div>
      )}

      {showRentModal && (
        <RentKharmaModal
          onClose={() => setShowRentModal(false)}
          onAddToPlan={(name) => {
            const opp = opportunities.find(o => o.category === 'rent_reporting');
            if (opp) addToPlan(opp);
          }}
        />
      )}

      {selectedOpp && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
          <div style={{ background: '#fff', borderRadius: 20, padding: 28, maxWidth: 480, width: '100%', maxHeight: '80vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 style={{ fontSize: 18, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>{selectedOpp.name}</h2>
              <button onClick={() => setSelectedOpp(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8' }}><X size={20} /></button>
            </div>
            {selectedOpp.description && (
              <p style={{ fontSize: 14, color: '#8b8fa8', marginBottom: 20, lineHeight: 1.6 }}>{selectedOpp.description}</p>
            )}
            {/* Provider list from JSONB if available */}
            {Array.isArray(selectedOpp.providers) && selectedOpp.providers.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
                <p style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>Recommended Providers</p>
                {selectedOpp.providers.map((p: any, i: number) => (
                  <div key={i} style={{ padding: '12px 16px', borderRadius: 12, border: '1px solid #e8e9f2', background: '#fafbff' }}>
                    <p style={{ fontSize: 14, fontWeight: 700, color: '#1a1c3a', margin: '0 0 4px' }}>{p.name ?? p}</p>
                    {p.description && <p style={{ fontSize: 13, color: '#8b8fa8', margin: 0 }}>{p.description}</p>}
                    {p.url && (
                      <a href={p.url} target="_blank" rel="noopener noreferrer"
                        style={{ fontSize: 12, color: '#3d5af1', fontWeight: 700, display: 'inline-block', marginTop: 6 }}>
                        Visit ↗
                      </a>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '16px', background: '#fafbff', borderRadius: 12, border: '1px solid #e8e9f2', marginBottom: 20 }}>
                <p style={{ fontSize: 13, color: '#8b8fa8', margin: 0, lineHeight: 1.6 }}>
                  Research providers for <strong>{selectedOpp.category.replace(/_/g, ' ')}</strong> strategies. Look for options that report to Experian, Equifax, or TransUnion to maximize score impact.
                </p>
              </div>
            )}
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setSelectedOpp(null)}
                style={{ flex: 1, padding: '11px', borderRadius: 10, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 14, fontWeight: 700, color: '#8b8fa8', cursor: 'pointer' }}>
                Close
              </button>
              <button onClick={() => { addToPlan(selectedOpp); setSelectedOpp(null); }}
                style={{ flex: 1, padding: '11px', borderRadius: 10, border: 'none', background: '#3d5af1', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>
                Add to Plan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
