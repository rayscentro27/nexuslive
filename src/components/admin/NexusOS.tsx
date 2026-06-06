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
  DollarSign, Video, TrendingUp, BookOpen, ChevronRight, Brain, Network, LayoutDashboard,
} from 'lucide-react';
import { NexusOverview } from '../nexus-os/NexusOverview';
import { ThemeToggle } from '../nexus-os/ThemeToggle';
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
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, description: 'Premium dashboard' },
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
  const [activeSection, setActiveSection] = useState<OsSection>('overview');

  function renderSection() {
    switch (activeSection) {
      case 'overview':       return <NexusOverview onNavigate={setActiveSection} />;
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
    <div className="flex h-full min-h-[600px] nexus-canvas">
      {/* Sidebar nav — hidden on small screens */}
      <aside className="hidden md:flex flex-col w-52 shrink-0 py-4 gap-0.5" style={{ background: 'var(--nexus-bg-soft)', borderRight: '1px solid var(--nexus-border)' }}>
        <div className="px-4 pb-3 mb-1" style={{ borderBottom: '1px solid var(--nexus-border)' }}>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center nexus-accent-grad">
              <Home className="w-3.5 h-3.5 text-white" />
            </div>
            <div>
              <p className="text-[11px] font-black leading-none nexus-ink">NEXUS OS</p>
              <p className="text-[9px] nexus-muted mt-0.5">Unified Control Layer</p>
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
              className="mx-2 flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left transition-all"
              style={isActive
                ? { backgroundImage: 'linear-gradient(135deg, var(--nexus-purple), var(--nexus-blue))', color: '#fff' }
                : { color: 'var(--nexus-text-muted)' }}
            >
              <Icon className="w-4 h-4 shrink-0" style={{ color: isActive ? '#fff' : 'var(--nexus-text-muted)' }} />
              <div className="flex-1 min-w-0">
                <p className="text-[11px] font-bold truncate" style={{ color: isActive ? '#fff' : 'var(--nexus-text)' }}>{item.label}</p>
              </div>
              {isActive && <ChevronRight className="w-3 h-3 shrink-0" style={{ color: 'rgba(255,255,255,0.7)' }} />}
            </button>
          );
        })}
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile top nav */}
        <div className="md:hidden flex overflow-x-auto gap-1.5 px-4 py-2 scrollbar-hide" style={{ background: 'var(--nexus-bg-soft)', borderBottom: '1px solid var(--nexus-border)' }}>
          {NAV.map(item => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-bold whitespace-nowrap transition-all"
                style={isActive
                  ? { backgroundImage: 'linear-gradient(135deg, var(--nexus-purple), var(--nexus-blue))', color: '#fff' }
                  : { background: 'var(--nexus-surface-strong)', color: 'var(--nexus-text-muted)', border: '1px solid var(--nexus-border)' }}
              >
                <Icon className="w-3 h-3" />
                {item.label}
              </button>
            );
          })}
        </div>

        {/* Breadcrumb + theme toggle */}
        <div className="px-6 py-3 flex items-center gap-2" style={{ background: 'var(--nexus-bg-soft)', borderBottom: '1px solid var(--nexus-border)' }}>
          <p className="text-[10px] font-black uppercase tracking-widest nexus-muted">Nexus OS</p>
          <ChevronRight className="w-3 h-3 nexus-muted" />
          <p className="text-[10px] font-black uppercase tracking-widest nexus-ink">{active.label}</p>
          <span className="text-[10px] nexus-muted ml-1 hidden sm:inline">— {active.description}</span>
          <div className="ml-auto"><ThemeToggle /></div>
        </div>

        {/* Section content — centered, max-width 1280px so widgets never stretch edge-to-edge */}
        <div className="flex-1 overflow-y-auto">
          <div className="w-full max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 pt-6 sm:pt-8 pb-24">
            {renderSection()}
          </div>
        </div>
      </div>
    </div>
  );
}
