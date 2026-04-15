import React, { useEffect, useState } from 'react';
import { Building2, Activity, Users, DollarSign, ShieldCheck, Target, ArrowUpRight, Zap, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAuth } from '../AuthProvider';
import { getProfile, getBusinessEntity, UserProfile, BusinessEntity } from '../../lib/db';

export function AdminMyBusiness() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [business, setBusiness] = useState<BusinessEntity | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    Promise.all([getProfile(user.id), getBusinessEntity(user.id)]).then(([{ data: p }, { data: b }]) => {
      setProfile(p);
      setBusiness(b);
      setLoading(false);
    });
  }, [user]);

  const readiness = profile?.readiness_score ?? 0;

  const readinessSections = [
    { label: 'Entity Structure', score: business ? (business.ein ? 100 : 40) : 0, status: business?.ein ? 'Verified' : 'Incomplete' },
    { label: 'Credit Profile', score: readiness > 0 ? Math.min(readiness + 10, 100) : 0, status: readiness >= 70 ? 'Strong' : 'Building' },
    { label: 'Financial Health', score: readiness, status: readiness >= 80 ? 'Excellent' : readiness >= 50 ? 'Good' : 'Early Stage' },
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div>
        <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">My Business</h1>
        <p className="text-slate-500 font-medium mt-1 text-sm">Manage your own business profile, funding readiness, and internal operations.</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24"><Loader2 className="w-6 h-6 text-slate-300 animate-spin" /></div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-8 space-y-8">
            {/* Readiness Overview */}
            <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-[#5B7CFA]/5 to-transparent rounded-full -mr-48 -mt-48 blur-3xl" />
              <div className="relative z-10">
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                      <Activity className="w-8 h-8" />
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-[#1A2244]">Business Readiness</h3>
                      <p className="text-xs font-medium text-slate-500 mt-1">
                        {profile?.full_name ?? 'Your'} · {business?.business_name ?? 'No entity on file'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-black text-[#5B7CFA]">{readiness}%</p>
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">Overall Score</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {readinessSections.map((item, i) => (
                    <div key={i} className="p-6 rounded-2xl bg-slate-50 border border-slate-100 space-y-4">
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{item.label}</span>
                        <span className={cn("text-[10px] font-black uppercase tracking-widest",
                          item.score >= 80 ? "text-green-600" : item.score >= 50 ? "text-blue-600" : "text-amber-600")}>
                          {item.status}
                        </span>
                      </div>
                      <h4 className="text-2xl font-black text-[#1A2244]">{item.score}%</h4>
                      <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div className={cn("h-full rounded-full",
                          item.score >= 80 ? "bg-green-500" : item.score >= 50 ? "bg-[#5B7CFA]" : "bg-amber-500")}
                          style={{ width: `${item.score}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Business Details */}
            {business && (
              <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-6 border-b border-slate-100 bg-slate-50/30">
                  <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-[#5B7CFA]" /> Entity Details
                  </h3>
                </div>
                <div className="p-6 grid grid-cols-2 md:grid-cols-3 gap-6">
                  {[
                    { label: 'Business Name', value: business.business_name },
                    { label: 'Entity Type', value: business.entity_type },
                    { label: 'EIN', value: business.ein },
                    { label: 'DUNS Number', value: business.duns_number },
                    { label: 'Formation State', value: business.formation_state },
                    { label: 'Formation Date', value: business.formation_date },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
                      <p className="text-xs font-bold text-slate-700 mt-1">{value ?? '—'}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Operations */}
            <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
              <div className="p-6 border-b border-slate-100 bg-slate-50/30">
                <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Internal Operations</h3>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                {[
                  { title: 'Team Management', desc: 'Manage internal staff and permissions.', icon: Users },
                  { title: 'Financial Tracking', desc: 'Monitor internal revenue and expenses.', icon: DollarSign },
                  { title: 'Compliance', desc: 'Ensure all business filings are up to date.', icon: ShieldCheck },
                  { title: 'Strategic Goals', desc: 'Track and manage quarterly objectives.', icon: Target },
                ].map((op, i) => (
                  <div key={i} className="flex items-start gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100 hover:border-[#5B7CFA]/30 transition-all group">
                    <div className="w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-[#5B7CFA]">
                      <op.icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-[#1A2244]">{op.title}</h4>
                      <p className="text-xs text-slate-500 mt-1">{op.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column */}
          <div className="lg:col-span-4 space-y-6">
            <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-4">
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Quick Actions</h3>
              {['Update Financials', 'Review Team Access', 'Compliance Check', 'Strategic Review'].map((action, i) => (
                <button key={i} className="w-full py-3 px-4 rounded-xl bg-slate-50 border border-slate-100 text-[10px] font-black text-slate-600 uppercase tracking-widest hover:bg-white hover:border-[#5B7CFA]/30 hover:text-[#5B7CFA] transition-all text-left flex items-center justify-between group">
                  {action}
                  <ArrowUpRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-all" />
                </button>
              ))}
            </div>

            <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
                  <Zap className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Profile Info</h3>
              </div>
              <div className="space-y-3">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Plan</p>
                  <p className="text-xs font-bold text-[#1A2244] mt-0.5 capitalize">{profile?.subscription_plan ?? 'Free'}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Role</p>
                  <p className="text-xs font-bold text-[#1A2244] mt-0.5 capitalize">{profile?.role?.replace('_', ' ') ?? '—'}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Member Since</p>
                  <p className="text-xs font-bold text-[#1A2244] mt-0.5">{profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : '—'}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
