import React, { useState, useEffect, useCallback } from 'react';
import { Cpu, Play, Pause, RotateCcw, Save, UserPlus, Search, Bot, Loader2, Activity, Clock, CheckCircle2, AlertCircle, Zap } from 'lucide-react';
import { cn } from '../../lib/utils';
import { getBotProfiles, BotProfile } from '../../lib/db';
import { supabase } from '../../lib/supabase';
import { WorkforceOffice } from './WorkforceOffice';
import { ResearchTicketBoard } from './ResearchTicketBoard';
import { IngestionStatusPanel } from './IngestionStatusPanel';

interface AgentRun {
  id: string;
  agent_key: string;
  trigger_type: string;
  status: string;
  events_processed: number;
  errors: number;
  started_at: string;
  completed_at: string | null;
  summary: string | null;
}

interface AgentEvent {
  id: string;
  agent_key: string;
  event_type: string;
  input_summary: string | null;
  output_summary: string | null;
  status: string;
  duration_ms: number | null;
  created_at: string;
}

const PANEL_TABS = ['Office', 'Tickets', 'Ingestion', 'Agents', 'Activity', 'Events'] as const;
type PanelTab = typeof PANEL_TABS[number];

function statusBadge(status: string) {
  if (status === 'completed') return { color: '#22c55e', bg: '#f0fdf4', label: 'Done' };
  if (status === 'running')   return { color: '#3d5af1', bg: '#eef0fd', label: 'Running' };
  if (status === 'error')     return { color: '#ef4444', bg: '#fef2f2', label: 'Error' };
  return                             { color: '#f59e0b', bg: '#fffbeb', label: status };
}

function elapsed(started: string, completed: string | null) {
  const end = completed ? new Date(completed) : new Date();
  const ms = end.getTime() - new Date(started).getTime();
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.round(s / 60)}m`;
}

export function AdminAIWorkforce() {
  const [bots,       setBots]      = useState<BotProfile[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading,    setLoading]   = useState(true);
  const [activeTab,  setActiveTab] = useState<PanelTab>('Office');
  const [runs,       setRuns]      = useState<AgentRun[]>([]);
  const [events,     setEvents]    = useState<AgentEvent[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [promptValue, setPromptValue] = useState('');
  const [savingPrompt, setSavingPrompt] = useState(false);
  const [agentSearch, setAgentSearch] = useState('');
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [deployForm, setDeployForm] = useState({ name: '', role: '', agent_key: '' });

  useEffect(() => {
    getBotProfiles().then(({ data }) => {
      setBots(data);
      if (data.length > 0) {
        setSelectedId(data[0].agent_key);
        setPromptValue((data[0] as any).system_prompt ?? `You are ${data[0].name}, the ${data[0].role} for Nexus.\n\nYour mission is to help clients achieve their funding goals.\n\nGuidelines:\n- Professional yet encouraging\n- Data-driven and precise\n- Action-oriented`);
      }
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    const bot = bots.find(b => b.agent_key === selectedId);
    if (bot) setPromptValue((bot as any).system_prompt ?? `You are ${bot.name}, the ${bot.role} for Nexus.\n\nYour mission is to help clients achieve their funding goals.\n\nGuidelines:\n- Professional yet encouraging\n- Data-driven and precise\n- Action-oriented`);
  }, [selectedId]);

  const loadActivity = useCallback(async () => {
    setRunsLoading(true);
    const [runsRes, eventsRes] = await Promise.all([
      supabase.from('ai_employee_runs').select('*').order('started_at', { ascending: false }).limit(50),
      supabase.from('ai_agent_events').select('*').order('created_at', { ascending: false }).limit(100),
    ]);
    setRuns((runsRes.data ?? []) as AgentRun[]);
    setEvents((eventsRes.data ?? []) as AgentEvent[]);
    setRunsLoading(false);
  }, []);

  useEffect(() => {
    if (activeTab === 'Activity' || activeTab === 'Events') loadActivity();
  }, [activeTab, loadActivity]);

  const current = bots.find(b => b.agent_key === selectedId);
  const filteredBots = agentSearch
    ? bots.filter(b => b.name.toLowerCase().includes(agentSearch.toLowerCase()) || (b.role ?? '').toLowerCase().includes(agentSearch.toLowerCase()))
    : bots;

  const savePrompt = async () => {
    if (!selectedId) return;
    setSavingPrompt(true);
    await supabase.from('bot_profiles').update({ system_prompt: promptValue }).eq('agent_key', selectedId);
    setSavingPrompt(false);
  };

  const updateStatus = async (status: 'active' | 'idle') => {
    if (!selectedId) return;
    await supabase.from('bot_profiles').update({ status }).eq('agent_key', selectedId);
    setBots(prev => prev.map(b => b.agent_key === selectedId ? { ...b, status } : b));
  };

  const deployAgent = async () => {
    if (!deployForm.name || !deployForm.agent_key) return;
    const { data } = await supabase.from('bot_profiles').insert({
      name: deployForm.name,
      role: deployForm.role,
      agent_key: deployForm.agent_key,
      status: 'idle',
    }).select().single();
    if (data) {
      setBots(prev => [...prev, data as BotProfile]);
      setSelectedId(deployForm.agent_key);
    }
    setShowDeployModal(false);
    setDeployForm({ name: '', role: '', agent_key: '' });
  };

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">AI Workforce</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Manage autonomous employees, monitor runs, and review events.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadActivity}
            className="px-4 py-2 rounded-xl bg-white text-slate-600 text-xs font-bold border border-slate-200 hover:bg-slate-50 transition-all flex items-center gap-2"
          >
            <Activity className="w-4 h-4" /> Refresh
          </button>
          <button
            onClick={() => setShowDeployModal(true)}
            className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2"
          >
            <UserPlus className="w-4 h-4" /> Deploy New AI
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Agents',  value: bots.length,                                          color: '#3d5af1' },
          { label: 'Active',        value: bots.filter(b => b.status === 'active').length,        color: '#22c55e' },
          { label: 'Runs Today',    value: runs.filter(r => r.started_at.startsWith(new Date().toISOString().slice(0,10))).length, color: '#f59e0b' },
          { label: 'Errors',        value: runs.reduce((s, r) => s + r.errors, 0),                color: '#ef4444' },
        ].map(s => (
          <div key={s.label} className="bg-white border border-slate-200 rounded-2xl p-4">
            <div className="text-2xl font-black" style={{ color: s.color }}>{s.value}</div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Panel tabs */}
      <div className="flex gap-2 bg-slate-100 rounded-xl p-1 w-fit">
        {PANEL_TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-5 py-2 rounded-lg text-xs font-bold transition-all",
              activeTab === tab ? "bg-white text-[#1A2244] shadow-sm" : "text-slate-500 hover:text-[#1A2244]"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
        </div>
      ) : activeTab === 'Office' ? (
        <WorkforceOffice />
      ) : activeTab === 'Tickets' ? (
        <ResearchTicketBoard />
      ) : activeTab === 'Ingestion' ? (
        <IngestionStatusPanel />
      ) : activeTab === 'Agents' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Bot List */}
          <div className="lg:col-span-4 space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={agentSearch}
                onChange={e => setAgentSearch(e.target.value)}
                placeholder="Search agents..."
                className="w-full pl-10 pr-4 py-2.5 text-xs bg-white border border-slate-200 rounded-xl focus:outline-none focus:border-[#5B7CFA]/40 shadow-sm"
              />
            </div>
            <div className="space-y-2">
              {filteredBots.map(bot => (
                <button
                  key={bot.agent_key}
                  onClick={() => setSelectedId(bot.agent_key)}
                  className={cn(
                    "w-full flex items-center justify-between p-4 rounded-2xl border transition-all",
                    selectedId === bot.agent_key
                      ? "bg-[#5B7CFA] border-[#5B7CFA] shadow-lg shadow-blue-500/20"
                      : "bg-white border-slate-200 hover:border-[#5B7CFA]/30"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center",
                      selectedId === bot.agent_key ? "bg-white/20 text-white" : "bg-blue-50 text-[#5B7CFA]")}>
                      <Bot className="w-5 h-5" />
                    </div>
                    <div className="text-left">
                      <h4 className={cn("text-sm font-black", selectedId === bot.agent_key ? "text-white" : "text-[#1A2244]")}>{bot.name}</h4>
                      <p className={cn("text-[9px] font-bold uppercase tracking-widest mt-0.5",
                        selectedId === bot.agent_key ? "text-blue-100" : "text-slate-400")}>{bot.role}</p>
                    </div>
                  </div>
                  <div className={cn("w-2 h-2 rounded-full",
                    bot.status === 'active' ? (selectedId === bot.agent_key ? "bg-white" : "bg-green-500") :
                    bot.status === 'idle' ? "bg-amber-400" : "bg-slate-300")} />
                </button>
              ))}
              {bots.length === 0 && (
                <p className="text-[10px] font-bold text-slate-400 text-center py-8 uppercase tracking-widest">No agents configured</p>
              )}
            </div>
          </div>

          {/* Control Panel */}
          <div className="lg:col-span-8">
            {current ? (
              <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                      <Bot className="w-7 h-7" />
                    </div>
                    <div>
                      <h3 className="text-xl font-black text-[#1A2244]">{current.name}</h3>
                      <p className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest mt-1">{current.role}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => updateStatus('idle')} title="Pause" className="p-2.5 bg-slate-50 text-slate-400 rounded-xl hover:text-[#1A2244] border border-slate-200 transition-all">
                      <Pause className="w-5 h-5" />
                    </button>
                    <button onClick={() => updateStatus('active')} title="Restart" className="p-2.5 bg-slate-50 text-slate-400 rounded-xl hover:text-[#1A2244] border border-slate-200 transition-all">
                      <RotateCcw className="w-5 h-5" />
                    </button>
                    <button onClick={savePrompt} disabled={savingPrompt} title="Save prompt" className="p-2.5 bg-[#5B7CFA] text-white rounded-xl hover:bg-[#4A6BEB] shadow-lg shadow-blue-500/20 transition-all">
                      {savingPrompt ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                    </button>
                  </div>
                </div>
                <div className="p-8 space-y-8">
                  <div className="grid grid-cols-3 gap-6">
                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Efficiency</p>
                      <h4 className="text-xl font-black text-green-600 mt-1">
                        {current.efficiency != null ? `${current.efficiency}%` : '—'}
                      </h4>
                    </div>
                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Status</p>
                      <h4 className={cn("text-xl font-black mt-1 capitalize",
                        current.status === 'active' ? "text-green-600" :
                        current.status === 'idle' ? "text-amber-600" : "text-slate-400")}>
                        {current.status}
                      </h4>
                    </div>
                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Division</p>
                      <h4 className="text-xl font-black text-[#1A2244] mt-1 text-sm">{current.division ?? '—'}</h4>
                    </div>
                  </div>

                  {current.description && (
                    <div className="space-y-2">
                      <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Description</h4>
                      <p className="text-sm text-slate-500 leading-relaxed bg-slate-50 p-4 rounded-2xl border border-slate-100 italic">
                        "{current.description}"
                      </p>
                    </div>
                  )}

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">System Prompt</h4>
                      <span className="text-[9px] font-bold text-[#5B7CFA] uppercase tracking-widest">Editable</span>
                    </div>
                    <textarea
                      className="w-full h-48 bg-white border border-slate-200 rounded-2xl p-6 text-xs font-mono text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 transition-all leading-relaxed no-scrollbar shadow-inner"
                      value={promptValue}
                      onChange={e => setPromptValue(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white border border-slate-200 rounded-3xl flex items-center justify-center min-h-[400px]">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Select an agent to manage</p>
              </div>
            )}
          </div>
        </div>

      ) : activeTab === 'Activity' ? (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-black text-[#1A2244]">Recent Runs</h3>
            <span className="text-[10px] text-slate-400 font-bold">{runs.length} total</span>
          </div>
          {runsLoading ? (
            <div className="p-8 text-center"><Loader2 className="w-5 h-5 animate-spin text-slate-300 mx-auto" /></div>
          ) : runs.length === 0 ? (
            <div className="p-8 text-center">
              <Activity className="w-8 h-8 text-slate-200 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No runs recorded yet. Agents will log here when triggered.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {runs.map(run => {
                const { color, bg, label } = statusBadge(run.status);
                return (
                  <div key={run.id} className="p-5 flex items-center justify-between hover:bg-slate-50/50 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                        <Zap className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-sm font-bold text-[#1A2244]">{run.agent_key}</p>
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                          {run.trigger_type} · {new Date(run.started_at).toLocaleString()} · {elapsed(run.started_at, run.completed_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-right">
                      <div>
                        <p className="text-sm font-black text-[#1A2244]">{run.events_processed}</p>
                        <p className="text-[9px] text-slate-400 uppercase tracking-widest">events</p>
                      </div>
                      {run.errors > 0 && (
                        <div>
                          <p className="text-sm font-black text-red-500">{run.errors}</p>
                          <p className="text-[9px] text-slate-400 uppercase tracking-widest">errors</p>
                        </div>
                      )}
                      <span style={{ background: bg, color, fontSize: 10, fontWeight: 700, padding: '3px 10px', borderRadius: 20 }}>{label}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      ) : (
        // Events tab
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-black text-[#1A2244]">Agent Events</h3>
            <span className="text-[10px] text-slate-400 font-bold">{events.length} recent</span>
          </div>
          {runsLoading ? (
            <div className="p-8 text-center"><Loader2 className="w-5 h-5 animate-spin text-slate-300 mx-auto" /></div>
          ) : events.length === 0 ? (
            <div className="p-8 text-center">
              <Bot className="w-8 h-8 text-slate-200 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No events yet. Events are logged when agents process client actions.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {events.map(ev => {
                const { color, bg, label } = statusBadge(ev.status);
                return (
                  <div key={ev.id} className="p-4 hover:bg-slate-50/50 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-black text-[#5B7CFA] bg-blue-50 px-2 py-0.5 rounded-md">{ev.agent_key}</span>
                        <span className="text-[10px] font-bold text-slate-600">{ev.event_type}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {ev.duration_ms && <span className="text-[10px] text-slate-400">{ev.duration_ms}ms</span>}
                        <span style={{ background: bg, color, fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20 }}>{label}</span>
                      </div>
                    </div>
                    {ev.input_summary && <p className="text-[11px] text-slate-400 mb-1"><strong>In:</strong> {ev.input_summary}</p>}
                    {ev.output_summary && <p className="text-[11px] text-slate-500"><strong>Out:</strong> {ev.output_summary}</p>}
                    <p className="text-[10px] text-slate-300 mt-1">{new Date(ev.created_at).toLocaleString()}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Deploy New AI Modal */}
      {showDeployModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
          <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl">
            <h2 className="text-xl font-black text-[#1A2244] mb-6">Deploy New AI Agent</h2>
            <div className="space-y-4">
              {[
                { label: 'Agent Name', key: 'name', placeholder: 'e.g. CreditBot' },
                { label: 'Role', key: 'role', placeholder: 'e.g. Credit Specialist' },
                { label: 'Agent Key', key: 'agent_key', placeholder: 'e.g. credit_bot (unique)' },
              ].map(f => (
                <div key={f.key}>
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1">{f.label}</label>
                  <input
                    type="text"
                    value={(deployForm as any)[f.key]}
                    onChange={e => setDeployForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                    className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-[#5B7CFA]/50"
                  />
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowDeployModal(false)} className="flex-1 py-3 rounded-xl border border-slate-200 text-sm font-bold text-slate-500 hover:bg-slate-50 transition-all">Cancel</button>
              <button onClick={deployAgent} disabled={!deployForm.name || !deployForm.agent_key} className="flex-1 py-3 rounded-xl bg-[#5B7CFA] text-white text-sm font-bold hover:bg-[#4A6BEB] transition-all disabled:opacity-50">Deploy</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
