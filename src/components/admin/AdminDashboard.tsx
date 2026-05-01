import React, { useEffect, useState } from 'react';
import {
  Users, DollarSign, Cpu, ShieldAlert,
  ArrowUpRight, Clock,
} from 'lucide-react';
import {
  getAllClients,
  getAllDocuments,
  getAllFundingApplications,
  getBotProfiles,
  UserProfile,
  Document,
  FundingApplication,
  BotProfile,
} from '../../lib/db';

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

  const metrics = [
    {
      label: 'Active Clients',
      value: loading ? '—' : clients.length.toString(),
      sub: 'Total enrolled',
      icon: Users,
      iconBg: '#eef0fd',
      iconColor: '#3d5af1',
    },
    {
      label: 'Pipeline Value',
      value: loading ? '—' : fmtMoney(pipelineValue),
      sub: 'Funding requested',
      icon: DollarSign,
      iconBg: '#f0fdf4',
      iconColor: '#22c55e',
    },
    {
      label: 'AI Health',
      value: loading ? '—' : `${botHealth}%`,
      sub: `${activeBots} of ${bots.length} active`,
      icon: Cpu,
      iconBg: '#f5f3ff',
      iconColor: '#7c3aed',
    },
    {
      label: 'Docs Pending',
      value: loading ? '—' : pendingDocs.toString(),
      sub: 'Awaiting review',
      icon: ShieldAlert,
      iconBg: pendingDocs > 5 ? '#fff7ed' : '#f0fdf4',
      iconColor: pendingDocs > 5 ? '#f59e0b' : '#22c55e',
    },
  ];

  const recentClients = clients.slice(0, 4);
  const recentApps = applications.slice(0, 3);

  return (
    <div
      style={{ background: '#eaebf6', minHeight: '100%' }}
      className="p-6 md:p-8 space-y-6"
    >
      {/* Page header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: '#1a1c3a', letterSpacing: -0.5, margin: 0 }}>
            Overview
          </h1>
          <p style={{ fontSize: 13, color: '#8b8fa8', marginTop: 4 }}>
            Operational workspace and system-wide performance monitoring.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            className="glass-card"
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 10 }}
          >
            <Clock size={14} style={{ color: '#8b8fa8' }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: '#8b8fa8' }}>
              Last Sync: {lastSync.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <button className="nexus-button-primary" style={{ padding: '8px 18px', fontSize: 12, borderRadius: 10 }}>
            System Report
          </button>
        </div>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m, i) => {
          const Icon = m.icon;
          return (
            <div key={i} className="glass-card" style={{ padding: 20 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 10,
                    background: m.iconBg,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Icon size={20} style={{ color: m.iconColor }} />
                </div>
                <ArrowUpRight size={14} style={{ color: '#e8e9f2' }} />
              </div>
              <div style={{ fontSize: 9, fontWeight: 700, color: '#8b8fa8', letterSpacing: '0.14em', textTransform: 'uppercase' }}>
                {m.label}
              </div>
              <div style={{ fontSize: 26, fontWeight: 800, color: '#1a1c3a', margin: '4px 0 2px', letterSpacing: -1 }}>
                {m.value}
              </div>
              <div style={{ fontSize: 11, color: '#8b8fa8' }}>{m.sub}</div>
            </div>
          );
        })}
      </div>

      {/* Main content row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Recent Clients table */}
        <div className="glass-card lg:col-span-2" style={{ overflow: 'hidden' }}>
          <div
            style={{
              padding: '16px 20px',
              borderBottom: '1px solid #e8e9f2',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#f8f9fe',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: '#eef0fd', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Users size={15} style={{ color: '#3d5af1' }} />
              </div>
              <span style={{ fontSize: 11, fontWeight: 800, color: '#1a1c3a', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                Recent Clients
              </span>
            </div>
            <span style={{ fontSize: 11, color: '#8b8fa8', fontWeight: 600 }}>{clients.length} total</span>
          </div>

          <div>
            {recentClients.length > 0 ? recentClients.map((c) => (
              <div
                key={c.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '14px 20px',
                  borderBottom: '1px solid #f5f6fb',
                  transition: 'background 0.12s',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 10,
                      background: '#eef0fd',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 14,
                      fontWeight: 800,
                      color: '#3d5af1',
                      flexShrink: 0,
                    }}
                  >
                    {(c.full_name ?? 'U').charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1c3a' }}>
                      {c.full_name ?? 'Unknown'}
                    </div>
                    <div style={{ fontSize: 10, color: '#8b8fa8', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginTop: 2 }}>
                      {c.subscription_plan} plan · joined {new Date(c.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 12, fontWeight: 800, color: '#1a1c3a' }}>{c.readiness_score}%</div>
                    <div style={{ width: 72, height: 4, background: '#eaebf6', borderRadius: 4, marginTop: 4, overflow: 'hidden' }}>
                      <div
                        style={{
                          height: '100%',
                          borderRadius: 4,
                          background: c.readiness_score >= 80 ? '#22c55e' : c.readiness_score >= 50 ? '#3d5af1' : '#f59e0b',
                          width: `${c.readiness_score}%`,
                        }}
                      />
                    </div>
                  </div>
                  <button
                    style={{
                      background: '#eef0fd',
                      color: '#3d5af1',
                      border: 'none',
                      borderRadius: 8,
                      padding: '5px 12px',
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: '0.1em',
                      textTransform: 'uppercase',
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                      transition: 'background 0.12s',
                    }}
                  >
                    View
                  </button>
                </div>
              </div>
            )) : (
              <div style={{ padding: '32px 20px', textAlign: 'center' }}>
                <span style={{ fontSize: 11, color: '#8b8fa8', fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                  No clients yet
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* AI Workforce card */}
          <div className="glass-card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: '#f5f3ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Cpu size={15} style={{ color: '#7c3aed' }} />
              </div>
              <span style={{ fontSize: 11, fontWeight: 800, color: '#1a1c3a', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                AI Workforce
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {bots.slice(0, 4).map(bot => (
                <div key={bot.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span
                      style={{
                        width: 7,
                        height: 7,
                        borderRadius: '50%',
                        background: bot.status === 'active' ? '#22c55e' : bot.status === 'idle' ? '#f59e0b' : '#e8e9f2',
                        display: 'inline-block',
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1c3a' }}>{bot.name}</span>
                  </div>
                  <span
                    style={{
                      fontSize: 9,
                      fontWeight: 800,
                      textTransform: 'uppercase',
                      letterSpacing: '0.1em',
                      padding: '2px 8px',
                      borderRadius: 20,
                      background: bot.status === 'active' ? '#f0fdf4' : bot.status === 'idle' ? '#fff7ed' : '#f5f6fb',
                      color: bot.status === 'active' ? '#22c55e' : bot.status === 'idle' ? '#f59e0b' : '#8b8fa8',
                    }}
                  >
                    {bot.status}
                  </span>
                </div>
              ))}
              {bots.length === 0 && (
                <span style={{ fontSize: 11, color: '#8b8fa8' }}>No bots configured</span>
              )}
            </div>
          </div>

          {/* Recent Applications card */}
          <div className="glass-card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <DollarSign size={15} style={{ color: '#22c55e' }} />
              </div>
              <span style={{ fontSize: 11, fontWeight: 800, color: '#1a1c3a', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                Applications
              </span>
            </div>
            {recentApps.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {recentApps.map(app => (
                  <div key={app.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a' }}>
                        {app.lender_name ?? 'Unknown'}
                      </div>
                      <div style={{ fontSize: 11, color: '#8b8fa8', fontWeight: 600, marginTop: 2 }}>
                        ${(app.requested_amount ?? 0).toLocaleString()}
                      </div>
                    </div>
                    <span
                      style={{
                        fontSize: 9,
                        fontWeight: 800,
                        textTransform: 'uppercase',
                        letterSpacing: '0.1em',
                        padding: '2px 8px',
                        borderRadius: 20,
                        background: app.status === 'approved' ? '#f0fdf4' : app.status === 'pending' ? '#eef0fd' : '#fff7ed',
                        color: app.status === 'approved' ? '#22c55e' : app.status === 'pending' ? '#3d5af1' : '#f59e0b',
                      }}
                    >
                      {app.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <span style={{ fontSize: 11, color: '#8b8fa8' }}>No applications yet</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
