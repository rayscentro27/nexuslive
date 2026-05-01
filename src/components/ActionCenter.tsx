import React, { useState, useEffect } from 'react';
import { CheckCircle2, Circle, Play, ArrowRight, Clock, Zap, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from './AuthProvider';
import { getTasks, updateTaskStatus, Task } from '../lib/db';

// Fallback tasks shown when database is empty or not yet connected
const STARTER_TASKS: Omit<Task, 'id' | 'user_id' | 'created_at'>[] = [
  { title: 'Review Your Credit Analysis',      category: 'credit',          status: 'pending',   priority: 2, readiness_impact: 5,  is_primary: false, duration_minutes: 8,   description: '5 dispute opportunities found in your latest report.',   due_date: null, completed_at: null },
  { title: 'Enter Your Business Details',       category: 'business_setup',  status: 'in_progress', priority: 1, readiness_impact: 8, is_primary: true,  duration_minutes: 10,  description: '1 of 4 fields left to complete.',                        due_date: null, completed_at: null },
  { title: 'Watch Business Funding Guide',      category: 'general',         status: 'pending',   priority: 4, readiness_impact: 2,  is_primary: false, duration_minutes: 10,  description: null,                                                      due_date: null, completed_at: null },
  { title: 'Upload Business Documents',         category: 'business_setup',  status: 'pending',   priority: 2, readiness_impact: 4,  is_primary: false, duration_minutes: 5,   description: '0 of 3 documents uploaded.',                              due_date: null, completed_at: null },
  { title: 'Generate Dispute Letters',          category: 'credit',          status: 'pending',   priority: 2, readiness_impact: 6,  is_primary: false, duration_minutes: 15,  description: null,                                                      due_date: null, completed_at: null },
  { title: 'LLC Formation Verified',            category: 'business_setup',  status: 'complete',  priority: 1, readiness_impact: 10, is_primary: false, duration_minutes: 20,  description: null,                                                      due_date: null, completed_at: new Date().toISOString() },
  { title: 'EIN Obtained',                      category: 'business_setup',  status: 'complete',  priority: 1, readiness_impact: 5,  is_primary: false, duration_minutes: 10,  description: null,                                                      due_date: null, completed_at: new Date().toISOString() },
];

// Static business setup steps used as fallback display data
const setupSteps = [
  { label: 'LLC Formation', done: true },
  { label: 'EIN Registration', done: true },
  { label: 'Business Bank Account', done: false },
  { label: 'DUNS Number', done: false },
  { label: 'Business Address', done: false },
  { label: 'Phone & Website', done: false },
];

// Priority badge colors
function priorityColor(priority: number): string {
  if (priority === 1) return '#ef4444';
  if (priority === 2) return '#f59e0b';
  return '#8b8fa8';
}

function priorityLabel(priority: number): string {
  if (priority === 1) return 'High';
  if (priority === 2) return 'Medium';
  return 'Low';
}

export function ActionCenter() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCompletedExpanded, setIsCompletedExpanded] = useState(false);
  const [isSetupExpanded, setIsSetupExpanded] = useState(false);

  useEffect(() => {
    if (!user) return;
    (async () => {
      const { data } = await getTasks(user.id);
      // If DB has no tasks yet (pre-migration or empty account), use starters as display
      setTasks(
        data.length > 0
          ? data
          : STARTER_TASKS.map((t, i) => ({ ...t, id: String(i), user_id: user.id, created_at: new Date().toISOString() }))
      );
      setLoading(false);
    })();
  }, [user]);

  const handleComplete = async (taskId: string) => {
    if (!user || taskId.length <= 1) return; // skip fake starter IDs
    const { data } = await updateTaskStatus(taskId, 'complete');
    if (data) setTasks(prev => prev.map(t => t.id === taskId ? data : t));
  };

  const primaryTask = tasks.find(t => t.is_primary && t.status !== 'complete');
  const remainingTasks = tasks.filter(t => !t.is_primary && t.status !== 'complete');
  const completedTasks = tasks.filter(t => t.status === 'complete');

  const totalImpact = tasks.reduce((sum, t) => sum + t.readiness_impact, 0);
  const completedImpact = completedTasks.reduce((sum, t) => sum + t.readiness_impact, 0);
  const progress = totalImpact > 0 ? Math.round((completedImpact / totalImpact) * 100) : 0;

  // All pending tasks for the main list (primary + remaining)
  const allPending = [...(primaryTask ? [primaryTask] : []), ...remainingTasks];

  return (
    <div style={{ padding: '16px 20px', background: '#eaebf6' }}>

      {/* Page header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1a1c3a', marginBottom: 3 }}>Action Center</h1>
          <p style={{ fontSize: 15, color: '#8b8fa8' }}>
            The engine of your funding journey. Complete tasks to advance.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span
            style={{
              background: '#22c55e18',
              color: '#22c55e',
              borderRadius: 20,
              padding: '4px 16px',
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            Completed: {completedTasks.length}/{tasks.length}
          </span>
          <button
            style={{
              padding: '7px 16px',
              borderRadius: 8,
              border: '1px solid #e8e9f2',
              background: '#fff',
              fontSize: 13,
              fontWeight: 600,
              color: '#1a1c3a',
              cursor: 'pointer',
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
          <Loader2 className="w-6 h-6 animate-spin text-[#5B7CFA]" />
        </div>
      ) : (
        /* Two-column layout */
        <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>

          {/* ── LEFT MAIN COLUMN ── */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* 1. Overall Readiness card */}
            <div className="glass-card" style={{ padding: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3 style={{ fontSize: 17, fontWeight: 700, color: '#1a1c3a' }}>Overall Readiness</h3>
                <span style={{ fontSize: 22, fontWeight: 800, color: '#3d5af1' }}>{progress}%</span>
              </div>
              <div style={{ height: 7, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden' }}>
                <div style={{ width: `${progress}%`, height: '100%', background: '#3d5af1', borderRadius: 10 }} />
              </div>
              <p style={{ fontSize: 14, color: '#8b8fa8', marginTop: 8 }}>
                {allPending.length} task{allPending.length !== 1 ? 's' : ''} remaining before funding unlock
              </p>
            </div>

            {/* 2. Business Setup collapsible card */}
            <div className="glass-card" style={{ padding: 20 }}>
              <button
                onClick={() => setIsSetupExpanded(!isSetupExpanded)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 0,
                  marginBottom: isSetupExpanded ? 16 : 0,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a' }}>Business Setup</h3>
                  <span
                    style={{
                      background: '#f59e0b18',
                      color: '#f59e0b',
                      borderRadius: 20,
                      padding: '2px 10px',
                      fontSize: 11,
                      fontWeight: 600,
                    }}
                  >
                    65% Ready
                  </span>
                </div>
                {isSetupExpanded
                  ? <ChevronUp size={16} color="#8b8fa8" />
                  : <ChevronDown size={16} color="#8b8fa8" />
                }
              </button>

              {isSetupExpanded && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
                  {setupSteps.map((step, i) => (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '10px 12px',
                        borderRadius: 8,
                        background: step.done ? '#f0fdf4' : '#f7f8ff',
                        border: `1px solid ${step.done ? '#bbf7d0' : '#e8e9f2'}`,
                      }}
                    >
                      {step.done
                        ? <CheckCircle2 size={14} color="#22c55e" style={{ flexShrink: 0 }} />
                        : <Circle size={14} color="#8b8fa8" style={{ flexShrink: 0 }} />
                      }
                      <span style={{ fontSize: 12, fontWeight: 600, color: step.done ? '#166534' : '#8b8fa8' }}>
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 3. Pending Tasks card */}
            <div className="glass-card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', marginBottom: 14 }}>Pending Tasks</h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {allPending.map((task) => {
                  const isChecked = task.status === 'complete';
                  const pColor = priorityColor(task.priority);
                  const pLabel = priorityLabel(task.priority);
                  return (
                    <div
                      key={task.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        padding: '12px 14px',
                        borderRadius: 10,
                        border: '1px solid #e8e9f2',
                        background: '#fff',
                      }}
                    >
                      {/* Checkbox */}
                      <div
                        onClick={() => handleComplete(task.id)}
                        style={{
                          width: 20,
                          height: 20,
                          borderRadius: 6,
                          border: `2px solid ${isChecked ? '#22c55e' : '#e8e9f2'}`,
                          background: isChecked ? '#22c55e' : '#fff',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: 'pointer',
                          flexShrink: 0,
                          transition: 'all 0.15s',
                        }}
                      >
                        {isChecked && (
                          <svg width="11" height="9" viewBox="0 0 11 9" fill="none">
                            <path d="M1 4L4 7L10 1" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </div>

                      {/* Task info */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontSize: 13, fontWeight: 600, color: '#1a1c3a', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {task.title}
                          {task.is_primary && (
                            <span
                              style={{
                                marginLeft: 8,
                                background: '#3d5af118',
                                color: '#3d5af1',
                                borderRadius: 20,
                                padding: '1px 8px',
                                fontSize: 10,
                                fontWeight: 600,
                              }}
                            >
                              Primary
                            </span>
                          )}
                        </p>
                        {task.due_date && (
                          <p style={{ fontSize: 11, color: '#8b8fa8', margin: '2px 0 0' }}>
                            Due {new Date(task.due_date).toLocaleDateString()}
                          </p>
                        )}
                      </div>

                      {/* Priority badge */}
                      <span
                        style={{
                          background: pColor + '18',
                          color: pColor,
                          borderRadius: 20,
                          padding: '2px 10px',
                          fontSize: 11,
                          fontWeight: 600,
                          flexShrink: 0,
                        }}
                      >
                        {pLabel}
                      </span>
                    </div>
                  );
                })}

                {allPending.length === 0 && (
                  <div style={{ textAlign: 'center', padding: '24px 0' }}>
                    <CheckCircle2 size={32} color="#22c55e" style={{ margin: '0 auto 8px' }} />
                    <p style={{ fontSize: 14, fontWeight: 600, color: '#22c55e' }}>All tasks complete!</p>
                  </div>
                )}
              </div>

              {/* Completed tasks collapsible */}
              {completedTasks.length > 0 && (
                <div style={{ marginTop: 16, borderTop: '1px solid #e8e9f2', paddingTop: 12 }}>
                  <button
                    onClick={() => setIsCompletedExpanded(!isCompletedExpanded)}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      padding: '4px 0',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, color: '#8b8fa8' }}>
                      <CheckCircle2 size={14} color="#22c55e" />
                      Completed Tasks ({completedTasks.length})
                    </div>
                    {isCompletedExpanded ? <ChevronUp size={14} color="#8b8fa8" /> : <ChevronDown size={14} color="#8b8fa8" />}
                  </button>

                  {isCompletedExpanded && (
                    <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {completedTasks.map((task) => (
                        <div
                          key={task.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10,
                            padding: '10px 14px',
                            borderRadius: 10,
                            border: '1px solid #e8e9f2',
                            background: '#f9fafb',
                            opacity: 0.7,
                          }}
                        >
                          <CheckCircle2 size={16} color="#22c55e" style={{ flexShrink: 0 }} />
                          <p style={{ fontSize: 13, fontWeight: 500, color: '#8b8fa8', margin: 0, textDecoration: 'line-through', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {task.title}
                          </p>
                          <span style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 600, color: '#22c55e', flexShrink: 0 }}>
                            +{task.readiness_impact}%
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* ── RIGHT SIDEBAR (260px) ── */}
          <div style={{ width: 260, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* 1. Recent Alerts card */}
            <div className="glass-card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1c3a', marginBottom: 14 }}>Recent Alerts</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {[
                  { label: 'Credit Score Updated', sub: 'Your score changed by +12 pts', color: '#22c55e', icon: '📈' },
                  { label: 'Grant Deadline', sub: 'SBIR application closes in 3 days', color: '#f59e0b', icon: '⏰' },
                  { label: 'Document Required', sub: 'Upload your bank statements', color: '#ef4444', icon: '📄' },
                ].map((alert, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: 8,
                        background: alert.color + '18',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        fontSize: 15,
                      }}
                    >
                      {alert.icon}
                    </div>
                    <div>
                      <p style={{ fontSize: 12, fontWeight: 600, color: '#1a1c3a', margin: 0 }}>{alert.label}</p>
                      <p style={{ fontSize: 11, color: '#8b8fa8', margin: '2px 0 0' }}>{alert.sub}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 2. AI Advisor card */}
            <div
              style={{
                padding: 20,
                borderRadius: 12,
                background: 'linear-gradient(135deg, #eef2ff 0%, #ede9fe 100%)',
                border: '1px solid #e8e9f2',
              }}
            >
              <div style={{ fontSize: 28, marginBottom: 10 }}>🤖</div>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1c3a', marginBottom: 8 }}>AI Advisor</h3>
              <p style={{ fontSize: 12, color: '#8b8fa8', marginBottom: 16, lineHeight: 1.5 }}>
                "Your funding readiness is strong. Focus on lowering credit utilization to unlock higher loan amounts."
              </p>
              <button
                className="nexus-button-primary"
                style={{
                  width: '100%',
                  padding: '10px 0',
                  fontSize: 13,
                  fontWeight: 600,
                  borderRadius: 8,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                Chat with Advisor
              </button>
            </div>

            {/* 3. Quick Stats card */}
            <div className="glass-card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1c3a', marginBottom: 14 }}>Quick Stats</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {[
                  { label: 'Credit Score', value: '—', color: '#3d5af1' },
                  { label: 'Funding Readiness', value: `${progress}%`, color: '#3d5af1' },
                  { label: 'Tasks Completed', value: `${completedTasks.length}`, color: '#22c55e' },
                  { label: 'Grants Eligible', value: '3', color: '#f59e0b' },
                ].map((stat, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 12, color: '#8b8fa8' }}>{stat.label}</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: stat.color }}>{stat.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
