import React, { useEffect, useState } from 'react';
import { ExternalLink, Activity, AlertCircle, CheckCircle2, Loader2, Server } from 'lucide-react';
import { getSystemHealth } from '../services/nexusApi';

interface HealthData {
  status: string;
  signals_received?: number;
  timestamp?: string;
}

export function AdminDashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSystemHealth()
      .then(d => { setHealth(d); setHealthError(false); })
      .catch(() => setHealthError(true))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-black text-[#1A2244]">Admin Dashboard</h2>
        <p className="text-xs text-slate-500 font-medium mt-1">System health, workers, and control center access.</p>
      </div>

      {/* Control Center link */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center">
              <Server className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h3 className="text-sm font-black text-[#1a1c3a]">Nexus Control Center</h3>
              <p className="text-[10px] text-slate-400 font-medium">Local port 4000 — full system management</p>
            </div>
          </div>
          <a
            href="http://127.0.0.1:4000"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-50 text-indigo-600 text-xs font-bold hover:bg-indigo-100 transition-all"
          >
            Open <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Trading engine health */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-black text-[#1a1c3a] mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#5B7CFA]" />
          Trading Engine Health
        </h3>

        {loading ? (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" /> Checking...
          </div>
        ) : healthError ? (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-amber-50 border border-amber-100">
            <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
            <p className="text-xs text-amber-700 font-medium">
              Engine not reachable. Ensure Nexus services are running on your Mac and the Cloudflare tunnel is active.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Status</p>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                <span className="text-sm font-black text-[#1a1c3a] capitalize">{health?.status ?? '—'}</span>
              </div>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Signals Received</p>
              <span className="text-2xl font-black text-[#3d5af1]">{health?.signals_received ?? '—'}</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Last Check</p>
              <span className="text-xs font-medium text-slate-600">
                {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : '—'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Services overview */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-black text-[#1a1c3a] mb-4">Services</h3>
        <div className="space-y-2">
          {[
            { name: 'Trading Engine',   port: 5000, path: '/health',    desc: 'Webhook + paper execution' },
            { name: 'Control Center',   port: 4000, path: '/api/health', desc: 'API backend' },
            { name: 'Dashboard',        port: 3000, path: '/',           desc: 'Local trading dashboard' },
            { name: 'Signal Review',    port: null, path: null,          desc: 'Supabase poller + Groq AI' },
          ].map(s => (
            <div key={s.name} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
              <div>
                <span className="text-xs font-bold text-[#1a1c3a]">{s.name}</span>
                <span className="text-[10px] text-slate-400 font-medium ml-2">{s.desc}</span>
              </div>
              {s.port ? (
                <a
                  href={`http://127.0.0.1:${s.port}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] font-bold text-[#5B7CFA] hover:underline flex items-center gap-1"
                >
                  :{s.port} <ExternalLink className="w-2.5 h-2.5" />
                </a>
              ) : (
                <span className="text-[10px] font-bold text-green-600">launchd</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
