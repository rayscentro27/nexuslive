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

function providerToState(status: string): WorkerState {
  if (status === 'online') return 'active';
  if (status === 'degraded') return 'warning';
  return 'offline';
}

function minutesAgo(ts: string | null): number {
  if (!ts) return 9999;
  return Math.floor((Date.now() - new Date(ts).getTime()) / 60_000);
}

export function buildWorkforceState(
  providers: ProviderHealth[],
  recentEvents: AnalyticsEvent[],
  oppsCount: number,
): DepartmentStatus[] {
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

  const departments: DepartmentStatus[] = [
    {
      id: 'ops',
      name: 'Operations Center',
      emoji: '🎯',
      isActive: hermesState === 'active',
      workers: [
        {
          id: 'hermes',
          label: 'Hermes',
          emoji: '🤖',
          state: hermesState,
          statusLine: hermesState === 'active' ? 'Monitoring operations' : hermesState === 'idle' ? 'On standby' : 'Check connection',
          department: 'ops',
          latency: hermes?.avg_latency_ms ?? undefined,
        },
        {
          id: 'anomaly',
          label: 'Anomaly Detector',
          emoji: '🔬',
          state: 'active',
          statusLine: 'Running 30-min scans',
          department: 'ops',
        },
        {
          id: 'provider_health',
          label: 'Provider Monitor',
          emoji: '📡',
          state: providers.length > 0 ? 'active' : 'idle',
          statusLine: providers.length > 0 ? `${providers.filter(p => p.status === 'online').length}/${providers.length} online` : 'No data yet',
          department: 'ops',
        },
      ],
    },
    {
      id: 'funding',
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
      ],
    },
    {
      id: 'opportunities',
      name: 'Opportunity Research',
      emoji: '🔭',
      isActive: oppsCount > 0,
      workers: [
        {
          id: 'opp_research',
          label: 'Opportunity Worker',
          emoji: '🔭',
          state: oppsCount > 0 ? 'researching' : 'idle',
          statusLine: oppsCount > 0 ? `${oppsCount} opps scored` : 'Pending first run',
          department: 'opportunities',
        },
        {
          id: 'opp_validator',
          label: 'Nexus Validator',
          emoji: '✅',
          state: oppsCount > 0 ? 'active' : 'idle',
          statusLine: oppsCount > 0 ? 'Validating catalog' : 'No data yet',
          department: 'opportunities',
        },
      ],
    },
    {
      id: 'grants',
      name: 'Grant Research',
      emoji: '🏆',
      isActive: recentFeatures.has('grants'),
      workers: [
        {
          id: 'grant_worker',
          label: 'Grant Finder',
          emoji: '🏆',
          state: recentFeatures.has('grants') ? 'researching' : 'idle',
          statusLine: recentFeatures.has('grants') ? 'Grant searches active' : 'Standby',
          department: 'grants',
        },
      ],
    },
    {
      id: 'trading',
      name: 'Trading Lab',
      emoji: '📈',
      isActive: recentFeatures.has('trading'),
      workers: [
        {
          id: 'paper_trading',
          label: 'Paper Trading',
          emoji: '📈',
          state: recentFeatures.has('trading') ? 'active' : 'idle',
          statusLine: 'Demo mode — no real funds',
          department: 'trading',
        },
        {
          id: 'strategy_engine',
          label: 'Strategy Engine',
          emoji: '⚙️',
          state: 'idle',
          statusLine: 'NEXUS_DRY_RUN=true',
          department: 'trading',
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
