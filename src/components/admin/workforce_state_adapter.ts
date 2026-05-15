/**
 * Maps live backend state (provider_health, analytics_events, etc.)
 * to per-worker visual states for the Workforce Office.
 */

export type WorkerState =
  | 'active'
  | 'researching'
  | 'analyzing'
  | 'idle'
  | 'warning'
  | 'offline';

export interface WorkerStatus {
  id: string;
  label: string;
  emoji: string;
  state: WorkerState;
  statusLine: string;
  department: string;
  latency?: number;
}

export interface DepartmentStatus {
  id: string;
  name: string;
  emoji: string;
  workers: WorkerStatus[];
  isActive: boolean;
}

export interface ProviderHealth {
  provider_name: string;
  status: string;
  avg_latency_ms: number | null;
  last_checked_at: string | null;
}

export interface AnalyticsEvent {
  feature: string | null;
  event_name: string | null;
  created_at: string;
}

export interface ResearchTicket {
  id: string;
  department: string;
  status: string;
  priority: string;
  topic: string;
  created_at: string;
  completed_at: string | null;
}

export interface ResearchTicketSummary {
  total: number;
  open: number;
  overdue: number;          // open for > 24h
  byDepartment: Record<string, number>;
}

export interface WorkforceSnapshotInputs {
  grantCount?: number;
  queuePressure?: number;
  schedulerFailed?: number;
  warnings?: string[];
  demoMode?: boolean;
}

function providerToState(status: string): WorkerState {
  if (status === 'online') return 'active';
  if (status === 'degraded') return 'warning';
  return 'offline';
}

function minutesAgo(ts: string | null): number {
  if (!ts) return 9999;
  return Math.floor((Date.now() - new Date(ts).getTime()) / 60_000);
}

export function summarizeTickets(tickets: ResearchTicket[]): ResearchTicketSummary {
  const open = tickets.filter(t =>
    ['submitted', 'queued', 'researching', 'needs_review'].includes(t.status)
  );
  const now = Date.now();
  const overdue = open.filter(t => (now - new Date(t.created_at).getTime()) > 24 * 60 * 60 * 1000);
  const byDepartment: Record<string, number> = {};
  for (const t of tickets) {
    byDepartment[t.department] = (byDepartment[t.department] ?? 0) + 1;
  }
  return { total: tickets.length, open: open.length, overdue: overdue.length, byDepartment };
}

function ticketStateForDept(dept: string, summary: ResearchTicketSummary): WorkerState {
  const count = summary.byDepartment[dept] ?? 0;
  if (count === 0) return 'idle';
  const overdueOpen = summary.overdue > 0 && (summary.byDepartment[dept] ?? 0) > 0;
  if (overdueOpen) return 'warning';
  return 'researching';
}

function ticketStatusLine(dept: string, summary: ResearchTicketSummary): string {
  const count = summary.byDepartment[dept] ?? 0;
  if (count === 0) return 'No open tickets';
  if (summary.overdue > 0) return `${count} ticket${count > 1 ? 's' : ''} · ⚠️ overdue`;
  return `${count} ticket${count > 1 ? 's' : ''} in progress`;
}

export function buildWorkforceState(
  providers: ProviderHealth[],
  recentEvents: AnalyticsEvent[],
  oppsCount: number,
  tickets: ResearchTicket[] = [],
  transcriptQueueCount = 0,
  extras: WorkforceSnapshotInputs = {},
): DepartmentStatus[] {
  const ticketSummary = summarizeTickets(tickets);
  const providerMap = Object.fromEntries(providers.map(p => [p.provider_name, p]));

  const recentFeatures = new Set(
    recentEvents
      .filter(e => minutesAgo(e.created_at) < 60)
      .map(e => e.feature)
      .filter(Boolean)
  );

  const hermes = providerMap['claude_cli'] || providerMap['ollama'];
  const hermesState: WorkerState = hermes
    ? providerToState(hermes.status)
    : 'idle';

  const grantCount = Math.max(0, extras.grantCount ?? 0);
  const queuePressure = Math.max(0, extras.queuePressure ?? transcriptQueueCount);
  const schedulerFailed = Math.max(0, extras.schedulerFailed ?? 0);
  const warningCount = (extras.warnings || []).length;
  const demoMode = Boolean(extras.demoMode);

  const departments: DepartmentStatus[] = [
    {
      id: 'hermes_operations',
      name: 'Hermes Operations',
      emoji: '🎯',
      isActive: hermesState === 'active' || queuePressure > 0,
      workers: [
        {
          id: 'hermes',
          label: 'Hermes',
          emoji: '🤖',
          state: hermesState,
          statusLine: hermesState === 'active' ? 'Monitoring operations' : hermesState === 'idle' ? 'On standby' : 'Check connection',
          department: 'hermes_operations',
          latency: hermes?.avg_latency_ms ?? undefined,
        },
        {
          id: 'anomaly',
          label: 'Anomaly Detector',
          emoji: '🔬',
          state: recentFeatures.size > 0 ? 'active' : 'idle',
          statusLine: recentFeatures.size > 0 ? 'Running 30-min scans' : 'Awaiting fresh events',
          department: 'hermes_operations',
        },
        {
          id: 'ingestion_queue',
          label: 'Ingestion Queue',
          emoji: '📥',
          state: transcriptQueueCount > 0 ? 'researching' : 'idle',
          statusLine: queuePressure > 0
            ? `${queuePressure} source${queuePressure > 1 ? 's' : ''} waiting`
            : 'No queued sources',
          department: 'hermes_operations',
        },
        {
          id: 'provider_health',
          label: 'Provider Monitor',
          emoji: '📡',
          state: providers.length > 0 ? 'active' : 'idle',
          statusLine: providers.length > 0 ? `${providers.filter(p => p.status === 'online').length}/${providers.length} online` : 'No data yet',
          department: 'hermes_operations',
        },
      ],
    },
    {
      id: 'funding_intelligence',
      name: 'Funding Intelligence',
      emoji: '💰',
      isActive: recentFeatures.has('funding') || recentFeatures.has('credit'),
      workers: [
        {
          id: 'user_intel',
          label: 'User Intelligence',
          emoji: '🧠',
          state: 'active',
          statusLine: 'Scoring users every 2h',
          department: 'funding',
        },
        {
          id: 'credit_worker',
          label: 'Credit Analyst',
          emoji: '📊',
          state: recentFeatures.has('credit') ? 'analyzing' : 'idle',
          statusLine: recentFeatures.has('credit') ? 'Processing credit events' : 'Waiting for activity',
          department: 'funding',
        },
        {
          id: 'funding_readiness',
          label: 'Funding Readiness',
          emoji: '💵',
          state: recentFeatures.has('funding') ? 'active' : 'idle',
          statusLine: recentFeatures.has('funding') ? 'Funding events detected' : 'Standby',
          department: 'funding',
        },
        {
          id: 'funding_research_tickets',
          label: 'Research Queue',
          emoji: '📋',
          state: ticketStateForDept('funding_intelligence', ticketSummary),
          statusLine: ticketStatusLine('funding_intelligence', ticketSummary),
          department: 'funding',
        },
      ],
    },
    {
      id: 'business_opportunities',
      name: 'Business Opportunities',
      emoji: '🔭',
      isActive: oppsCount > 0,
      workers: [
        {
          id: 'opp_research',
          label: 'Opportunity Worker',
          emoji: '🔭',
          state: oppsCount > 0 ? 'researching' : 'idle',
          statusLine: oppsCount > 0 ? `${oppsCount} opps scored` : 'Pending first run',
          department: 'business_opportunities',
        },
        {
          id: 'opp_validator',
          label: 'Nexus Validator',
          emoji: '✅',
          state: oppsCount > 0 ? 'active' : 'idle',
          statusLine: oppsCount > 0 ? 'Validating catalog' : 'No data yet',
          department: 'business_opportunities',
        },
        {
          id: 'opp_research_tickets',
          label: 'Research Queue',
          emoji: '📋',
          state: ticketStateForDept('business_opportunities', ticketSummary),
          statusLine: ticketStatusLine('business_opportunities', ticketSummary),
          department: 'business_opportunities',
        },
      ],
    },
    {
      id: 'grant_research',
      name: 'Grant Research',
      emoji: '🏆',
      isActive: recentFeatures.has('grants') || grantCount > 0,
      workers: [
        {
          id: 'grant_worker',
          label: 'Grant Finder',
          emoji: '🏆',
          state: recentFeatures.has('grants') || grantCount > 0 ? 'researching' : ticketStateForDept('grants_research', ticketSummary),
          statusLine: grantCount > 0 ? `${grantCount} grants tracked` : ticketStatusLine('grants_research', ticketSummary),
          department: 'grant_research',
        },
        {
          id: 'grant_research_tickets',
          label: 'Research Queue',
          emoji: '📋',
          state: ticketStateForDept('grants_research', ticketSummary),
          statusLine: ticketStatusLine('grants_research', ticketSummary),
          department: 'grant_research',
        },
      ],
    },
    {
      id: 'trading_intelligence',
      name: 'Trading Intelligence',
      emoji: '📈',
      isActive: recentFeatures.has('trading'),
      workers: [
        {
          id: 'paper_trading',
          label: 'Paper Trading',
          emoji: '📈',
          state: recentFeatures.has('trading') ? 'active' : 'idle',
          statusLine: demoMode ? 'Demo / Simulated mode active' : 'Paper mode — no real funds',
          department: 'trading_intelligence',
        },
        {
          id: 'strategy_engine',
          label: 'Strategy Engine',
          emoji: '⚙️',
          state: 'idle',
          statusLine: 'NEXUS_DRY_RUN=true',
          department: 'trading_intelligence',
        },
      ],
    },
    {
      id: 'credit_intelligence',
      name: 'Credit Intelligence',
      emoji: '💳',
      isActive: recentFeatures.has('credit') || (ticketSummary.byDepartment.credit_research ?? 0) > 0,
      workers: [
        {
          id: 'credit_signal_mapper',
          label: 'Credit Signal Mapper',
          emoji: '🧮',
          state: recentFeatures.has('credit') ? 'analyzing' : 'idle',
          statusLine: recentFeatures.has('credit') ? 'Refreshing credit factors' : 'Awaiting credit deltas',
          department: 'credit_intelligence',
        },
        {
          id: 'credit_ticket_queue',
          label: 'Research Queue',
          emoji: '📋',
          state: ticketStateForDept('credit_research', ticketSummary),
          statusLine: ticketStatusLine('credit_research', ticketSummary),
          department: 'credit_intelligence',
        },
      ],
    },
    {
      id: 'marketing_intelligence',
      name: 'Marketing Intelligence',
      emoji: '📣',
      isActive: recentFeatures.has('marketing') || (ticketSummary.byDepartment.marketing_intelligence ?? 0) > 0,
      workers: [
        {
          id: 'campaign_scout',
          label: 'Campaign Scout',
          emoji: '📣',
          state: recentFeatures.has('marketing') ? 'researching' : ticketStateForDept('marketing_intelligence', ticketSummary),
          statusLine: recentFeatures.has('marketing') ? 'Campaign intelligence updating' : ticketStatusLine('marketing_intelligence', ticketSummary),
          department: 'marketing_intelligence',
        },
      ],
    },
    {
      id: 'system_monitoring',
      name: 'System Monitoring',
      emoji: '🛡️',
      isActive: schedulerFailed > 0 || warningCount > 0 || providers.length > 0,
      workers: [
        {
          id: 'scheduler_guard',
          label: 'Scheduler Guard',
          emoji: '⏱️',
          state: schedulerFailed > 0 ? 'warning' : 'active',
          statusLine: schedulerFailed > 0 ? `${schedulerFailed} failed runs` : 'Scheduler healthy',
          department: 'system_monitoring',
        },
        {
          id: 'warning_triage',
          label: 'Warning Triage',
          emoji: '🚨',
          state: warningCount > 0 ? 'warning' : 'idle',
          statusLine: warningCount > 0 ? `${warningCount} operational warnings` : 'No active warnings',
          department: 'system_monitoring',
        },
      ],
    },
    {
      id: 'ai_providers',
      name: 'AI Providers',
      emoji: '🔌',
      isActive: providers.some(p => p.status === 'online'),
      workers: providers.slice(0, 4).map(p => ({
        id: p.provider_name,
        label: p.provider_name.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()),
        emoji: { ollama: '🧠', groq: '⚡', openrouter: '🔀', claude_cli: '🤖', codex: '📝', opencode: '💻', notebooklm: '📚' }[p.provider_name] || '🔌',
        state: providerToState(p.status),
        statusLine: p.status === 'online' ? `Online${p.avg_latency_ms ? ` · ${p.avg_latency_ms}ms` : ''}` : p.status,
        department: 'ai_providers',
        latency: p.avg_latency_ms ?? undefined,
      })),
    },
  ];

  return departments;
}
