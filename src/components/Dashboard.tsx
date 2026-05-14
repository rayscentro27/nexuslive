import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import {
  ArrowRight,
  CheckCircle2,
  TrendingUp,
  Zap,
  AlertCircle,
  Loader2,
  Sparkles,
  Target,
  Activity,
} from 'lucide-react';
import { useAuth } from './AuthProvider';
import {
  getProfile, getTasks, getActivity, getCreditReport,
  UserProfile, Task, ActivityItem, CreditReport
} from '../lib/db';
import { useAnalytics } from '../hooks/useAnalytics';
import { ProgressionSystem } from './ProgressionSystem';
import { LiveActivityFeed } from './LiveActivityFeed';
import { NexusIntelligencePanel } from './NexusIntelligencePanel';

export function Dashboard({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const { user } = useAuth();
  const { emit } = useAnalytics();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [credit, setCredit] = useState<CreditReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) emit('page_view', { event_name: 'dashboard_viewed', feature: 'dashboard', page: '/dashboard' });
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!user) return;
    (async () => {
      const [profileRes, tasksRes, activityRes, creditRes] = await Promise.all([
        getProfile(user.id),
        getTasks(user.id),
        getActivity(user.id, 5),
        getCreditReport(user.id),
      ]);
      setProfile(profileRes.data);
      setTasks(tasksRes.data);
      setActivity(activityRes.data);
      setCredit(creditRes.data);
      setLoading(false);
    })();
  }, [user]);

  // Derived display values — fall back to sensible defaults when DB is fresh
  const readinessScore = profile?.readiness_score ?? 65;
  const userName = profile?.full_name ?? user?.user_metadata?.full_name ?? user?.email?.split('@')[0] ?? 'there';
  const subscriptionPlan = profile?.subscription_plan ?? 'free';

  const primaryTask = tasks.find(t => t.is_primary && t.status !== 'complete');
  const nextStep = primaryTask?.title ?? 'Complete Business Details';

  const pendingTasks = tasks.filter(t => t.status !== 'complete');

  const creditScore = credit?.score ?? null;
  const fundingMin = credit?.funding_range_min ?? null;
  const fundingMax = credit?.funding_range_max ?? null;
  const utilization = credit?.utilization_percent ?? null;

  const fundingLevel = profile?.current_funding_level ?? 1;
  const roadmapSteps = [
    { label: 'L1: Foundation',       completed: fundingLevel > 1,  active: fundingLevel === 1, locked: false },
    { label: 'L2: 0% Cards',         completed: fundingLevel > 2,  active: fundingLevel === 2, locked: fundingLevel < 2 },
    { label: 'L3: Business Credit',  completed: fundingLevel > 3,  active: fundingLevel === 3, locked: fundingLevel < 3 },
    { label: 'L4: SBA & Term Loans', completed: false,             active: fundingLevel === 4, locked: fundingLevel < 4 },
  ];

  // Journey steps derived from data
  const journeySteps = [
    {
      label: 'Upload Credit Report',
      done: credit !== null,
      icon: credit !== null ? null : '📄',
    },
    {
      label: 'AI Credit Analysis',
      done: credit !== null && creditScore !== null,
      icon: credit !== null && creditScore !== null ? null : '🤖',
    },
    {
      label: 'Funding Strategy',
      done: fundingLevel > 1,
      icon: fundingLevel > 1 ? null : '🗺️',
    },
    {
      label: 'Business Opportunities',
      done: fundingLevel > 2,
      icon: fundingLevel > 2 ? null : '🚀',
    },
  ];

  // Risk badge color
  const riskColor = readinessScore >= 70 ? '#22c55e' : readinessScore >= 40 ? '#f59e0b' : '#ef4444';
  const riskLabel = readinessScore >= 70 ? 'Low Risk' : readinessScore >= 40 ? 'Moderate Risk' : 'High Risk';

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[#5B7CFA]" />
      </div>
    );
  }

  return (
    <div style={{ padding: '10px 12px', background: '#eaebf6', minHeight: '100%' }}>
      {/* Page header — compact, elegant */}
      <motion.div
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ marginBottom: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
      >
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 800, color: '#1a1c3a', marginBottom: 1 }}>
            Welcome back, {userName} 👋
          </h1>
          <p style={{ fontSize: 12, color: '#8b8fa8', margin: 0 }}>
            {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            {' · '}
            <span style={{ color: '#3d5af1', fontWeight: 600 }}>{readinessScore}% Ready</span>
          </p>
        </div>
        {/* Live pulse indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6,
          padding: '5px 10px', borderRadius: 20,
          background: 'linear-gradient(135deg, #1a1c3a 0%, #2d3160 100%)',
          border: '1px solid rgba(61,90,241,0.3)',
        }}>
          <motion.div
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            style={{ width: 6, height: 6, borderRadius: '50%', background: '#3d5af1' }}
          />
          <span style={{ fontSize: 10, fontWeight: 700, color: '#7b9bf8' }}>LIVE</span>
        </div>
      </motion.div>

      {/* Three-column layout: main | intelligence | sidebar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-start' }}>

        {/* ── LEFT MAIN COLUMN ── */}
        <div style={{ flex: '1 1 260px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>

          {/* 1. Upload Credit Report hero card */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="glass-card"
            style={{
              padding: '12px 14px',
              background: credit
                ? 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)'
                : 'linear-gradient(135deg, #dbeafe 0%, #ede9fe 100%)',
              border: credit ? '1px solid #86efac' : '1px solid #c7d2fe',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 20 }}>🚀</span>
                  <h2 style={{ fontSize: 16, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>
                    {credit ? 'Credit Report Uploaded' : 'Upload Your Credit Report'}
                  </h2>
                </div>
                <p style={{ fontSize: 12, color: '#8b8fa8', marginBottom: credit ? 0 : 10 }}>
                  {credit
                    ? 'Analyzed — review your funding range below.'
                    : 'Get your personalized funding range in 2 minutes.'}
                </p>
                {!credit && (
                  <button
                    onClick={() => onNavigate?.('credit')}
                    className="nexus-button-primary"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', fontSize: 13, fontWeight: 600, borderRadius: 8, border: 'none', cursor: 'pointer' }}
                  >
                    Upload Report <ArrowRight size={13} />
                  </button>
                )}
              </div>
              {credit && <CheckCircle2 size={28} color="#22c55e" style={{ flexShrink: 0 }} />}
            </div>
          </motion.div>

          {/* 2. Funding Journey card — compact with inline stats */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-card"
            style={{ padding: '12px 14px' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
              <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>Funding Journey</h3>
              <span style={{ fontSize: 13, color: '#3d5af1', fontWeight: 700 }}>{readinessScore}% Ready</span>
            </div>
            <div style={{ height: 4, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden', marginBottom: 8 }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${readinessScore}%` }}
                transition={{ duration: 0.8, ease: 'easeOut', delay: 0.3 }}
                style={{ height: '100%', background: 'linear-gradient(90deg, #3d5af1, #7c3aed)', borderRadius: 10 }}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 5 }}>
              {journeySteps.map((step, i) => (
                <div key={i} style={{
                  padding: '7px 5px',
                  borderRadius: 8,
                  background: step.done ? '#eef0fd' : '#f7f8ff',
                  border: `1px solid ${step.done ? '#3d5af1' : '#e8e9f2'}`,
                  textAlign: 'center',
                }}>
                  <div style={{ marginBottom: 3 }}>
                    {step.done
                      ? <CheckCircle2 size={16} color="#3d5af1" style={{ margin: '0 auto' }} />
                      : <span style={{ fontSize: 16 }}>{step.icon}</span>
                    }
                  </div>
                  <p style={{ fontSize: 11, fontWeight: 600, color: step.done ? '#3d5af1' : '#8b8fa8', lineHeight: 1.3, margin: 0 }}>
                    {step.label}
                  </p>
                </div>
              ))}
            </div>
          </motion.div>

          {/* 3. Funding Range + Readiness — premium card */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="glass-card"
            style={{
              padding: '14px 16px',
              background: 'linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%)',
            }}
          >
            {/* Header row with funding range inline */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <div>
                <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', margin: 0, marginBottom: 2 }}>
                  Estimated Funding Range
                </h3>
                <p style={{ fontSize: 22, fontWeight: 800, color: fundingMin !== null ? '#1a1c3a' : '#c7d2fe', margin: 0 }}>
                  {fundingMin !== null && fundingMax !== null
                    ? `$${(fundingMin / 1000).toFixed(0)}k – $${(fundingMax / 1000).toFixed(0)}k`
                    : 'No report yet'}
                </p>
              </div>
              <span style={{
                background: riskColor + '18', color: riskColor,
                borderRadius: 20, padding: '4px 12px',
                fontSize: 12, fontWeight: 700,
                border: `1px solid ${riskColor}30`,
              }}>
                {riskLabel}
              </span>
            </div>

            {/* Compact readiness bar */}
            <div style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#8b8fa8', marginBottom: 4 }}>
                <span>Readiness Score</span>
                <span style={{ fontWeight: 700, color: '#3d5af1' }}>{readinessScore}%</span>
              </div>
              <div style={{ height: 5, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden' }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${readinessScore}%` }}
                  transition={{ duration: 0.9, ease: 'easeOut', delay: 0.4 }}
                  style={{ height: '100%', background: `linear-gradient(90deg, ${riskColor}, #3d5af1)`, borderRadius: 10 }}
                />
              </div>
            </div>

            {/* Info tip — compact */}
            {(utilization != null && utilization > 10) && (
              <div style={{
                background: '#fffbeb', border: '1px solid #fde68a',
                borderRadius: 7, padding: '7px 10px', marginBottom: 8,
                display: 'flex', gap: 6, alignItems: 'flex-start',
              }}>
                <AlertCircle size={13} color="#f59e0b" style={{ flexShrink: 0, marginTop: 1 }} />
                <p style={{ fontSize: 11, color: '#92400e', margin: 0 }}>
                  Utilization {utilization.toFixed(0)}% — reduce below 10% to unlock higher funding.
                </p>
              </div>
            )}

            <button
              onClick={() => onNavigate?.('action-center')}
              className="nexus-button-primary"
              style={{
                width: '100%',
                padding: '11px 0',
                fontSize: 13,
                fontWeight: 600,
                borderRadius: 8,
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              <TrendingUp size={14} /> Improve Approval Odds
            </button>
          </motion.div>

          {/* 4. Recent Activity — compact */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-card"
            style={{ padding: '10px 14px' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 7 }}>
              <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>Recent Activity</h3>
              <Activity size={12} color="#8b8fa8" />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {activity.length > 0
                ? activity.slice(0, 4).map((item) => (
                    <div key={item.id} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <div style={{ width: 24, height: 24, borderRadius: 6, background: '#eef0fd', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        <Zap size={11} color="#3d5af1" />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontSize: 11, fontWeight: 600, color: '#1a1c3a', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.actor}
                        </p>
                        <p style={{ fontSize: 10, color: '#8b8fa8', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.action}
                        </p>
                      </div>
                      <span style={{ fontSize: 9, color: '#8b8fa8', flexShrink: 0 }}>
                        {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  ))
                : (
                    <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>No activity yet — complete a task to get started.</p>
                  )}
            </div>
          </motion.div>
        </div>

        {/* ── MIDDLE INTELLIGENCE COLUMN ── */}
        <div style={{ flex: '1 1 200px', maxWidth: 300, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <NexusIntelligencePanel onNavigate={onNavigate} />

          {/* Quick stats strip */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[
              { label: 'Credit Score', value: creditScore ? `${creditScore}` : '—', color: '#3d5af1', sub: 'FICO' },
              { label: 'Funding Level', value: `L${fundingLevel}`, color: '#7c3aed', sub: 'Journey' },
              { label: 'Tasks Left', value: `${pendingTasks.length}`, color: pendingTasks.length > 0 ? '#f59e0b' : '#22c55e', sub: 'Actions' },
              { label: 'Readiness', value: `${readinessScore}%`, color: riskColor, sub: 'Score' },
            ].map(stat => (
              <div key={stat.label} style={{
                padding: '10px 12px', borderRadius: 12,
                background: '#fff', border: '1px solid #e8e9f2',
                boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
              }}>
                <p style={{ fontSize: 18, fontWeight: 800, color: stat.color, margin: 0, lineHeight: 1 }}>{stat.value}</p>
                <p style={{ fontSize: 9, color: '#8b8fa8', margin: '3px 0 0', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{stat.label}</p>
                <p style={{ fontSize: 9, color: '#c5c9d6', margin: 0 }}>{stat.sub}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ── RIGHT SIDEBAR ── */}
        <div style={{ flex: '1 1 200px', maxWidth: 300, display: 'flex', flexDirection: 'column', gap: 10 }}>

          {/* Next Best Action (primary task) */}
          {primaryTask ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.08 }}
              style={{
                padding: '14px 16px', borderRadius: 16,
                background: 'linear-gradient(135deg, #1a1c3a 0%, #3d5af1 100%)',
                color: '#fff',
                boxShadow: '0 4px 20px rgba(61,90,241,0.3), 0 0 40px rgba(61,90,241,0.12)',
                border: '1px solid rgba(61,90,241,0.4)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                <Target size={12} color="rgba(255,255,255,0.7)" />
                <p style={{ fontSize: 10, fontWeight: 700, opacity: 0.75, margin: 0, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Next Best Action
                </p>
              </div>
              <p style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, lineHeight: 1.4 }}>
                {primaryTask.title}
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 12, opacity: 0.8 }}>
                <Sparkles size={11} />
                <span style={{ fontSize: 11, fontWeight: 600 }}>+{primaryTask.readiness_impact}% readiness impact</span>
              </div>
              <button
                onClick={() => onNavigate?.('action-center')}
                style={{
                  width: '100%', padding: '8px 0', fontSize: 12, fontWeight: 700,
                  borderRadius: 10, border: '1px solid rgba(255,255,255,0.35)',
                  background: 'rgba(255,255,255,0.15)', color: '#fff', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                  backdropFilter: 'blur(8px)',
                }}
              >
                Start Task <ArrowRight size={12} />
              </button>
            </motion.div>
          ) : (
            <div style={{ padding: 14, borderRadius: 16, background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <CheckCircle2 size={18} color="#22c55e" />
                <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>All Tasks Complete!</h3>
              </div>
              <p style={{ fontSize: 13, color: '#8b8fa8', margin: 0 }}>Check back soon for new recommendations.</p>
            </div>
          )}

          {/* Readiness Score Breakdown — compact multi-bar */}
          <div className="glass-card" style={{ padding: '12px 14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <h3 style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>Readiness Breakdown</h3>
              <button onClick={() => onNavigate?.('action-center')} style={{
                background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 11, fontWeight: 700, color: '#3d5af1', padding: 0,
                display: 'flex', alignItems: 'center', gap: 3,
              }}>
                Improve <ArrowRight size={10} />
              </button>
            </div>
            {[
              { label: 'Credit', score: creditScore ? Math.min(100, Math.round(((creditScore - 300) / 550) * 100)) : 0, color: '#3d5af1', tab: 'credit' },
              { label: 'Business', score: profile?.current_funding_level ? (profile.current_funding_level - 1) * 30 : 0, color: '#6366f1', tab: 'business-setup' },
              { label: 'Funding', score: readinessScore, color: '#22c55e', tab: 'funding' },
              { label: 'Grants', score: readinessScore > 50 ? 45 : 20, color: '#f59e0b', tab: 'grants' },
            ].map(item => (
              <div key={item.label} style={{ marginBottom: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                  <button onClick={() => onNavigate?.(item.tab)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600, color: '#1a1c3a', padding: 0 }}>
                    {item.label}
                  </button>
                  <span style={{ fontSize: 11, fontWeight: 700, color: item.color }}>{item.score}%</span>
                </div>
                <div style={{ height: 3, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden' }}>
                  <div style={{ width: `${item.score}%`, height: '100%', background: item.color, borderRadius: 10, transition: 'width 0.5s ease' }} />
                </div>
              </div>
            ))}
          </div>

          {/* Progression System */}
          <ProgressionSystem score={readinessScore} onNavigate={onNavigate} />

          {/* Active Tasks — compact */}
          <div className="glass-card" style={{ padding: '12px 14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <h3 style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>Active Tasks</h3>
              <span style={{ background: '#f59e0b18', color: '#f59e0b', borderRadius: 10, padding: '2px 8px', fontSize: 11, fontWeight: 700 }}>
                {pendingTasks.length}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {pendingTasks.slice(0, 3).map(task => (
                <div key={task.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 7 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: task.is_primary ? '#3d5af1' : '#f59e0b', flexShrink: 0, marginTop: 4 }} />
                  <p style={{ fontSize: 12, color: '#1a1c3a', margin: 0, lineHeight: 1.4 }}>{task.title}</p>
                </div>
              ))}
              {pendingTasks.length === 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <CheckCircle2 size={14} color="#22c55e" />
                  <p style={{ fontSize: 12, color: '#22c55e', margin: 0, fontWeight: 600 }}>All caught up!</p>
                </div>
              )}
            </div>
            {pendingTasks.length > 0 && (
              <button onClick={() => onNavigate?.('action-center')} style={{ width: '100%', marginTop: 8, padding: '7px 0', borderRadius: 8, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 12, fontWeight: 700, color: '#3d5af1', cursor: 'pointer' }}>
                View All Tasks
              </button>
            )}
          </div>

          {/* AI Workforce */}
          <LiveActivityFeed />

          {/* Invite Friends — compact */}
          <div className="glass-card" style={{ padding: '12px 14px' }}>
            <h3 style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a', marginBottom: 3 }}>
              Invite &amp; Earn Rewards
            </h3>
            <p style={{ fontSize: 11, color: '#8b8fa8', marginBottom: 8 }}>
              2% commission on every friend's approved funding.
            </p>
            <div style={{ background: '#eef0fd', border: '1px solid #e8e9f2', borderRadius: 7, padding: '6px 10px', fontSize: 11, color: '#3d5af1', fontWeight: 600, marginBottom: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              nexuslive.app/ref/{user?.id?.slice(0, 8) ?? 'xxxxxxxx'}
            </div>
            <button onClick={() => onNavigate?.('referral')} className="nexus-button-primary" style={{ width: '100%', padding: '8px 0', fontSize: 12, fontWeight: 600, borderRadius: 8, border: 'none', cursor: 'pointer' }}>
              Invite &amp; Earn
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
