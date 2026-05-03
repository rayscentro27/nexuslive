import React, { useEffect, useState } from 'react';
import {
  UserPlus, Mail, Search, MoreVertical, CheckCircle2,
  Clock, AlertCircle, RefreshCw, Send, Unlock, Lock,
  Loader2, X, Toggle
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../AuthProvider';

interface InvitedUser {
  id: string;
  name: string;
  email: string;
  phone: string | null;
  notes: string | null;
  access_type: string;
  subscription_required: boolean;
  subscription_status: string;
  invite_status: string;
  invite_sent_at: string | null;
  accepted_at: string | null;
  grace_period_days: number;
  auth_user_id: string | null;
  created_at: string;
}

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  pending:   { label: 'Pending',   color: '#f59e0b', bg: '#fffbeb' },
  sent:      { label: 'Sent',      color: '#3d5af1', bg: '#eef0fd' },
  accepted:  { label: 'Accepted',  color: '#22c55e', bg: '#f0fdf4' },
  expired:   { label: 'Expired',   color: '#ef4444', bg: '#fef2f2' },
};

const SUB_META: Record<string, { label: string; color: string }> = {
  waived:       { label: 'Waived',       color: '#22c55e' },
  active:       { label: 'Active',       color: '#3d5af1' },
  grace_period: { label: 'Grace Period', color: '#f59e0b' },
  required:     { label: 'Required',     color: '#ef4444' },
};

function AddInviteModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const { user } = useAuth();
  const [form, setForm] = useState({ name: '', email: '', phone: '', notes: '', grace_period_days: 14 });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim()) { setError('Name and email are required'); return; }
    setSaving(true);
    setError('');
    const signupLink = `${window.location.origin}/?invited=true&email=${encodeURIComponent(form.email)}`;
    const { error: err } = await supabase.from('invited_users').insert({
      name: form.name.trim(),
      email: form.email.trim().toLowerCase(),
      phone: form.phone.trim() || null,
      notes: form.notes.trim() || null,
      access_type: 'free_full_access',
      subscription_required: false,
      subscription_status: 'waived',
      invite_status: 'pending',
      invited_by: user?.id,
      grace_period_days: form.grace_period_days,
      signup_link: signupLink,
    });
    setSaving(false);
    if (err) { setError(err.message); return; }
    onSaved();
    onClose();
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 500,
        background: 'rgba(26,28,58,0.6)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: '#fff', borderRadius: 20, padding: 28, width: '100%', maxWidth: 460,
        boxShadow: '0 20px 60px rgba(60,80,180,0.2)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: '#1a1c3a' }}>Add Invite</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8' }}><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: '#8b8fa8', marginBottom: 4, display: 'block' }}>FULL NAME *</label>
            <input
              value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Jane Smith"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 14, color: '#1a1c3a', outline: 'none', boxSizing: 'border-box' }}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: '#8b8fa8', marginBottom: 4, display: 'block' }}>EMAIL ADDRESS *</label>
            <input
              type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              placeholder="jane@example.com"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 14, color: '#1a1c3a', outline: 'none', boxSizing: 'border-box' }}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: '#8b8fa8', marginBottom: 4, display: 'block' }}>PHONE (OPTIONAL)</label>
            <input
              value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
              placeholder="+1 555 000 0000"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 14, color: '#1a1c3a', outline: 'none', boxSizing: 'border-box' }}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: '#8b8fa8', marginBottom: 4, display: 'block' }}>NOTES (OPTIONAL)</label>
            <textarea
              value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              placeholder="Referral source, context, etc."
              rows={2}
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 14, color: '#1a1c3a', outline: 'none', resize: 'none', boxSizing: 'border-box' }}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: '#8b8fa8', marginBottom: 4, display: 'block' }}>GRACE PERIOD (DAYS)</label>
            <input
              type="number" min={0} max={365} value={form.grace_period_days}
              onChange={e => setForm(f => ({ ...f, grace_period_days: parseInt(e.target.value) || 14 }))}
              style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 14, color: '#1a1c3a', outline: 'none', boxSizing: 'border-box' }}
            />
            <p style={{ fontSize: 11, color: '#8b8fa8', marginTop: 4 }}>Days before subscription billing starts after activation</p>
          </div>
          {error && (
            <div style={{ padding: '10px 14px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontSize: 13 }}>
              {error}
            </div>
          )}
          <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
            <button type="button" onClick={onClose}
              style={{ flex: 1, padding: '11px 0', borderRadius: 10, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 14, fontWeight: 700, color: '#8b8fa8', cursor: 'pointer' }}>
              Cancel
            </button>
            <button type="submit" disabled={saving}
              style={{ flex: 2, padding: '11px 0', borderRadius: 10, border: 'none', background: '#3d5af1', fontSize: 14, fontWeight: 700, color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              {saving ? <Loader2 size={15} className="animate-spin" /> : <UserPlus size={15} />}
              Add Invite
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function SendWelcomeModal({ invite, onClose, onSent }: { invite: InvitedUser; onClose: () => void; onSent: () => void }) {
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const WELCOME_SUBJECT = `Welcome to Nexus — Your Free Full Access Is Ready`;
  const WELCOME_BODY = `Hi ${invite.name},

Welcome to Nexus.

Nexus is a guided financial growth platform designed to help you improve your credit profile, build a fundable business foundation, discover funding opportunities, explore grants, and follow a clear step-by-step action plan.

Your account currently includes free full access. You will not be charged a monthly subscription during this access period.

Inside Nexus, you can:
- Upload and review credit information
- See credit improvement recommendations
- Build your business foundation
- Track funding readiness
- Explore grant opportunities
- Use messaging and support features
- Follow your personalized Action Center

When subscription billing becomes active, we will notify you before any changes are made to your access.

Click below to create your account:
${invite.signup_link ?? window.location.origin}

Welcome to Nexus,
The Nexus Team`;

  const handleSend = async () => {
    setSending(true);
    // Mark invite as sent in DB
    await supabase.from('invited_users').update({
      invite_status: 'sent',
      invite_sent_at: new Date().toISOString(),
    }).eq('id', invite.id);
    setSending(false);
    setSent(true);
    setTimeout(() => { onSent(); onClose(); }, 1500);
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 500,
        background: 'rgba(26,28,58,0.6)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{ background: '#fff', borderRadius: 20, padding: 28, width: '100%', maxWidth: 500, boxShadow: '0 20px 60px rgba(60,80,180,0.2)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: '#1a1c3a' }}>Send Welcome Email</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8' }}><X size={18} /></button>
        </div>
        <div style={{ marginBottom: 16 }}>
          <div style={{ padding: '10px 14px', background: '#f7f8ff', borderRadius: 10, marginBottom: 12 }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: '#8b8fa8', margin: '0 0 4px' }}>TO</p>
            <p style={{ fontSize: 14, color: '#1a1c3a', margin: 0 }}>{invite.name} &lt;{invite.email}&gt;</p>
          </div>
          <div style={{ padding: '10px 14px', background: '#f7f8ff', borderRadius: 10, marginBottom: 12 }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: '#8b8fa8', margin: '0 0 4px' }}>SUBJECT</p>
            <p style={{ fontSize: 14, color: '#1a1c3a', margin: 0 }}>{WELCOME_SUBJECT}</p>
          </div>
          <div style={{ padding: '10px 14px', background: '#f7f8ff', borderRadius: 10, maxHeight: 200, overflowY: 'auto' }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: '#8b8fa8', margin: '0 0 4px' }}>BODY PREVIEW</p>
            <pre style={{ fontSize: 12, color: '#1a1c3a', margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: 1.6 }}>{WELCOME_BODY}</pre>
          </div>
        </div>
        <p style={{ fontSize: 12, color: '#8b8fa8', marginBottom: 16 }}>
          Note: Configure your email service (Resend/SendGrid) in Supabase Edge Functions to deliver this email. The invite status will be updated to "sent" immediately.
        </p>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={onClose}
            style={{ flex: 1, padding: '11px 0', borderRadius: 10, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 14, fontWeight: 700, color: '#8b8fa8', cursor: 'pointer' }}>
            Cancel
          </button>
          <button onClick={handleSend} disabled={sending || sent}
            style={{ flex: 2, padding: '11px 0', borderRadius: 10, border: 'none', background: sent ? '#22c55e' : '#3d5af1', fontSize: 14, fontWeight: 700, color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            {sent ? <><CheckCircle2 size={15} /> Sent!</> : sending ? <Loader2 size={15} className="animate-spin" /> : <><Send size={15} /> Send Welcome Email</>}
          </button>
        </div>
      </div>
    </div>
  );
}

export function AdminInviteUsers() {
  const [invites, setInvites] = useState<InvitedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [sendingWelcome, setSendingWelcome] = useState<InvitedUser | null>(null);
  const [activatingSub, setActivatingSub] = useState<string | null>(null);
  const [actionMenu, setActionMenu] = useState<string | null>(null);

  const fetchInvites = async () => {
    setLoading(true);
    const { data } = await supabase
      .from('invited_users')
      .select('*')
      .order('created_at', { ascending: false });
    setInvites((data ?? []) as InvitedUser[]);
    setLoading(false);
  };

  useEffect(() => { fetchInvites(); }, []);

  const filtered = invites.filter(i =>
    !search ||
    i.name.toLowerCase().includes(search.toLowerCase()) ||
    i.email.toLowerCase().includes(search.toLowerCase())
  );

  const activateSubscription = async (invite: InvitedUser) => {
    setActivatingSub(invite.id);
    const gracePeriodEndsAt = new Date(Date.now() + invite.grace_period_days * 86400000).toISOString();
    await supabase.from('invited_users').update({
      subscription_required: true,
      subscription_status: 'grace_period',
      grace_period_ends_at: gracePeriodEndsAt,
    }).eq('id', invite.id);

    // Create in-app notification if user has signed up
    if (invite.auth_user_id) {
      await supabase.from('notifications').insert({
        user_id: invite.auth_user_id,
        type: 'subscription',
        title: 'Subscription Activation Notice',
        body: `Your Nexus free access period is ending. Subscription billing will begin in ${invite.grace_period_days} days.`,
        priority: 3,
        action_label: 'View Billing',
        action_url: '/settings',
      });

      // Also create override record
      await supabase.from('user_access_overrides').upsert({
        user_id: invite.auth_user_id,
        subscription_required: true,
        subscription_status: 'grace_period',
        access_type: 'grace_period',
        override_reason: 'Subscription activation from admin',
        effective_until: gracePeriodEndsAt,
      }, { onConflict: 'user_id' });
    }
    await fetchInvites();
    setActivatingSub(null);
    setActionMenu(null);
  };

  const revokeAccess = async (invite: InvitedUser) => {
    await supabase.from('invited_users').update({
      subscription_required: true,
      subscription_status: 'required',
    }).eq('id', invite.id);
    if (invite.auth_user_id) {
      await supabase.from('user_access_overrides').upsert({
        user_id: invite.auth_user_id,
        subscription_required: true,
        subscription_status: 'required',
        access_type: 'subscription',
        override_reason: 'Free access revoked by admin',
      }, { onConflict: 'user_id' });
    }
    await fetchInvites();
    setActionMenu(null);
  };

  const restoreAccess = async (invite: InvitedUser) => {
    await supabase.from('invited_users').update({
      subscription_required: false,
      subscription_status: 'waived',
    }).eq('id', invite.id);
    if (invite.auth_user_id) {
      await supabase.from('user_access_overrides').upsert({
        user_id: invite.auth_user_id,
        subscription_required: false,
        subscription_status: 'waived',
        access_type: 'free_full_access',
        override_reason: 'Free access restored by admin',
      }, { onConflict: 'user_id' });
    }
    await fetchInvites();
    setActionMenu(null);
  };

  const stats = {
    total: invites.length,
    pending: invites.filter(i => i.invite_status === 'pending').length,
    accepted: invites.filter(i => i.invite_status === 'accepted').length,
    freeAccess: invites.filter(i => !i.subscription_required).length,
  };

  return (
    <div style={{ padding: '32px', background: '#f8faff', minHeight: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Pilot Invites</h1>
          <p style={{ fontSize: 14, color: '#8b8fa8', marginTop: 4 }}>
            Manage free full access invitations for early users.
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px',
            background: '#3d5af1', color: '#fff', borderRadius: 12, border: 'none',
            cursor: 'pointer', fontSize: 14, fontWeight: 700,
            boxShadow: '0 4px 12px rgba(61,90,241,0.3)',
          }}
        >
          <UserPlus size={16} /> Add Invite
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
        {[
          { label: 'Total Invited', value: stats.total, color: '#3d5af1', bg: '#eef0fd' },
          { label: 'Pending', value: stats.pending, color: '#f59e0b', bg: '#fffbeb' },
          { label: 'Accepted', value: stats.accepted, color: '#22c55e', bg: '#f0fdf4' },
          { label: 'Free Access', value: stats.freeAccess, color: '#6366f1', bg: '#ede9fe' },
        ].map(s => (
          <div key={s.label} style={{
            background: '#fff', borderRadius: 14, padding: '16px 20px',
            border: '1px solid #e8e9f2', boxShadow: '0 2px 8px rgba(60,80,180,0.06)',
          }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: s.color, marginBottom: 4 }}>{s.value}</div>
            <div style={{ fontSize: 13, color: '#8b8fa8', fontWeight: 600 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div style={{
        background: '#fff', borderRadius: 14, padding: '12px 16px',
        border: '1px solid #e8e9f2', marginBottom: 16,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <Search size={16} color="#8b8fa8" />
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search by name or email..."
          style={{ flex: 1, border: 'none', outline: 'none', fontSize: 14, color: '#1a1c3a', background: 'transparent' }}
        />
        {search && (
          <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8' }}>
            <X size={14} />
          </button>
        )}
      </div>

      {/* Table */}
      <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e8e9f2', overflow: 'hidden', boxShadow: '0 2px 8px rgba(60,80,180,0.06)' }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <Loader2 size={24} color="#3d5af1" style={{ animation: 'spin 1s linear infinite', margin: '0 auto' }} />
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <UserPlus size={32} color="#c7d2fe" style={{ margin: '0 auto 12px' }} />
            <p style={{ fontSize: 15, color: '#8b8fa8', fontWeight: 500 }}>No invites yet</p>
            <button
              onClick={() => setShowAdd(true)}
              style={{ marginTop: 12, padding: '10px 24px', background: '#3d5af1', color: '#fff', borderRadius: 10, border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: 700 }}
            >
              Add First Invite
            </button>
          </div>
        ) : (
          <>
            {/* Table header */}
            <div style={{
              display: 'grid', gridTemplateColumns: '200px 180px 120px 120px 100px 60px',
              padding: '12px 20px', borderBottom: '1px solid #f0f0f8',
              fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '0.06em',
            }}>
              <span>Person</span>
              <span>Email</span>
              <span>Invite Status</span>
              <span>Access</span>
              <span>Subscription</span>
              <span></span>
            </div>
            {filtered.map(invite => {
              const statusMeta = STATUS_META[invite.invite_status] ?? STATUS_META.pending;
              const subMeta = SUB_META[invite.subscription_status] ?? SUB_META.waived;
              return (
                <div
                  key={invite.id}
                  style={{
                    display: 'grid', gridTemplateColumns: '200px 180px 120px 120px 100px 60px',
                    padding: '14px 20px', borderBottom: '1px solid #f8f8fd',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{invite.name}</p>
                    {invite.phone && <p style={{ fontSize: 12, color: '#8b8fa8', margin: 0 }}>{invite.phone}</p>}
                  </div>
                  <div style={{ overflow: 'hidden' }}>
                    <p style={{ fontSize: 13, color: '#1a1c3a', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{invite.email}</p>
                    {invite.auth_user_id && (
                      <span style={{ fontSize: 11, color: '#22c55e', fontWeight: 600 }}>● Signed up</span>
                    )}
                  </div>
                  <div>
                    <span style={{
                      padding: '3px 10px', borderRadius: 20,
                      background: statusMeta.bg, color: statusMeta.color,
                      fontSize: 12, fontWeight: 700,
                    }}>{statusMeta.label}</span>
                  </div>
                  <div>
                    <span style={{
                      fontSize: 12, fontWeight: 700,
                      color: invite.subscription_required ? '#ef4444' : '#22c55e',
                    }}>
                      {invite.subscription_required ? '🔒 Restricted' : '✓ Free Full'}
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: subMeta.color }}>{subMeta.label}</span>
                  </div>
                  <div style={{ position: 'relative' }}>
                    <button
                      onClick={() => setActionMenu(actionMenu === invite.id ? null : invite.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8', padding: 6, borderRadius: 8 }}
                    >
                      <MoreVertical size={16} />
                    </button>
                    {actionMenu === invite.id && (
                      <div style={{
                        position: 'absolute', right: 0, top: 32, zIndex: 100,
                        background: '#fff', borderRadius: 12, border: '1px solid #e8e9f2',
                        boxShadow: '0 8px 32px rgba(60,80,180,0.12)',
                        minWidth: 200, overflow: 'hidden',
                      }}>
                        {[
                          {
                            icon: Mail, label: 'Send Welcome Email',
                            action: () => { setSendingWelcome(invite); setActionMenu(null); },
                            color: '#3d5af1',
                          },
                          {
                            icon: RefreshCw, label: 'Resend Invite',
                            action: () => { setSendingWelcome(invite); setActionMenu(null); },
                            color: '#6366f1',
                          },
                          ...(!invite.subscription_required ? [{
                            icon: AlertCircle, label: 'Activate Subscription',
                            action: () => activateSubscription(invite),
                            color: '#f59e0b',
                            loading: activatingSub === invite.id,
                          }] : [{
                            icon: Unlock, label: 'Restore Free Access',
                            action: () => restoreAccess(invite),
                            color: '#22c55e',
                          }]),
                          ...(!invite.subscription_required ? [{
                            icon: Lock, label: 'Revoke Access',
                            action: () => revokeAccess(invite),
                            color: '#ef4444',
                          }] : []),
                        ].map(item => (
                          <button
                            key={item.label}
                            onClick={item.action}
                            disabled={'loading' in item && !!item.loading}
                            style={{
                              width: '100%', padding: '11px 16px', background: 'none', border: 'none',
                              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
                              fontSize: 13, fontWeight: 600, color: item.color,
                              borderBottom: '1px solid #f8f8fd',
                            }}
                          >
                            {'loading' in item && item.loading
                              ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                              : <item.icon size={14} />
                            }
                            {item.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>

      {showAdd && (
        <AddInviteModal onClose={() => setShowAdd(false)} onSaved={fetchInvites} />
      )}
      {sendingWelcome && (
        <SendWelcomeModal
          invite={sendingWelcome}
          onClose={() => setSendingWelcome(null)}
          onSent={fetchInvites}
        />
      )}
    </div>
  );
}
