import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
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
import { NexusVirtualOffice } from './NexusVirtualOffice';
import { NexusWorkforceCommand } from './NexusWorkforceCommand';
import { NexusOS } from './NexusOS';
import { Showroom } from '../Showroom';
import { supabase } from '../../lib/supabase';

const ADMIN_DOCK = [
  { id: 'dashboard',         emoji: '🏠', label: 'Overview' },
  { id: 'clients',           emoji: '👥', label: 'Clients' },
  { id: 'funding',           emoji: '💰', label: 'Funding' },
  { id: 'opportunities',     emoji: '💡', label: 'Opps' },
  { id: 'ai-workforce',      emoji: '🤖', label: 'AI Team' },
  { id: 'nexus-os',          emoji: '🖥️', label: 'Nexus OS' },
  { id: 'showroom',          emoji: '🛍️', label: 'Showroom' },
  // overflow items
  { id: 'workforce-command', emoji: '⚡', label: 'Command' },
  { id: 'invites',       emoji: '✉️', label: 'Invites' },
  { id: 'pipeline',      emoji: '📊', label: 'Pipeline' },
  { id: 'credit',        emoji: '🛡️', label: 'Credit' },
  { id: 'documents',     emoji: '📄', label: 'Docs' },
  { id: 'messages',      emoji: '💬', label: 'Messages' },
  { id: 'trading',       emoji: '📈', label: 'Trading' },
  { id: 'my-business',   emoji: '🏢', label: 'Business' },
  { id: 'reports',       emoji: '📋', label: 'Reports' },
  { id: 'subscriptions', emoji: '💳', label: 'Plans' },
  { id: 'grants-review', emoji: '🔬', label: 'Grants' },
  { id: 'ceo-mode',      emoji: '🧠', label: 'CEO Mode' },
  { id: 'virtual-office', emoji: '🏙', label: 'Office' },
  { id: 'settings',      emoji: '⚙️', label: 'Settings' },
];

const DOCK_PRIMARY = ADMIN_DOCK.slice(0, 7);
const DOCK_OVERFLOW = ADMIN_DOCK.slice(7);

function AdminDockButton({
  item, isActive, onClick, badge, badgeColor,
}: {
  item: { emoji: string; label: string; id: string };
  isActive: boolean;
  onClick: () => void;
  badge?: number;
  badgeColor?: string;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
        cursor: 'pointer', minWidth: 52, background: 'none', border: 'none', padding: '2px 0',
        position: 'relative',
      }}
    >
      <div style={{
        width: 52, height: 52, borderRadius: 15, fontSize: 24,
        background: isActive ? 'rgba(129,140,248,0.9)' : 'rgba(255,255,255,0.12)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        border: isActive ? '2px solid rgba(255,255,255,0.9)' : '1.5px solid rgba(255,255,255,0.2)',
        boxShadow: isActive
          ? '0 0 0 4px rgba(129,140,248,0.25), 0 6px 18px rgba(0,0,0,0.3)'
          : '0 2px 8px rgba(0,0,0,0.2)',
        transition: 'all 0.15s',
        position: 'relative',
      }}>
        {item.emoji}
        {badge !== undefined && badge > 0 && (
          <div style={{
            position: 'absolute', top: -4, right: -4,
            minWidth: 18, height: 18, borderRadius: 9,
            background: badgeColor ?? '#ef4444',
            color: '#fff',
            fontSize: 10, fontWeight: 800,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '0 4px',
            border: '2px solid rgba(15,18,50,0.92)',
            boxShadow: `0 0 8px ${badgeColor ?? '#ef4444'}88`,
          }}>
            {badge > 99 ? '99+' : badge}
          </div>
        )}
      </div>
      <span style={{
        fontSize: 10, fontWeight: isActive ? 700 : 500,
        color: isActive ? '#a5b4fc' : 'rgba(255,255,255,0.7)',
        textAlign: 'center', lineHeight: 1.1,
      }}>{item.label}</span>
    </button>
  );
}

function AdminBottomDock({
  activeTab, setActiveTab, pendingApprovals,
}: {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingApprovals: number;
}) {
  const [showOverflow, setShowOverflow] = useState(false);

  return (
    <>
      {/* Overflow menu */}
      {showOverflow && (
        <>
          <div
            style={{ position: 'fixed', inset: 0, zIndex: 195 }}
            onClick={() => setShowOverflow(false)}
          />
          <div style={{
            position: 'fixed', bottom: 110, left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 210,
            background: 'rgba(15, 18, 50, 0.96)',
            backdropFilter: 'blur(32px)',
            WebkitBackdropFilter: 'blur(32px)' as React.CSSProperties['backdropFilter'],
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: 24, padding: '10px 12px',
            display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap',
            maxWidth: 'calc(100vw - 32px)',
            boxShadow: '0 10px 48px rgba(0,0,20,0.6)',
            justifyContent: 'center',
          }}>
            {DOCK_OVERFLOW.map(item => (
              <AdminDockButton
                key={item.id}
                item={item}
                isActive={activeTab === item.id}
                onClick={() => { setActiveTab(item.id); setShowOverflow(false); }}
              />
            ))}
          </div>
        </>
      )}

      {/* Primary dock */}
      <div style={{
        position: 'fixed', bottom: 16, left: '50%', transform: 'translateX(-50%)',
        zIndex: 200,
        background: 'rgba(15, 18, 50, 0.92)',
        backdropFilter: 'blur(32px)',
        WebkitBackdropFilter: 'blur(32px)' as React.CSSProperties['backdropFilter'],
        border: '1px solid rgba(255,255,255,0.15)',
        borderRadius: 30, padding: '10px 16px',
        display: 'flex', alignItems: 'center', gap: 4,
        boxShadow: '0 10px 48px rgba(0,0,20,0.5), 0 2px 8px rgba(0,0,0,0.3)',
      }}>
        {DOCK_PRIMARY.map(item => (
          <AdminDockButton
            key={item.id}
            item={item}
            isActive={activeTab === item.id}
            onClick={() => setActiveTab(item.id)}
            badge={item.id === 'workforce-command' ? pendingApprovals : undefined}
            badgeColor="#ef4444"
          />
        ))}

        {/* More button */}
        <AdminDockButton
          item={{ id: 'more', emoji: '⋯', label: 'More' }}
          isActive={showOverflow || DOCK_OVERFLOW.some(d => d.id === activeTab)}
          onClick={() => setShowOverflow(v => !v)}
        />
      </div>
    </>
  );
}

export function AdminPortal() {
  const location = useLocation();
  const navigate = useNavigate();
  const pathTab = location.pathname.replace(/^\/admin\/?/, '').split('/')[0] || 'dashboard';
  const initialTab = ADMIN_DOCK.some(item => item.id === pathTab) ? pathTab : 'dashboard';
  const [activeTab, setActiveTabState] = useState(initialTab);
  const [pendingApprovals, setPendingApprovals] = useState(0);

  useEffect(() => {
    const nextTab = ADMIN_DOCK.some(item => item.id === pathTab) ? pathTab : 'dashboard';
    setActiveTabState(nextTab);
  }, [pathTab]);

  const setActiveTab = (tab: string) => {
    setActiveTabState(tab);
    navigate(tab === 'dashboard' ? '/admin' : `/admin/${tab}`);
  };

  // Poll approval count every 30s for red badge
  useEffect(() => {
    const fetchApprovals = async () => {
      try {
        const { count } = await supabase
          .from('human_approval_requests')
          .select('*', { count: 'exact', head: true })
          .eq('status', 'pending');
        setPendingApprovals(count ?? 0);
      } catch { /* silent */ }
    };
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 30_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#eaebf6' }}>
      <AdminSidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 h-screen flex flex-col overflow-hidden">
        <AdminHeader />

        <div className="flex-1 overflow-y-auto no-scrollbar" style={{ paddingBottom: 100 }}>
          {activeTab === 'dashboard'         && <AdminDashboard onNavigate={setActiveTab} />}
          {activeTab === 'clients'           && <AdminClients />}
          {activeTab === 'invites'           && <AdminInviteUsers />}
          {activeTab === 'pipeline'          && <AdminFunding />}
          {activeTab === 'credit'            && <AdminCreditOps />}
          {activeTab === 'funding'           && <AdminFunding />}
          {activeTab === 'opportunities'     && <AdminBusinessOpportunities />}
          {activeTab === 'documents'         && <AdminDocuments />}
          {activeTab === 'messages'          && <AdminMessaging />}
          {activeTab === 'ai-workforce'      && <AdminAIWorkforce />}
          {activeTab === 'nexus-os'          && <NexusOS />}
          {activeTab === 'trading'           && <AdminTrading />}
          {activeTab === 'my-business'       && <AdminMyBusiness />}
          {activeTab === 'reports'           && <AdminReports />}
          {activeTab === 'showroom'          && <Showroom />}
          {activeTab === 'subscriptions'     && <AdminSubscriptionSettings />}
          {activeTab === 'grants-review'     && <AdminGrantReviews />}
          {activeTab === 'ceo-mode'          && <AdminCEOMode />}
          {activeTab === 'virtual-office'    && <NexusVirtualOffice />}
          {activeTab === 'workforce-command' && <NexusWorkforceCommand />}
          {activeTab === 'settings'          && <AdminSettings onNavigate={setActiveTab} />}
        </div>
      </main>

      {activeTab !== 'nexus-os' && (
        <AdminBottomDock
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          pendingApprovals={pendingApprovals}
        />
      )}
    </div>
  );
}
