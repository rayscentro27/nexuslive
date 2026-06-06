/**
 * Nexus OS — unified operating layer over the Nexus ecosystem.
 * Integrated into AdminPortal as the 'nexus-os' tab.
 *
 * Sections: Command Center, Hermes Chat, Approvals, Notifications,
 *           Tools, Revenue, Content, Trading, Knowledge
 */
import React, { useState } from 'react';
import {
  Home, MessageSquare, CheckCircle2, Bell, Cpu,
  DollarSign, Video, TrendingUp, BookOpen, ChevronRight, Brain, Network,
} from 'lucide-react';
import { CommandCenter } from '../nexus-os/CommandCenter';
import { HermesChat } from '../nexus-os/HermesChat';
import { HermesTraining } from '../nexus-os/HermesTraining';
import { ApprovalCenter } from '../nexus-os/ApprovalCenter';
import { NotificationCenter } from '../nexus-os/NotificationCenter';
import { ToolRegistry } from '../nexus-os/ToolRegistry';
import { RevenueHub } from '../nexus-os/RevenueHub';
import { ContentStudio } from '../nexus-os/ContentStudio';
import { TradingOps } from '../nexus-os/TradingOps';
import { ArtifactHub } from '../nexus-os/ArtifactHub';
import { KnowledgeGraph } from '../nexus-os/KnowledgeGraph';
import type { OsSection } from '../nexus-os/types';

interface NavItem {
  id: OsSection;
  label: string;
  icon: React.ElementType;
  description: string;
}

const NAV: NavItem[] = [
  { id: 'command-center', label: 'Command Center', icon: Home, description: 'System status overview' },
  { id: 'hermes-chat', label: 'Hermes Chat', icon: MessageSquare, description: 'Talk to Nexus AI' },
  { id: 'hermes-training', label: 'Hermes Training', icon: Brain, description: 'Voice, skills & recommendations' },
  { id: 'approvals', label: 'Approvals', icon: CheckCircle2, description: 'Pending actions inbox' },
  { id: 'notifications', label: 'Notifications', icon: Bell, description: 'System notifications' },
  { id: 'tools', label: 'Tool Registry', icon: Cpu, description: 'Agents & services' },
  { id: 'revenue', label: 'Revenue Hub', icon: DollarSign, description: 'Campaigns & pipeline' },
  { id: 'content', label: 'Content Studio', icon: Video, description: 'Creative pipeline' },
  { id: 'trading', label: 'Trading Ops', icon: TrendingUp, description: 'Paper trading & signals' },
  { id: 'knowledge', label: 'Artifact Hub', icon: BookOpen, description: 'Knowledge & artifacts' },
  { id: 'graph', label: 'Knowledge Graph', icon: Network, description: 'Entities & relationships' },
];

export function NexusOS() {
  const [activeSection, setActiveSection] = useState<OsSection>('command-center');

  function renderSection() {
    switch (activeSection) {
      case 'command-center': return <CommandCenter onNavigate={setActiveSection} />;
      case 'hermes-chat':    return <HermesChat />;
      case 'hermes-training': return <HermesTraining />;
      case 'approvals':      return <ApprovalCenter />;
      case 'notifications':  return <NotificationCenter />;
      case 'tools':          return <ToolRegistry />;
      case 'revenue':        return <RevenueHub />;
      case 'content':        return <ContentStudio />;
      case 'trading':        return <TradingOps />;
      case 'knowledge':      return <ArtifactHub />;
      case 'graph':          return <KnowledgeGraph />;
      default:               return null;
    }
  }

  const active = NAV.find(n => n.id === activeSection)!;

  return (
    <div className="flex h-full min-h-[600px]" style={{ background: '#f4f5fb' }}>
      {/* Sidebar nav — hidden on small screens */}
      <aside className="hidden md:flex flex-col w-52 shrink-0 bg-white border-r border-slate-200 py-4 gap-0.5">
        <div className="px-4 pb-3 border-b border-slate-100 mb-1">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-[#5B7CFA] flex items-center justify-center">
              <Home className="w-3.5 h-3.5 text-white" />
            </div>
            <div>
              <p className="text-[11px] font-black text-[#1A2244] leading-none">NEXUS OS</p>
              <p className="text-[9px] text-slate-400 mt-0.5">Unified Control Layer</p>
            </div>
          </div>
        </div>
        {NAV.map(item => {
          const Icon = item.icon;
          const isActive = activeSection === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={`mx-2 flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left transition-all group ${
                isActive
                  ? 'bg-[#5B7CFA] text-white shadow-sm shadow-blue-500/20'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-[#5B7CFA]'}`} />
              <div className="flex-1 min-w-0">
                <p className={`text-[11px] font-bold truncate ${isActive ? 'text-white' : 'text-[#1A2244]'}`}>
                  {item.label}
                </p>
              </div>
              {isActive && <ChevronRight className="w-3 h-3 text-white/70 shrink-0" />}
            </button>
          );
        })}
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile top nav */}
        <div className="md:hidden flex overflow-x-auto gap-1.5 px-4 py-2 bg-white border-b border-slate-200 scrollbar-hide">
          {NAV.map(item => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-bold whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-[#5B7CFA] text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                <Icon className="w-3 h-3" />
                {item.label}
              </button>
            );
          })}
        </div>

        {/* Breadcrumb */}
        <div className="px-6 py-3 flex items-center gap-2 bg-white border-b border-slate-100">
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Nexus OS</p>
          <ChevronRight className="w-3 h-3 text-slate-300" />
          <p className="text-[10px] font-black text-[#1A2244] uppercase tracking-widest">{active.label}</p>
          <span className="text-[10px] text-slate-400 ml-1">— {active.description}</span>
        </div>

        {/* Section content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 pb-20">
          {renderSection()}
        </div>
      </div>
    </div>
  );
}
