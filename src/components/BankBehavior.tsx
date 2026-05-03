import React, { useState, useEffect, useCallback } from 'react';
import {
  Landmark, Plus, Loader2, CheckCircle2, AlertCircle,
  TrendingUp, TrendingDown, Info,
} from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthProvider';

interface Snapshot {
  id: string;
  bank_name: string | null;
  average_balance: number | null;
  monthly_deposits: number | null;
  monthly_withdrawals: number | null;
  overdraft_count: number;
  nsf_count: number;
  deposit_consistency: string | null;
  bank_readiness_score: number;
  snapshot_month: string | null;
  notes: string | null;
  created_at: string;
}

const CONSISTENCY_OPTIONS = ['excellent', 'good', 'fair', 'poor'];

function scoreColor(score: number) {
  return score >= 75 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444';
}

function calcScore(form: FormState): number {
  let score = 0;
  const bal = parseFloat(form.average_balance) || 0;
  const nsf = parseInt(form.nsf_count) || 0;
  const od  = parseInt(form.overdraft_count) || 0;

  if (bal >= 10000) score += 30;
  else if (bal >= 5000) score += 20;
  else if (bal >= 1000) score += 10;

  if (form.deposit_consistency === 'excellent') score += 30;
  else if (form.deposit_consistency === 'good') score += 20;
  else if (form.deposit_consistency === 'fair') score += 10;

  if (nsf === 0 && od === 0) score += 25;
  else if (nsf <= 1 && od <= 1) score += 15;
  else if (nsf <= 3 && od <= 3) score += 5;

  const dep = parseFloat(form.monthly_deposits) || 0;
  if (dep >= 10000) score += 15;
  else if (dep >= 5000) score += 10;
  else if (dep >= 2000) score += 5;

  return Math.min(100, score);
}

interface FormState {
  bank_name: string;
  average_balance: string;
  monthly_deposits: string;
  monthly_withdrawals: string;
  overdraft_count: string;
  nsf_count: string;
  deposit_consistency: string;
  snapshot_month: string;
  notes: string;
}

const EMPTY_FORM: FormState = {
  bank_name: '',
  average_balance: '',
  monthly_deposits: '',
  monthly_withdrawals: '',
  overdraft_count: '0',
  nsf_count: '0',
  deposit_consistency: 'good',
  snapshot_month: new Date().toISOString().slice(0, 7),
  notes: '',
};

export function BankBehavior() {
  const { user } = useAuth();
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [showForm,  setShowForm]  = useState(false);
  const [form,      setForm]      = useState<FormState>(EMPTY_FORM);
  const [saving,    setSaving]    = useState(false);
  const [saved,     setSaved]     = useState(false);

  const load = useCallback(async () => {
    if (!user) return;
    const { data } = await supabase
      .from('bank_behavior_snapshots')
      .select('*')
      .eq('user_id', user.id)
      .order('snapshot_month', { ascending: false });
    setSnapshots((data ?? []) as Snapshot[]);
    setLoading(false);
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const handleChange = (field: keyof FormState, value: string) =>
    setForm(prev => ({ ...prev, [field]: value }));

  const handleSave = async () => {
    if (!user) return;
    setSaving(true);
    const score = calcScore(form);
    await supabase.from('bank_behavior_snapshots').insert({
      user_id:              user.id,
      bank_name:            form.bank_name || null,
      average_balance:      parseFloat(form.average_balance) || null,
      monthly_deposits:     parseFloat(form.monthly_deposits) || null,
      monthly_withdrawals:  parseFloat(form.monthly_withdrawals) || null,
      overdraft_count:      parseInt(form.overdraft_count) || 0,
      nsf_count:            parseInt(form.nsf_count) || 0,
      deposit_consistency:  form.deposit_consistency || null,
      bank_readiness_score: score,
      snapshot_month:       form.snapshot_month || null,
      notes:                form.notes || null,
    });
    setSaving(false);
    setSaved(true);
    setShowForm(false);
    setForm(EMPTY_FORM);
    setTimeout(() => setSaved(false), 3000);
    load();
  };

  const previewScore = calcScore(form);

  return (
    <div style={{ padding: 24, maxWidth: 680, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Bank Behavior</h1>
          <p style={{ fontSize: 13, color: '#8b8fa8', marginTop: 4 }}>
            Track your banking patterns — lenders review 3–6 months of statements.
          </p>
        </div>
        <button
          onClick={() => setShowForm(v => !v)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '9px 16px', borderRadius: 12, border: 'none',
            background: '#3d5af1', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer',
          }}
        >
          <Plus size={14} /> Add Month
        </button>
      </div>

      {/* Success toast */}
      {saved && (
        <div style={{ marginBottom: 16, padding: '10px 16px', borderRadius: 12, background: '#f0fdf4', border: '1px solid #bbf7d0', display: 'flex', gap: 8, alignItems: 'center' }}>
          <CheckCircle2 size={16} color="#22c55e" />
          <span style={{ fontSize: 13, color: '#16a34a', fontWeight: 600 }}>Snapshot saved successfully.</span>
        </div>
      )}

      {/* Add Form */}
      {showForm && (
        <div style={{ background: '#fff', borderRadius: 20, border: '1px solid #e8e9f2', padding: 24, marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>New Month Snapshot</h3>
            {/* Live score preview */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 11, color: '#8b8fa8', fontWeight: 600 }}>Bank Score:</span>
              <span style={{ fontSize: 20, fontWeight: 800, color: scoreColor(previewScore) }}>{previewScore}</span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { label: 'Bank Name',         field: 'bank_name',           type: 'text',   placeholder: 'Chase, BofA, etc.' },
              { label: 'Month (YYYY-MM)',   field: 'snapshot_month',      type: 'month',  placeholder: '' },
              { label: 'Avg Daily Balance', field: 'average_balance',     type: 'number', placeholder: '5000' },
              { label: 'Monthly Deposits',  field: 'monthly_deposits',    type: 'number', placeholder: '8000' },
              { label: 'Monthly Withdrawals', field: 'monthly_withdrawals', type: 'number', placeholder: '6000' },
              { label: 'Overdraft Count',   field: 'overdraft_count',     type: 'number', placeholder: '0' },
              { label: 'NSF Count',         field: 'nsf_count',           type: 'number', placeholder: '0' },
            ].map(f => (
              <div key={f.field}>
                <label style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', display: 'block', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>{f.label}</label>
                <input
                  type={f.type}
                  value={form[f.field as keyof FormState]}
                  onChange={e => handleChange(f.field as keyof FormState, e.target.value)}
                  placeholder={f.placeholder}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 13, color: '#1a1c3a', outline: 'none', boxSizing: 'border-box' }}
                />
              </div>
            ))}

            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', display: 'block', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>Deposit Consistency</label>
              <select
                value={form.deposit_consistency}
                onChange={e => handleChange('deposit_consistency', e.target.value)}
                style={{ width: '100%', padding: '9px 12px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 13, color: '#1a1c3a', outline: 'none', background: '#fff', boxSizing: 'border-box' }}
              >
                {CONSISTENCY_OPTIONS.map(o => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>)}
              </select>
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', display: 'block', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>Notes</label>
            <textarea
              value={form.notes}
              onChange={e => handleChange('notes', e.target.value)}
              placeholder="Any context about this month..."
              rows={2}
              style={{ width: '100%', padding: '9px 12px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 13, color: '#1a1c3a', outline: 'none', resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }}
            />
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button
              onClick={() => setShowForm(false)}
              style={{ flex: 1, padding: '10px 0', borderRadius: 10, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 13, fontWeight: 700, color: '#8b8fa8', cursor: 'pointer' }}
            >Cancel</button>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{ flex: 2, padding: '10px 0', borderRadius: 10, border: 'none', background: '#3d5af1', fontSize: 13, fontWeight: 700, color: '#fff', cursor: saving ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
            >
              {saving ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <CheckCircle2 size={14} />}
              {saving ? 'Saving…' : 'Save Snapshot'}
            </button>
          </div>
        </div>
      )}

      {/* Tip */}
      <div style={{ padding: '10px 14px', borderRadius: 12, background: '#fffbeb', border: '1px solid #fde68a', display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 20 }}>
        <Info size={14} color="#f59e0b" style={{ flexShrink: 0, marginTop: 1 }} />
        <p style={{ fontSize: 12, color: '#92400e', margin: 0 }}>
          Lenders want to see consistent deposits, average balance above $1,000, and zero NSF/overdraft events for the past 3–6 months.
          Enter one snapshot per month for best tracking.
        </p>
      </div>

      {/* Snapshots list */}
      {loading ? (
        <div style={{ padding: 40, textAlign: 'center' }}>
          <Loader2 size={24} color="#3d5af1" style={{ animation: 'spin 1s linear infinite', margin: '0 auto' }} />
        </div>
      ) : snapshots.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', background: '#fff', borderRadius: 16, border: '1px solid #e8e9f2' }}>
          <Landmark size={28} color="#c7d2fe" style={{ margin: '0 auto 12px' }} />
          <p style={{ fontSize: 14, color: '#8b8fa8' }}>No snapshots yet. Add your first month above.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {snapshots.map(s => (
            <div key={s.id} style={{ background: '#fff', borderRadius: 16, border: '1px solid #e8e9f2', padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                  <p style={{ fontSize: 15, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>
                    {s.bank_name ?? 'Bank'} {s.snapshot_month && `· ${s.snapshot_month}`}
                  </p>
                  {s.deposit_consistency && (
                    <p style={{ fontSize: 11, color: '#8b8fa8', margin: '2px 0 0' }}>
                      Consistency: <strong style={{ textTransform: 'capitalize' }}>{s.deposit_consistency}</strong>
                    </p>
                  )}
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 22, fontWeight: 800, color: scoreColor(s.bank_readiness_score) }}>{s.bank_readiness_score}</div>
                  <div style={{ fontSize: 10, color: '#8b8fa8', fontWeight: 600 }}>Bank Score</div>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                {[
                  { label: 'Avg Balance', value: s.average_balance != null ? `$${s.average_balance.toLocaleString()}` : '—', icon: <Landmark size={12} color="#3d5af1" /> },
                  { label: 'Deposits', value: s.monthly_deposits != null ? `$${s.monthly_deposits.toLocaleString()}` : '—', icon: <TrendingUp size={12} color="#22c55e" /> },
                  { label: 'Withdrawals', value: s.monthly_withdrawals != null ? `$${s.monthly_withdrawals.toLocaleString()}` : '—', icon: <TrendingDown size={12} color="#f59e0b" /> },
                  { label: 'NSF / OD', value: `${s.nsf_count} / ${s.overdraft_count}`, icon: <AlertCircle size={12} color={s.nsf_count + s.overdraft_count > 0 ? '#ef4444' : '#22c55e'} /> },
                ].map(m => (
                  <div key={m.label} style={{ background: '#f7f8ff', borderRadius: 10, padding: '8px 10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>{m.icon}<span style={{ fontSize: 10, color: '#8b8fa8', fontWeight: 600 }}>{m.label}</span></div>
                    <div style={{ fontSize: 13, fontWeight: 800, color: '#1a1c3a' }}>{m.value}</div>
                  </div>
                ))}
              </div>
              {s.notes && <p style={{ fontSize: 12, color: '#8b8fa8', marginTop: 10 }}>{s.notes}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
