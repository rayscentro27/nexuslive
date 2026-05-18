/**
 * NexusVirtualOffice — 2D animated AI workforce visualization.
 * Movement and state driven by real Supabase operational data.
 * Demo mode active when no real data is present.
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence, LayoutGroup } from 'motion/react';
import { supabase } from '../../lib/supabase';
import { Shield, RefreshCw, AlertTriangle, Wifi, WifiOff, Coffee, ChevronDown, ChevronUp } from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────

type EmployeeId = 'hermes' | 'sage' | 'rex' | 'vera' | 'aria' | 'nova' | 'mira' | 'orion';
type RoomId = 'command' | 'trading' | 'funding' | 'credit' | 'grants' | 'opportunities' | 'marketing' | 'system' | 'research' | 'break';
type EmployeeStatus = 'idle' | 'researching' | 'analyzing' | 'reviewing' | 'blocked' | 'learning' | 'coordinating' | 'monitoring' | 'writing';

interface EmployeeState {
  status: EmployeeStatus;
  task: string;
  urgency: 'low' | 'medium' | 'high' | 'critical';
}

interface ProviderHealth {
  provider_name: string;
  status: string;
  avg_latency_ms: number | null;
}

interface ResearchTicket {
  id: string;
  department: string;
  status: string;
  topic: string;
  created_at: string;
}

interface VirtualOfficeData {
  providers: ProviderHealth[];
  tickets: ResearchTicket[];
  opportunityCount: number;
  recentFeatures: Set<string>;
  ingestCount: number;
  knowledgeCount: number;
  revenueEventCount: number;
  isDemo: boolean;
}

// ─── Employee + Room Config ───────────────────────────────────────────────────

const EMPLOYEES: Record<EmployeeId, { name: string; emoji: string; role: string; homeRoom: RoomId; color: string }> = {
  hermes: { name: 'Hermes', emoji: '🤖', role: 'Chief Operations', homeRoom: 'command', color: '#3d5af1' },
  sage:   { name: 'Sage',   emoji: '📈', role: 'Trading Analyst',    homeRoom: 'trading',   color: '#22c55e' },
  rex:    { name: 'Rex',    emoji: '💰', role: 'Funding Strategist', homeRoom: 'funding',   color: '#f59e0b' },
  vera:   { name: 'Vera',   emoji: '🛡️', role: 'Credit Coach',       homeRoom: 'credit',    color: '#6366f1' },
  aria:   { name: 'Aria',   emoji: '🏆', role: 'Grant Researcher',   homeRoom: 'grants',    color: '#8b5cf6' },
  nova:   { name: 'Nova',   emoji: '🔭', role: 'Opportunity Analyst', homeRoom: 'opportunities', color: '#0d9488' },
  mira:   { name: 'Mira',   emoji: '🎨', role: 'Marketing Strategist', homeRoom: 'marketing', color: '#ec4899' },
  orion:  { name: 'Orion',  emoji: '📡', role: 'Systems Monitor',    homeRoom: 'system',    color: '#ef4444' },
};

interface RoomConfig {
  name: string; emoji: string; color: string; bg: string; border: string;
  gridArea: string; description: string;
}

const ROOMS: Record<RoomId, RoomConfig> = {
  command:       { name: 'Hermes Command',     emoji: '🎯', color: '#3d5af1', bg: '#eef0fd', border: '#c7d2fe', gridArea: 'command',   description: 'Central coordination hub' },
  trading:       { name: 'Trading Desk',        emoji: '📊', color: '#22c55e', bg: '#f0fdf4', border: '#bbf7d0', gridArea: 'trading',   description: 'Demo / paper trading only' },
  funding:       { name: 'Funding Strategy',    emoji: '💰', color: '#f59e0b', bg: '#fffbeb', border: '#fde68a', gridArea: 'funding',   description: 'Funding readiness & strategy' },
  credit:        { name: 'Credit Intelligence', emoji: '🛡️', color: '#6366f1', bg: '#eef2ff', border: '#c7d2fe', gridArea: 'credit',    description: 'Credit analysis & coaching' },
  grants:        { name: 'Grants Research',     emoji: '🏆', color: '#8b5cf6', bg: '#f5f3ff', border: '#ddd6fe', gridArea: 'grants',    description: 'Grant discovery & eligibility' },
  opportunities: { name: 'Opportunity Lab',     emoji: '💡', color: '#0d9488', bg: '#f0fdfa', border: '#99f6e4', gridArea: 'opps',      description: 'Business opportunity scoring' },
  marketing:     { name: 'Marketing Studio',    emoji: '🎨', color: '#ec4899', bg: '#fdf2f8', border: '#fbcfe8', gridArea: 'marketing', description: 'Content & campaign strategy' },
  system:        { name: 'System Monitor',      emoji: '📡', color: '#ef4444', bg: '#fef2f2', border: '#fecaca', gridArea: 'system',    description: 'Infrastructure & AI health' },
  research:      { name: 'Research Library',    emoji: '📚', color: '#78716c', bg: '#fafaf9', border: '#e7e5e4', gridArea: 'library',   description: 'Knowledge ingestion & learning' },
  break:         { name: 'Break Area',          emoji: '☕', color: '#9ca3af', bg: '#f9fafb', border: '#e5e7eb', gridArea: 'break',     description: 'Standby / idle' },
};

const STATUS_COLORS: Record<EmployeeStatus, string> = {
  idle:        '#9ca3af',
  researching: '#7c3aed',
  analyzing:   '#0d9488',
  reviewing:   '#f59e0b',
  blocked:     '#ef4444',
  learning:    '#6366f1',
  coordinating:'#3d5af1',
  monitoring:  '#ef4444',
  writing:     '#ec4899',
};

const STATUS_ICONS: Record<EmployeeStatus, string> = {
  idle:         '💤',
  researching:  '🔬',
  analyzing:    '📊',
  reviewing:    '👁️',
  blocked:      '🚫',
  learning:     '📖',
  coordinating: '🔗',
  monitoring:   '📡',
  writing:      '✍️',
};

// ─── Demo Data ────────────────────────────────────────────────────────────────

function buildDemoData(): VirtualOfficeData {
  return {
    providers: [
      { provider_name: 'openrouter', status: 'online',   avg_latency_ms: 312 },
      { provider_name: 'groq',       status: 'online',   avg_latency_ms: 89  },
      { provider_name: 'ollama',     status: 'degraded', avg_latency_ms: null },
    ],
    tickets: [
      { id: 'd1', department: 'grants_research',      status: 'researching', topic: 'SBIR Phase I eligibility for tech startups', created_at: new Date(Date.now() - 3600000).toISOString() },
      { id: 'd2', department: 'trading_intelligence', status: 'queued',      topic: 'RSI divergence strategy back-test', created_at: new Date(Date.now() - 7200000).toISOString() },
      { id: 'd3', department: 'funding_intelligence', status: 'submitted',   topic: 'SBA 7(a) approval factor analysis', created_at: new Date(Date.now() - 1800000).toISOString() },
    ],
    opportunityCount: 7,
    recentFeatures: new Set(['grants', 'funding', 'trading']),
    ingestCount: 3,
    knowledgeCount: 12,
    revenueEventCount: 0,
    isDemo: true,
  };
}

// ─── State Mapping ────────────────────────────────────────────────────────────

function deptTickets(tickets: ResearchTicket[], dept: string, status?: string) {
  return tickets.filter(t => t.department === dept && (status ? t.status === status : true));
}

function computeRooms(data: VirtualOfficeData): Record<EmployeeId, RoomId> {
  const { providers, tickets, opportunityCount, recentFeatures } = data;

  const criticalProviders = providers.filter(p => p.status !== 'online').length;
  const grantResearching  = deptTickets(tickets, 'grants_research', 'researching').length;
  const grantActive       = deptTickets(tickets, 'grants_research').length;
  const tradingActive     = deptTickets(tickets, 'trading_intelligence').length > 0 || recentFeatures.has('trading');
  const fundingActive     = deptTickets(tickets, 'funding_intelligence').length > 0 || recentFeatures.has('funding');
  const creditActive      = deptTickets(tickets, 'credit_research').length > 0 || recentFeatures.has('credit');
  const mktActive         = recentFeatures.has('marketing') || recentFeatures.has('content');

  // Hermes: stays in command, moves to busiest dept when ≥3 active tickets there
  const deptActivity: Array<[RoomId, number]> = [
    ['trading',       deptTickets(tickets, 'trading_intelligence').length],
    ['grants',        grantActive],
    ['funding',       deptTickets(tickets, 'funding_intelligence').length],
    ['credit',        deptTickets(tickets, 'credit_research').length],
    ['opportunities', opportunityCount > 5 ? 2 : 0],
  ];
  const [topRoom, topCount] = deptActivity.sort((a, b) => b[1] - a[1])[0];
  const hermes: RoomId = topCount >= 3 ? topRoom : 'command';

  return {
    hermes,
    sage:  tradingActive ? 'trading'      : 'break',
    rex:   fundingActive ? 'funding'      : 'break',
    vera:  creditActive  ? 'credit'       : 'break',
    aria:  grantResearching > 0 ? 'research' : grantActive > 0 ? 'grants' : 'break',
    nova:  opportunityCount > 0 ? 'opportunities' : 'research',
    mira:  mktActive     ? 'marketing'   : 'break',
    orion: criticalProviders >= 2 ? 'command' : 'system',
  };
}

function computeStatuses(data: VirtualOfficeData, rooms: Record<EmployeeId, RoomId>): Record<EmployeeId, EmployeeState> {
  const { providers, tickets, opportunityCount, recentFeatures, ingestCount } = data;

  const hermesProvider = providers.find(p => ['claude_cli', 'ollama', 'openrouter'].includes(p.provider_name));
  const onlineCount = providers.filter(p => p.status === 'online').length;
  const offlineCount = providers.filter(p => p.status !== 'online').length;

  const grantTasks = deptTickets(tickets, 'grants_research');
  const tradingTasks = deptTickets(tickets, 'trading_intelligence');
  const fundingTasks = deptTickets(tickets, 'funding_intelligence');
  const creditTasks = deptTickets(tickets, 'credit_research');

  return {
    hermes: {
      status: hermesProvider?.status === 'online' ? 'coordinating' : rooms.hermes !== 'command' ? 'coordinating' : 'idle',
      task: rooms.hermes !== 'command'
        ? `Coordinating with ${ROOMS[rooms.hermes].name}`
        : `Monitoring ${onlineCount} providers · ${tickets.length} active tasks`,
      urgency: offlineCount >= 2 ? 'critical' : tickets.length > 3 ? 'high' : 'low',
    },
    sage: {
      status: tradingTasks.some(t => t.status === 'researching') ? 'analyzing' : tradingTasks.length > 0 ? 'researching' : 'idle',
      task: tradingTasks.length > 0 ? tradingTasks[0].topic.slice(0, 48) : 'No active trades — paper mode',
      urgency: 'low',
    },
    rex: {
      status: fundingTasks.some(t => t.status === 'researching') ? 'researching' : fundingTasks.length > 0 ? 'reviewing' : 'idle',
      task: fundingTasks.length > 0 ? `${fundingTasks.length} funding task${fundingTasks.length > 1 ? 's' : ''} in queue` : 'Standby — funding readiness monitoring',
      urgency: fundingTasks.length > 2 ? 'medium' : 'low',
    },
    vera: {
      status: recentFeatures.has('credit') ? 'analyzing' : creditTasks.length > 0 ? 'reviewing' : 'idle',
      task: creditTasks.length > 0 ? `${creditTasks.length} credit analysis task${creditTasks.length > 1 ? 's' : ''}` : 'Credit score monitoring standby',
      urgency: 'low',
    },
    aria: {
      status: grantTasks.some(t => t.status === 'researching') ? 'researching' : grantTasks.length > 0 ? 'reviewing' : 'idle',
      task: grantTasks.length > 0 ? grantTasks[0].topic.slice(0, 48) : 'Grant catalog standby',
      urgency: grantTasks.length > 2 ? 'medium' : 'low',
    },
    nova: {
      status: opportunityCount > 0 ? 'analyzing' : 'learning',
      task: opportunityCount > 0 ? `${opportunityCount} opportunities scored in catalog` : 'Scanning for new opportunities',
      urgency: opportunityCount > 10 ? 'medium' : 'low',
    },
    mira: {
      status: recentFeatures.has('marketing') ? 'writing' : 'idle',
      task: recentFeatures.has('marketing') ? 'Crafting content strategy' : 'Content queue standby',
      urgency: 'low',
    },
    orion: {
      status: offlineCount > 0 ? 'monitoring' : providers.length > 0 ? 'monitoring' : 'idle',
      task: offlineCount > 0
        ? `⚠️ ${offlineCount} provider${offlineCount > 1 ? 's' : ''} degraded — investigating`
        : `All ${onlineCount} providers online · ${ingestCount} ingestion items`,
      urgency: offlineCount >= 2 ? 'critical' : offlineCount === 1 ? 'high' : 'low',
    },
  };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function EmployeeAvatar({ id, state, size = 'md', showTask = false }: {
  id: EmployeeId;
  state: EmployeeState;
  size?: 'sm' | 'md';
  showTask?: boolean;
}) {
  const emp = EMPLOYEES[id];
  const statusColor = STATUS_COLORS[state.status];
  const isActive = state.status !== 'idle';
  const dim = size === 'sm' ? 40 : 52;
  const emojiSize = size === 'sm' ? 18 : 22;

  const urgencyGlow: Record<string, string> = {
    critical: '0 0 20px rgba(239,68,68,0.5)',
    high:     '0 0 14px rgba(245,158,11,0.4)',
    medium:   `0 0 12px ${emp.color}33`,
    low:      isActive ? `0 0 8px ${emp.color}22` : 'none',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      {showTask && state.status !== 'idle' && (
        <motion.div
          initial={{ opacity: 0, y: 4, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          style={{
            background: '#1a1c3a', color: '#fff',
            fontSize: 9, fontWeight: 600, padding: '3px 7px',
            borderRadius: 6, maxWidth: 120, textAlign: 'center',
            lineHeight: 1.3, marginBottom: 2,
          }}
        >
          {STATUS_ICONS[state.status]} {state.task.length > 40 ? state.task.slice(0, 40) + '…' : state.task}
        </motion.div>
      )}

      <div style={{ position: 'relative' }}>
        {isActive && (
          <motion.div
            animate={{ scale: [1, 1.5, 1], opacity: [0.4, 0, 0.4] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
            style={{
              position: 'absolute', inset: -5, borderRadius: '50%',
              background: statusColor, opacity: 0.2, pointerEvents: 'none',
            }}
          />
        )}

        <motion.div
          animate={isActive ? { y: [0, -3, 0] } : {}}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            width: dim, height: dim, borderRadius: '50%',
            background: isActive ? `${emp.color}15` : '#f3f4f6',
            border: `2.5px solid ${isActive ? emp.color : '#d1d5db'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: emojiSize,
            boxShadow: urgencyGlow[state.urgency],
          }}
        >
          {emp.emoji}
        </motion.div>

        {/* Status dot */}
        <div style={{
          position: 'absolute', bottom: 1, right: 1,
          width: 10, height: 10, borderRadius: '50%',
          background: statusColor, border: '2px solid #fff',
        }} />

        {/* Urgency badge */}
        {(state.urgency === 'critical' || state.urgency === 'high') && (
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 0.8, repeat: Infinity }}
            style={{
              position: 'absolute', top: -4, right: -4,
              width: 14, height: 14, borderRadius: '50%',
              background: state.urgency === 'critical' ? '#ef4444' : '#f59e0b',
              border: '2px solid #fff', fontSize: 7,
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff',
            }}
          >
            !
          </motion.div>
        )}
      </div>

      <div style={{ textAlign: 'center' }}>
        <p style={{ fontSize: size === 'sm' ? 9 : 10, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>
          {emp.name}
        </p>
        <p style={{ fontSize: 8, color: statusColor, margin: 0, fontWeight: 600 }}>
          {state.status}
        </p>
      </div>
    </div>
  );
}

function RoomCard({ roomId, employees, statuses, expanded, onToggle, isMobile }: {
  roomId: RoomId;
  employees: EmployeeId[];
  statuses: Record<EmployeeId, EmployeeState>;
  expanded?: boolean;
  onToggle?: () => void;
  isMobile?: boolean;
}) {
  const room = ROOMS[roomId];
  const activeCount = employees.filter(id => statuses[id]?.status !== 'idle').length;
  const hasCritical = employees.some(id => statuses[id]?.urgency === 'critical');
  const hasHigh = employees.some(id => statuses[id]?.urgency === 'high');

  const borderColor = hasCritical ? '#ef4444' : hasHigh ? '#f59e0b' : activeCount > 0 ? room.border : '#e5e7eb';
  const bgColor = employees.length === 0 ? '#f9fafb' : room.bg;

  if (isMobile && onToggle) {
    return (
      <div style={{
        borderRadius: 12, border: `1.5px solid ${borderColor}`,
        background: bgColor, overflow: 'hidden',
        boxShadow: activeCount > 0 ? `0 2px 10px ${room.color}15` : 'none',
      }}>
        <button
          onClick={onToggle}
          style={{
            width: '100%', padding: '10px 14px',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: 'transparent', border: 'none', cursor: 'pointer',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16 }}>{room.emoji}</span>
            <div style={{ textAlign: 'left' }}>
              <p style={{ fontSize: 12, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{room.name}</p>
              <p style={{ fontSize: 10, color: '#6b7280', margin: 0 }}>
                {employees.length === 0 ? 'Empty' : `${employees.length} employee${employees.length > 1 ? 's' : ''}${activeCount > 0 ? ` · ${activeCount} active` : ''}`}
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {activeCount > 0 && (
              <motion.div
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                style={{ width: 6, height: 6, borderRadius: '50%', background: room.color }}
              />
            )}
            {expanded ? <ChevronUp size={14} color="#9ca3af" /> : <ChevronDown size={14} color="#9ca3af" />}
          </div>
        </button>
        <AnimatePresence>
          {expanded && employees.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              style={{ overflow: 'hidden' }}
            >
              <div style={{ padding: '8px 14px 12px', display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                {employees.map(id => (
                  <EmployeeAvatar key={id} id={id} state={statuses[id]} size="sm" showTask />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <div style={{
      gridArea: room.gridArea,
      borderRadius: 12,
      border: `1.5px solid ${borderColor}`,
      background: bgColor,
      padding: '10px 12px',
      display: 'flex', flexDirection: 'column', gap: 8,
      minHeight: 120,
      position: 'relative',
      overflow: 'hidden',
      boxShadow: activeCount > 0 ? `0 2px 10px ${room.color}15` : 'none',
      transition: 'border-color 0.3s, box-shadow 0.3s',
    }}>
      {/* Room header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 7,
            background: activeCount > 0 ? `${room.color}20` : '#f3f4f6',
            border: `1px solid ${activeCount > 0 ? room.color + '40' : '#e5e7eb'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14,
          }}>
            {room.emoji}
          </div>
          <div>
            <p style={{ fontSize: 11, fontWeight: 800, color: '#1a1c3a', margin: 0, lineHeight: 1.2 }}>
              {room.name}
            </p>
            <p style={{ fontSize: 9, color: '#9ca3af', margin: 0 }}>{room.description}</p>
          </div>
        </div>
        {activeCount > 0 && (
          <motion.div
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.8, repeat: Infinity }}
            style={{ width: 7, height: 7, borderRadius: '50%', background: room.color, flexShrink: 0 }}
          />
        )}
      </div>

      {/* Desk element */}
      {employees.length > 0 && (
        <div style={{
          flex: 1, borderRadius: 8,
          background: activeCount > 0 ? `${room.color}08` : 'rgba(0,0,0,0.02)',
          border: `1px dashed ${activeCount > 0 ? room.color + '30' : '#e5e7eb'}`,
          display: 'flex', flexWrap: 'wrap', gap: 8,
          padding: '8px 10px', alignItems: 'flex-start', alignContent: 'flex-start',
        }}>
          {employees.map(id => (
            <motion.div key={id} layoutId={`employee-${id}`} layout transition={{ duration: 0.5, ease: 'easeInOut' }}>
              <EmployeeAvatar id={id} state={statuses[id]} size="sm" showTask />
            </motion.div>
          ))}
        </div>
      )}

      {employees.length === 0 && (
        <div style={{
          flex: 1, borderRadius: 8,
          background: 'rgba(0,0,0,0.02)',
          border: '1px dashed #e5e7eb',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <p style={{ fontSize: 10, color: '#d1d5db', margin: 0 }}>Empty</p>
        </div>
      )}

      {/* Special: Trading room safety badge */}
      {roomId === 'trading' && (
        <div style={{
          position: 'absolute', top: 6, right: 6,
          background: '#f0fdf4', border: '1px solid #bbf7d0',
          borderRadius: 6, padding: '2px 6px',
          fontSize: 8, fontWeight: 700, color: '#16a34a',
        }}>
          DEMO ONLY
        </div>
      )}
    </div>
  );
}

function TodayPanel({ data, statuses }: { data: VirtualOfficeData; statuses: Record<EmployeeId, EmployeeState> }) {
  const activeEmployees = (Object.keys(statuses) as EmployeeId[]).filter(id => statuses[id].status !== 'idle');
  const criticalItems = (Object.keys(statuses) as EmployeeId[]).filter(id => statuses[id].urgency === 'critical' || statuses[id].urgency === 'high');
  const onlineProviders = data.providers.filter(p => p.status === 'online').length;

  return (
    <div style={{
      padding: '12px 14px',
      background: '#1a1c3a',
      borderRadius: 12,
      color: '#fff',
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <motion.div
          animate={{ opacity: [1, 0.4, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }}
        />
        <p style={{ fontSize: 11, fontWeight: 800, color: '#a5b4fc', margin: 0, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Today in Nexus
        </p>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {[
          { label: 'Active', value: activeEmployees.length, color: '#22c55e' },
          { label: 'Tasks', value: data.tickets.length, color: '#7c3aed' },
          { label: 'Opps', value: data.opportunityCount, color: '#0d9488' },
          { label: 'AI Providers', value: onlineProviders, color: '#3d5af1' },
        ].map(s => (
          <div key={s.label} style={{ flex: '1 1 50px', textAlign: 'center' }}>
            <p style={{ fontSize: 20, fontWeight: 800, color: s.color, margin: 0, lineHeight: 1 }}>{s.value}</p>
            <p style={{ fontSize: 8, color: 'rgba(255,255,255,0.5)', margin: '2px 0 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{s.label}</p>
          </div>
        ))}
      </div>

      {criticalItems.length > 0 && (
        <div style={{ padding: '7px 10px', borderRadius: 8, background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)' }}>
          <p style={{ fontSize: 10, fontWeight: 700, color: '#fca5a5', margin: 0 }}>
            ⚠️ {criticalItems.map(id => EMPLOYEES[id].name).join(', ')} need attention
          </p>
        </div>
      )}

      {data.isDemo && (
        <div style={{ padding: '6px 10px', borderRadius: 8, background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', textAlign: 'center' }}>
          <p style={{ fontSize: 9, fontWeight: 700, color: '#fbbf24', margin: 0, letterSpacing: '0.04em' }}>
            DEMO / SIMULATED — No live data yet
          </p>
        </div>
      )}

      {/* Active tasks */}
      {data.tickets.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <p style={{ fontSize: 9, fontWeight: 700, color: 'rgba(255,255,255,0.4)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Open Tasks
          </p>
          {data.tickets.slice(0, 3).map(t => (
            <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ width: 5, height: 5, borderRadius: '50%', background: t.status === 'researching' ? '#7c3aed' : '#6b7280', flexShrink: 0 }} />
              <p style={{ fontSize: 9, color: 'rgba(255,255,255,0.7)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {t.topic}
              </p>
            </div>
          ))}
          {data.tickets.length > 3 && (
            <p style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', margin: 0 }}>
              +{data.tickets.length - 3} more tasks
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function SystemStatusBar({ providers, isDemo }: { providers: ProviderHealth[]; isDemo: boolean }) {
  const online = providers.filter(p => p.status === 'online').length;
  const degraded = providers.filter(p => p.status === 'degraded').length;
  const offline = providers.filter(p => !['online', 'degraded'].includes(p.status)).length;

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
      padding: '8px 14px', borderRadius: 10,
      background: offline > 0 ? '#fef2f2' : degraded > 0 ? '#fffbeb' : '#f0fdf4',
      border: `1px solid ${offline > 0 ? '#fecaca' : degraded > 0 ? '#fde68a' : '#bbf7d0'}`,
    }}>
      {providers.length === 0 ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <WifiOff size={12} color="#9ca3af" />
          <p style={{ fontSize: 10, color: '#9ca3af', margin: 0, fontWeight: 600 }}>No provider data yet</p>
        </div>
      ) : (
        <>
          <Wifi size={12} color={offline > 0 ? '#ef4444' : '#22c55e'} />
          <p style={{ fontSize: 10, fontWeight: 700, color: offline > 0 ? '#ef4444' : '#16a34a', margin: 0 }}>
            AI Providers: {online} online{degraded > 0 ? ` · ${degraded} degraded` : ''}{offline > 0 ? ` · ${offline} offline` : ''}
          </p>
        </>
      )}
      {providers.filter(p => p.status !== 'online').map(p => (
        <div key={p.provider_name} style={{
          display: 'flex', alignItems: 'center', gap: 4,
          padding: '2px 6px', borderRadius: 5,
          background: p.status === 'degraded' ? '#fffbeb' : '#fef2f2',
          border: `1px solid ${p.status === 'degraded' ? '#fde68a' : '#fecaca'}`,
        }}>
          <AlertTriangle size={9} color={p.status === 'degraded' ? '#f59e0b' : '#ef4444'} />
          <span style={{ fontSize: 9, fontWeight: 600, color: '#1a1c3a' }}>{p.provider_name}</span>
        </div>
      ))}
      {isDemo && (
        <div style={{ marginLeft: 'auto', padding: '2px 8px', borderRadius: 5, background: '#fffbeb', border: '1px solid #fde68a' }}>
          <span style={{ fontSize: 9, fontWeight: 700, color: '#f59e0b' }}>DEMO MODE</span>
        </div>
      )}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

function timeAgo(ts: string) {
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export function NexusVirtualOffice() {
  const [data, setData] = useState<VirtualOfficeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date().toISOString());
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [expandedRooms, setExpandedRooms] = useState<Set<RoomId>>(new Set(['command', 'trading', 'system']));
  const prevRooms = useRef<Record<EmployeeId, RoomId> | null>(null);

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const load = useCallback(async () => {
    const [phRes, evRes, oppsRes, ticketRes, transcriptRes, knowledgeRes] = await Promise.all([
      supabase.from('provider_health').select('provider_name,status,avg_latency_ms').order('provider_name'),
      supabase.from('analytics_events').select('feature,event_name,created_at').order('created_at', { ascending: false }).limit(60),
      supabase.from('user_opportunities').select('id', { count: 'exact', head: true }),
      supabase.from('research_requests').select('id,department,status,topic,created_at').in('status', ['submitted', 'queued', 'researching', 'needs_review']).order('created_at', { ascending: false }).limit(30),
      supabase.from('transcript_queue').select('id', { count: 'exact', head: true }),
      supabase.from('knowledge_items').select('id', { count: 'exact', head: true }).eq('status', 'approved'),
    ]);

    const providers = (phRes.data || []) as ProviderHealth[];
    const events = ((evRes.data || []) as Array<{ feature: string | null; created_at: string }>);
    const tickets = (ticketRes.data || []) as ResearchTicket[];
    const opportunityCount = oppsRes.count || 0;
    const ingestCount = transcriptRes.count || 0;
    const knowledgeCount = knowledgeRes.count || 0;

    const minutesAgo = (ts: string) => Math.floor((Date.now() - new Date(ts).getTime()) / 60000);
    const recentFeatures = new Set(
      events.filter(e => minutesAgo(e.created_at) < 60).map(e => e.feature).filter(Boolean) as string[]
    );

    const hasRealData = providers.length > 0 || tickets.length > 0 || opportunityCount > 0;

    if (!hasRealData) {
      setData(buildDemoData());
    } else {
      setData({ providers, tickets, opportunityCount, recentFeatures, ingestCount, knowledgeCount, revenueEventCount: 0, isDemo: false });
    }

    setLastRefresh(new Date().toISOString());
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => { void load(); const t = setInterval(() => void load(), 90_000); return () => clearInterval(t); }, [load]);

  const handleRefresh = () => { setRefreshing(true); void load(); };

  if (loading || !data) {
    return (
      <div style={{ padding: 20 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[...Array(6)].map((_, i) => (
            <div key={i} style={{ height: 80, borderRadius: 12, background: '#f3f4f6', animation: 'pulse 1.5s infinite' }} />
          ))}
        </div>
      </div>
    );
  }

  const employeeRooms = computeRooms(data);
  const statuses = computeStatuses(data, employeeRooms);

  // Track movements (for logging, could be used for notifications)
  if (prevRooms.current) {
    (Object.keys(employeeRooms) as EmployeeId[]).forEach(id => {
      if (prevRooms.current![id] !== employeeRooms[id]) {
        // Employee moved rooms — motion/react layoutId handles the animation
      }
    });
  }
  prevRooms.current = employeeRooms;

  // Group employees by room
  const roomEmployees = (Object.keys(ROOMS) as RoomId[]).reduce((acc, roomId) => {
    acc[roomId] = (Object.keys(employeeRooms) as EmployeeId[]).filter(id => employeeRooms[id] === roomId);
    return acc;
  }, {} as Record<RoomId, EmployeeId[]>);

  const toggleRoom = (roomId: RoomId) => {
    setExpandedRooms(prev => {
      const next = new Set(prev);
      if (next.has(roomId)) next.delete(roomId);
      else next.add(roomId);
      return next;
    });
  };

  const ROOM_ORDER: RoomId[] = ['command', 'system', 'trading', 'opportunities', 'research', 'funding', 'credit', 'marketing', 'grants', 'break'];

  return (
    <div style={{ padding: '14px 18px', paddingBottom: 120 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div>
          <h2 style={{ fontSize: 19, fontWeight: 800, color: '#1a1c3a', margin: 0, marginBottom: 2 }}>
            🏢 Nexus Virtual Office
          </h2>
          <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>
            AI workforce — real-time operational visualization
          </p>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <motion.div
            animate={{ opacity: [1, 0.4, 1] }}
            transition={{ duration: 3, repeat: Infinity }}
            style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }}
          />
          <span style={{ fontSize: 10, color: '#8b8fa8' }}>Synced {timeAgo(lastRefresh)}</span>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '5px 10px', borderRadius: 8, border: '1px solid #e5e7eb',
              background: '#fff', color: '#3d5af1', fontWeight: 600, fontSize: 11, cursor: 'pointer',
            }}
          >
            <RefreshCw size={10} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>
      </div>

      {/* Demo banner */}
      {data.isDemo && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            padding: '8px 14px', borderRadius: 10, marginBottom: 12,
            background: '#fffbeb', border: '1.5px solid #fde68a',
            display: 'flex', alignItems: 'center', gap: 8,
          }}
        >
          <span style={{ fontSize: 14 }}>🎭</span>
          <div>
            <p style={{ fontSize: 11, fontWeight: 800, color: '#92400e', margin: 0 }}>
              DEMO / SIMULATED MODE
            </p>
            <p style={{ fontSize: 10, color: '#78350f', margin: 0 }}>
              Showing simulated office activity — real data will appear once Nexus operations are running
            </p>
          </div>
        </motion.div>
      )}

      {/* System status */}
      <div style={{ marginBottom: 12 }}>
        <SystemStatusBar providers={data.providers} isDemo={data.isDemo} />
      </div>

      {/* Desktop: 2D office floor plan */}
      {!isMobile ? (
        <LayoutGroup>
          <div style={{ display: 'flex', gap: 14 }}>
            {/* Main office grid */}
            <div style={{
              flex: 1,
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gridTemplateRows: 'auto auto auto auto',
              gridTemplateAreas: `
                "command command system"
                "trading opps library"
                "funding credit marketing"
                "grants grants break"
              `,
              gap: 10,
            }}>
              {(Object.keys(ROOMS) as RoomId[]).map(roomId => (
                <RoomCard
                  key={roomId}
                  roomId={roomId}
                  employees={roomEmployees[roomId]}
                  statuses={statuses}
                />
              ))}
            </div>

            {/* Today panel sidebar */}
            <div style={{ width: 200, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <TodayPanel data={data} statuses={statuses} />

              {/* Employee roster */}
              <div style={{
                borderRadius: 12, border: '1px solid #e5e7eb',
                background: '#fff', padding: '12px',
              }}>
                <p style={{ fontSize: 10, fontWeight: 800, color: '#6b7280', margin: '0 0 8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Employee Roster
                </p>
                {(Object.keys(EMPLOYEES) as EmployeeId[]).map(id => {
                  const emp = EMPLOYEES[id];
                  const state = statuses[id];
                  const room = ROOMS[employeeRooms[id]];
                  return (
                    <div key={id} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6 }}>
                      <span style={{ fontSize: 14 }}>{emp.emoji}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontSize: 10, fontWeight: 700, color: '#1a1c3a', margin: 0 }}>{emp.name}</p>
                        <p style={{ fontSize: 9, color: '#9ca3af', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {room.emoji} {room.name}
                        </p>
                      </div>
                      <div style={{
                        width: 7, height: 7, borderRadius: '50%',
                        background: STATUS_COLORS[state.status], flexShrink: 0,
                      }} />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </LayoutGroup>
      ) : (
        /* Mobile: swipeable stacked rooms */
        <LayoutGroup>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {/* Today panel on mobile (compact) */}
            <TodayPanel data={data} statuses={statuses} />

            {ROOM_ORDER.map(roomId => (
              <RoomCard
                key={roomId}
                roomId={roomId}
                employees={roomEmployees[roomId]}
                statuses={statuses}
                expanded={expandedRooms.has(roomId)}
                onToggle={() => toggleRoom(roomId)}
                isMobile
              />
            ))}
          </div>
        </LayoutGroup>
      )}

      {/* Safety footer */}
      <div style={{
        marginTop: 16, padding: '8px 14px', borderRadius: 10,
        background: '#f0fdf4', border: '1px solid #bbf7d0',
        display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
      }}>
        <Shield size={12} color="#16a34a" />
        <p style={{ fontSize: 10, color: '#16a34a', fontWeight: 700, margin: 0 }}>
          NEXUS_DRY_RUN=true · LIVE_TRADING=false · DEMO trading only · No real-money execution · No automated social posting
        </p>
      </div>
    </div>
  );
}
