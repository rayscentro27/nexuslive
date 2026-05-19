/**
 * NexusVirtualOffice — Living AI workforce simulation.
 * Agents physically walk between zones, receive tasks, work, and return results.
 * Simulation-first: task flow is visible on the office floor at all times.
 */
import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'motion/react';
import { supabase } from '../../lib/supabase';

// ─── Types ───────────────────────────────────────────────────────────────────

type ZoneId =
  | 'hermes_command' | 'review_table'
  | 'trading_desk' | 'opportunity_lab' | 'grants_research'
  | 'funding_strategy' | 'credit_intel' | 'marketing_studio'
  | 'research_library' | 'system_monitor' | 'break_area';

type AgentId = 'hermes' | 'sage' | 'rex' | 'vera' | 'aria' | 'nova' | 'mira' | 'orion';

type MovementState =
  | 'idle' | 'resting' | 'walking_to_hermes' | 'receiving_task'
  | 'walking_to_department' | 'working' | 'blocked'
  | 'returning_result' | 'reviewing' | 'completed';

type Priority = 'low' | 'medium' | 'high' | 'critical';
type ViewMode = 'full' | 'follow_hermes' | 'follow_task' | 'trading' | 'opportunity' | 'system';

interface ZoneConfig {
  label: string;
  emoji: string;
  color: string;
  bg: string;
  border: string;
  // logical coords on 800×560 canvas
  x: number; y: number; w: number; h: number;
  capacity: number;
  description: string;
}

interface AgentConfig {
  name: string;
  emoji: string;
  color: string;
  homeZone: ZoneId;
  role: string;
  departmentZone: ZoneId;
}

interface TaskBubble {
  id: string;
  title: string;
  source: string;
  priority: Priority;
  riskLevel: 'low' | 'medium' | 'high';
  description: string;
}

interface ResultCard {
  taskId: string;
  outcome: 'completed' | 'blocked' | 'review';
  summary: string;
  nextAction?: string;
  approvalNeeded?: boolean;
}

interface AgentSimState {
  agentId: AgentId;
  currentZone: ZoneId;
  targetZone: ZoneId;
  movementState: MovementState;
  currentTask: TaskBubble | null;
  result: ResultCard | null;
  ticksInState: number;
  urgency: Priority;
  destinationReason: string;
}

interface OfficeData {
  isDemo: boolean;
  pendingTasks: TaskBubble[];
  providerHealth: { name: string; status: 'online' | 'offline' | 'degraded'; latency?: number }[];
  approvalCount: number;
  taskQueueCount: number;
}

// ─── Zone Layout (800×560 logical canvas) ────────────────────────────────────

const ZONES: Record<ZoneId, ZoneConfig> = {
  hermes_command: {
    label: 'Hermes Command', emoji: '🎯', color: '#3d5af1',
    bg: 'rgba(61,90,241,0.12)', border: 'rgba(61,90,241,0.5)',
    x: 300, y: 20, w: 200, h: 90, capacity: 2,
    description: 'Central coordination hub',
  },
  review_table: {
    label: 'Review Table', emoji: '📋', color: '#64748b',
    bg: 'rgba(100,116,139,0.10)', border: 'rgba(100,116,139,0.4)',
    x: 280, y: 140, w: 240, h: 70, capacity: 4,
    description: 'Blocked tasks & approval review',
  },
  trading_desk: {
    label: 'Trading Desk', emoji: '📊', color: '#22c55e',
    bg: 'rgba(34,197,94,0.10)', border: 'rgba(34,197,94,0.4)',
    x: 20, y: 50, w: 180, h: 100, capacity: 2,
    description: 'DEMO / PAPER ONLY — no live execution',
  },
  opportunity_lab: {
    label: 'Opportunity Lab', emoji: '💡', color: '#0d9488',
    bg: 'rgba(13,148,136,0.10)', border: 'rgba(13,148,136,0.4)',
    x: 20, y: 190, w: 180, h: 95, capacity: 2,
    description: 'Business opportunity scoring',
  },
  grants_research: {
    label: 'Grants Research', emoji: '🏆', color: '#8b5cf6',
    bg: 'rgba(139,92,246,0.10)', border: 'rgba(139,92,246,0.4)',
    x: 20, y: 335, w: 180, h: 95, capacity: 2,
    description: 'Grant discovery & eligibility',
  },
  funding_strategy: {
    label: 'Funding Strategy', emoji: '💰', color: '#f59e0b',
    bg: 'rgba(245,158,11,0.10)', border: 'rgba(245,158,11,0.4)',
    x: 600, y: 50, w: 180, h: 100, capacity: 2,
    description: 'Funding readiness & lender match',
  },
  credit_intel: {
    label: 'Credit Intelligence', emoji: '🛡️', color: '#6366f1',
    bg: 'rgba(99,102,241,0.10)', border: 'rgba(99,102,241,0.4)',
    x: 600, y: 190, w: 180, h: 95, capacity: 2,
    description: 'Credit score analysis & coaching',
  },
  marketing_studio: {
    label: 'Marketing Studio', emoji: '🎨', color: '#ec4899',
    bg: 'rgba(236,72,153,0.10)', border: 'rgba(236,72,153,0.4)',
    x: 600, y: 335, w: 180, h: 95, capacity: 2,
    description: 'Content & campaign strategy',
  },
  research_library: {
    label: 'Research Library', emoji: '📚', color: '#78716c',
    bg: 'rgba(120,113,108,0.08)', border: 'rgba(120,113,108,0.35)',
    x: 220, y: 260, w: 160, h: 80, capacity: 3,
    description: 'Knowledge ingestion & learning',
  },
  system_monitor: {
    label: 'System Monitor', emoji: '📡', color: '#ef4444',
    bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.35)',
    x: 420, y: 260, w: 160, h: 80, capacity: 2,
    description: 'Infrastructure & AI provider health',
  },
  break_area: {
    label: 'Break Area', emoji: '☕', color: '#9ca3af',
    bg: 'rgba(156,163,175,0.07)', border: 'rgba(156,163,175,0.3)',
    x: 300, y: 380, w: 200, h: 65, capacity: 8,
    description: 'Standby / idle',
  },
};

// Agent center within a zone (with slight offsets so they don't overlap)
const ZONE_AGENT_SLOTS: Partial<Record<ZoneId, [number, number][]>> = {
  hermes_command: [[0, 0], [40, 0]],
  review_table:   [[-40, 0], [0, 0], [40, 0]],
  break_area:     [[-60, 0], [-20, 0], [20, 0], [60, 0]],
};

function getZoneCenter(zoneId: ZoneId): { x: number; y: number } {
  const z = ZONES[zoneId];
  return { x: z.x + z.w / 2, y: z.y + z.h / 2 };
}

// ─── Agent Config ─────────────────────────────────────────────────────────────

const AGENTS: Record<AgentId, AgentConfig> = {
  hermes: { name: 'Hermes', emoji: '🤖', color: '#3d5af1', homeZone: 'hermes_command', departmentZone: 'hermes_command', role: 'Chief Operations' },
  sage:   { name: 'Sage',   emoji: '📈', color: '#22c55e', homeZone: 'break_area',     departmentZone: 'trading_desk',    role: 'Trading Analyst (Paper)' },
  rex:    { name: 'Rex',    emoji: '💰', color: '#f59e0b', homeZone: 'break_area',     departmentZone: 'funding_strategy', role: 'Funding Strategist' },
  vera:   { name: 'Vera',   emoji: '🛡️', color: '#6366f1', homeZone: 'break_area',     departmentZone: 'credit_intel',    role: 'Credit Coach' },
  aria:   { name: 'Aria',   emoji: '🏆', color: '#8b5cf6', homeZone: 'break_area',     departmentZone: 'grants_research',  role: 'Grant Researcher' },
  nova:   { name: 'Nova',   emoji: '🔭', color: '#0d9488', homeZone: 'break_area',     departmentZone: 'opportunity_lab',  role: 'Opportunity Analyst' },
  mira:   { name: 'Mira',   emoji: '🎨', color: '#ec4899', homeZone: 'break_area',     departmentZone: 'marketing_studio', role: 'Marketing Strategist' },
  orion:  { name: 'Orion',  emoji: '📡', color: '#ef4444', homeZone: 'system_monitor', departmentZone: 'system_monitor',   role: 'Systems Monitor' },
};

// ─── Demo Task Queue ──────────────────────────────────────────────────────────

const DEMO_TASKS: Record<AgentId, TaskBubble[]> = {
  sage: [
    { id: 'sage-1', title: 'London Breakout Analysis', source: 'strategy_v1', priority: 'medium', riskLevel: 'low', description: 'Paper trade journal — GBP/USD session setup' },
    { id: 'sage-2', title: 'EMA Pullback Review', source: 'strategy_v2', priority: 'low', riskLevel: 'low', description: 'EUR/USD trend continuation check' },
  ],
  nova: [
    { id: 'nova-1', title: 'Opportunity Scoring: Affiliate Stack', source: 'phase2_opportunity', priority: 'high', riskLevel: 'low', description: 'Score Lendio + Bluevine + Nav affiliate stack' },
    { id: 'nova-2', title: 'Faceless YouTube Channel Fit', source: 'phase2_content', priority: 'medium', riskLevel: 'low', description: 'Validate Business Credit Lab niche score' },
  ],
  rex: [
    { id: 'rex-1', title: 'Funding Readiness Audit', source: 'phase2_monetization', priority: 'high', riskLevel: 'low', description: 'Generate $297 audit report for test client' },
  ],
  vera: [
    { id: 'vera-1', title: 'PAYDEX Score Article', source: 'phase2_content', priority: 'medium', riskLevel: 'low', description: 'SEO article — paydex score keyword' },
  ],
  aria: [
    { id: 'aria-1', title: 'SBIR/STTR Eligibility Check', source: 'grant_research_v1', priority: 'medium', riskLevel: 'low', description: 'Phase I tech business grant match' },
    { id: 'aria-2', title: 'Women-Owned Business Grants', source: 'grant_research_v1', priority: 'low', riskLevel: 'low', description: 'Top 10 sources ranked 2026' },
  ],
  mira: [
    { id: 'mira-1', title: 'Newsletter Issue #1', source: 'nexus_business_brief', priority: 'medium', riskLevel: 'low', description: 'Week 1: funding tip + credit move + grant watch' },
  ],
  orion: [
    { id: 'orion-1', title: 'Provider Health Alert', source: 'system_monitor', priority: 'high', riskLevel: 'low', description: 'ollama + claude_cli offline — investigating' },
  ],
  hermes: [],
};

// ─── Simulation Engine ────────────────────────────────────────────────────────

const MOVEMENT_DURATIONS: Record<MovementState, number> = {
  idle:                  0,
  resting:               8,
  walking_to_hermes:     3,
  receiving_task:        2,
  walking_to_department: 3,
  working:               10,
  blocked:               4,
  returning_result:      3,
  reviewing:             3,
  completed:             2,
};

function buildInitialAgentStates(officeData: OfficeData): AgentSimState[] {
  return (Object.keys(AGENTS) as AgentId[]).map((agentId) => {
    const cfg = AGENTS[agentId];
    return {
      agentId,
      currentZone: agentId === 'hermes' ? 'hermes_command' : agentId === 'orion' ? 'system_monitor' : 'break_area',
      targetZone: agentId === 'hermes' ? 'hermes_command' : agentId === 'orion' ? 'system_monitor' : 'break_area',
      movementState: agentId === 'hermes' ? 'idle' : 'resting',
      currentTask: null,
      result: null,
      ticksInState: 0,
      urgency: 'low',
      destinationReason: agentId === 'hermes' ? 'Coordinating workforce' : 'Standby',
    };
  });
}

function tickAgentState(
  agent: AgentSimState,
  taskQueue: TaskBubble[],
  hasApprovals: boolean,
): AgentSimState {
  const cfg = AGENTS[agent.agentId];
  const duration = MOVEMENT_DURATIONS[agent.movementState];
  const nextTick = agent.ticksInState + 1;

  if (agent.agentId === 'hermes') {
    return {
      ...agent,
      movementState: 'idle',
      ticksInState: nextTick,
      urgency: hasApprovals ? 'high' : 'low',
      destinationReason: hasApprovals
        ? `${taskQueue.length} pending — dispatching`
        : 'Monitoring workforce',
    };
  }

  // State machine transitions
  switch (agent.movementState) {
    case 'resting':
    case 'idle': {
      if (taskQueue.length === 0) {
        return { ...agent, ticksInState: nextTick };
      }
      if (nextTick < 2) return { ...agent, ticksInState: nextTick };
      const task = taskQueue[0];
      return {
        ...agent,
        movementState: 'walking_to_hermes',
        targetZone: 'hermes_command',
        currentTask: task,
        ticksInState: 0,
        urgency: task.priority,
        destinationReason: 'Picking up task',
      };
    }

    case 'walking_to_hermes': {
      if (nextTick < duration) {
        return {
          ...agent,
          currentZone: agent.currentZone === agent.targetZone ? agent.currentZone : agent.currentZone,
          ticksInState: nextTick,
        };
      }
      return {
        ...agent,
        currentZone: 'hermes_command',
        movementState: 'receiving_task',
        ticksInState: 0,
        destinationReason: 'Receiving task from Hermes',
      };
    }

    case 'receiving_task': {
      if (nextTick < MOVEMENT_DURATIONS.receiving_task) {
        return { ...agent, ticksInState: nextTick };
      }
      return {
        ...agent,
        movementState: 'walking_to_department',
        targetZone: cfg.departmentZone,
        ticksInState: 0,
        destinationReason: `Heading to ${ZONES[cfg.departmentZone].label}`,
      };
    }

    case 'walking_to_department': {
      if (nextTick < duration) {
        return { ...agent, ticksInState: nextTick };
      }
      return {
        ...agent,
        currentZone: cfg.departmentZone,
        movementState: 'working',
        ticksInState: 0,
        destinationReason: `Working: ${agent.currentTask?.title ?? '—'}`,
      };
    }

    case 'working': {
      if (nextTick < MOVEMENT_DURATIONS.working) {
        return { ...agent, ticksInState: nextTick };
      }
      const shouldBlock = agent.currentTask?.riskLevel === 'high';
      if (shouldBlock) {
        return {
          ...agent,
          movementState: 'blocked',
          targetZone: 'review_table',
          ticksInState: 0,
          destinationReason: 'Blocked — needs review',
          urgency: 'high',
        };
      }
      return {
        ...agent,
        movementState: 'returning_result',
        targetZone: 'hermes_command',
        ticksInState: 0,
        result: {
          taskId: agent.currentTask?.id ?? '',
          outcome: 'completed',
          summary: `${agent.currentTask?.title ?? 'Task'} — done`,
          nextAction: 'Review output',
          approvalNeeded: false,
        },
        destinationReason: 'Returning result to Hermes',
      };
    }

    case 'blocked': {
      if (nextTick < MOVEMENT_DURATIONS.blocked) {
        return { ...agent, ticksInState: nextTick };
      }
      return {
        ...agent,
        currentZone: 'review_table',
        movementState: 'reviewing',
        ticksInState: 0,
        destinationReason: 'Under review at approval table',
      };
    }

    case 'reviewing': {
      if (nextTick < MOVEMENT_DURATIONS.reviewing) {
        return { ...agent, ticksInState: nextTick };
      }
      return {
        ...agent,
        movementState: 'returning_result',
        targetZone: 'hermes_command',
        ticksInState: 0,
        result: {
          taskId: agent.currentTask?.id ?? '',
          outcome: 'review',
          summary: `${agent.currentTask?.title ?? 'Task'} — reviewed`,
          approvalNeeded: true,
        },
        destinationReason: 'Returning reviewed result',
      };
    }

    case 'returning_result': {
      if (nextTick < MOVEMENT_DURATIONS.returning_result) {
        return { ...agent, ticksInState: nextTick };
      }
      return {
        ...agent,
        currentZone: 'hermes_command',
        movementState: 'completed',
        ticksInState: 0,
        destinationReason: 'Result delivered',
      };
    }

    case 'completed': {
      if (nextTick < MOVEMENT_DURATIONS.completed) {
        return { ...agent, ticksInState: nextTick };
      }
      return {
        ...agent,
        movementState: 'resting',
        currentZone: 'break_area',
        targetZone: 'break_area',
        currentTask: null,
        result: null,
        ticksInState: 0,
        urgency: 'low',
        destinationReason: 'Standby',
      };
    }

    default:
      return { ...agent, ticksInState: nextTick };
  }
}

// Returns x,y on the canvas for an agent given its current movement state
function getAgentPosition(agent: AgentSimState): { x: number; y: number } {
  if (
    agent.movementState === 'walking_to_hermes' ||
    agent.movementState === 'walking_to_department' ||
    agent.movementState === 'returning_result' ||
    agent.movementState === 'blocked'
  ) {
    const target = getZoneCenter(agent.targetZone);
    const current = getZoneCenter(agent.currentZone);
    return {
      x: (current.x + target.x) / 2,
      y: (current.y + target.y) / 2,
    };
  }
  return getZoneCenter(agent.currentZone);
}

// ─── Data Fetching ────────────────────────────────────────────────────────────

async function fetchOfficeData(): Promise<OfficeData> {
  try {
    const [providerRes, approvalRes, taskRes] = await Promise.allSettled([
      supabase.from('provider_health').select('provider_name,status,avg_latency_ms').limit(10),
      supabase.from('human_approval_requests').select('id').eq('status', 'pending'),
      supabase.from('agent_dispatch_tasks').select('id').eq('status', 'received'),
    ]);

    const providers = providerRes.status === 'fulfilled'
      ? (providerRes.value.data ?? []).map((p: { provider_name: string; status: string; avg_latency_ms: number | null }) => ({
          name: p.provider_name,
          status: (p.status === 'online' ? 'online' : p.status === 'degraded' ? 'degraded' : 'offline') as 'online' | 'offline' | 'degraded',
          latency: p.avg_latency_ms ?? undefined,
        }))
      : [];

    const approvalCount = approvalRes.status === 'fulfilled'
      ? (approvalRes.value.data?.length ?? 0) : 0;

    const taskQueueCount = taskRes.status === 'fulfilled'
      ? (taskRes.value.data?.length ?? 0) : 0;

    return { isDemo: false, pendingTasks: [], providerHealth: providers, approvalCount, taskQueueCount };
  } catch {
    return buildDemoOfficeData();
  }
}

function buildDemoOfficeData(): OfficeData {
  return {
    isDemo: true,
    pendingTasks: [],
    providerHealth: [
      { name: 'openrouter', status: 'online', latency: 312 },
      { name: 'groq', status: 'online', latency: 89 },
      { name: 'ollama', status: 'offline' },
      { name: 'claude_cli', status: 'offline' },
    ],
    approvalCount: 0,
    taskQueueCount: 12,
  };
}

// ─── Visual Components ────────────────────────────────────────────────────────

const PRIORITY_COLORS: Record<Priority, string> = {
  low: '#22c55e', medium: '#f59e0b', high: '#ef4444', critical: '#7c3aed',
};

const MOVEMENT_LABELS: Record<MovementState, string> = {
  idle: 'Idle', resting: 'Resting', walking_to_hermes: 'Walking to Hermes',
  receiving_task: 'Receiving task', walking_to_department: 'Heading to dept',
  working: 'Working', blocked: 'Blocked', returning_result: 'Returning result',
  reviewing: 'Reviewing', completed: 'Task complete',
};

function TaskBubbleView({ task, priority }: { task: TaskBubble; priority: Priority }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.7, y: -8 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.7, y: -8 }}
      style={{
        position: 'absolute',
        bottom: '100%', left: '50%',
        transform: 'translateX(-50%)',
        marginBottom: 6,
        background: '#0f1117',
        border: `1.5px solid ${PRIORITY_COLORS[priority]}55`,
        borderRadius: 10,
        padding: '5px 10px',
        minWidth: 110,
        maxWidth: 180,
        textAlign: 'center',
        pointerEvents: 'none',
        zIndex: 20,
        boxShadow: `0 2px 12px ${PRIORITY_COLORS[priority]}30`,
      }}
    >
      <div style={{ fontSize: 9, fontWeight: 700, color: PRIORITY_COLORS[priority], textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {priority}
      </div>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#fff', lineHeight: 1.3, marginTop: 2 }}>
        {task.title.length > 32 ? task.title.slice(0, 32) + '…' : task.title}
      </div>
      <div style={{ fontSize: 9, color: '#94a3b8', marginTop: 2, lineHeight: 1.2 }}>
        {task.source}
      </div>
    </motion.div>
  );
}

function ResultBadge({ result }: { result: ResultCard }) {
  const colors = {
    completed: { bg: '#166534', border: '#22c55e', text: '#4ade80' },
    blocked: { bg: '#7f1d1d', border: '#ef4444', text: '#f87171' },
    review: { bg: '#78350f', border: '#f59e0b', text: '#fbbf24' },
  };
  const c = colors[result.outcome];
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.7 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      style={{
        position: 'absolute',
        bottom: '100%', left: '50%',
        transform: 'translateX(-50%)',
        marginBottom: 6,
        background: c.bg,
        border: `1.5px solid ${c.border}`,
        borderRadius: 8,
        padding: '4px 10px',
        minWidth: 100,
        maxWidth: 160,
        textAlign: 'center',
        pointerEvents: 'none',
        zIndex: 20,
      }}
    >
      <div style={{ fontSize: 10, fontWeight: 700, color: c.text }}>
        {result.outcome === 'completed' ? '✅ Done' : result.outcome === 'blocked' ? '🚫 Blocked' : '👁 Review'}
      </div>
      <div style={{ fontSize: 9, color: '#cbd5e1', marginTop: 1 }}>
        {result.summary.length > 30 ? result.summary.slice(0, 30) + '…' : result.summary}
      </div>
      {result.approvalNeeded && (
        <div style={{ fontSize: 8, color: '#fbbf24', marginTop: 2 }}>⚡ Approval needed</div>
      )}
    </motion.div>
  );
}

interface AgentAvatarProps {
  agent: AgentSimState;
  canvasW: number;
  canvasH: number;
  reducedMotion: boolean;
  onClick: (id: AgentId) => void;
}

function AgentAvatar({ agent, canvasW, canvasH, reducedMotion, onClick }: AgentAvatarProps) {
  const cfg = AGENTS[agent.agentId];
  const pos = getAgentPosition(agent);
  const isMoving = [
    'walking_to_hermes', 'walking_to_department',
    'returning_result', 'blocked',
  ].includes(agent.movementState);
  const isWorking = agent.movementState === 'working';
  const isBlocked = agent.movementState === 'blocked' || agent.movementState === 'reviewing';

  const px = (pos.x / 800) * canvasW - 24;
  const py = (pos.y / 560) * canvasH - 24;

  return (
    <motion.div
      key={agent.agentId}
      animate={{ x: px, y: py }}
      transition={reducedMotion
        ? { duration: 0 }
        : { type: 'spring', stiffness: 60, damping: 14, mass: 1.2 }
      }
      style={{
        position: 'absolute',
        top: 0, left: 0,
        width: 48, height: 48,
        zIndex: 15,
        cursor: 'pointer',
      }}
      onClick={() => onClick(agent.agentId)}
    >
      <div style={{ position: 'relative', width: 48, height: 48 }}>

        {/* Working pulse ring */}
        {isWorking && !reducedMotion && (
          <motion.div
            animate={{ scale: [1, 1.6, 1], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
            style={{
              position: 'absolute', inset: -6, borderRadius: '50%',
              border: `2px solid ${cfg.color}`, opacity: 0.5,
              pointerEvents: 'none',
            }}
          />
        )}

        {/* Blocked indicator */}
        {isBlocked && !reducedMotion && (
          <motion.div
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
            style={{
              position: 'absolute', inset: -4, borderRadius: '50%',
              border: '2px solid #ef4444', pointerEvents: 'none',
            }}
          />
        )}

        {/* Agent circle */}
        <motion.div
          animate={isMoving && !reducedMotion ? { y: [0, -4, 0] } : {}}
          transition={{ duration: 0.6, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            width: 48, height: 48, borderRadius: '50%',
            background: cfg.color + '22',
            border: `2.5px solid ${cfg.color}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22,
            boxShadow: agent.urgency === 'critical'
              ? `0 0 18px ${cfg.color}99`
              : agent.urgency === 'high'
              ? `0 0 12px ${cfg.color}66`
              : `0 0 6px ${cfg.color}33`,
          }}
        >
          {cfg.emoji}
        </motion.div>

        {/* Name label */}
        <div style={{
          position: 'absolute', bottom: -16, left: '50%',
          transform: 'translateX(-50%)',
          fontSize: 9, fontWeight: 700, color: cfg.color,
          whiteSpace: 'nowrap',
          textShadow: '0 1px 3px rgba(0,0,0,0.8)',
        }}>
          {cfg.name}
        </div>

        {/* Task bubble or result */}
        <AnimatePresence>
          {agent.currentTask && agent.movementState !== 'resting' && agent.movementState !== 'completed' && (
            <TaskBubbleView
              key={`tb-${agent.currentTask.id}`}
              task={agent.currentTask}
              priority={agent.urgency}
            />
          )}
          {agent.result && agent.movementState === 'returning_result' && (
            <ResultBadge key={`rb-${agent.result.taskId}`} result={agent.result} />
          )}
        </AnimatePresence>

        {/* Movement state dot */}
        <div style={{
          position: 'absolute', top: 0, right: 0,
          width: 12, height: 12, borderRadius: '50%',
          background: PRIORITY_COLORS[agent.urgency],
          border: '2px solid #1e2235',
          boxShadow: `0 0 6px ${PRIORITY_COLORS[agent.urgency]}66`,
        }} />
      </div>
    </motion.div>
  );
}

// ─── Office Floor Zone Renderer ───────────────────────────────────────────────

function OfficeZone({
  zoneId, config, canvasW, canvasH, activeAgents, isActive,
}: {
  zoneId: ZoneId;
  config: ZoneConfig;
  canvasW: number;
  canvasH: number;
  activeAgents: number;
  isActive: boolean;
}) {
  const scaleX = canvasW / 800;
  const scaleY = canvasH / 560;

  return (
    <motion.div
      animate={isActive ? { boxShadow: [`0 0 0 0 ${config.color}00`, `0 0 12px 2px ${config.color}44`, `0 0 0 0 ${config.color}00`] } : {}}
      transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
      style={{
        position: 'absolute',
        left: config.x * scaleX,
        top: config.y * scaleY,
        width: config.w * scaleX,
        height: config.h * scaleY,
        background: config.bg,
        border: `1.5px solid ${isActive ? config.color : config.border}`,
        borderRadius: 12,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '4px 6px',
        overflow: 'hidden',
        transition: 'border-color 0.4s ease',
      }}
    >
      <div style={{ fontSize: zoneId === 'hermes_command' ? 18 : 14, lineHeight: 1 }}>
        {config.emoji}
      </div>
      <div style={{
        fontSize: zoneId === 'hermes_command' ? 9 : 8,
        fontWeight: 700,
        color: isActive ? config.color : '#64748b',
        textAlign: 'center',
        lineHeight: 1.2,
        marginTop: 2,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        maxWidth: '100%',
      }}>
        {config.label}
      </div>

      {/* Capacity dots */}
      {activeAgents > 0 && (
        <div style={{ display: 'flex', gap: 3, marginTop: 3 }}>
          {Array.from({ length: Math.min(activeAgents, config.capacity) }).map((_, i) => (
            <div key={i} style={{
              width: 5, height: 5, borderRadius: '50%',
              background: isActive ? config.color : '#64748b',
              opacity: 0.8,
            }} />
          ))}
        </div>
      )}

      {/* Trading desk safety label */}
      {zoneId === 'trading_desk' && (
        <div style={{
          fontSize: 7, fontWeight: 700,
          color: '#22c55e', marginTop: 2,
          background: 'rgba(34,197,94,0.15)',
          padding: '1px 5px', borderRadius: 4,
        }}>
          PAPER ONLY
        </div>
      )}
    </motion.div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function NexusVirtualOffice() {
  const reducedMotion = useReducedMotion() ?? false;
  const canvasRef = useRef<HTMLDivElement>(null);
  const [canvasSize, setCanvasSize] = useState({ w: 800, h: 560 });
  const [officeData, setOfficeData] = useState<OfficeData>(buildDemoOfficeData());
  const [agentStates, setAgentStates] = useState<AgentSimState[]>([]);
  const [taskQueues, setTaskQueues] = useState<Record<AgentId, TaskBubble[]>>(DEMO_TASKS as Record<AgentId, TaskBubble[]>);
  const [viewMode, setViewMode] = useState<ViewMode>('full');
  const [selectedAgent, setSelectedAgent] = useState<AgentId | null>(null);
  const [showRoster, setShowRoster] = useState(false);
  const [tick, setTick] = useState(0);
  const tickRef = useRef(0);

  // Canvas resize observer
  useEffect(() => {
    if (!canvasRef.current) return;
    const ro = new ResizeObserver(([entry]) => {
      const { width } = entry.contentRect;
      setCanvasSize({ w: width, h: Math.round(width * 0.7) });
    });
    ro.observe(canvasRef.current);
    return () => ro.disconnect();
  }, []);

  // Fetch live data
  useEffect(() => {
    fetchOfficeData().then(setOfficeData).catch(() => {});
    const interval = setInterval(() => {
      fetchOfficeData().then(setOfficeData).catch(() => {});
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  // Initialize agent states
  useEffect(() => {
    setAgentStates(buildInitialAgentStates(officeData));
  }, []);

  // Simulation tick — every 2 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      tickRef.current += 1;
      setTick(tickRef.current);

      setAgentStates(prev => prev.map(agent => {
        if (agent.agentId === 'hermes') {
          return {
            ...agent,
            movementState: 'idle',
            ticksInState: agent.ticksInState + 1,
            urgency: officeData.approvalCount > 0 ? 'high' : 'low',
            destinationReason: officeData.approvalCount > 0
              ? `${officeData.approvalCount} approval${officeData.approvalCount > 1 ? 's' : ''} pending`
              : `Coordinating ${Object.values(taskQueues).flat().length} queued tasks`,
          };
        }

        const queue = taskQueues[agent.agentId] ?? [];
        const currentTasks = queue.filter(t =>
          !agent.currentTask || agent.currentTask.id !== t.id
        );
        const nextState = tickAgentState(agent, currentTasks, officeData.approvalCount > 0);

        // Pop task from queue when agent picks it up
        if (
          nextState.movementState === 'walking_to_hermes' &&
          nextState.currentTask &&
          nextState.currentTask !== agent.currentTask
        ) {
          setTaskQueues(prev => ({
            ...prev,
            [agent.agentId]: prev[agent.agentId].filter(t => t.id !== nextState.currentTask!.id),
          }));
        }

        // Re-add task to queue after completion (demo loop)
        if (nextState.movementState === 'resting' && agent.movementState === 'completed') {
          const completedTask = agent.currentTask;
          if (completedTask && officeData.isDemo) {
            setTimeout(() => {
              setTaskQueues(prev => ({
                ...prev,
                [agent.agentId]: [...(prev[agent.agentId] ?? []), { ...completedTask, id: `${completedTask.id}-${Date.now()}` }],
              }));
            }, 8000);
          }
        }

        return nextState;
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, [officeData, taskQueues]);

  // Count agents in each zone
  const agentsInZone = useMemo(() => {
    const counts: Partial<Record<ZoneId, number>> = {};
    agentStates.forEach(a => {
      counts[a.currentZone] = (counts[a.currentZone] ?? 0) + 1;
    });
    return counts;
  }, [agentStates]);

  // Active zones (have agents working)
  const activeZones = useMemo(() => {
    return new Set(
      agentStates
        .filter(a => a.movementState === 'working' || a.movementState === 'receiving_task')
        .map(a => a.currentZone)
    );
  }, [agentStates]);

  const handleAgentClick = useCallback((id: AgentId) => {
    setSelectedAgent(prev => prev === id ? null : id);
  }, []);

  const selectedAgentState = selectedAgent ? agentStates.find(a => a.agentId === selectedAgent) : null;

  // Provider health summary
  const onlineProviders = officeData.providerHealth.filter(p => p.status === 'online').length;
  const totalProviders = officeData.providerHealth.length;

  return (
    <div style={{
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      background: '#0d0f1a',
      borderRadius: 16,
      overflow: 'hidden',
      border: '1px solid #1e2a4a',
    }}>

      {/* Header */}
      <div style={{
        padding: '12px 16px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid #1e2a4a',
        background: 'rgba(61,90,241,0.06)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>🏢</span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#e2e8f0' }}>
              Nexus Virtual Office
            </div>
            <div style={{ fontSize: 10, color: '#64748b' }}>
              Living AI workforce simulation · {agentStates.length} agents active
            </div>
          </div>
          {officeData.isDemo && (
            <div style={{
              fontSize: 9, fontWeight: 700, padding: '2px 8px',
              background: 'rgba(245,158,11,0.15)',
              border: '1px solid rgba(245,158,11,0.4)',
              borderRadius: 20, color: '#f59e0b',
            }}>
              DEMO / SIMULATED
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* View mode selector */}
          <div style={{ display: 'flex', gap: 4 }}>
            {(['full', 'trading', 'opportunity', 'system'] as ViewMode[]).map(v => (
              <button
                key={v}
                onClick={() => setViewMode(v)}
                style={{
                  fontSize: 9, fontWeight: 600,
                  padding: '3px 8px', borderRadius: 6,
                  border: '1px solid',
                  borderColor: viewMode === v ? '#3d5af1' : '#1e2a4a',
                  background: viewMode === v ? 'rgba(61,90,241,0.2)' : 'transparent',
                  color: viewMode === v ? '#818cf8' : '#64748b',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  textTransform: 'capitalize',
                }}
              >
                {v === 'full' ? '🗺 Full' : v === 'trading' ? '📊 Trading' : v === 'opportunity' ? '💡 Opps' : '📡 System'}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowRoster(v => !v)}
            style={{
              fontSize: 9, fontWeight: 600, padding: '3px 8px',
              borderRadius: 6, border: '1px solid #1e2a4a',
              background: showRoster ? 'rgba(61,90,241,0.15)' : 'transparent',
              color: showRoster ? '#818cf8' : '#64748b',
              cursor: 'pointer',
            }}
          >
            👥 Roster
          </button>
        </div>
      </div>

      {/* Status bar */}
      <div style={{
        padding: '6px 16px',
        display: 'flex', gap: 16, flexWrap: 'wrap',
        borderBottom: '1px solid #1e2a4a',
        background: 'rgba(0,0,0,0.3)',
      }}>
        <div style={{ fontSize: 10, color: '#64748b' }}>
          <span style={{ color: onlineProviders === totalProviders ? '#22c55e' : '#f59e0b' }}>●</span>
          {' '}{onlineProviders}/{totalProviders} providers online
        </div>
        <div style={{ fontSize: 10, color: '#64748b' }}>
          <span style={{ color: '#3d5af1' }}>●</span>
          {' '}{Object.values(taskQueues).flat().length} tasks queued
        </div>
        {officeData.approvalCount > 0 && (
          <div style={{ fontSize: 10, color: '#ef4444', fontWeight: 700 }}>
            ⚡ {officeData.approvalCount} approval{officeData.approvalCount > 1 ? 's' : ''} needed
          </div>
        )}
        <div style={{ fontSize: 10, color: '#22c55e', marginLeft: 'auto' }}>
          🔒 DRY_RUN=true · LIVE_TRADING=false
        </div>
      </div>

      <div style={{ display: 'flex' }}>
        {/* Office canvas */}
        <div
          ref={canvasRef}
          style={{
            flex: 1,
            position: 'relative',
            height: canvasSize.h,
            background: 'linear-gradient(135deg, #0d0f1a 0%, #0f1424 100%)',
            overflow: 'hidden',
            minHeight: 300,
          }}
        >
          {/* Zone backgrounds */}
          {(Object.entries(ZONES) as [ZoneId, ZoneConfig][]).map(([id, cfg]) => (
            <OfficeZone
              key={id}
              zoneId={id}
              config={cfg}
              canvasW={canvasSize.w}
              canvasH={canvasSize.h}
              activeAgents={agentsInZone[id] ?? 0}
              isActive={activeZones.has(id)}
            />
          ))}

          {/* Walking path lines */}
          <svg
            style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 5 }}
          >
            {agentStates.map(agent => {
              if (!['walking_to_hermes', 'walking_to_department', 'returning_result'].includes(agent.movementState)) return null;
              const from = getZoneCenter(agent.currentZone);
              const to = getZoneCenter(agent.targetZone);
              const cfg = AGENTS[agent.agentId];
              const scaleX = canvasSize.w / 800;
              const scaleY = canvasSize.h / 560;
              return (
                <line
                  key={`path-${agent.agentId}`}
                  x1={from.x * scaleX} y1={from.y * scaleY}
                  x2={to.x * scaleX} y2={to.y * scaleY}
                  stroke={cfg.color}
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  opacity={0.35}
                />
              );
            })}
          </svg>

          {/* Agent avatars */}
          <AnimatePresence>
            {agentStates.map(agent => (
              <AgentAvatar
                key={agent.agentId}
                agent={agent}
                canvasW={canvasSize.w}
                canvasH={canvasSize.h}
                reducedMotion={reducedMotion}
                onClick={handleAgentClick}
              />
            ))}
          </AnimatePresence>
        </div>

        {/* Roster panel */}
        <AnimatePresence>
          {showRoster && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 200, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              style={{
                overflow: 'hidden',
                borderLeft: '1px solid #1e2a4a',
                background: '#0a0c15',
                flexShrink: 0,
              }}
            >
              <div style={{ padding: '12px 10px', minWidth: 200 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Agent Roster
                </div>
                {agentStates.map(agent => {
                  const cfg = AGENTS[agent.agentId];
                  return (
                    <div
                      key={agent.agentId}
                      onClick={() => handleAgentClick(agent.agentId)}
                      style={{
                        padding: '7px 8px',
                        borderRadius: 8,
                        marginBottom: 4,
                        cursor: 'pointer',
                        background: selectedAgent === agent.agentId ? `${cfg.color}22` : 'transparent',
                        border: selectedAgent === agent.agentId ? `1px solid ${cfg.color}55` : '1px solid transparent',
                        transition: 'all 0.15s',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: 14 }}>{cfg.emoji}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 11, fontWeight: 700, color: cfg.color }}>
                            {cfg.name}
                          </div>
                          <div style={{ fontSize: 9, color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {MOVEMENT_LABELS[agent.movementState]}
                          </div>
                        </div>
                        <div style={{
                          width: 7, height: 7, borderRadius: '50%',
                          background: PRIORITY_COLORS[agent.urgency],
                          flexShrink: 0,
                        }} />
                      </div>
                      {agent.currentTask && (
                        <div style={{ fontSize: 9, color: '#475569', marginTop: 3, paddingLeft: 20, lineHeight: 1.3 }}>
                          {agent.currentTask.title.length > 28 ? agent.currentTask.title.slice(0, 28) + '…' : agent.currentTask.title}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Selected agent detail panel */}
      <AnimatePresence>
        {selectedAgentState && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden', borderTop: '1px solid #1e2a4a' }}
          >
            <div style={{
              padding: '12px 16px',
              background: 'rgba(0,0,0,0.4)',
              display: 'flex', gap: 16, flexWrap: 'wrap',
            }}>
              {(() => {
                const cfg = AGENTS[selectedAgentState.agentId];
                return (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 44, height: 44, borderRadius: '50%',
                        background: `${cfg.color}22`,
                        border: `2px solid ${cfg.color}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 20,
                      }}>
                        {cfg.emoji}
                      </div>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: cfg.color }}>{cfg.name}</div>
                        <div style={{ fontSize: 10, color: '#64748b' }}>{cfg.role}</div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      {[
                        { label: 'State', value: MOVEMENT_LABELS[selectedAgentState.movementState] },
                        { label: 'Zone', value: ZONES[selectedAgentState.currentZone].label },
                        { label: 'Urgency', value: selectedAgentState.urgency },
                        { label: 'Queue', value: `${taskQueues[selectedAgentState.agentId]?.length ?? 0} tasks` },
                      ].map(({ label, value }) => (
                        <div key={label}>
                          <div style={{ fontSize: 9, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0', marginTop: 2 }}>{value}</div>
                        </div>
                      ))}
                    </div>

                    {selectedAgentState.currentTask && (
                      <div style={{
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid #1e2a4a',
                        borderRadius: 8, padding: '8px 12px',
                        maxWidth: 280,
                      }}>
                        <div style={{ fontSize: 9, color: '#64748b', marginBottom: 3 }}>Current task</div>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#e2e8f0' }}>
                          {selectedAgentState.currentTask.title}
                        </div>
                        <div style={{ fontSize: 10, color: '#475569', marginTop: 3 }}>
                          {selectedAgentState.currentTask.description}
                        </div>
                        <div style={{ fontSize: 9, color: '#334155', marginTop: 4 }}>
                          Source: {selectedAgentState.currentTask.source}
                        </div>
                      </div>
                    )}

                    {selectedAgentState.destinationReason && (
                      <div style={{ fontSize: 10, color: '#475569', alignSelf: 'center', fontStyle: 'italic' }}>
                        💬 {selectedAgentState.destinationReason}
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer */}
      <div style={{
        padding: '8px 16px',
        borderTop: '1px solid #1e2a4a',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: 'rgba(0,0,0,0.2)',
      }}>
        <div style={{ display: 'flex', gap: 12 }}>
          {[
            { label: 'Working', color: '#22c55e' },
            { label: 'Walking', color: '#3d5af1' },
            { label: 'Blocked', color: '#ef4444' },
            { label: 'Resting', color: '#475569' },
          ].map(({ label, color }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: color }} />
              <span style={{ fontSize: 9, color: '#475569' }}>{label}</span>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 9, color: '#1e2a4a' }}>
          tick #{tick} · 2s interval · Click agent to inspect
        </div>
      </div>
    </div>
  );
}

export default NexusVirtualOffice;
