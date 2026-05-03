import React, { useEffect, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  TrendingUp,
  ShieldCheck,
  FileText,
  Zap,
  Lock,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';
import { useAuth } from './AuthProvider';
import {
  getProfile, getTasks, getActivity, getCreditReport,
  UserProfile, Task, ActivityItem, CreditReport
} from '../lib/db';

export function Dashboard({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [credit, setCredit] = useState<CreditReport | null>(null);
  const [loading, setLoading] = useState(true);

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
  const fundingMin = credit?.funding_range_min ?? 13000;
  const fundingMax = credit?.funding_range_max ?? 75000;
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
    <div style={{ padding: '16px 20px', background: '#eaebf6' }}>
      {/* Page header */}
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1a1c3a', marginBottom: 3 }}>
          Welcome back, {userName} 👋
        </h1>
        <p style={{ fontSize: 15, color: '#8b8fa8' }}>
          Here's where your funding journey stands today.
        </p>
      </div>

      {/* Two-column layout */}
      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>

        {/* ── LEFT MAIN COLUMN ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 14 }}>

          {/* 1. Upload Credit Report hero card */}
          <div
            className="glass-card"
            style={{
              padding: '18px 20px',
              background: 'linear-gradient(135deg, #dbeafe 0%, #ede9fe 100%)',
              border: '1px solid #e8e9f2',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 28, marginBottom: 6 }}>🚀</div>
                <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a1c3a', marginBottom: 5 }}>
                  {credit ? 'Credit Report Uploaded' : 'Upload Your Credit Report'}
                </h2>
                <p style={{ fontSize: 14, color: '#8b8fa8', marginBottom: 12 }}>
                  {credit
                    ? 'Your credit report has been analyzed. Review your funding range below.'
                    : 'Get your personalized funding range and AI-powered credit analysis in minutes.'}
                </p>
                {!credit && (
                  <button
                    onClick={() => onNavigate?.('credit')}
                    className="nexus-button-primary"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 20px', fontSize: 14, fontWeight: 600, borderRadius: 8, border: 'none', cursor: 'pointer' }}
                  >
                    Upload Report <ArrowRight size={15} />
                  </button>
                )}
              </div>
              {credit && (
                <div style={{ textAlign: 'right' }}>
                  <CheckCircle2 size={32} color="#22c55e" />
                </div>
              )}
            </div>
            {!credit && (
              <div style={{ marginTop: 12, display: 'flex', gap: 16, fontSize: 13, color: '#8b8fa8' }}>
                <span>⏱ Takes 2 minutes</span>
                <span>🔒 Secure</span>
                <span>📱 Phone or computer</span>
              </div>
            )}
          </div>

          {/* 2. Funding Journey card */}
          <div className="glass-card" style={{ padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3 style={{ fontSize: 17, fontWeight: 700, color: '#1a1c3a' }}>Funding Journey</h3>
              <span style={{ fontSize: 15, color: '#3d5af1', fontWeight: 600 }}>{readinessScore}% Ready</span>
            </div>

            {/* Progress bar */}
            <div style={{ height: 7, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden', marginBottom: 14 }}>
              <div style={{ width: `${readinessScore}%`, height: '100%', background: '#3d5af1', borderRadius: 10 }} />
            </div>

            {/* Journey step boxes */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
              {journeySteps.map((step, i) => (
                <div
                  key={i}
                  style={{
                    padding: '12px 10px',
                    borderRadius: 10,
                    background: step.done ? '#eef0fd' : '#f7f8ff',
                    border: `1px solid ${step.done ? '#3d5af1' : '#e8e9f2'}`,
                    textAlign: 'center',
                  }}
                >
                  <div style={{ marginBottom: 6 }}>
                    {step.done
                      ? <CheckCircle2 size={20} color="#3d5af1" style={{ margin: '0 auto' }} />
                      : <span style={{ fontSize: 20 }}>{step.icon}</span>
                    }
                  </div>
                  <p style={{ fontSize: 13, fontWeight: 600, color: step.done ? '#3d5af1' : '#8b8fa8', lineHeight: 1.3 }}>
                    {step.label}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* 3. Estimated Funding Range card */}
          <div className="glass-card" style={{ padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3 style={{ fontSize: 17, fontWeight: 700, color: '#1a1c3a' }}>Estimated Funding Range</h3>
              <span
                style={{
                  background: riskColor + '18',
                  color: riskColor,
                  borderRadius: 20,
                  padding: '3px 12px',
                  fontSize: 13,
                  fontWeight: 600,
                }}
              >
                {riskLabel}
              </span>
            </div>

            {/* Readiness progress bar */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, color: '#8b8fa8', marginBottom: 6 }}>
                <span>Readiness Score</span>
                <span style={{ fontWeight: 600, color: '#1a1c3a' }}>{readinessScore}%</span>
              </div>
              <div style={{ height: 7, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden' }}>
                <div style={{ width: `${readinessScore}%`, height: '100%', background: '#3d5af1', borderRadius: 10 }} />
              </div>
            </div>

            {/* Info box */}
            <div
              style={{
                background: '#fef9c3',
                border: '1px solid #fde68a',
                borderRadius: 8,
                padding: '10px 14px',
                marginBottom: 12,
                display: 'flex',
                gap: 8,
                alignItems: 'flex-start',
              }}
            >
              <AlertCircle size={15} color="#f59e0b" style={{ flexShrink: 0, marginTop: 1 }} />
              <p style={{ fontSize: 14, color: '#92400e', margin: 0 }}>
                {utilization != null && utilization > 10
                  ? `Credit utilization at ${utilization.toFixed(0)}%. Reducing below 10% can unlock higher funding.`
                  : 'Upload your credit report to get a precise funding estimate tailored to your profile.'}
              </p>
            </div>

            {/* Funding amount */}
            <div style={{ textAlign: 'center', marginBottom: 14 }}>
              <p style={{ fontSize: 14, color: '#8b8fa8', marginBottom: 4 }}>Estimated range</p>
              <p style={{ fontSize: 34, fontWeight: 800, color: '#1a1c3a' }}>
                ${(fundingMin / 1000).toFixed(0)}k – ${(fundingMax / 1000).toFixed(0)}k
              </p>
            </div>

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
              <TrendingUp size={15} /> Improve Approval Odds
            </button>
          </div>

          {/* 4. Recent Activity card */}
          <div className="glass-card" style={{ padding: 18 }}>
            <h3 style={{ fontSize: 17, fontWeight: 700, color: '#1a1c3a', marginBottom: 12 }}>Recent Activity</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {activity.length > 0
                ? activity.map((item) => (
                    <div key={item.id} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                      <div style={{ width: 36, height: 36, borderRadius: 8, background: '#eef0fd', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        <Zap size={17} color="#3d5af1" />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <p style={{ fontSize: 14, fontWeight: 600, color: '#1a1c3a', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {item.actor}
                          </p>
                          <span style={{ fontSize: 12, color: '#8b8fa8', flexShrink: 0, marginLeft: 8 }}>
                            {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p style={{ fontSize: 13, color: '#8b8fa8', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.action}
                        </p>
                      </div>
                    </div>
                  ))
                : [
                    { actor: 'James Mitchell', action: 'Analyzed credit report. Found 2 new disputes.', time: '10m' },
                    { actor: 'Nexus AI', action: 'Business entity filed Articles of Incorporation.', time: '2h' },
                    { actor: 'Nexus AI', action: 'Credit report data parsed. 5 items found.', time: '4h' },
                  ].map((item, i) => (
                    <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                      <div style={{ width: 36, height: 36, borderRadius: 8, background: '#eef0fd', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        <Zap size={17} color="#3d5af1" />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <p style={{ fontSize: 14, fontWeight: 600, color: '#1a1c3a', margin: 0 }}>{item.actor}</p>
                          <span style={{ fontSize: 12, color: '#8b8fa8' }}>{item.time}</span>
                        </div>
                        <p style={{ fontSize: 13, color: '#8b8fa8', margin: 0 }}>{item.action}</p>
                      </div>
                    </div>
                  ))}
            </div>
          </div>
        </div>

        {/* ── RIGHT SIDEBAR (260px) ── */}
        <div style={{ width: 260, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>

          {/* Next Best Action (primary task) */}
          {primaryTask ? (
            <div style={{
              padding: 18, borderRadius: 16,
              background: 'linear-gradient(135deg, #3d5af1 0%, #6366f1 100%)',
              color: '#fff', boxShadow: '0 4px 16px rgba(61,90,241,0.25)',
            }}>
              <p style={{ fontSize: 11, fontWeight: 700, opacity: 0.8, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Next Best Action
              </p>
              <p style={{ fontSize: 15, fontWeight: 700, marginBottom: 10, lineHeight: 1.4 }}>
                {primaryTask.title}
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 14, opacity: 0.85 }}>
                <Zap size={12} />
                <span style={{ fontSize: 12, fontWeight: 600 }}>+{primaryTask.readiness_impact}% readiness impact</span>
              </div>
              <button
                onClick={() => onNavigate?.('action-center')}
                style={{
                  width: '100%', padding: '9px 0', fontSize: 13, fontWeight: 700,
                  borderRadius: 10, border: '1px solid rgba(255,255,255,0.4)',
                  background: 'rgba(255,255,255,0.18)', color: '#fff', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}
              >
                Start Task <ArrowRight size={13} />
              </button>
            </div>
          ) : (
            <div style={{ padding: 18, borderRadius: 16, background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <CheckCircle2 size={18} color="#22c55e" />
                <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>All Tasks Complete!</h3>
              </div>
              <p style={{ fontSize: 13, color: '#8b8fa8', margin: 0 }}>Check back soon for new recommendations.</p>
            </div>
          )}

          {/* Readiness Score Breakdown */}
          <div className="glass-card" style={{ padding: 18 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', marginBottom: 14 }}>Readiness Breakdown</h3>
            {[
              { label: 'Credit', score: creditScore ? Math.min(100, Math.round(((creditScore - 300) / 550) * 100)) : 0, color: '#3d5af1', tab: 'credit' },
              { label: 'Business', score: profile?.current_funding_level ? (profile.current_funding_level - 1) * 30 : 0, color: '#6366f1', tab: 'business-setup' },
              { label: 'Funding', score: readinessScore, color: '#22c55e', tab: 'funding' },
              { label: 'Grants', score: readinessScore > 50 ? 45 : 20, color: '#f59e0b', tab: 'grants' },
            ].map(item => (
              <div key={item.label} style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <button onClick={() => onNavigate?.(item.tab)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600, color: '#1a1c3a', padding: 0 }}>
                    {item.label}
                  </button>
                  <span style={{ fontSize: 13, fontWeight: 700, color: item.color }}>{item.score}%</span>
                </div>
                <div style={{ height: 5, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden' }}>
                  <div style={{ width: `${item.score}%`, height: '100%', background: item.color, borderRadius: 10, transition: 'width 0.5s ease' }} />
                </div>
              </div>
            ))}
            <button onClick={() => onNavigate?.('action-center')} style={{
              width: '100%', marginTop: 4, padding: '9px 0', borderRadius: 10,
              border: '1.5px solid #e8e9f2', background: '#fff',
              fontSize: 13, fontWeight: 700, color: '#3d5af1', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}>
              Improve Scores <ArrowRight size={13} />
            </button>
          </div>

          {/* Pending Tasks card */}
          <div className="glass-card" style={{ padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a' }}>Active Tasks</h3>
              <span style={{ background: '#f59e0b18', color: '#f59e0b', borderRadius: 20, padding: '3px 10px', fontSize: 12, fontWeight: 700 }}>
                {pendingTasks.length}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {pendingTasks.slice(0, 4).map(task => (
                <div key={task.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <span style={{ width: 7, height: 7, borderRadius: '50%', background: task.is_primary ? '#3d5af1' : '#f59e0b', flexShrink: 0, marginTop: 5 }} />
                  <p style={{ fontSize: 13, color: '#1a1c3a', margin: 0, lineHeight: 1.4 }}>{task.title}</p>
                </div>
              ))}
              {pendingTasks.length === 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CheckCircle2 size={16} color="#22c55e" />
                  <p style={{ fontSize: 13, color: '#22c55e', margin: 0, fontWeight: 600 }}>All caught up!</p>
                </div>
              )}
            </div>
            {pendingTasks.length > 0 && (
              <button onClick={() => onNavigate?.('action-center')} style={{ width: '100%', marginTop: 12, padding: '8px 0', borderRadius: 10, border: '1.5px solid #e8e9f2', background: '#fff', fontSize: 13, fontWeight: 700, color: '#3d5af1', cursor: 'pointer' }}>
                View All Tasks
              </button>
            )}
          </div>

          {/* Invite Friends */}
          <div className="glass-card" style={{ padding: 18 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1c3a', marginBottom: 4 }}>
              Invite Friends, Earn Rewards
            </h3>
            <p style={{ fontSize: 12, color: '#8b8fa8', marginBottom: 10 }}>
              Earn 2% commission on every friend's approved funding.
            </p>
            <div style={{ background: '#eef0fd', border: '1px solid #e8e9f2', borderRadius: 8, padding: '7px 11px', fontSize: 12, color: '#3d5af1', fontWeight: 600, marginBottom: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              nexuslive.app/ref/{user?.id?.slice(0, 8) ?? 'xxxxxxxx'}
            </div>
            <button onClick={() => onNavigate?.('referral')} className="nexus-button-primary" style={{ width: '100%', padding: '9px 0', fontSize: 13, fontWeight: 600, borderRadius: 8, border: 'none', cursor: 'pointer' }}>
              Invite &amp; Earn
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
