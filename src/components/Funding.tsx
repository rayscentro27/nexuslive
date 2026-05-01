import React, { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, TrendingUp, DollarSign, Award, Percent, Loader2, Plus } from 'lucide-react';
import { useAuth } from './AuthProvider';
import { getProfile, getFundingApplications, getTasks, UserProfile, FundingApplication, Task } from '../lib/db';

function statusColors(status: string): { text: string; color: string } {
  switch (status.toLowerCase()) {
    case 'approved':  return { text: 'Approved',  color: '#22c55e' };
    case 'pending':   return { text: 'Pending',   color: '#3d5af1' };
    case 'submitted': return { text: 'Submitted', color: '#f59e0b' };
    case 'rejected':  return { text: 'Rejected',  color: '#ef4444' };
    default:          return { text: status,       color: '#8b8fa8' };
  }
}

function formatAmount(n: number | null) {
  if (n === null) return '—';
  return '$' + n.toLocaleString();
}

const TABS = ['Overview', 'Applications', 'Pipeline', 'History'] as const;
type Tab = typeof TABS[number];

export function Funding() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [applications, setApplications] = useState<FundingApplication[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>('Overview');

  useEffect(() => {
    if (!user) return;
    Promise.all([
      getProfile(user.id),
      getFundingApplications(user.id),
      getTasks(user.id),
    ]).then(([{ data: p }, { data: apps }, { data: t }]) => {
      setProfile(p);
      setApplications(apps);
      setTasks(t);
      setLoading(false);
    });
  }, [user]);

  const readiness = profile?.readiness_score ?? 0;
  const circumference = 314;
  const offset = circumference * (1 - readiness / 100);

  // Derive checklist from tasks (primary tasks only)
  const primaryTasks = tasks.filter(t => t.is_primary).slice(0, 4);
  const checklistItems = primaryTasks.length > 0 ? primaryTasks : [
    { id: '1', title: 'Business EIN & Formation Docs', status: 'pending' },
    { id: '2', title: 'Last 3 Months Bank Statements', status: 'pending' },
    { id: '3', title: 'Business Website & Email', status: 'pending' },
    { id: '4', title: "Personal ID (Driver's License)", status: 'pending' },
  ] as any[];

  const readinessLabel = readiness >= 80 ? "You're ready to apply!" : readiness >= 50 ? "Almost there!" : "Keep building your profile";
  const readinessDesc = readiness >= 80
    ? "Your profile meets requirements for $50k+ funding."
    : readiness >= 50
    ? "Complete your remaining tasks to unlock higher funding."
    : "Complete your setup steps to improve your funding readiness.";

  // Metric calculations
  const totalApplied = applications.reduce((sum, a) => sum + (a.requested_amount ?? 0), 0);
  const preApprovedCount = applications.filter(a => a.status === 'approved').length;
  const preApprovedAmt = applications
    .filter(a => a.status === 'approved')
    .reduce((sum, a) => sum + (a.approved_amount ?? a.requested_amount ?? 0), 0);

  // Static fallback pipeline data
  const pipelineStages = [
    { label: 'Submitted', pct: 85, color: '#3d5af1' },
    { label: 'Under Review', pct: 60, color: '#f59e0b' },
    { label: 'Pre-Approved', pct: 40, color: '#22c55e' },
    { label: 'Funded', pct: 20, color: '#8b8fa8' },
  ];

  // Static lender matches
  const lenderMatches = [
    { name: 'Fundbox', match: 94 },
    { name: 'OnDeck', match: 87 },
    { name: 'Lendio', match: 81 },
  ];

  // Approval odds checklist — static placeholders, real data preferred if available
  const oddsItems = [
    { label: 'Credit Utilization', ok: ((profile as any)?.credit_utilization ?? 99) < 30 },
    { label: 'Accounts Open', ok: ((profile as any)?.accounts_open ?? 0) >= 2 },
    { label: 'Business Age', ok: ((profile as any)?.business_age_months ?? 0) >= 12 },
    { label: 'Annual Revenue', ok: ((profile as any)?.annual_revenue ?? 0) >= 50000 },
  ];

  // Table data: real apps or static fallback
  const tableApps: (FundingApplication | { id: string; lender_name: string; requested_amount: number; status: string; product_type?: string })[] =
    applications.length > 0
      ? applications
      : [
          { id: 's1', lender_name: 'Chase Business', requested_amount: 50000, status: 'pending', product_type: 'Business Line' },
          { id: 's2', lender_name: 'Fundbox',        requested_amount: 25000, status: 'approved', product_type: 'Invoice Financing' },
          { id: 's3', lender_name: 'OnDeck',         requested_amount: 35000, status: 'submitted', product_type: 'Term Loan' },
        ];

  const readinessColor = readiness >= 80 ? '#22c55e' : readiness >= 50 ? '#3d5af1' : '#f59e0b';
  const readinessRisk = readiness >= 80 ? 'Low Risk' : readiness >= 50 ? 'Medium' : 'High Risk';
  const readinessRiskColor = readiness >= 80 ? '#22c55e' : readiness >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <div className="p-6 max-w-6xl mx-auto h-full flex flex-col overflow-y-auto no-scrollbar" style={{ gap: 24 }}>
      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexShrink: 0 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>Funding</h1>
          <p style={{ fontSize: 13, color: '#8b8fa8', marginTop: 4 }}>Track your funding applications and opportunities.</p>
        </div>
        <button className="nexus-button-primary" style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 18px', fontSize: 13 }}>
          <Plus size={15} /> New Application
        </button>
      </div>

      {loading ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Loader2 className="animate-spin" size={28} color="#8b8fa8" />
        </div>
      ) : (
        <>
          {/* ── Metric Cards ── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, flexShrink: 0 }}>
            {[
              {
                icon: DollarSign,
                iconBg: '#eef0fd',
                iconColor: '#3d5af1',
                value: totalApplied > 0 ? '$' + (totalApplied / 1000).toFixed(0) + 'k' : '$128k',
                label: 'Total Applied',
              },
              {
                icon: Award,
                iconBg: '#f0fdf4',
                iconColor: '#22c55e',
                value: preApprovedAmt > 0 ? '$' + (preApprovedAmt / 1000).toFixed(0) + 'k' : '$25k',
                label: 'Pre-Approved',
              },
              {
                icon: TrendingUp,
                iconBg: '#fff7ed',
                iconColor: '#f59e0b',
                value: '$23.5k',
                label: 'Funded (All Time)',
              },
              {
                icon: Percent,
                iconBg: '#fef2f2',
                iconColor: '#ef4444',
                value: '68%',
                label: 'Approval Rate',
              },
            ].map(({ icon: Icon, iconBg, iconColor, value, label }) => (
              <div key={label} className="glass-card" style={{ padding: '20px 18px', display: 'flex', alignItems: 'center', gap: 14 }}>
                <div style={{ width: 44, height: 44, borderRadius: 12, background: iconBg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Icon size={20} color={iconColor} />
                </div>
                <div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: '#1a1c3a', lineHeight: 1 }}>{value}</div>
                  <div style={{ fontSize: 12, color: '#8b8fa8', marginTop: 3 }}>{label}</div>
                </div>
              </div>
            ))}
          </div>

          {/* ── Tab Bar ── */}
          <div style={{ display: 'flex', gap: 4, background: '#eaebf6', borderRadius: 10, padding: 4, flexShrink: 0, width: 'fit-content' }}>
            {TABS.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  padding: '7px 18px',
                  borderRadius: 7,
                  fontSize: 13,
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                  background: activeTab === tab ? '#fff' : 'transparent',
                  color: activeTab === tab ? '#1a1c3a' : '#8b8fa8',
                  boxShadow: activeTab === tab ? '0 1px 4px rgba(0,0,0,0.08)' : 'none',
                  transition: 'all 0.15s',
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* ── Two-Column Body ── */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: 20, flex: 1, minHeight: 0 }}>
            {/* Left main column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {/* Overview / Pipeline tabs: hero + pipeline card */}
              {(activeTab === 'Overview' || activeTab === 'Pipeline') && (
                <>
                  {/* Hero Banner */}
                  <div className="glass-card" style={{ padding: 24, background: 'linear-gradient(135deg, #eef0fd 0%, #fff 100%)', position: 'relative', overflow: 'hidden' }}>
                    <div style={{ position: 'absolute', top: -20, right: -20, width: 120, height: 120, borderRadius: '50%', background: '#3d5af108' }} />
                    <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                      {/* Mini readiness circle */}
                      <div style={{ position: 'relative', width: 72, height: 72, flexShrink: 0 }}>
                        <svg width="72" height="72" style={{ transform: 'rotate(-90deg)' }}>
                          <circle cx="36" cy="36" r="32" fill="none" stroke="#e8e9f2" strokeWidth="6" />
                          <circle
                            cx="36" cy="36" r="32" fill="none"
                            stroke={readinessColor}
                            strokeWidth="6"
                            strokeDasharray={201}
                            strokeDashoffset={201 * (1 - readiness / 100)}
                            strokeLinecap="round"
                          />
                        </svg>
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                          <span style={{ fontSize: 14, fontWeight: 800, color: '#1a1c3a' }}>{readiness}%</span>
                        </div>
                      </div>

                      <div style={{ flex: 1 }}>
                        <p style={{ fontSize: 12, color: '#8b8fa8', marginBottom: 4 }}>Your Estimated Funding Range</p>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{ fontSize: 28, fontWeight: 800, color: '#1a1c3a' }}>$25,000 – $75,000</span>
                          <span style={{ background: readinessRiskColor + '18', color: readinessRiskColor, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 600 }}>
                            {readinessRisk}
                          </span>
                        </div>
                        <p style={{ fontSize: 12, color: '#8b8fa8', marginTop: 4 }}>{readinessDesc}</p>
                      </div>
                    </div>
                  </div>

                  {/* Application Pipeline */}
                  <div className="glass-card" style={{ padding: 20 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1c3a', marginBottom: 16 }}>Application Pipeline</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                      {pipelineStages.map(({ label, pct, color }) => (
                        <div key={label}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                            <span style={{ fontSize: 13, color: '#1a1c3a', fontWeight: 500 }}>{label}</span>
                            <span style={{ fontSize: 12, color: '#8b8fa8' }}>{pct}%</span>
                          </div>
                          <div style={{ height: 6, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden' }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 10 }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Active Applications Table */}
              <div className="glass-card" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1c3a', marginBottom: 16 }}>
                  {activeTab === 'History' ? 'Funding History' : 'Active Applications'}
                </h3>

                {/* Table Header */}
                <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1.2fr 0.8fr 1.2fr', gap: 8, padding: '8px 12px', background: '#eaebf6', borderRadius: 8, marginBottom: 8 }}>
                  {['Product', 'Amount', 'Lender', 'Status', 'Progress'].map(col => (
                    <span key={col} style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{col}</span>
                  ))}
                </div>

                {/* Table Rows */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {tableApps.map((app: any) => {
                    const { color } = statusColors(app.status);
                    const amount = app.approved_amount ?? app.requested_amount;
                    const progress = app.status === 'approved' ? 100 : app.status === 'submitted' ? 60 : app.status === 'pending' ? 35 : 10;
                    return (
                      <div key={app.id} style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1.2fr 0.8fr 1.2fr', gap: 8, padding: '10px 12px', borderRadius: 8, alignItems: 'center', transition: 'background 0.15s' }}
                        onMouseEnter={e => (e.currentTarget.style.background = '#eaebf6')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                      >
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1c3a' }}>{(app as any).product_type ?? 'Business Loan'}</span>
                        <span style={{ fontSize: 13, color: '#1a1c3a' }}>{formatAmount(amount)}</span>
                        <span style={{ fontSize: 13, color: '#8b8fa8' }}>{app.lender_name ?? 'Unknown'}</span>
                        <span style={{ background: color + '18', color, borderRadius: 20, padding: '2px 10px', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap' }}>
                          {app.status.charAt(0).toUpperCase() + app.status.slice(1)}
                        </span>
                        <div style={{ height: 6, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden' }}>
                          <div style={{ width: `${progress}%`, height: '100%', background: color, borderRadius: 10 }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* ── Right Sidebar ── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Improve Approval Odds */}
              <div className="glass-card" style={{ padding: 18 }}>
                <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', marginBottom: 14 }}>Improve Approval Odds</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {oddsItems.map(({ label, ok }) => (
                    <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      {ok
                        ? <CheckCircle2 size={16} color="#22c55e" style={{ flexShrink: 0 }} />
                        : <XCircle size={16} color="#ef4444" style={{ flexShrink: 0 }} />
                      }
                      <span style={{ fontSize: 13, color: ok ? '#1a1c3a' : '#8b8fa8', fontWeight: ok ? 600 : 400 }}>{label}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Lender Matches */}
              <div className="glass-card" style={{ padding: 18 }}>
                <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a', marginBottom: 14 }}>Lender Matches</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {lenderMatches.map(({ name, match }) => (
                    <div key={name}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1c3a' }}>{name}</span>
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#3d5af1' }}>{match}%</span>
                      </div>
                      <div style={{ height: 6, background: '#e8e9f2', borderRadius: 10, overflow: 'hidden' }}>
                        <div style={{ width: `${match}%`, height: '100%', background: '#3d5af1', borderRadius: 10 }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
