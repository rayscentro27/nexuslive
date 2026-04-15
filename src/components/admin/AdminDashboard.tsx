import React, { useEffect, useState } from 'react';
import {
  Users, DollarSign, Cpu, ShieldAlert,
  ArrowUpRight, Clock, CheckCircle2, AlertCircle,
  Zap, Lightbulb, ChevronRight, FileText
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { getAllClients, getAllDocuments, getAllFundingApplications, getBotProfiles, UserProfile, Document, FundingApplication, BotProfile } from '../../lib/db';

function fmtMoney(n: number) {
  if (n >= 1_000_000) return '$' + (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return '$' + (n / 1_000).toFixed(0) + 'k';
  return '$' + n.toLocaleString();
}

export function AdminDashboard() {
  const [clients, setClients] = useState<UserProfile[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [applications, setApplications] = useState<FundingApplication[]>([]);
  const [bots, setBots] = useState<BotProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastSync] = useState(new Date());

  useEffect(() => {
    Promise.all([
      getAllClients(),
      getAllDocuments(),
      getAllFundingApplications(),
      getBotProfiles(),
    ]).then(([{ data: c }, { data: d }, { data: a }, { data: b }]) => {
      setClients(c);
      setDocuments(d);
      setApplications(a);
      setBots(b);
      setLoading(false);
    });
  }, []);

  const pipelineValue = applications.reduce((sum, a) => sum + (a.requested_amount ?? 0), 0);
  const activeBots = bots.filter(b => b.status === 'active').length;
  const botHealth = bots.length > 0 ? Math.round((activeBots / bots.length) * 100) : 0;
  const pendingDocs = documents.filter(d => d.status === 'pending').length;

  const stats = [
    { label: 'Active Clients', value: loading ? '—' : clients.length.toString(), change: 'Total enrolled', trend: 'up', icon: Users, color: 'blue' },
    { label: 'Pipeline Value', value: loading ? '—' : fmtMoney(pipelineValue), change: 'Funding requested', trend: 'up', icon: DollarSign, color: 'green' },
    { label: 'AI Health', value: loading ? '—' : `${botHealth}%`, change: `${activeBots} of ${bots.length} active`, trend: 'up', icon: Cpu, color: 'purple' },
    { label: 'Docs Pending', value: loading ? '—' : pendingDocs.toString(), change: 'Awaiting review', trend: pendingDocs > 5 ? 'up' : 'down', icon: ShieldAlert, color: 'amber' },
  ];

  const colorMap: Record<string, string> = {
    blue: 'bg-blue-50 text-[#5B7CFA]',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    amber: 'bg-amber-50 text-amber-600',
  };

  const recentClients = clients.slice(0, 4);
  const recentApps = applications.slice(0, 3);

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Overview</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Operational workspace and system-wide performance monitoring.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 rounded-xl bg-white border border-slate-200 flex items-center gap-2 shadow-sm">
            <Clock className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-bold text-slate-500">
              Last Sync: {lastSync.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">
            System Report
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <div key={i} className="bg-white border border-slate-200 p-6 rounded-3xl relative overflow-hidden group hover:border-[#5B7CFA]/30 transition-all shadow-sm">
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#5B7CFA]/5 rounded-full -mr-16 -mt-16 blur-3xl group-hover:bg-[#5B7CFA]/10 transition-all" />
            <div className="relative z-10 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className={cn("w-12 h-12 rounded-2xl flex items-center justify-center", colorMap[stat.color])}>
                  <stat.icon className="w-6 h-6" />
                </div>
                <ArrowUpRight className="w-4 h-4 text-slate-200" />
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</p>
                <h3 className="text-2xl font-black text-[#1A2244] mt-1">{stat.value}</h3>
                <p className="text-[10px] font-bold text-slate-400 mt-1">{stat.change}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Clients */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
          <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                <Users className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Recent Clients</h3>
            </div>
            <span className="text-[10px] font-bold text-slate-400">{clients.length} total</span>
          </div>
          <div className="divide-y divide-slate-50">
            {recentClients.length > 0 ? recentClients.map((c) => (
              <div key={c.id} className="px-6 py-4 flex items-center justify-between hover:bg-slate-50/50 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="w-9 h-9 rounded-xl bg-[#C5C9F7] flex items-center justify-center font-black text-[#5B7CFA] text-sm shrink-0">
                    {(c.full_name ?? 'U').charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="text-sm font-black text-[#1A2244]">{c.full_name ?? 'Unknown'}</p>
                    <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">
                      {c.subscription_plan} plan · joined {new Date(c.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-[10px] font-black text-[#1A2244]">{c.readiness_score}%</p>
                    <div className="w-20 h-1.5 bg-slate-100 rounded-full mt-1 overflow-hidden">
                      <div
                        className={cn("h-full rounded-full", c.readiness_score >= 80 ? "bg-green-500" : c.readiness_score >= 50 ? "bg-[#5B7CFA]" : "bg-amber-500")}
                        style={{ width: `${c.readiness_score}%` }}
                      />
                    </div>
                  </div>
                  <button className="px-3 py-1.5 bg-blue-50 text-[#5B7CFA] text-[10px] font-black uppercase tracking-widest rounded-lg hover:bg-[#5B7CFA] hover:text-white transition-all">
                    View
                  </button>
                </div>
              </div>
            )) : (
              <div className="px-6 py-8 text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">No clients yet</p>
              </div>
            )}
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Bot Health */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
                <Cpu className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">AI Workforce</h3>
            </div>
            <div className="space-y-3">
              {bots.slice(0, 4).map(bot => (
                <div key={bot.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className={cn("w-2 h-2 rounded-full", bot.status === 'active' ? "bg-green-500" : bot.status === 'idle' ? "bg-amber-400" : "bg-slate-300")} />
                    <span className="text-[11px] font-bold text-slate-700">{bot.name}</span>
                  </div>
                  <span className={cn(
                    "text-[9px] font-black uppercase px-2 py-0.5 rounded-full",
                    bot.status === 'active' ? "bg-green-50 text-green-600" :
                    bot.status === 'idle' ? "bg-amber-50 text-amber-600" :
                    "bg-slate-100 text-slate-400"
                  )}>{bot.status}</span>
                </div>
              ))}
              {bots.length === 0 && (
                <p className="text-[10px] font-bold text-slate-400">No bots configured</p>
              )}
            </div>
          </div>

          {/* Recent Applications */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center text-green-600">
                <DollarSign className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Applications</h3>
            </div>
            {recentApps.length > 0 ? (
              <div className="space-y-3">
                {recentApps.map(app => (
                  <div key={app.id} className="flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-black text-[#1A2244]">{app.lender_name ?? 'Unknown'}</p>
                      <p className="text-[9px] text-slate-400 font-bold">${(app.requested_amount ?? 0).toLocaleString()}</p>
                    </div>
                    <span className={cn(
                      "text-[9px] font-black uppercase px-2 py-0.5 rounded-full",
                      app.status === 'approved' ? "bg-green-50 text-green-600" :
                      app.status === 'pending' ? "bg-blue-50 text-blue-600" :
                      "bg-amber-50 text-amber-600"
                    )}>{app.status}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[10px] font-bold text-slate-400">No applications yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
