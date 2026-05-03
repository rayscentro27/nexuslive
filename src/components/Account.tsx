import React, { useState, useEffect } from 'react';
import { User, Mail, Building2, Shield, CreditCard, Bell, Globe, LogOut, ChevronRight, CheckCircle2, Pencil, Save, X, Loader2, Star } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from './AuthProvider';
import { getProfile, updateProfile, getBusinessEntity, UserProfile, BusinessEntity } from '../lib/db';
import { supabase } from '../lib/supabase';

export function Account() {
  const { user, signOut } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [business, setBusiness] = useState<BusinessEntity | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [nameInput, setNameInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [hasPilotAccess, setHasPilotAccess] = useState(false);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      getProfile(user.id),
      getBusinessEntity(user.id),
      supabase.from('user_access_overrides').select('subscription_required').eq('user_id', user.id).maybeSingle(),
    ]).then(([{ data: p }, { data: b }, { data: override }]) => {
      setProfile(p);
      setBusiness(b);
      setNameInput(p?.full_name ?? user.user_metadata?.full_name ?? '');
      setHasPilotAccess(override?.subscription_required === false);
      setLoading(false);
    });
  }, [user]);

  const handleSaveName = async () => {
    if (!user || !nameInput.trim()) return;
    setSaving(true);
    const { data } = await updateProfile(user.id, { full_name: nameInput.trim() });
    if (data) setProfile(data);
    setSaving(false);
    setEditing(false);
  };

  const displayName = profile?.full_name || user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User';
  const email = user?.email ?? '';
  const avatarUrl = profile?.avatar_url || user?.user_metadata?.avatar_url;
  const planLabel = profile?.subscription_plan ?? 'free';
  const roleLabel = profile?.role ?? 'client';

  const planColors: Record<string, string> = {
    free: 'bg-slate-100 text-slate-600',
    starter: 'bg-green-50 text-green-600',
    pro: 'bg-blue-50 text-blue-600',
  };

  return (
    <div className="p-4 max-w-6xl mx-auto space-y-4 h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex flex-col space-y-1 shrink-0">
        <h1 className="text-xl font-black text-[#1A2244]">Review Profile</h1>
        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Manage your personal and professional identity.</p>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-4">
            {/* Profile Card */}
            <div className="glass-card p-5">
              <div className="flex items-center gap-6">
                <div className="relative shrink-0">
                  {avatarUrl ? (
                    <img
                      src={avatarUrl}
                      alt={displayName}
                      className="w-24 h-24 rounded-2xl object-cover border-2 border-white shadow-lg"
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <div className="w-24 h-24 rounded-2xl bg-[#C5C9F7] flex items-center justify-center border-2 border-white shadow-lg">
                      <span className="text-3xl font-black text-[#5B7CFA]">
                        {displayName.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  )}
                  <div className="absolute -bottom-1 -right-1 bg-green-500 text-white p-1 rounded-lg border-2 border-white">
                    <CheckCircle2 className="w-3 h-3" />
                  </div>
                </div>

                <div className="flex-1 space-y-2">
                  <div className="space-y-0.5">
                    {editing ? (
                      <div className="flex items-center gap-2">
                        <input
                          autoFocus
                          value={nameInput}
                          onChange={e => setNameInput(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') setEditing(false); }}
                          className="text-lg font-black text-[#1A2244] border-b-2 border-[#5B7CFA] bg-transparent focus:outline-none w-48"
                        />
                        <button onClick={handleSaveName} disabled={saving} className="text-green-600 hover:text-green-700 disabled:opacity-50">
                          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        </button>
                        <button onClick={() => setEditing(false)} className="text-slate-400 hover:text-slate-600">
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-black text-[#1A2244]">{displayName}</h2>
                        <span className={cn("px-1.5 py-0.5 text-[8px] font-black uppercase rounded-md", planColors[planLabel] ?? 'bg-slate-100 text-slate-600')}>
                          {planLabel}
                        </span>
                        {hasPilotAccess && (
                          <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[8px] font-black uppercase rounded-md bg-amber-50 text-amber-600">
                            <Star className="w-2.5 h-2.5" />Pilot
                          </span>
                        )}
                        <button onClick={() => setEditing(true)} className="text-slate-300 hover:text-[#5B7CFA] transition-colors">
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                    <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">{roleLabel.replace('_', ' ')}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <div className="flex items-center gap-1.5 text-[10px] text-slate-600 bg-slate-50 px-2 py-1 rounded-lg">
                      <Mail className="w-3 h-3 text-[#5B7CFA]" />
                      {email}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Business Info */}
            <div className="glass-card p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-black text-[#1A2244] flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-[#5B7CFA]" />
                  Business Information
                </h3>
              </div>
              {business ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-0.5">
                    <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Entity Name</p>
                    <p className="text-xs font-bold text-slate-700">{business.business_name ?? '—'}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Entity Type</p>
                    <p className="text-xs font-bold text-slate-700">{business.entity_type ?? '—'}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">EIN</p>
                    <p className="text-xs font-bold text-slate-700">{business.ein ?? '—'}</p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Formation State</p>
                    <p className="text-xs font-bold text-slate-700">{business.formation_state ?? '—'}</p>
                  </div>
                </div>
              ) : (
                <p className="text-[10px] text-slate-400 font-bold">No business entity on file yet. Complete your setup to add one.</p>
              )}
            </div>
          </div>

          {/* Profile Completion Widget */}
          {(() => {
            const checks = [
              { label: 'Name set',             done: !!(profile?.full_name) },
              { label: 'Email verified',        done: !!user?.email },
              { label: 'Business name',         done: !!(business?.business_name) },
              { label: 'Entity type',           done: !!(business?.entity_type) },
              { label: 'EIN on file',           done: !!(business?.ein) },
              { label: 'Formation state',       done: !!(business?.formation_state) },
              { label: 'NAICS code',            done: !!(business?.naics_code) },
              { label: 'DUNS number',           done: !!(business?.duns_number) },
            ];
            const doneCount = checks.filter(c => c.done).length;
            const pct = Math.round((doneCount / checks.length) * 100);
            return (
              <div className="glass-card p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-black text-[#1A2244]">Profile Completion</h3>
                  <span className="text-sm font-black" style={{ color: pct >= 80 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444' }}>{pct}%</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: pct >= 80 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#3d5af1' }} />
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {checks.map(c => (
                    <div key={c.label} className="flex items-center gap-1.5">
                      <CheckCircle2 className={cn("w-3 h-3 shrink-0", c.done ? "text-green-500" : "text-slate-200")} />
                      <span className={cn("text-[10px] font-bold", c.done ? "text-[#1A2244]" : "text-slate-400")}>{c.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Right Column */}
          <div className="space-y-6">
            <div className="glass-card p-8 bg-gradient-to-br from-nexus-600 to-nexus-700 text-white">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="p-2 bg-white/10 rounded-xl">
                    <CreditCard className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-bold uppercase tracking-widest opacity-60">Nexus Credits</span>
                </div>
                <div className="space-y-1">
                  <h4 className="text-4xl font-black">$0</h4>
                  <p className="text-sm font-medium opacity-60">0 credits available</p>
                </div>
                <div className="space-y-2">
                  <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-white w-0" />
                  </div>
                  <div className="flex justify-between text-[10px] font-bold uppercase opacity-60">
                    <span>0 Credits</span>
                    <span>0 Remaining</span>
                  </div>
                </div>
                <button className="w-full bg-white text-nexus-700 font-bold py-3 rounded-xl shadow-lg hover:bg-nexus-50 transition-all">
                  Add Credits
                </button>
              </div>
            </div>

            <div className="glass-card p-6 space-y-2">
              <h3 className="px-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Quick Settings</h3>
              {[
                { icon: Shield, label: 'Security & Privacy', color: 'text-blue-500' },
                { icon: Bell, label: 'Notifications', color: 'text-amber-500' },
                { icon: Globe, label: 'Integrations', color: 'text-purple-500' },
              ].map((item, i) => (
                <button key={i} className="w-full flex items-center justify-between p-3 hover:bg-slate-50 rounded-xl transition-all group">
                  <div className="flex items-center gap-3">
                    <item.icon className={cn("w-5 h-5", item.color)} />
                    <span className="font-semibold text-slate-700">{item.label}</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-400" />
                </button>
              ))}
              <div className="pt-4 mt-4 border-t border-slate-100">
                <button
                  onClick={signOut}
                  className="w-full flex items-center gap-3 p-3 text-red-600 hover:bg-red-50 rounded-xl transition-all font-bold"
                >
                  <LogOut className="w-5 h-5" />
                  Sign Out
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
