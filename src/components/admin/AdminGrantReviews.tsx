import React, { useEffect, useState } from 'react';
import { Search, CheckCircle2, Clock, MessageSquare, Loader2, ArrowRight, X } from 'lucide-react';
import { supabase } from '../../lib/supabase';

interface GrantRequest {
  id: string;
  user_id: string;
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

export function AdminGrantReviews() {
  const [requests, setRequests] = useState<GrantRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [responding, setResponding] = useState<string | null>(null);
  const [response, setResponse] = useState('');

  useEffect(() => {
    supabase
      .from('grant_review_requests')
      .select('*')
      .order('created_at', { ascending: false })
      .then(({ data }) => {
        setRequests((data ?? []) as GrantRequest[]);
        setLoading(false);
      });
  }, []);

  const submitResponse = async (req: GrantRequest) => {
    if (!response.trim()) return;
    await supabase.from('grant_review_requests').update({
      status: 'completed',
      response: response.trim(),
      completed_at: new Date().toISOString(),
    }).eq('id', req.id);

    // Notify user
    await supabase.from('notifications').insert({
      user_id: req.user_id,
      type: 'grant',
      title: 'Grant Research Complete',
      body: 'Your grant research request has been completed. View results in the Grants section.',
      priority: 2,
      action_url: '/grants',
      action_label: 'View Results',
    });

    setRequests(prev => prev.map(r => r.id === req.id ? { ...r, status: 'completed', response: response.trim() } : r));
    setResponding(null);
    setResponse('');
  };

  return (
    <div style={{ padding: 32 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Grant Review Requests</h1>
        <p style={{ fontSize: 14, color: '#8b8fa8', marginTop: 4 }}>
          Review and respond to client grant research requests.
        </p>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 24 }}>
        {[
          { label: 'Total', value: requests.length, color: '#3d5af1' },
          { label: 'Pending', value: requests.filter(r => r.status === 'pending').length, color: '#f59e0b' },
          { label: 'Completed', value: requests.filter(r => r.status === 'completed').length, color: '#22c55e' },
        ].map(s => (
          <div key={s.label} style={{ background: '#fff', borderRadius: 14, padding: '16px 20px', border: '1px solid #e8e9f2' }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 13, color: '#8b8fa8', fontWeight: 600 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: 'center' }}><Loader2 size={24} color="#3d5af1" style={{ animation: 'spin 1s linear infinite', margin: '0 auto' }} /></div>
      ) : requests.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', background: '#fff', borderRadius: 16, border: '1px solid #e8e9f2' }}>
          <Search size={28} color="#c7d2fe" style={{ margin: '0 auto 12px' }} />
          <p style={{ fontSize: 14, color: '#8b8fa8' }}>No requests yet</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {requests.map(req => (
            <div key={req.id} style={{ background: '#fff', borderRadius: 16, border: `1px solid ${req.status === 'pending' ? '#fde68a' : '#e8e9f2'}`, padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                  {req.keyword && <p style={{ fontSize: 16, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>"{req.keyword}"</p>}
                  {req.business_type && <p style={{ fontSize: 13, color: '#8b8fa8', margin: '2px 0 0' }}>{req.business_type}</p>}
                  {(req.city || req.state) && <p style={{ fontSize: 12, color: '#8b8fa8', margin: '2px 0 0' }}>{[req.city, req.state].filter(Boolean).join(', ')}</p>}
                  {req.grant_url && <a href={req.grant_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, color: '#3d5af1', display: 'block', marginTop: 2 }}>{req.grant_url}</a>}
                </div>
                <span style={{
                  padding: '4px 12px', borderRadius: 20,
                  background: req.status === 'pending' ? '#fffbeb' : '#f0fdf4',
                  color: req.status === 'pending' ? '#f59e0b' : '#22c55e',
                  fontSize: 12, fontWeight: 700,
                }}>{req.status === 'pending' ? 'Pending' : 'Complete'}</span>
              </div>
              {req.notes && <p style={{ fontSize: 13, color: '#8b8fa8', marginBottom: 12, padding: '10px 14px', background: '#f7f8ff', borderRadius: 10 }}>{req.notes}</p>}
              {req.response && (
                <div style={{ padding: '10px 14px', background: '#f0fdf4', borderRadius: 10, border: '1px solid #bbf7d0', marginBottom: 12 }}>
                  <p style={{ fontSize: 12, fontWeight: 700, color: '#16a34a', margin: '0 0 4px' }}>Your Response</p>
                  <p style={{ fontSize: 13, color: '#1a1c3a', margin: 0, lineHeight: 1.5 }}>{req.response}</p>
                </div>
              )}
              {req.status === 'pending' && (
                responding === req.id ? (
                  <div>
                    <textarea
                      value={response} onChange={e => setResponse(e.target.value)}
                      placeholder="Enter grant research results, recommended grants, eligibility notes..."
                      rows={4}
                      style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 13, color: '#1a1c3a', outline: 'none', resize: 'vertical', marginBottom: 10, boxSizing: 'border-box', fontFamily: 'inherit' }}
                    />
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button onClick={() => { setResponding(null); setResponse(''); }}
                        style={{ flex: 1, padding: '9px 0', borderRadius: 10, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 13, fontWeight: 700, color: '#8b8fa8', cursor: 'pointer' }}>
                        Cancel
                      </button>
                      <button onClick={() => submitResponse(req)}
                        style={{ flex: 2, padding: '9px 0', borderRadius: 10, border: 'none', background: '#3d5af1', fontSize: 13, fontWeight: 700, color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                        <CheckCircle2 size={14} /> Send Response
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setResponding(req.id)}
                    style={{ padding: '9px 18px', borderRadius: 10, border: 'none', background: '#3d5af1', fontSize: 13, fontWeight: 700, color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}
                  >
                    <MessageSquare size={14} /> Respond to Request
                  </button>
                )
              )}
              <p style={{ fontSize: 11, color: '#c7d2fe', marginTop: 8 }}>Submitted {new Date(req.created_at).toLocaleDateString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
