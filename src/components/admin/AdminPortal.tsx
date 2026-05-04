import React, { useState } from 'react';
import { AdminSidebar } from './AdminSidebar';
import { AdminHeader } from './AdminHeader';
import { AdminDashboard } from './AdminDashboard';
import { AdminClients } from './AdminClients';
import { AdminAIWorkforce } from './AdminAIWorkforce';
import { AdminTrading } from './AdminTrading';
import { AdminFunding } from './AdminFunding';
import { AdminCreditOps } from './AdminCreditOps';
import { AdminBusinessOpportunities } from './AdminBusinessOpportunities';
import { AdminDocuments } from './AdminDocuments';
import { AdminMyBusiness } from './AdminMyBusiness';
import { AdminReports } from './AdminReports';
import { AdminSettings } from './AdminSettings';
import { AdminMessaging } from './AdminMessaging';
import { AdminSubscriptionSettings } from './AdminSubscriptionSettings';
import { AdminInviteUsers } from './AdminInviteUsers';
import { AdminGrantReviews } from './AdminGrantReviews';
import { AdminCEOMode } from './AdminCEOMode';

const ADMIN_DOCK = [
  { id: 'dashboard',     emoji: '🏠', label: 'Overview' },
  { id: 'clients',       emoji: '👥', label: 'Clients' },
  { id: 'invites',       emoji: '✉️', label: 'Invites' },
  { id: 'funding',       emoji: '💰', label: 'Funding' },
  { id: 'pipeline',      emoji: '📊', label: 'Pipeline' },
  { id: 'credit',        emoji: '🛡️', label: 'Credit' },
  { id: 'opportunities', emoji: '💡', label: 'Opps' },
  { id: 'documents',     emoji: '📄', label: 'Docs' },
  { id: 'messages',      emoji: '💬', label: 'Messages' },
  { id: 'ai-workforce',  emoji: '🤖', label: 'AI Team' },
  { id: 'trading',       emoji: '📈', label: 'Trading' },
  { id: 'my-business',   emoji: '🏢', label: 'Business' },
  { id: 'reports',       emoji: '📋', label: 'Reports' },
  { id: 'subscriptions', emoji: '💳', label: 'Plans' },
  { id: 'grants-review', emoji: '🔬', label: 'Grants' },
  { id: 'ceo-mode',      emoji: '🧠', label: 'CEO Mode' },
  { id: 'settings',      emoji: '⚙️', label: 'Settings' },
];

function AdminDockButton({ item, isActive, onClick }: {
  item: { emoji: string; label: string };
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
        cursor: 'pointer', minWidth: 52, background: 'none', border: 'none', padding: '2px 0',
      }}
    >
      <div style={{
        width: 52, height: 52, borderRadius: 15, fontSize: 24,
        background: isActive ? 'rgba(129,140,248,0.9)' : 'rgba(255,255,255,0.12)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        border: isActive ? '2px solid rgba(255,255,255,0.9)' : '1.5px solid rgba(255,255,255,0.2)',
        boxShadow: isActive ? '0 0 0 4px rgba(129,140,248,0.25), 0 6px 18px rgba(0,0,0,0.3)' : '0 2px 8px rgba(0,0,0,0.2)',
        transition: 'all 0.15s',
      }}>
        {item.emoji}
      </div>
      <span style={{
        fontSize: 10, fontWeight: isActive ? 700 : 500,
        color: isActive ? '#a5b4fc' : 'rgba(255,255,255,0.7)',
        textAlign: 'center', lineHeight: 1.1,
      }}>{item.label}</span>
    </button>
  );
}

function AdminBottomDock({ activeTab, setActiveTab }: {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}) {
  return (
    <div style={{
      position: 'fixed', bottom: 16, left: '50%', transform: 'translateX(-50%)',
      zIndex: 200,
      background: 'rgba(15, 18, 50, 0.92)',
      backdropFilter: 'blur(32px)',
      WebkitBackdropFilter: 'blur(32px)' as any,
      border: '1px solid rgba(255,255,255,0.15)',
      borderRadius: 30, padding: '10px 16px',
      display: 'flex', alignItems: 'center', gap: 4,
      boxShadow: '0 10px 48px rgba(0,0,20,0.5), 0 2px 8px rgba(0,0,0,0.3)',
      overflowX: 'auto',
      maxWidth: 'calc(100vw - 32px)',
    }}>
      {ADMIN_DOCK.map(item => (
        <AdminDockButton
          key={item.id}
          item={item}
          isActive={activeTab === item.id}
          onClick={() => setActiveTab(item.id)}
        />
      ))}
    </div>
  );
}

export function AdminPortal() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#eaebf6' }}>
      <AdminSidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 h-screen flex flex-col overflow-hidden">
        <AdminHeader />

        <div className="flex-1 overflow-y-auto no-scrollbar" style={{ paddingBottom: 100 }}>
          {activeTab === 'dashboard'     && <AdminDashboard onNavigate={setActiveTab} />}
          {activeTab === 'clients'       && <AdminClients />}
          {activeTab === 'invites'       && <AdminInviteUsers />}
          {activeTab === 'pipeline'      && <AdminFunding />}
          {activeTab === 'credit'        && <AdminCreditOps />}
          {activeTab === 'funding'       && <AdminFunding />}
          {activeTab === 'opportunities' && <AdminBusinessOpportunities />}
          {activeTab === 'documents'     && <AdminDocuments />}
          {activeTab === 'messages'      && <AdminMessaging />}
          {activeTab === 'ai-workforce'  && <AdminAIWorkforce />}
          {activeTab === 'trading'       && <AdminTrading />}
          {activeTab === 'my-business'   && <AdminMyBusiness />}
          {activeTab === 'reports'       && <AdminReports />}
          {activeTab === 'subscriptions' && <AdminSubscriptionSettings />}
          {activeTab === 'grants-review' && <AdminGrantReviews />}
          {activeTab === 'ceo-mode'      && <AdminCEOMode />}
          {activeTab === 'settings'      && <AdminSettings onNavigate={setActiveTab} />}
        </div>
      </main>

      <AdminBottomDock activeTab={activeTab} setActiveTab={setActiveTab} />
    </div>
  );
}
