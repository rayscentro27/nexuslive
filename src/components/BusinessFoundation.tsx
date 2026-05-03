/**
 * Business Foundation — Phase 6 & 7
 * Tabs: Foundation | LLC Setup | Business Credit | Vendor Tradelines
 */
import React, { useState, useEffect } from 'react';
import {
  Building2, FileText, Globe, CreditCard, CheckCircle2,
  ArrowRight, ExternalLink, Plus, Loader2, AlertCircle,
  ChevronDown, ChevronUp, Star, Layers, DollarSign, X
} from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthProvider';
import { getBusinessEntity, upsertBusinessEntity, BusinessEntity } from '../lib/db';

// ─── Types ────────────────────────────────────────────────────────────────────

interface VendorCatalog {
  id: string;
  vendor_name: string;
  tier: number;
  category: string;
  description: string | null;
  requirements: string | null;
  credit_limit_range: string | null;
  reports_to: string[] | null;
  application_url: string | null;
}

interface UserVendorAccount {
  id: string;
  vendor_id: string | null;
  vendor_name: string;
  tier: number;
  status: string;
  credit_limit: number | null;
}

interface BusinessCreditProfile {
  user_id: string;
  duns_number: string | null;
  paydex_score: number | null;
  experian_score: number | null;
  equifax_score: number | null;
}

// ─── Business Readiness Score ─────────────────────────────────────────────────

function ReadinessScore({ entity }: { entity: BusinessEntity | null }) {
  const checks = [
    { label: 'Business Name',  done: !!entity?.business_name },
    { label: 'Entity Type',    done: !!entity?.entity_type },
    { label: 'EIN',            done: !!entity?.ein },
    { label: 'State Formation', done: !!entity?.formation_state },
    { label: 'NAICS Code',     done: !!entity?.naics_code },
    { label: 'DUNS Number',    done: !!entity?.duns_number },
  ];
  const score = Math.round((checks.filter(c => c.done).length / checks.length) * 100);
  const color = score >= 80 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <div className="glass-card" style={{ padding: 20, marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Business Readiness Score</h3>
          <p style={{ fontSize: 12, color: '#8b8fa8', marginTop: 3 }}>Lenders check these to assess business legitimacy.</p>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 32, fontWeight: 800, color }}>{score}%</div>
          <div style={{ fontSize: 11, color: '#8b8fa8', fontWeight: 600 }}>Readiness</div>
        </div>
      </div>
      <div style={{ height: 6, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden', marginBottom: 14 }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: 10, transition: 'width 0.5s' }} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        {checks.map(c => (
          <div key={c.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <CheckCircle2 size={14} color={c.done ? '#22c55e' : '#e8e9f2'} />
            <span style={{ fontSize: 12, color: c.done ? '#1a1c3a' : '#8b8fa8', fontWeight: c.done ? 600 : 400 }}>{c.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Foundation Tab ───────────────────────────────────────────────────────────

function FoundationTab({ entity, onSave }: {
  entity: BusinessEntity | null;
  onSave: (updates: Partial<BusinessEntity>) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    business_name: entity?.business_name ?? '',
    entity_type: entity?.entity_type ?? 'LLC',
    ein: entity?.ein ?? '',
    formation_state: entity?.formation_state ?? '',
    naics_code: entity?.naics_code ?? '',
    duns_number: entity?.duns_number ?? '',
  });

  useEffect(() => {
    if (entity) {
      setForm({
        business_name: entity.business_name ?? '',
        entity_type: entity.entity_type ?? 'LLC',
        ein: entity.ein ?? '',
        formation_state: entity.formation_state ?? '',
        naics_code: entity.naics_code ?? '',
        duns_number: entity.duns_number ?? '',
      });
    }
  }, [entity]);

  const handleSave = async () => {
    setSaving(true);
    await onSave(form);
    setSaving(false);
    setEditing(false);
  };

  const fields = [
    { key: 'business_name', label: 'Legal Business Name', placeholder: 'NexusOne LLC' },
    { key: 'entity_type', label: 'Entity Type', placeholder: 'LLC', isSelect: true, options: ['LLC', 'S-Corp', 'C-Corp', 'Sole Proprietor', 'Partnership'] },
    { key: 'ein', label: 'EIN (Employer ID Number)', placeholder: 'XX-XXXXXXX' },
    { key: 'formation_state', label: 'Formation State', placeholder: 'GA' },
    { key: 'naics_code', label: 'NAICS Code', placeholder: '541512' },
    { key: 'duns_number', label: 'DUNS Number', placeholder: 'Optional' },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Entity & Identification</h3>
        <button
          onClick={() => editing ? handleSave() : setEditing(true)}
          disabled={saving}
          style={{ padding: '8px 16px', borderRadius: 10, border: editing ? 'none' : '1.5px solid #e8e9f2', background: editing ? '#3d5af1' : '#fff', color: editing ? '#fff' : '#3d5af1', fontSize: 13, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
        >
          {saving ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : null}
          {editing ? 'Save Changes' : 'Edit'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {fields.map(field => (
          <div key={field.key} style={{ padding: 14, background: '#fff', borderRadius: 12, border: '1px solid #e8e9f2' }}>
            <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', margin: '0 0 4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{field.label}</p>
            {editing ? (
              field.isSelect ? (
                <select
                  value={(form as any)[field.key]}
                  onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                  style={{ width: '100%', padding: '6px 0', border: 'none', outline: 'none', fontSize: 14, fontWeight: 700, color: '#1a1c3a', background: 'transparent' }}
                >
                  {field.options!.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : (
                <input
                  value={(form as any)[field.key]}
                  onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                  placeholder={field.placeholder}
                  style={{ width: '100%', padding: '6px 0', border: 'none', borderBottom: '1.5px solid #3d5af1', outline: 'none', fontSize: 14, fontWeight: 700, color: '#1a1c3a', background: 'transparent' }}
                />
              )
            ) : (
              <p style={{ fontSize: 14, fontWeight: 700, color: (entity as any)?.[field.key] ? '#1a1c3a' : '#c7d2fe', margin: 0 }}>
                {(entity as any)?.[field.key] || field.placeholder}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* NAICS info */}
      <div style={{ marginTop: 16, padding: '12px 16px', background: '#eef0fd', borderRadius: 12, border: '1px solid #c7d2fe' }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: '#3d5af1', margin: '0 0 4px' }}>NAICS Code Tip</p>
        <p style={{ fontSize: 12, color: '#6366f1', margin: 0, lineHeight: 1.5 }}>
          Your NAICS code affects which lenders and grants you qualify for. Choose a low-risk code (retail, professional services, tech consulting) when possible. Avoid: firearms, gambling, cannabis, lending.
        </p>
      </div>
    </div>
  );
}

// ─── LLC Setup Tab ────────────────────────────────────────────────────────────

const LLC_PROVIDERS = [
  { name: 'ZenBusiness', price: '$0 + state fee', rating: '4.8', url: 'https://www.zenbusiness.com', badge: 'Best Value' },
  { name: 'Northwest Registered Agent', price: '$39 + state fee', rating: '4.9', url: 'https://www.northwestregisteredagent.com', badge: 'Best Privacy' },
  { name: 'LegalZoom', price: '$79 + state fee', rating: '4.5', url: 'https://www.legalzoom.com', badge: '' },
  { name: 'Bizee (Incfile)', price: '$0 + state fee', rating: '4.7', url: 'https://www.bizee.com', badge: 'Most Popular' },
];

const LLC_CHECKLIST = [
  { step: 1, label: 'Choose your state', description: 'Best states: Wyoming, Delaware, Nevada for asset protection. Or your home state for simplicity.' },
  { step: 2, label: 'Choose business name', description: 'Must be unique in your state. Check Secretary of State website.' },
  { step: 3, label: 'Select entity type', description: 'LLC is recommended for most small businesses. S-Corp for higher income.' },
  { step: 4, label: 'File Articles of Organization', description: 'Submit to your state Secretary of State. Takes 1-10 business days.' },
  { step: 5, label: 'Get your EIN', description: 'Apply free at IRS.gov. Takes 5 minutes online. Required for banking.' },
  { step: 6, label: 'Create Operating Agreement', description: 'Required in most states. Defines ownership, management, and profit sharing.' },
  { step: 7, label: 'Open business bank account', description: 'Required for business credit. Recommended: Chase, Bank of America, Mercury.' },
];

function LLCSetupTab() {
  const [path, setPath] = useState<'guided' | 'done-for-you' | null>(null);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  const toggleStep = (step: number) => {
    setCompletedSteps(prev =>
      prev.includes(step) ? prev.filter(s => s !== step) : [...prev, step]
    );
  };

  return (
    <div>
      <h3 style={{ fontSize: 17, fontWeight: 800, color: '#1a1c3a', marginBottom: 6 }}>LLC Setup</h3>
      <p style={{ fontSize: 13, color: '#8b8fa8', marginBottom: 20 }}>Choose your path to set up your business entity.</p>

      {!path && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <button onClick={() => setPath('guided')} style={{
            padding: 24, borderRadius: 16, border: '2px solid #c7d2fe', background: '#eef0fd',
            cursor: 'pointer', textAlign: 'left',
          }}>
            <div style={{ fontSize: 28, marginBottom: 10 }}>📋</div>
            <h4 style={{ fontSize: 16, fontWeight: 800, color: '#1a1c3a', margin: '0 0 6px' }}>Guided Setup</h4>
            <p style={{ fontSize: 13, color: '#8b8fa8', margin: 0 }}>Step-by-step checklist. Do it yourself with our guidance.</p>
            <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 6, color: '#3d5af1', fontSize: 13, fontWeight: 700 }}>
              Start Checklist <ArrowRight size={13} />
            </div>
          </button>
          <button onClick={() => setPath('done-for-you')} style={{
            padding: 24, borderRadius: 16, border: '2px solid #bbf7d0', background: '#f0fdf4',
            cursor: 'pointer', textAlign: 'left',
          }}>
            <div style={{ fontSize: 28, marginBottom: 10 }}>🏢</div>
            <h4 style={{ fontSize: 16, fontWeight: 800, color: '#1a1c3a', margin: '0 0 6px' }}>Done For You</h4>
            <p style={{ fontSize: 13, color: '#8b8fa8', margin: 0 }}>Use a trusted service to handle filing for you.</p>
            <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 6, color: '#16a34a', fontSize: 13, fontWeight: 700 }}>
              See Providers <ArrowRight size={13} />
            </div>
          </button>
        </div>
      )}

      {path === 'guided' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h4 style={{ fontSize: 15, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>
              LLC Formation Checklist ({completedSteps.length}/{LLC_CHECKLIST.length} complete)
            </h4>
            <button onClick={() => setPath(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8', fontSize: 13 }}>← Back</button>
          </div>
          <div style={{ height: 5, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden', marginBottom: 16 }}>
            <div style={{ width: `${(completedSteps.length / LLC_CHECKLIST.length) * 100}%`, height: '100%', background: '#22c55e', borderRadius: 10, transition: 'width 0.3s' }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {LLC_CHECKLIST.map(item => {
              const done = completedSteps.includes(item.step);
              return (
                <div key={item.step}
                  onClick={() => toggleStep(item.step)}
                  style={{
                    padding: '14px 16px', borderRadius: 14, cursor: 'pointer',
                    background: done ? '#f0fdf4' : '#fff',
                    border: `1.5px solid ${done ? '#bbf7d0' : '#e8e9f2'}`,
                    display: 'flex', gap: 12, alignItems: 'flex-start',
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{
                    width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                    background: done ? '#22c55e' : '#f0f0f8',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {done ? <CheckCircle2 size={16} color="#fff" /> : <span style={{ fontSize: 13, fontWeight: 800, color: '#8b8fa8' }}>{item.step}</span>}
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 14, fontWeight: 700, color: done ? '#16a34a' : '#1a1c3a', margin: 0 }}>{item.label}</p>
                    <p style={{ fontSize: 12, color: '#8b8fa8', margin: '3px 0 0', lineHeight: 1.4 }}>{item.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
          {completedSteps.length === LLC_CHECKLIST.length && (
            <div style={{ marginTop: 16, padding: 16, background: '#f0fdf4', borderRadius: 14, border: '1px solid #bbf7d0', textAlign: 'center' }}>
              <CheckCircle2 size={24} color="#22c55e" style={{ margin: '0 auto 8px' }} />
              <p style={{ fontSize: 15, fontWeight: 700, color: '#16a34a', margin: 0 }}>LLC Setup Complete! Update your business profile with your details.</p>
            </div>
          )}
        </div>
      )}

      {path === 'done-for-you' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h4 style={{ fontSize: 15, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>LLC Formation Services</h4>
            <button onClick={() => setPath(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8', fontSize: 13 }}>← Back</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {LLC_PROVIDERS.map(p => (
              <div key={p.name} style={{ padding: 16, background: '#fff', borderRadius: 14, border: '1px solid #e8e9f2', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                    <p style={{ fontSize: 15, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>{p.name}</p>
                    {p.badge && <span style={{ padding: '2px 8px', borderRadius: 20, background: '#eef0fd', color: '#3d5af1', fontSize: 10, fontWeight: 700 }}>{p.badge}</span>}
                  </div>
                  <p style={{ fontSize: 13, color: '#8b8fa8', margin: 0 }}>{p.price} · ⭐ {p.rating}</p>
                </div>
                <a href={p.url} target="_blank" rel="noopener noreferrer"
                  style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 10, background: '#3d5af1', color: '#fff', fontSize: 13, fontWeight: 700, textDecoration: 'none' }}>
                  Get Started <ExternalLink size={12} />
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Business Credit Tab ──────────────────────────────────────────────────────

function BusinessCreditTab({ userId }: { userId: string }) {
  const [profile, setProfile] = useState<BusinessCreditProfile | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ duns_number: '', paydex_score: '', experian_score: '', equifax_score: '' });

  useEffect(() => {
    supabase.from('business_credit_profiles').select('*').eq('user_id', userId).single()
      .then(({ data }) => {
        setProfile(data as BusinessCreditProfile | null);
        if (data) {
          setForm({
            duns_number: data.duns_number ?? '',
            paydex_score: data.paydex_score?.toString() ?? '',
            experian_score: data.experian_score?.toString() ?? '',
            equifax_score: data.equifax_score?.toString() ?? '',
          });
        }
      });
  }, [userId]);

  const save = async () => {
    setSaving(true);
    const updates = {
      user_id: userId,
      duns_number: form.duns_number || null,
      paydex_score: form.paydex_score ? parseInt(form.paydex_score) : null,
      experian_score: form.experian_score ? parseInt(form.experian_score) : null,
      equifax_score: form.equifax_score ? parseInt(form.equifax_score) : null,
    };
    const { data } = await supabase.from('business_credit_profiles')
      .upsert(updates, { onConflict: 'user_id' }).select().single();
    if (data) setProfile(data as BusinessCreditProfile);
    setSaving(false);
    setEditing(false);
  };

  const scores = [
    { label: 'PAYDEX Score', value: profile?.paydex_score, max: 100, good: 80, key: 'paydex_score', description: 'D&B payment score. 80+ is good.' },
    { label: 'Experian Business', value: profile?.experian_score, max: 100, good: 75, key: 'experian_score', description: 'Experian Intelliscore. 76+ is good.' },
    { label: 'Equifax Business', value: profile?.equifax_score, max: 100, good: 75, key: 'equifax_score', description: 'Equifax Small Business. 75+ is good.' },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Business Credit Profile</h3>
        <button onClick={() => editing ? save() : setEditing(true)} disabled={saving}
          style={{ padding: '8px 16px', borderRadius: 10, border: editing ? 'none' : '1.5px solid #e8e9f2', background: editing ? '#3d5af1' : '#fff', color: editing ? '#fff' : '#3d5af1', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
          {saving ? 'Saving...' : editing ? 'Save' : 'Update Scores'}
        </button>
      </div>

      {/* DUNS */}
      <div className="glass-card" style={{ padding: 16, marginBottom: 16 }}>
        <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', margin: '0 0 4px', textTransform: 'uppercase' }}>DUNS Number</p>
        {editing ? (
          <input value={form.duns_number} onChange={e => setForm(f => ({ ...f, duns_number: e.target.value }))}
            placeholder="Get free at dnb.com"
            style={{ width: '100%', padding: '6px 0', border: 'none', borderBottom: '1.5px solid #3d5af1', outline: 'none', fontSize: 16, fontWeight: 700, color: '#1a1c3a', background: 'transparent' }} />
        ) : (
          <p style={{ fontSize: 16, fontWeight: 700, color: profile?.duns_number ? '#1a1c3a' : '#c7d2fe', margin: 0 }}>
            {profile?.duns_number ?? 'Not entered — get free at dnb.com'}
          </p>
        )}
        {!profile?.duns_number && !editing && (
          <a href="https://www.dnb.com/duns-number/get-a-duns.html" target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 12, color: '#3d5af1', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 6 }}>
            Get DUNS Free <ExternalLink size={11} />
          </a>
        )}
      </div>

      {/* Scores */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        {scores.map(s => {
          const pct = s.value ? (s.value / s.max) * 100 : 0;
          const color = s.value ? (s.value >= s.good ? '#22c55e' : s.value >= s.good * 0.75 ? '#f59e0b' : '#ef4444') : '#c7d2fe';
          return (
            <div key={s.label} className="glass-card" style={{ padding: 16, textAlign: 'center' }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', margin: '0 0 8px', textTransform: 'uppercase' }}>{s.label}</p>
              {editing ? (
                <input type="number" value={(form as any)[s.key]}
                  onChange={e => setForm(f => ({ ...f, [s.key]: e.target.value }))}
                  placeholder="0"
                  style={{ width: '100%', textAlign: 'center', padding: '6px 0', border: 'none', borderBottom: '1.5px solid #3d5af1', outline: 'none', fontSize: 24, fontWeight: 800, color: '#1a1c3a', background: 'transparent' }} />
              ) : (
                <p style={{ fontSize: 28, fontWeight: 800, color, margin: '0 0 6px' }}>{s.value ?? '—'}</p>
              )}
              <div style={{ height: 4, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden', margin: '8px 0' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 10 }} />
              </div>
              <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>{s.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Vendor Tradelines Tab ────────────────────────────────────────────────────

function VendorTradelinesTab({ userId }: { userId: string }) {
  const [vendors, setVendors] = useState<VendorCatalog[]>([]);
  const [userAccounts, setUserAccounts] = useState<UserVendorAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState<string | null>(null);
  const [tierFilter, setTierFilter] = useState<number | 'all'>('all');

  useEffect(() => {
    Promise.all([
      supabase.from('vendor_tradelines_catalog').select('*').eq('is_active', true).order('sort_order'),
      supabase.from('user_vendor_accounts').select('*').eq('user_id', userId),
    ]).then(([{ data: v }, { data: ua }]) => {
      setVendors((v ?? []) as VendorCatalog[]);
      setUserAccounts((ua ?? []) as UserVendorAccount[]);
      setLoading(false);
    });
  }, [userId]);

  const applyToVendor = async (vendor: VendorCatalog) => {
    setApplying(vendor.id);
    const { data } = await supabase.from('user_vendor_accounts').upsert({
      user_id: userId,
      vendor_id: vendor.id,
      vendor_name: vendor.vendor_name,
      tier: vendor.tier,
      status: 'applied',
      applied_at: new Date().toISOString(),
    }, { onConflict: 'user_id,vendor_id' }).select().single() as any;
    if (data) setUserAccounts(prev => {
      const existing = prev.find(a => a.vendor_id === vendor.id);
      if (existing) return prev.map(a => a.vendor_id === vendor.id ? data : a);
      return [...prev, data];
    });

    // Create task to follow up
    await supabase.from('tasks').insert({
      user_id: userId,
      title: `Follow up on ${vendor.vendor_name} application`,
      description: `You applied to ${vendor.vendor_name} Tier ${vendor.tier} vendor account. Follow up in 5-7 business days.`,
      category: 'business_credit',
      status: 'pending',
      priority: 3,
      readiness_impact: 8,
      is_primary: false,
    });

    setApplying(null);
    // Open application URL
    if (vendor.application_url) window.open(vendor.application_url, '_blank');
  };

  const TIER_COLORS: Record<number, { bg: string; color: string; border: string; label: string }> = {
    1: { bg: '#f0fdf4', color: '#16a34a', border: '#bbf7d0', label: 'Tier 1 — Starter' },
    2: { bg: '#eff6ff', color: '#1d4ed8', border: '#bfdbfe', label: 'Tier 2 — Established' },
    3: { bg: '#fdf4ff', color: '#7c3aed', border: '#e9d5ff', label: 'Tier 3 — Advanced' },
  };

  const filtered = tierFilter === 'all' ? vendors : vendors.filter(v => v.tier === tierFilter);

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><Loader2 size={20} color="#3d5af1" style={{ animation: 'spin 1s linear infinite', margin: '0 auto' }} /></div>;

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h3 style={{ fontSize: 17, fontWeight: 800, color: '#1a1c3a', margin: '0 0 4px' }}>Vendor Tradelines</h3>
        <p style={{ fontSize: 13, color: '#8b8fa8' }}>Apply for vendor accounts that report to business credit bureaus. Start with Tier 1.</p>
      </div>

      {/* Tier info */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 20 }}>
        {([1, 2, 3] as number[]).map(tier => {
          const tc = TIER_COLORS[tier];
          const count = userAccounts.filter(a => a.tier === tier && a.status !== 'considering').length;
          return (
            <div key={tier} style={{ padding: 12, borderRadius: 12, background: tc.bg, border: `1px solid ${tc.border}`, textAlign: 'center' }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: tc.color, margin: '0 0 4px', textTransform: 'uppercase' }}>{tc.label}</p>
              <p style={{ fontSize: 22, fontWeight: 800, color: tc.color, margin: 0 }}>{count}</p>
              <p style={{ fontSize: 11, color: '#8b8fa8', margin: '2px 0 0' }}>Applied/Active</p>
            </div>
          );
        })}
      </div>

      {/* Filter */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {(['all', 1, 2, 3] as const).map(t => (
          <button key={t} onClick={() => setTierFilter(t)}
            style={{ padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 700, border: '1.5px solid', cursor: 'pointer', background: tierFilter === t ? '#3d5af1' : '#fff', color: tierFilter === t ? '#fff' : '#3d5af1', borderColor: tierFilter === t ? '#3d5af1' : '#c7d2fe' }}>
            {t === 'all' ? 'All Tiers' : `Tier ${t}`}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {filtered.map(vendor => {
          const account = userAccounts.find(a => a.vendor_id === vendor.id);
          const tc = TIER_COLORS[vendor.tier];
          const STATUS_COLORS: Record<string, string> = { applied: '#3d5af1', approved: '#22c55e', active: '#22c55e', declined: '#ef4444' };
          return (
            <div key={vendor.id} style={{ padding: 18, background: '#fff', borderRadius: 16, border: `1.5px solid ${account ? tc.border : '#e8e9f2'}`, boxShadow: '0 2px 8px rgba(60,80,180,0.05)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <h4 style={{ fontSize: 15, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>{vendor.vendor_name}</h4>
                    <span style={{ padding: '2px 8px', borderRadius: 20, background: tc.bg, color: tc.color, fontSize: 10, fontWeight: 700 }}>Tier {vendor.tier}</span>
                  </div>
                  <p style={{ fontSize: 13, color: '#8b8fa8', margin: '0 0 6px' }}>{vendor.category} · {vendor.credit_limit_range ?? 'Varies'}</p>
                  {vendor.requirements && <p style={{ fontSize: 12, color: '#8b8fa8', margin: '0 0 8px' }}>Req: {vendor.requirements}</p>}
                  {vendor.reports_to && (
                    <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                      {vendor.reports_to.map(b => (
                        <span key={b} style={{ padding: '2px 8px', background: '#f0f4ff', color: '#3d5af1', borderRadius: 20, fontSize: 10, fontWeight: 700 }}>{b}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div style={{ flexShrink: 0, marginLeft: 12 }}>
                  {account ? (
                    <span style={{ padding: '6px 12px', borderRadius: 20, background: (STATUS_COLORS[account.status] ?? '#8b8fa8') + '18', color: STATUS_COLORS[account.status] ?? '#8b8fa8', fontSize: 12, fontWeight: 700 }}>
                      {account.status.charAt(0).toUpperCase() + account.status.slice(1)}
                    </span>
                  ) : (
                    <button
                      onClick={() => applyToVendor(vendor)}
                      disabled={applying === vendor.id}
                      style={{ padding: '8px 16px', borderRadius: 10, border: 'none', background: '#3d5af1', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                      {applying === vendor.id ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} /> : null}
                      Apply <ExternalLink size={12} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 16, padding: '12px 16px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 12 }}>
        <p style={{ fontSize: 12, color: '#92400e', margin: 0, lineHeight: 1.5 }}>
          <strong>Strategy:</strong> Start with all Tier 1 vendors first. After 3-6 months of on-time payments, move to Tier 2, then Tier 3. Never apply to higher tiers without establishing lower ones first.
        </p>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

type BizTab = 'foundation' | 'llc' | 'credit' | 'vendors';

export function BusinessFoundation() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<BizTab>('foundation');
  const [entity, setEntity] = useState<BusinessEntity | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    getBusinessEntity(user.id).then(({ data }) => {
      setEntity(data);
      setLoading(false);
    });
  }, [user]);

  const saveEntity = async (updates: Partial<BusinessEntity>) => {
    if (!user) return;
    const { data } = await upsertBusinessEntity(user.id, updates);
    if (data) setEntity(data);
  };

  const TABS: { id: BizTab; label: string; icon: React.ElementType }[] = [
    { id: 'foundation', label: 'Foundation', icon: Building2 },
    { id: 'llc', label: 'LLC Setup', icon: FileText },
    { id: 'credit', label: 'Biz Credit', icon: CreditCard },
    { id: 'vendors', label: 'Vendors', icon: Layers },
  ];

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}><Loader2 size={24} color="#3d5af1" style={{ animation: 'spin 1s linear infinite' }} /></div>;

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Business Foundation</h2>
        <p style={{ fontSize: 14, color: '#8b8fa8', marginTop: 4 }}>Build a lender-ready business identity from the ground up.</p>
      </div>

      <ReadinessScore entity={entity} />

      {/* Tab nav */}
      <div style={{ display: 'flex', gap: 6, background: '#f0f0f8', borderRadius: 14, padding: 4, marginBottom: 20 }}>
        {TABS.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1, padding: '8px 0', borderRadius: 10, border: 'none', cursor: 'pointer',
              background: activeTab === tab.id ? '#fff' : 'transparent',
              color: activeTab === tab.id ? '#3d5af1' : '#8b8fa8',
              fontSize: 12, fontWeight: 700,
              boxShadow: activeTab === tab.id ? '0 2px 8px rgba(60,80,180,0.1)' : 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
            }}>
            <tab.icon size={13} /> {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'foundation' && <FoundationTab entity={entity} onSave={saveEntity} />}
      {activeTab === 'llc' && <LLCSetupTab />}
      {activeTab === 'credit' && user && <BusinessCreditTab userId={user.id} />}
      {activeTab === 'vendors' && user && <VendorTradelinesTab userId={user.id} />}
    </div>
  );
}
