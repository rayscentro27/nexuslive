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
import { Lock, Zap } from 'lucide-react';

function LockedPage({ title, requiredScore, onAction }: { title: string, requiredScore: number, onAction: () => void }) {
  return (
    <div className="h-full flex items-center justify-center p-6">
      <div className="max-w-md w-full glass-card p-10 text-center space-y-8">
        <div className="w-20 h-20 bg-slate-100 rounded-3xl flex items-center justify-center mx-auto text-slate-400">
          <Lock className="w-10 h-10" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-black text-[#1A2244]">{title} is Locked</h2>
          <p className="text-slate-500 font-medium">
            Reach a <span className="text-[#5B7CFA] font-bold">{requiredScore}% Readiness Score</span> to unlock this feature.
          </p>
        </div>
        
        <div className="space-y-4">
          <div className="w-full h-3 bg-nexus-100 rounded-full overflow-hidden p-0.5">
            <div className="w-[65%] h-full bg-[#5B7CFA] rounded-full shadow-[0_0_8px_rgba(91,124,250,0.4)]" />
          </div>
          <div className="flex justify-between text-[10px] font-black text-slate-400 uppercase tracking-widest">
            <span>Current: 65%</span>
            <span>Target: {requiredScore}%</span>
          </div>
        </div>

        <div className="pt-4 space-y-3">
          <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">How to unlock faster:</p>
          <div className="flex items-center gap-3 p-4 rounded-2xl bg-blue-50/50 border border-blue-100 text-left">
            <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center text-[#5B7CFA] shadow-sm">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <p className="text-[10px] font-black text-[#1A2244]">Complete Primary Task</p>
              <p className="text-[8px] text-slate-500 font-bold uppercase tracking-widest">+8% Readiness Boost</p>
            </div>
          </div>
        </div>

        <button 
          onClick={onAction}
          className="w-full py-4 bg-[#5B7CFA] text-white font-black rounded-2xl shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all"
        >
          Go to Action Center
        </button>
      </div>
    </div>
  );
}

// Placeholder components for other tabs
const Placeholder = ({ title }: { title: string }) => (
  <div className="p-8 flex flex-col items-center justify-center min-h-[60vh] text-nexus-400">
    <h2 className="text-2xl font-bold mb-2">{title}</h2>
    <p>This module is currently under development.</p>
  </div>
);

function AppContent() {
  const { user, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('home');
  const [publicView, setPublicView] = useState<'pricing' | 'auth' | 'legal'>('pricing');

  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-nexus-50">
        <div className="w-12 h-12 border-4 border-nexus-200 border-t-nexus-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-nexus-50">
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
              className="absolute top-8 left-8 z-50 text-[10px] font-black text-slate-400 uppercase tracking-widest hover:text-[#5B7CFA] transition-colors"
            >
              ← Back to Pricing
            </button>
            <Auth onShowLegal={() => setPublicView('legal')} />
          </div>
        )}
        {publicView === 'legal' && (
          <Legal onBack={() => setPublicView('pricing')} />
        )}
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-nexus-50 overflow-hidden">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="flex-1 ml-64 h-screen flex flex-col overflow-hidden">
        <Header />
        
        <div className="flex-1 overflow-y-auto scrollbar-hide">
          {activeTab === 'home' && <Dashboard />}
          {activeTab === 'action-center' && <ActionCenter />}
          {activeTab === 'business-setup' && <BusinessSetup />}
          {activeTab === 'messages' && <Messages />}
          {activeTab === 'documents' && <Documents />}
          {activeTab === 'funding' && <Funding />}
          {activeTab === 'roadmap' && <FundingRoadmap />}
          {activeTab === 'grants' && <LockedPage title="Grants Finder" requiredScore={70} onAction={() => setActiveTab('action-center')} />}
          {activeTab === 'trading' && <LockedPage title="Trading Lab" requiredScore={85} onAction={() => setActiveTab('action-center')} />}
          {activeTab === 'referral' && <Referral />}
          {activeTab === 'account' && <Account />}
          {activeTab === 'settings' && <Settings />}
          {activeTab === 'credit' && <CreditAnalysis />}
          {activeTab === 'auth' && <Auth onBackToDashboard={() => setActiveTab('home')} />}
          {activeTab === 'bots' && <Bots onInteract={() => setActiveTab('messages')} />}
          {activeTab === 'rewards' && <Rewards />}
        </div>

        <footer className="p-3 text-center text-[8px] text-nexus-400 font-bold uppercase tracking-widest border-t border-nexus-100 shrink-0">
          © 2025 Nexus. All rights reserved.
        </footer>
      </main>
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
