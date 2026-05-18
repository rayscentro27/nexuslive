/**
 * NexusWorkforceCommand — AI Workforce Command Center
 * Shows dispatch tasks, agent registry, approval queue, and resource health.
 * Extends the existing AI Team panel as a new tab.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { supabase } from '../../lib/supabase';
import { Shield, RefreshCw, CheckCircle2, XCircle, Clock, AlertTriangle, Zap, Cpu, Terminal, Book } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface DispatchTask {
  id: string;
  source: string;
  original_prompt: string;
  normalized_goal: string | null;
  task_type: string | null;
  risk_level: string;
  status: string;
  clarification_question: string | null;
  approval_required: boolean;
  final_summary: string | null;
  created_at: string;
  completed_at: string | null;
}

interface ApprovalRequest {
  id: string;
  task_id: string | null;
  approval_type: string;
  risk_level: string;
  request_summary: string;
  proposed_action: Record<string, unknown> | null;
  status: string;
  created_at: string;
}

interface AgentCapability {
  agent_key: string;
  display_name: string;
  agent_type: string;
  description: string | null;
  supported_task_types: string[];
  allowed_risk_levels: string[];
  requires_approval: boolean;
  is_enabled: boolean;
  priority: number;
}

interface NexusSkill {
  skill_key: string;
  display_name: string;
  category: string;
  description: string | null;
  risk_level: string;
  requires_approval: boolean;
  is_enabled: boolean;
  success_count: number;
  failure_count: number;
}

interface CliTool {
  cli_key: string;
  command_name: string;
  description: string | null;
  risk_level: string;
  requires_approval: boolean;
  is_enabled: boolean;
}

type CommandTab = 'inbox' | 'registry' | 'approvals' | 'completed';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function timeAgo(ts: string) {
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

const STATUS_COLORS: Record<string, string> = {
  received: '#6366f1', needs_clarification: '#f59e0b', planned: '#0d9488',
  running: '#3d5af1', blocked: '#ef4444', awaiting_approval: '#f59e0b',
  completed: '#22c55e', failed: '#ef4444',
};
const RISK_COLORS: Record<string, string> = {
  low: '#22c55e', medium: '#f59e0b', high: '#ef4444', critical: '#dc2626',
};

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || '#9ca3af';
  return (
    <span style={{
      fontSize: 9, fontWeight: 700, padding: '2px 6px',
      borderRadius: 5, background: `${color}18`, color, border: `1px solid ${color}30`,
      textTransform: 'uppercase', letterSpacing: '0.05em',
    }}>{status.replace(/_/g, ' ')}</span>
  );
}

function RiskBadge({ level }: { level: string }) {
  const color = RISK_COLORS[level] || '#9ca3af';
  return (
    <span style={{
      fontSize: 9, fontWeight: 700, padding: '2px 5px', borderRadius: 4,
      background: `${color}15`, color, border: `1px solid ${color}25`,
    }}>{level}</span>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function DispatchInbox({ tasks, onApprove }: {
  tasks: DispatchTask[];
  onApprove?: (id: string) => void;
}) {
  const inbox = tasks.filter(t => !['completed', 'failed'].includes(t.status));
  if (inbox.length === 0) {
    return (
      <div style={{ padding: 20, textAlign: 'center' }}>
        <p style={{ fontSize: 13, color: '#8b8fa8' }}>No active dispatch tasks.</p>
        <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>
          Tasks appear when Ray sends Hermes a request via Telegram or admin.
        </p>
      </div>
    );
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {inbox.map(t => (
        <motion.div
          key={t.id}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            padding: '10px 14px', borderRadius: 12,
            border: `1px solid ${(STATUS_COLORS[t.status] || '#e5e7eb')}25`,
            background: t.status === 'awaiting_approval' ? '#fffbeb' : '#fff',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a', margin: '0 0 3px',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {t.normalized_goal || t.original_prompt}
              </p>
              <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                <StatusBadge status={t.status} />
                <RiskBadge level={t.risk_level} />
                {t.task_type && (
                  <span style={{ fontSize: 9, color: '#9ca3af', padding: '2px 5px', background: '#f3f4f6', borderRadius: 4 }}>
                    {t.task_type}
                  </span>
                )}
                <span style={{ fontSize: 9, color: '#9ca3af' }}>{timeAgo(t.created_at)}</span>
              </div>
            </div>
          </div>
          {t.clarification_question && (
            <div style={{ marginTop: 7, padding: '6px 10px', borderRadius: 7,
              background: '#fffbeb', border: '1px solid #fde68a' }}>
              <p style={{ fontSize: 10, color: '#92400e', margin: 0 }}>
                ⚠️ Needs clarification: {t.clarification_question}
              </p>
            </div>
          )}
          {t.approval_required && t.status === 'awaiting_approval' && onApprove && (
            <div style={{ marginTop: 7, display: 'flex', gap: 6 }}>
              <button
                onClick={() => onApprove(t.id)}
                style={{
                  padding: '4px 10px', borderRadius: 7, border: 'none',
                  background: '#22c55e', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer',
                }}
              >
                Approve
              </button>
              <button
                style={{
                  padding: '4px 10px', borderRadius: 7, border: '1px solid #e5e7eb',
                  background: '#fff', color: '#ef4444', fontSize: 11, fontWeight: 700, cursor: 'pointer',
                }}
              >
                Reject
              </button>
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}

function ResourceRegistry({ agents, skills, cliTools }: {
  agents: AgentCapability[];
  skills: NexusSkill[];
  cliTools: CliTool[];
}) {
  const [activeTab, setActiveTab] = useState<'agents' | 'skills' | 'cli'>('agents');
  const tabs = [
    { id: 'agents' as const, label: `Agents (${agents.length})`, icon: Cpu },
    { id: 'skills' as const, label: `Skills (${skills.length})`, icon: Book },
    { id: 'cli' as const, label: `CLI (${cliTools.length})`, icon: Terminal },
  ];

  return (
    <div>
      <div style={{ display: 'flex', gap: 5, marginBottom: 10 }}>
        {tabs.map(t => {
          const Icon = t.icon;
          return (
            <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
              flex: 1, padding: '6px 8px', borderRadius: 8, fontSize: 11, fontWeight: 700,
              border: activeTab === t.id ? '1.5px solid #3d5af1' : '1px solid #e5e7eb',
              background: activeTab === t.id ? '#eef0fd' : '#fff',
              color: activeTab === t.id ? '#3d5af1' : '#6b7280',
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
            }}>
              <Icon size={11} /> {t.label}
            </button>
          );
        })}
      </div>

      {activeTab === 'agents' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {agents.map(a => (
            <div key={a.agent_key} style={{
              padding: '8px 12px', borderRadius: 10,
              background: a.is_enabled ? '#f9fafb' : '#f3f4f6',
              border: `1px solid ${a.is_enabled ? '#e5e7eb' : '#d1d5db'}`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 3 }}>
                <p style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{a.display_name}</p>
                <div style={{ display: 'flex', gap: 4 }}>
                  {!a.is_enabled && <span style={{ fontSize: 9, color: '#9ca3af' }}>disabled</span>}
                  {a.requires_approval && <span style={{ fontSize: 9, color: '#f59e0b', background: '#fffbeb', padding: '1px 5px', borderRadius: 4 }}>needs approval</span>}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {(a.supported_task_types || []).slice(0, 4).map(tt => (
                  <span key={tt} style={{ fontSize: 8, color: '#6b7280', background: '#f3f4f6', padding: '1px 5px', borderRadius: 3 }}>{tt}</span>
                ))}
              </div>
            </div>
          ))}
          {agents.length === 0 && <p style={{ fontSize: 12, color: '#8b8fa8', padding: 12 }}>No agents in registry yet. Run migrations to seed.</p>}
        </div>
      )}

      {activeTab === 'skills' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {skills.map(s => (
            <div key={s.skill_key} style={{
              padding: '8px 12px', borderRadius: 10,
              background: '#f9fafb', border: '1px solid #e5e7eb',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <p style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{s.display_name}</p>
                <div style={{ display: 'flex', gap: 4 }}>
                  <RiskBadge level={s.risk_level} />
                  <span style={{ fontSize: 9, color: '#9ca3af' }}>{s.category}</span>
                </div>
              </div>
              {(s.success_count > 0 || s.failure_count > 0) && (
                <p style={{ fontSize: 9, color: '#9ca3af', margin: '3px 0 0' }}>
                  {s.success_count} runs · {s.failure_count} failures
                </p>
              )}
            </div>
          ))}
          {skills.length === 0 && <p style={{ fontSize: 12, color: '#8b8fa8', padding: 12 }}>No skills yet. Run migrations.</p>}
        </div>
      )}

      {activeTab === 'cli' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {cliTools.map(c => (
            <div key={c.cli_key} style={{
              padding: '8px 12px', borderRadius: 10,
              background: '#f0fdfa', border: '1px solid #99f6e4',
              fontFamily: 'monospace',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <p style={{ fontSize: 12, fontWeight: 700, color: '#0f766e', margin: 0 }}>{c.command_name}</p>
                <RiskBadge level={c.risk_level} />
              </div>
              {c.description && <p style={{ fontSize: 10, color: '#6b7280', margin: '2px 0 0' }}>{c.description}</p>}
            </div>
          ))}
          {cliTools.length === 0 && <p style={{ fontSize: 12, color: '#8b8fa8', padding: 12 }}>No CLI tools yet. Run migrations.</p>}
        </div>
      )}
    </div>
  );
}

function ApprovalQueue({ approvals, onApprove, onReject }: {
  approvals: ApprovalRequest[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const pending = approvals.filter(a => a.status === 'pending');
  if (pending.length === 0) {
    return (
      <div style={{ padding: 20, textAlign: 'center' }}>
        <CheckCircle2 size={20} color="#22c55e" style={{ marginBottom: 6 }} />
        <p style={{ fontSize: 13, color: '#22c55e', fontWeight: 700 }}>No pending approvals</p>
      </div>
    );
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {pending.map(a => (
        <motion.div key={a.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          style={{ padding: '12px 14px', borderRadius: 12, border: '1.5px solid #fde68a', background: '#fffbeb' }}>
          <div style={{ display: 'flex', gap: 5, marginBottom: 6 }}>
            <AlertTriangle size={12} color="#f59e0b" />
            <p style={{ fontSize: 12, fontWeight: 700, color: '#92400e', margin: 0 }}>{a.approval_type}</p>
            <RiskBadge level={a.risk_level} />
          </div>
          <p style={{ fontSize: 11, color: '#1a1c3a', margin: '0 0 8px' }}>{a.request_summary}</p>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={() => onApprove(a.id)} style={{
              padding: '4px 12px', borderRadius: 7, border: 'none',
              background: '#22c55e', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer',
            }}>Approve</button>
            <button onClick={() => onReject(a.id)} style={{
              padding: '4px 12px', borderRadius: 7, border: '1px solid #fecaca',
              background: '#fff', color: '#ef4444', fontSize: 11, fontWeight: 700, cursor: 'pointer',
            }}>Reject</button>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function NexusWorkforceCommand() {
  const [tasks, setTasks] = useState<DispatchTask[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [agents, setAgents] = useState<AgentCapability[]>([]);
  const [skills, setSkills] = useState<NexusSkill[]>([]);
  const [cliTools, setCliTools] = useState<CliTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<CommandTab>('inbox');

  const load = useCallback(async () => {
    const [tasksRes, approvalsRes, agentsRes, skillsRes, cliRes] = await Promise.all([
      supabase.from('agent_dispatch_tasks').select('*').order('created_at', { ascending: false }).limit(30),
      supabase.from('human_approval_requests').select('*').eq('status', 'pending').order('created_at', { ascending: false }).limit(20),
      supabase.from('agent_capabilities').select('*').eq('is_enabled', true).order('priority'),
      supabase.from('nexus_skills').select('*').eq('is_enabled', true).order('category'),
      supabase.from('nexus_cli_tools').select('*').eq('is_enabled', true),
    ]);
    setTasks((tasksRes.data || []) as DispatchTask[]);
    setApprovals((approvalsRes.data || []) as ApprovalRequest[]);
    setAgents((agentsRes.data || []) as AgentCapability[]);
    setSkills((skillsRes.data || []) as NexusSkill[]);
    setCliTools((cliRes.data || []) as CliTool[]);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => { void load(); const t = setInterval(() => void load(), 60_000); return () => clearInterval(t); }, [load]);

  const handleApproveTask = async (taskId: string) => {
    await supabase.from('agent_dispatch_tasks').update({ status: 'running', updated_at: new Date().toISOString() }).eq('id', taskId);
    void load();
  };

  const handleApproveRequest = async (approvalId: string) => {
    await supabase.from('human_approval_requests').update({ status: 'approved', reviewed_at: new Date().toISOString() }).eq('id', approvalId);
    void load();
  };

  const handleRejectRequest = async (approvalId: string) => {
    await supabase.from('human_approval_requests').update({ status: 'rejected', reviewed_at: new Date().toISOString() }).eq('id', approvalId);
    void load();
  };

  const pendingApprovals = approvals.filter(a => a.status === 'pending').length;
  const activeTasks = tasks.filter(t => ['running', 'planned', 'received'].includes(t.status)).length;
  const completedTasks = tasks.filter(t => t.status === 'completed').length;

  const TABS: Array<{ id: CommandTab; label: string; badge?: number }> = [
    { id: 'inbox', label: 'Dispatch Inbox', badge: activeTasks },
    { id: 'registry', label: 'Resources' },
    { id: 'approvals', label: 'Approvals', badge: pendingApprovals },
    { id: 'completed', label: 'Completed', badge: completedTasks },
  ];

  if (loading) {
    return (
      <div style={{ padding: 16 }}>
        {[...Array(4)].map((_, i) => (
          <div key={i} style={{ height: 60, borderRadius: 10, background: '#f3f4f6', animation: 'pulse 1.5s infinite', marginBottom: 8 }} />
        ))}
      </div>
    );
  }

  return (
    <div style={{ padding: '14px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>
            ⚡ Workforce Command Center
          </h3>
          <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>Agent dispatch · skill library · approval queue</p>
        </div>
        <button onClick={() => { setRefreshing(true); void load(); }} disabled={refreshing}
          style={{ display: 'flex', gap: 4, padding: '5px 10px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', color: '#3d5af1', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
          <RefreshCw size={10} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 7, marginBottom: 12 }}>
        {[
          { label: 'Agents', value: agents.length, color: '#6366f1' },
          { label: 'Skills', value: skills.length, color: '#0d9488' },
          { label: 'Active Tasks', value: activeTasks, color: '#3d5af1' },
          { label: 'Pending Approval', value: pendingApprovals, color: pendingApprovals > 0 ? '#f59e0b' : '#9ca3af' },
        ].map(s => (
          <div key={s.label} style={{ flex: '1 1 60px', padding: '7px', borderRadius: 9, background: `${s.color}10`, border: `1px solid ${s.color}20`, textAlign: 'center' }}>
            <p style={{ fontSize: 18, fontWeight: 800, color: s.color, margin: 0 }}>{s.value}</p>
            <p style={{ fontSize: 8, color: '#6b7280', margin: 0, fontWeight: 600, textTransform: 'uppercase' }}>{s.label}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 5, marginBottom: 12 }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            flex: 1, padding: '6px 4px', borderRadius: 8, fontSize: 10, fontWeight: 700,
            border: activeTab === t.id ? '1.5px solid #3d5af1' : '1px solid #e5e7eb',
            background: activeTab === t.id ? '#eef0fd' : '#fff',
            color: activeTab === t.id ? '#3d5af1' : '#6b7280', cursor: 'pointer',
          }}>
            {t.label}
            {(t.badge ?? 0) > 0 && (
              <span style={{ marginLeft: 4, background: activeTab === t.id ? '#3d5af1' : '#f3f4f6', color: activeTab === t.id ? '#fff' : '#6b7280', borderRadius: 4, padding: '0px 4px', fontSize: 9 }}>
                {t.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Panel content */}
      <AnimatePresence mode="wait">
        {activeTab === 'inbox' && (
          <motion.div key="inbox" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <DispatchInbox tasks={tasks} onApprove={handleApproveTask} />
          </motion.div>
        )}
        {activeTab === 'registry' && (
          <motion.div key="registry" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <ResourceRegistry agents={agents} skills={skills} cliTools={cliTools} />
          </motion.div>
        )}
        {activeTab === 'approvals' && (
          <motion.div key="approvals" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <ApprovalQueue approvals={approvals} onApprove={handleApproveRequest} onReject={handleRejectRequest} />
          </motion.div>
        )}
        {activeTab === 'completed' && (
          <motion.div key="completed" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {tasks.filter(t => ['completed', 'failed'].includes(t.status)).map(t => (
                <div key={t.id} style={{
                  padding: '8px 12px', borderRadius: 10,
                  background: t.status === 'completed' ? '#f0fdf4' : '#fef2f2',
                  border: `1px solid ${t.status === 'completed' ? '#bbf7d0' : '#fecaca'}`,
                }}>
                  <p style={{ fontSize: 11, fontWeight: 700, color: '#1a1c3a', margin: '0 0 3px',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {t.normalized_goal || t.original_prompt}
                  </p>
                  <div style={{ display: 'flex', gap: 5 }}>
                    <StatusBadge status={t.status} />
                    {t.task_type && <span style={{ fontSize: 9, color: '#9ca3af' }}>{t.task_type}</span>}
                    <span style={{ fontSize: 9, color: '#9ca3af' }}>{timeAgo(t.created_at)}</span>
                  </div>
                  {t.final_summary && (
                    <p style={{ fontSize: 10, color: '#6b7280', margin: '5px 0 0' }}>{t.final_summary.slice(0, 120)}</p>
                  )}
                </div>
              ))}
              {tasks.filter(t => ['completed', 'failed'].includes(t.status)).length === 0 && (
                <p style={{ fontSize: 13, color: '#8b8fa8', textAlign: 'center', padding: 20 }}>No completed tasks yet.</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Safety footer */}
      <div style={{
        marginTop: 14, padding: '7px 12px', borderRadius: 10,
        background: '#f0fdf4', border: '1px solid #bbf7d0',
        display: 'flex', alignItems: 'center', gap: 7,
      }}>
        <Shield size={11} color="#16a34a" />
        <p style={{ fontSize: 9, color: '#16a34a', fontWeight: 700, margin: 0 }}>
          All high/critical tasks require human approval · No auto-send · No real-money trading · NEXUS_DRY_RUN=true
        </p>
      </div>
    </div>
  );
}
