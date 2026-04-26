import React, { useState } from 'react';
import { AuthProvider, useAuth } from './components/AuthProvider';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Dashboard } from './components/Dashboard';
import { Messages } from './components/Messages';
import { Documents } from './components/Documents';
import { Funding } from './components/Funding';
import { TradingLab } from './components/TradingLab';
import { GrantsFinder } from './components/GrantsFinder';
import { Referral } from './components/Referral';
import { Settings } from './components/Settings';
import { ActionCenter } from './components/ActionCenter';
import { FundingRoadmap } from './components/FundingRoadmap';
import { Account } from './components/Account';
import { CreditAnalysis } from './components/CreditAnalysis';
import { BusinessSetup } from './components/BusinessSetup';
import { Auth } from './components/Auth';
import { Bots } from './components/Bots';
import { Pricing } from './components/Pricing';
import { Legal } from './components/Legal';
import { Rewards } from './components/Rewards';
import { AdminPortal } from './components/admin/AdminPortal';
import { Landing } from './components/Landing';
import { Home, Zap, CreditCard, User, FileText, Lock } from 'lucide-react';

function LockedPage({ title, requiredScore, onAction }: { title: string; requiredScore: number; onAction: () => void }) {
  return (
    <div className="h-full flex items-center justify-center p-6">
      <div className="max-w-md w-full glass-card p-10 text-center space-y-8">
        <div className="w-20 h-20 bg-nexus-50 rounded-3xl flex items-center justify-center mx-auto" style={{ color: '#8b8fa8' }}>
          <Lock className="w-10 h-10" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-black" style={{ color: '#1a1c3a' }}>{title} is Locked</h2>
          <p style={{ color: '#8b8fa8', fontWeight: 500 }}>
            Reach a <span style={{ color: '#3d5af1', fontWeight: 700 }}>{requiredScore}% Readiness Score</span> to unlock this feature.
          </p>
        </div>

        <div className="space-y-4">
          <div className="w-full h-3 rounded-full overflow-hidden" style={{ background: '#eaebf6' }}>
            <div className="w-[65%] h-full rounded-full" style={{ background: 'linear-gradient(135deg, #3d5af1, #5b8ef5)' }} />
          </div>
          <div className="flex justify-between text-[10px] font-black uppercase tracking-widest" style={{ color: '#8b8fa8' }}>
            <span>Current: 65%</span>
            <span>Target: {requiredScore}%</span>
          </div>
        </div>

        <div className="pt-4 space-y-3">
          <p className="text-xs font-bold uppercase tracking-widest" style={{ color: '#8b8fa8' }}>How to unlock faster:</p>
          <div className="flex items-center gap-3 p-4 rounded-2xl text-left" style={{ background: '#eef0fd', border: '1px solid #c7d2fe' }}>
            <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center shadow-sm" style={{ color: '#3d5af1' }}>
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <p className="text-[10px] font-black" style={{ color: '#1a1c3a' }}>Complete Primary Task</p>
              <p className="text-[8px] font-bold uppercase tracking-widest" style={{ color: '#8b8fa8' }}>+8% Readiness Boost</p>
            </div>
          </div>
        </div>

        <button
          onClick={onAction}
          className="nexus-button-primary w-full py-4"
          style={{ borderRadius: 16 }}
        >
          Go to Action Center
        </button>
      </div>
    </div>
  );
}

const ADMIN_EMAIL = import.meta.env.VITE_ADMIN_EMAIL as string | undefined;

function AppContent() {
  const { user, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('home');
  const [publicView, setPublicView] = useState<'landing' | 'pricing' | 'auth' | 'legal'>('landing');
  const [portal, setPortal] = useState<'client' | 'admin'>('client');
  const isAdmin = !!ADMIN_EMAIL && user?.email === ADMIN_EMAIL;

  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center" style={{ background: '#eaebf6' }}>
        <div className="w-12 h-12 border-4 border-t-[#3d5af1] rounded-full animate-spin" style={{ borderColor: '#c7d2fe', borderTopColor: '#3d5af1' }} />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen" style={{ background: '#eaebf6' }}>
        {publicView === 'landing' && (
          <Landing
            onGetStarted={() => setPublicView('auth')}
            onViewPricing={() => setPublicView('pricing')}
            onShowLegal={() => setPublicView('legal')}
          />
        )}
        {publicView === 'pricing' && (
          <Pricing
            onSelectPlan={() => setPublicView('auth')}
            onShowLegal={() => setPublicView('legal')}
          />
        )}
        {publicView === 'auth' && (
          <div className="relative">
            <button
              onClick={() => setPublicView('pricing')}
              className="absolute top-8 left-8 z-50 text-[10px] font-black uppercase tracking-widest transition-colors"
              style={{ color: '#8b8fa8' }}
            >
              ← Back to Pricing
            </button>
            <Auth onShowLegal={() => setPublicView('legal')} />
          </div>
        )}
        {publicView === 'legal' && <Legal onBack={() => setPublicView('pricing')} />}
      </div>
    );
  }

  // Admin Portal View
  if (portal === 'admin') {
    return (
      <>
        <AdminPortal />
        <button
          onClick={() => setPortal('client')}
          className="fixed bottom-4 right-4 z-[100] bg-white px-4 py-2 rounded-full shadow-2xl text-[10px] font-black uppercase tracking-widest flex items-center gap-2 transition-all hover:bg-nexus-50"
          style={{ color: '#1a1c3a', border: '1px solid #e8e9f2' }}
        >
          <Zap className="w-3 h-3" style={{ color: '#3d5af1' }} />
          Switch to Client Portal
        </button>
      </>
    );
  }

  const mobileNavItems = [
    { id: 'home',          label: 'Home',     icon: Home },
    { id: 'action-center', label: 'Actions',  icon: Zap },
    { id: 'funding',       label: 'Funding',  icon: CreditCard },
    { id: 'documents',     label: 'Docs',     icon: FileText },
    { id: 'account',       label: 'Account',  icon: User },
  ];

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#eaebf6' }}>
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main content — ml-0 on mobile, ml-52 on md+ to clear sidebar */}
      <main className="flex-1 h-screen flex flex-col overflow-hidden md:ml-[208px]">
        <Header onNavigate={setActiveTab} />

        <div className="flex-1 overflow-y-auto scrollbar-hide pb-16 md:pb-0" style={{ padding: 24 }}>
          {activeTab === 'home'           && <Dashboard />}
          {activeTab === 'action-center'  && <ActionCenter />}
          {activeTab === 'business-setup' && <BusinessSetup />}
          {activeTab === 'messages'       && <Messages />}
          {activeTab === 'documents'      && <Documents />}
          {activeTab === 'funding'        && <Funding />}
          {activeTab === 'roadmap'        && <FundingRoadmap />}
          {activeTab === 'grants'         && <GrantsFinder />}
          {activeTab === 'trading'        && <TradingLab />}
          {activeTab === 'referral'       && <Referral />}
          {activeTab === 'account'        && <Account />}
          {activeTab === 'settings'       && <Settings />}
          {activeTab === 'credit'         && <CreditAnalysis />}
          {activeTab === 'auth'           && <Auth onBackToDashboard={() => setActiveTab('home')} />}
          {activeTab === 'bots'           && <Bots onInteract={() => setActiveTab('messages')} />}
          {activeTab === 'rewards'        && <Rewards />}
        </div>

        <footer
          className="hidden md:block p-3 text-center text-[8px] font-bold uppercase tracking-widest shrink-0"
          style={{ color: '#8b8fa8', borderTop: '1px solid #e8e9f2', background: '#fff' }}
        >
          © 2026 Nexus. All rights reserved.
        </footer>
      </main>

      {/* Mobile bottom navigation — hidden on md+ */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 flex md:hidden"
        style={{ background: '#fff', borderTop: '1px solid #e8e9f2' }}
      >
        {mobileNavItems.map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className="flex-1 flex flex-col items-center justify-center py-2 gap-0.5"
              style={{ color: isActive ? '#3d5af1' : '#8b8fa8', background: 'none', border: 'none' }}
            >
              <Icon size={20} />
              <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
            </button>
          );
        })}
      </nav>

      {/* Admin switcher — only visible to admin account, desktop only */}
      {isAdmin && (
        <button
          onClick={() => setPortal('admin')}
          className="fixed bottom-20 right-4 md:bottom-4 z-[100] px-4 py-2 rounded-full shadow-2xl text-[10px] font-black uppercase tracking-widest flex items-center gap-2 transition-all"
          style={{ background: '#1a1c3a', color: '#fff', border: '1px solid #2d3748' }}
        >
          <Zap className="w-3 h-3" style={{ color: '#818cf8' }} />
          Admin
        </button>
      )}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
