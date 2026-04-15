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

export function AdminPortal() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <AdminSidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="flex-1 ml-64 h-screen flex flex-col overflow-hidden">
        <AdminHeader />
        
        <div className="flex-1 overflow-y-auto no-scrollbar">
          {activeTab === 'dashboard' && <AdminDashboard />}
          {activeTab === 'clients' && <AdminClients />}
          {activeTab === 'pipeline' && <AdminFunding />}
          {activeTab === 'credit' && <AdminCreditOps />}
          {activeTab === 'funding' && <AdminFunding />}
          {activeTab === 'opportunities' && <AdminBusinessOpportunities />}
          {activeTab === 'documents' && <AdminDocuments />}
          {activeTab === 'ai-workforce' && <AdminAIWorkforce />}
          {activeTab === 'trading' && <AdminTrading />}
          {activeTab === 'my-business' && <AdminMyBusiness />}
          {activeTab === 'reports' && <AdminReports />}
          {activeTab === 'settings' && <AdminSettings />}
        </div>

        <footer className="p-4 text-center text-[9px] text-slate-400 font-black uppercase tracking-[0.3em] border-t border-slate-200 shrink-0 bg-white">
          NEXUS ADMIN OS v2.0.4 // SECURE CONNECTION ACTIVE
        </footer>
      </main>
    </div>
  );
}
