import React, { useState, useEffect } from 'react';
import { Search, Send, CheckCircle2, Clock, Loader2, X, AlertCircle } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthProvider';

interface GrantRequest {
  id: string;
  keyword: string | null;
  business_type: string | null;
  city: string | null;
  state: string | null;
  grant_url: string | null;
  notes: string | null;
  status: string;
  response: string | null;
  created_at: string;
  completed_at: string | null;
}

const STATUS_META: Record<string, { label: string; color: string; bg: string; icon: React.ElementType }> = {
  pending:     { label: 'Submitted',   color: '#f59e0b', bg: '#fffbeb', icon: Clock },
  in_progress: { label: 'Researching', color: '#3d5af1', bg: '#eef0fd', icon: Search },
  completed:   { label: 'Complete',    color: '#22c55e', bg: '#f0fdf4', icon: CheckCircle2 },
  cancelled:   { label: 'Cancelled',   color: '#8b8fa8', bg: '#f7f8ff', icon: X },
};

export function GrantResearchRequest() {
  const { user } = useAuth();
  const [requests, setRequests] = useState<GrantRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    keyword: '',
    business_type: '',
    city: '',
    state: '',
    grant_url: '',
    notes: '',
  });

  const fetchRequests = async () => {
    if (!user) return;
    const { data } = await supabase
      .from('grant_review_requests')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false });
    setRequests((data ?? []) as GrantRequest[]);
    setLoading(false);
  };

  useEffect(() => { fetchRequests(); }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setSubmitting(true);
    await supabase.from('grant_review_requests').insert({
      user_id: user.id,
      keyword: form.keyword.trim() || null,
      business_type: form.business_type.trim() || null,
      city: form.city.trim() || null,
      state: form.state.trim() || null,
      grant_url: form.grant_url.trim() || null,
      notes: form.notes.trim() || null,
      status: 'pending',
    });

    // Create notification
    await supabase.from('notifications').insert({
      user_id: user.id,
      type: 'grant',
      title: 'Grant Research Request Submitted',
      body: 'Our team will research grants matching your criteria within 24-48 hours.',
      priority: 2,
    });

    setForm({ keyword: '', business_type: '', city: '', state: '', grant_url: '', notes: '' });
    setShowForm(false);
    setSubmitting(false);
    fetchRequests();
  };

  return (
    <div style={{ padding: '20px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Grant Research Requests</h2>
          <p style={{ fontSize: 13, color: '#8b8fa8', marginTop: 3 }}>
            Submit a research request and our team will find matching grants within 24-48 hours.
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 18px', borderRadius: 12, border: 'none',
            background: '#3d5af1', color: '#fff', cursor: 'pointer',
            fontSize: 13, fontWeight: 700, boxShadow: '0 4px 12px rgba(61,90,241,0.3)',
          }}
        >
          <Search size={15} /> Request Research
        </button>
      </div>

      {/* SLA notice */}
      <div style={{ padding: '10px 14px', background: '#eef0fd', border: '1px solid #c7d2fe', borderRadius: 10, marginBottom: 16, display: 'flex', gap: 8, alignItems: 'center' }}>
        <AlertCircle size={14} color="#3d5af1" />
        <p style={{ fontSize: 12, color: '#3d5af1', fontWeight: 600, margin: 0 }}>
          Research requests are processed by our team — not live API calls. Results typically arrive within 24-48 hours.
        </p>
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: 'center' }}>
          <Loader2 size={20} color="#3d5af1" style={{ animation: 'spin 1s linear infinite', margin: '0 auto' }} />
        </div>
      ) : requests.length === 0 ? (
        <div style={{ padding: '32px 20px', textAlign: 'center', background: '#fff', borderRadius: 14, border: '1px solid #e8e9f2' }}>
          <Search size={28} color="#c7d2fe" style={{ margin: '0 auto 12px' }} />
          <p style={{ fontSize: 14, color: '#8b8fa8', fontWeight: 500, marginBottom: 16 }}>No research requests yet</p>
          <button
            onClick={() => setShowForm(true)}
            style={{ padding: '10px 24px', borderRadius: 10, border: 'none', background: '#3d5af1', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}
          >
            Submit First Request
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {requests.map(req => {
            const meta = STATUS_META[req.status] ?? STATUS_META.pending;
            const MetaIcon = meta.icon;
            return (
              <div key={req.id} style={{
                padding: 18, background: '#fff', borderRadius: 14, border: '1px solid #e8e9f2',
                boxShadow: '0 2px 8px rgba(60,80,180,0.05)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div>
                    {req.keyword && <p style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>"{req.keyword}"</p>}
                    {req.business_type && <p style={{ fontSize: 13, color: '#8b8fa8', margin: '2px 0 0' }}>{req.business_type}</p>}
                    {(req.city || req.state) && (
                      <p style={{ fontSize: 12, color: '#8b8fa8', margin: '2px 0 0' }}>
                        {[req.city, req.state].filter(Boolean).join(', ')}
                      </p>
                    )}
                  </div>
                  <span style={{
                    display: 'flex', alignItems: 'center', gap: 5,
                    padding: '4px 10px', borderRadius: 20,
                    background: meta.bg, color: meta.color,
                    fontSize: 11, fontWeight: 700,
                  }}>
                    <MetaIcon size={11} /> {meta.label}
                  </span>
                </div>
                {req.notes && (
                  <p style={{ fontSize: 12, color: '#8b8fa8', margin: '0 0 8px', lineHeight: 1.5 }}>
                    <strong style={{ color: '#1a1c3a' }}>Notes:</strong> {req.notes}
                  </p>
                )}
                {req.response && (
                  <div style={{ padding: '10px 14px', background: '#f0fdf4', borderRadius: 10, border: '1px solid #bbf7d0', marginTop: 8 }}>
                    <p style={{ fontSize: 12, fontWeight: 700, color: '#16a34a', margin: '0 0 4px' }}>Research Results</p>
                    <p style={{ fontSize: 13, color: '#1a1c3a', margin: 0, lineHeight: 1.5 }}>{req.response}</p>
                  </div>
                )}
                <p style={{ fontSize: 11, color: '#c7d2fe', margin: '8px 0 0' }}>
                  Submitted {new Date(req.created_at).toLocaleDateString()}
                  {req.completed_at && ` · Completed ${new Date(req.completed_at).toLocaleDateString()}`}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Submit Form Modal */}
      {showForm && (
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 500, background: 'rgba(26,28,58,0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}
          onClick={e => { if (e.target === e.currentTarget) setShowForm(false); }}
        >
          <div style={{ background: '#fff', borderRadius: 20, padding: 28, width: '100%', maxWidth: 480, boxShadow: '0 20px 60px rgba(60,80,180,0.2)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 style={{ fontSize: 18, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Request Grant Research</h2>
              <button onClick={() => setShowForm(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8' }}><X size={18} /></button>
            </div>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[
                { key: 'keyword', label: 'KEYWORDS', placeholder: 'e.g. woman-owned, tech startup, green energy' },
                { key: 'business_type', label: 'BUSINESS TYPE', placeholder: 'e.g. LLC, retail, tech, restaurant' },
                { key: 'city', label: 'CITY', placeholder: 'e.g. Atlanta' },
                { key: 'state', label: 'STATE', placeholder: 'e.g. GA' },
                { key: 'grant_url', label: 'SPECIFIC GRANT URL (OPTIONAL)', placeholder: 'https://...' },
              ].map(field => (
                <div key={field.key}>
                  <label style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', display: 'block', marginBottom: 4 }}>{field.label}</label>
                  <input
                    value={(form as any)[field.key]}
                    onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                    placeholder={field.placeholder}
                    style={{ width: '100%', padding: '9px 12px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 13, color: '#1a1c3a', outline: 'none', boxSizing: 'border-box' }}
                  />
                </div>
              ))}
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', display: 'block', marginBottom: 4 }}>ADDITIONAL NOTES</label>
                <textarea
                  value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                  placeholder="Any other details about your business, goals, or grant requirements..."
                  rows={3}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 13, color: '#1a1c3a', outline: 'none', resize: 'none', boxSizing: 'border-box' }}
                />
              </div>
              <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                <button type="button" onClick={() => setShowForm(false)}
                  style={{ flex: 1, padding: '11px 0', borderRadius: 10, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 14, fontWeight: 700, color: '#8b8fa8', cursor: 'pointer' }}>
                  Cancel
                </button>
                <button type="submit" disabled={submitting}
                  style={{ flex: 2, padding: '11px 0', borderRadius: 10, border: 'none', background: '#3d5af1', fontSize: 14, fontWeight: 700, color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                  {submitting ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={15} />}
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
