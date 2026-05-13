import React, { useState, useEffect, useCallback } from 'react';
import {
  Users, Copy, QrCode, TrendingUp, DollarSign, Award,
  MessageSquare, ChevronRight, CheckCircle2, Clock, ArrowUpRight,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthProvider';
import { useAnalytics } from '../hooks/useAnalytics';

interface Referral {
  id: string;
  referred_email: string;
  status: string;
  referral_code: string;
  converted_at: string | null;
  created_at: string;
}

interface Earning {
  id: string;
  amount: number;
  status: string;
  created_at: string;
}

interface Commission {
  id: string;
  funding_amount: number;
  commission_amount: number;
  status: string;
  created_at: string;
}

function statusMeta(status: string) {
  if (status === 'converted') return { label: 'Converted', color: '#22c55e' };
  if (status === 'signed_up')  return { label: 'Signed Up',  color: '#3d5af1' };
  return                              { label: 'Pending',    color: '#f59e0b' };
}

export function Referral() {
  const { user } = useAuth();
  const { emit } = useAnalytics();
  const [referrals,    setReferrals]    = useState<Referral[]>([]);
  const [earnings,     setEarnings]     = useState<Earning[]>([]);
  const [commissions,  setCommissions]  = useState<Commission[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [copied,       setCopied]       = useState(false);

  // Generate a deterministic referral code from the user id
  const referralCode = user ? user.id.slice(0, 8).toUpperCase() : 'XXXXXX';
  const referralLink = `${window.location.origin}/signup?ref=${referralCode}`;

  const load = useCallback(async () => {
    if (!user) return;
    const [refRes, earRes, comRes] = await Promise.all([
      supabase.from('referrals').select('*').eq('referrer_id', user.id).order('created_at', { ascending: false }),
      supabase.from('referral_earnings').select('*').eq('referrer_id', user.id).order('created_at', { ascending: false }),
      supabase.from('funding_commissions').select('*').eq('user_id', user.id).order('created_at', { ascending: false }),
    ]);
    setReferrals((refRes.data ?? []) as Referral[]);
    setEarnings((earRes.data ?? []) as Earning[]);
    setCommissions((comRes.data ?? []) as Commission[]);
    setLoading(false);
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const handleCopy = () => {
    navigator.clipboard.writeText(referralLink).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
    emit('invite_sent', { event_name: 'referral_link_copied', feature: 'referral', metadata: { referral_code: referralCode } });
  };

  // Computed totals — fall back to display zeros if no DB data yet
  const totalReferralEarnings = earnings.filter(e => e.status !== 'pending').reduce((s, e) => s + e.amount, 0);
  const totalCommissions      = commissions.filter(c => c.status !== 'pending').reduce((s, c) => s + c.commission_amount, 0);
  const pendingEarnings       = earnings.filter(e => e.status === 'pending').reduce((s, e) => s + e.amount, 0);
  const totalEarned           = totalReferralEarnings + totalCommissions;
  const convertedCount        = referrals.filter(r => r.status === 'converted').length;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="space-y-0.5">
          <h2 className="text-2xl font-bold text-[#1A2244]">Refer & Earn</h2>
          <p className="text-xs text-slate-500 font-medium">Earn up to $550 for each referral</p>
        </div>
        <div className="flex items-center gap-3">
          <p className="text-slate-500 font-medium text-xs">
            Converted: <span className="text-[#1A2244] font-bold">{convertedCount}</span>
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide space-y-6 pr-1">
        {/* Hero Banner */}
        <div className="glass-card overflow-hidden relative min-h-[180px] group shadow-xl shrink-0"
          style={{ background: 'linear-gradient(135deg, #1e2a6e 0%, #3d5af1 100%)' }}>
          <div className="absolute inset-0 bg-gradient-to-r from-[#1A2244]/40 to-transparent pointer-events-none" />
          <div className="absolute bottom-6 left-6 space-y-3 max-w-lg">
            <h3 className="text-2xl font-black text-white tracking-tight leading-tight">
              Invite your network and<br />
              <span className="text-blue-300">earn $75+ per referral</span>
            </h3>
            <button
              onClick={handleCopy}
              className="bg-white text-[#1A2244] px-6 py-2.5 rounded-xl text-xs font-bold shadow-xl flex items-center gap-2 hover:bg-slate-50 transition-all"
            >
              {copied ? 'Copied!' : 'Copy My Link'}
              <ArrowUpRight className="w-4 h-4" />
            </button>
          </div>
          <div className="absolute bottom-2 right-2 w-28 h-28 opacity-80 group-hover:scale-110 transition-transform duration-500">
            <BotAvatar type="referral" size="xl" className="bg-transparent shadow-none" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Link + Earnings */}
          <div className="lg:col-span-2 space-y-6">
            {/* Share Link */}
            <div className="glass-card p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                  <Users className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-[#1A2244]">Your Referral Link</h3>
              </div>
              <div className="flex flex-col md:flex-row gap-3">
                <div className="flex-1 bg-slate-50 border border-slate-100 rounded-xl px-4 py-2.5 text-slate-600 font-medium text-xs flex items-center justify-between">
                  <span className="truncate">{referralLink}</span>
                  <div className="flex gap-1.5 ml-2 shrink-0">
                    <button onClick={handleCopy} className="p-1.5 hover:bg-slate-200 rounded-lg transition-colors">
                      <Copy className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
                <button
                  onClick={handleCopy}
                  className="bg-[#5B7CFA] text-white px-6 py-2.5 rounded-xl text-xs font-bold shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all"
                >
                  {copied ? '✓ Copied' : 'Copy Link'}
                </button>
              </div>
              <p className="text-[10px] text-slate-400">Your code: <strong className="text-[#1A2244]">{referralCode}</strong></p>
            </div>

            {/* Earnings Summary */}
            <div className="glass-card p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center text-green-600">
                    <DollarSign className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-[#1A2244] text-base">Earnings Summary</h3>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400" />
              </div>

              <div className="space-y-2">
                <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Total Earned</p>
                <p className="text-4xl font-black text-[#1A2244] tracking-tight">
                  ${totalEarned.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </p>
              </div>

              <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-100">
                <div className="space-y-1">
                  <p className="text-[8px] font-bold text-slate-500 uppercase tracking-widest">Referrals</p>
                  <p className="text-lg font-black text-green-600">
                    ${totalReferralEarnings.toLocaleString(undefined, { minimumFractionDigits: 0 })}
                  </p>
                  <p className="text-[8px] text-slate-400 font-bold">{referrals.length} total</p>
                </div>
                <div className="space-y-1">
                  <p className="text-[8px] font-bold text-slate-500 uppercase tracking-widest">Funding</p>
                  <p className="text-lg font-black text-green-600">
                    ${totalCommissions.toLocaleString(undefined, { minimumFractionDigits: 0 })}
                  </p>
                  <p className="text-[8px] text-slate-400 font-bold">{commissions.length} deals</p>
                </div>
                <div className="space-y-1">
                  <p className="text-[8px] font-bold text-slate-500 uppercase tracking-widest">Pending</p>
                  <p className="text-lg font-black text-[#1A2244]">
                    ${pendingEarnings.toLocaleString(undefined, { minimumFractionDigits: 0 })}
                  </p>
                  <p className="text-[8px] text-slate-400 font-bold">Awaiting verification</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Program Info */}
          <div className="space-y-6">
            <div className="glass-card p-6 space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
                  <Award className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-[#1A2244]">Program</h3>
              </div>
              <div className="space-y-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <p className="text-xs font-bold text-[#1A2244]">Referral Commission</p>
                  </div>
                  <p className="text-[10px] text-slate-500 pl-6 leading-relaxed">$75 per person who signs up via your link</p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <p className="text-xs font-bold text-[#1A2244]">Funding Commission</p>
                  </div>
                  <p className="text-[10px] text-slate-500 pl-6 leading-relaxed">Earn 2% of funded amount when your referral gets funded</p>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <p className="text-xs font-bold text-[#1A2244]">Conversion Bonus</p>
                  </div>
                  <p className="text-[10px] text-slate-500 pl-6 leading-relaxed">Extra $25 when referral upgrades to Pro</p>
                </div>
              </div>
            </div>

            {/* Stats */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-[#1A2244]">Your Stats</h3>
              </div>
              <div className="space-y-3">
                {[
                  { label: 'Total referred',   value: referrals.length },
                  { label: 'Converted',        value: convertedCount },
                  { label: 'Signed up',        value: referrals.filter(r => r.status === 'signed_up').length },
                  { label: 'Pending',          value: referrals.filter(r => r.status === 'pending').length },
                ].map(s => (
                  <div key={s.label} className="flex justify-between items-center">
                    <span className="text-xs text-slate-500">{s.label}</span>
                    <span className="text-xs font-bold text-[#1A2244]">{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Activity Table */}
        <div className="glass-card overflow-hidden shrink-0">
          <div className="p-6 border-b border-slate-100 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center text-slate-400">
              <Clock className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-[#1A2244]">Referral Activity</h3>
          </div>

          {loading ? (
            <div className="p-8 text-center text-slate-400 text-sm">Loading…</div>
          ) : referrals.length === 0 ? (
            <div className="p-8 text-center">
              <Users className="w-8 h-8 text-slate-300 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No referrals yet — share your link to get started!</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-50/50 text-left">
                    <th className="px-6 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest">Email</th>
                    <th className="px-6 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest text-center">Date</th>
                    <th className="px-6 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {referrals.map(ref => {
                    const { label, color } = statusMeta(ref.status);
                    return (
                      <tr key={ref.id} className="hover:bg-slate-50/30 transition-colors">
                        <td className="px-6 py-4">
                          <p className="text-sm font-bold text-[#1A2244]">{ref.referred_email}</p>
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-600 text-center font-bold">
                          {new Date(ref.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <span style={{ background: color + '18', color, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 700 }}>
                            {label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Invite Footer */}
        <div className="glass-card p-6 space-y-4 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <MessageSquare className="w-5 h-5" />
            </div>
            <h3 className="text-xl font-black text-[#1A2244]">Invite More Friends</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {['Email', 'SMS', 'WhatsApp', 'Messenger'].map(channel => (
              <button
                key={channel}
                onClick={handleCopy}
                className="bg-slate-50 text-[#1A2244] py-2.5 text-[10px] rounded-xl font-bold border border-slate-100 hover:bg-slate-100 transition-all"
              >
                {channel}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
