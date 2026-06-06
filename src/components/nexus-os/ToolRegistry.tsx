import React, { useState } from 'react';
import {
  Cpu, Bot, Globe, Database, Server, Zap, ShieldCheck, AlertTriangle,
  ExternalLink, ChevronDown, ChevronUp,
} from 'lucide-react';
import { OSCard, StatusDot, Badge, MockLabel } from './shared';
import type { ToolRegistryEntry } from './types';

// Static registry — auto-discovery not yet implemented.
// Future: pull live status from Supabase nexus_os_tool_registry table.
const REGISTRY: ToolRegistryEntry[] = [
  {
    id: 'hermes',
    name: 'Hermes Gateway',
    type: 'agent',
    status: 'unknown',
    best_use: 'Primary AI orchestration, multi-model routing, Telegram, memory, scheduling',
    cost_level: 'low',
    auth_method: 'API key (config.yaml extra.key)',
    allowed_actions: ['chat', 'tool_use', 'schedule', 'telegram_message', 'memory_write'],
    approval_required: false,
    log_path: '~/nexus-ai/logs/hermes_gateway.log',
    notes: 'Runs on 127.0.0.1:8642. OpenRouter meta-llama/llama-3.3-70b. Launchd managed.',
    last_success: null,
    last_failure: null,
  },
  {
    id: 'claude-code',
    name: 'Claude Code',
    type: 'ai_model',
    status: 'online',
    best_use: 'Code generation, refactoring, file editing, complex reasoning',
    cost_level: 'medium',
    auth_method: 'Anthropic API key',
    allowed_actions: ['code', 'edit_files', 'explain', 'review'],
    approval_required: false,
    notes: 'claude-sonnet-4-6 active. Use via CLI or MCP server.',
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    type: 'platform',
    status: 'online',
    best_use: 'Model routing for Hermes (llama-3.3-70b-instruct, 128K context)',
    cost_level: 'low',
    auth_method: 'OpenRouter API key (via Hermes config)',
    allowed_actions: ['chat', 'completions'],
    approval_required: false,
    notes: 'Primary provider for Hermes. Handles 128K context without hitting limits.',
  },
  {
    id: 'supabase',
    name: 'Supabase',
    type: 'service',
    status: 'online',
    best_use: 'Auth, database, real-time subscriptions, storage, RLS',
    cost_level: 'low',
    auth_method: 'anon key (frontend) / service role (backend only)',
    allowed_actions: ['read', 'write', 'subscribe'],
    approval_required: false,
    log_path: 'Supabase Dashboard → Logs',
    notes: 'Project ygqglfbhxiumqdisauar. 50+ tables. RLS on all user data.',
  },
  {
    id: 'telegram',
    name: 'Telegram Bot',
    type: 'integration',
    status: 'unknown',
    best_use: 'Notifications, approval requests, status updates to Ray',
    cost_level: 'free',
    auth_method: 'TELEGRAM_BOT_TOKEN env var',
    allowed_actions: ['send_message', 'receive_commands'],
    approval_required: false,
    log_path: '~/telegram-integration.log',
    notes: 'Runs via Hermes platform. 409 conflict fix: clear TELEGRAM_BOT_TOKEN from ~/.hermes/.env, wait 70s, reload.',
  },
  {
    id: 'oracle-vm',
    name: 'Oracle VM (Ampere)',
    type: 'service',
    status: 'unknown',
    best_use: 'Local LLM hosting (qwen2.5:14b via Ollama), API worker, nexus-llm-worker',
    cost_level: 'free',
    auth_method: 'SSH key ~/.ssh/oracle_vm',
    allowed_actions: ['llm_inference', 'api_worker', 'storage'],
    approval_required: false,
    notes: '161.153.40.41 — 4 OCPU / 24GB RAM. Often unreachable (100% packet loss). Restart from Oracle Cloud console.',
  },
  {
    id: 'vibe-trading',
    name: 'Vibe-Trading',
    type: 'integration',
    status: 'online',
    best_use: 'Paper trading simulation, backtesting, EUR/USD RSI(14) research',
    cost_level: 'free',
    auth_method: 'Local venv, MCP server',
    allowed_actions: ['backtest', 'paper_trade', 'signal_research'],
    approval_required: true,
    log_path: '~/nexus-ai/integrations/vibe_trading/',
    notes: 'EDUCATION/PAPER ONLY. No live execution. venv at integrations/vibe_trading/.venv',
  },
  {
    id: 'oanda',
    name: 'Oanda (Paper/Practice)',
    type: 'service',
    status: 'limited',
    best_use: 'Paper trading practice account. EUR/USD, GBP/USD, USD/JPY',
    cost_level: 'free',
    auth_method: 'Oanda practice API key (trading_config.json — ROTATE_THIS_KEY)',
    allowed_actions: ['paper_trade', 'market_data', 'account_info'],
    approval_required: true,
    notes: 'Account 101-001-27557105-003. api-fxpractice.oanda.com. live_trading=false. DO NOT flip to live.',
  },
  {
    id: 'netlify',
    name: 'Netlify',
    type: 'platform',
    status: 'online',
    best_use: 'Frontend hosting, serverless functions (nexus-api proxy, stripe-webhook)',
    cost_level: 'low',
    auth_method: 'Netlify dashboard',
    allowed_actions: ['deploy', 'function_exec', 'env_vars'],
    approval_required: true,
    notes: 'Functions: nexus-api.js, stripe-webhook.js, admin-invite.js. Deploy requires approval.',
  },
  {
    id: 'stripe',
    name: 'Stripe',
    type: 'service',
    status: 'online',
    best_use: 'Subscription billing, plan management, webhooks',
    cost_level: 'medium',
    auth_method: 'Stripe secret key (Netlify env var)',
    allowed_actions: ['read_subscriptions', 'create_checkout'],
    approval_required: true,
    notes: 'Webhook at /netlify/functions/stripe-webhook. Subscription plans: free/pro/elite.',
  },
  {
    id: 'gemini',
    name: 'Gemini API (Google)',
    type: 'ai_model',
    status: 'online',
    best_use: 'Multimodal analysis, document understanding, business opportunities',
    cost_level: 'low',
    auth_method: '@google/genai SDK (GEMINI_API_KEY)',
    allowed_actions: ['chat', 'analyze', 'research'],
    approval_required: false,
    notes: 'Used in geminiService.ts. Configured as alternative model for certain features.',
  },
  {
    id: 'nexus-claw3d',
    name: 'Claw3D',
    type: 'integration',
    status: 'unknown',
    best_use: '3D visual agent office / workforce visualization',
    cost_level: 'free',
    auth_method: 'Local',
    allowed_actions: ['visualize'],
    approval_required: false,
    log_path: '~/nexus-claw3d/',
    notes: 'Integrated at ~/nexus-claw3d. Reference visual layer for workforce.',
  },
];

export function ToolRegistry() {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  const types = ['all', 'agent', 'ai_model', 'platform', 'service', 'integration'];

  const filtered = REGISTRY.filter(t => {
    const matchSearch = !search ||
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.best_use.toLowerCase().includes(search.toLowerCase());
    const matchType = typeFilter === 'all' || t.type === typeFilter;
    return matchSearch && matchType;
  });

  function toggleExpand(id: string) {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const onlineCount = REGISTRY.filter(t => t.status === 'online').length;
  const unknownCount = REGISTRY.filter(t => t.status === 'unknown').length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Tool <span className="text-[#5B7CFA]">Registry</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5 flex items-center gap-2">
            {onlineCount} online · {unknownCount} unknown · <MockLabel />
            <span className="text-slate-300">|</span>
            <span>Status auto-check: not yet wired</span>
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search tools..."
          className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#5B7CFA]/20 w-48"
        />
        {types.map(t => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
              typeFilter === t
                ? 'bg-[#5B7CFA] text-white shadow'
                : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Registry list */}
      <div className="space-y-2">
        {filtered.map(tool => (
          <ToolCard
            key={tool.id}
            tool={tool}
            expanded={expanded.has(tool.id)}
            onToggle={() => toggleExpand(tool.id)}
          />
        ))}
      </div>
    </div>
  );
}

function ToolCard({
  tool,
  expanded,
  onToggle,
}: {
  tool: ToolRegistryEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  const TypeIcon = {
    agent: Bot,
    ai_model: Cpu,
    platform: Globe,
    service: Server,
    integration: Zap,
  }[tool.type] ?? Cpu;

  const costColor = {
    free: 'text-green-600',
    low: 'text-blue-500',
    medium: 'text-amber-500',
    high: 'text-red-500',
  }[tool.cost_level] ?? 'text-slate-400';

  return (
    <OSCard>
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-50/50 transition-colors"
      >
        <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center shrink-0 text-slate-500">
          <TypeIcon className="w-4.5 h-4.5 w-[18px] h-[18px]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-bold text-[#1A2244]">{tool.name}</p>
            <StatusDot status={tool.status} />
            <span className="text-[10px] text-slate-400">{tool.status}</span>
            <Badge label={tool.type} variant="default" />
            {tool.approval_required && (
              <Badge label="Approval Required" variant="warn" />
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{tool.best_use}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-[10px] font-bold uppercase ${costColor}`}>{tool.cost_level}</span>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4 space-y-3">
          <Row label="Best Use" value={tool.best_use} />
          <Row label="Auth" value={tool.auth_method} />
          <Row label="Cost" value={tool.cost_level} />
          <div className="flex items-start gap-2">
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest w-24 shrink-0 mt-0.5">Allowed Actions</span>
            <div className="flex flex-wrap gap-1">
              {tool.allowed_actions.map(a => (
                <span key={a} className="px-2 py-0.5 rounded-full bg-slate-100 text-[10px] font-semibold text-slate-600">{a}</span>
              ))}
            </div>
          </div>
          {tool.log_path && <Row label="Log Path" value={tool.log_path} mono />}
          {tool.notes && (
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Notes</p>
              <p className="text-xs text-slate-500">{tool.notes}</p>
            </div>
          )}
          {tool.approval_required && (
            <div className="flex items-center gap-2 p-2 rounded-lg bg-amber-50 border border-amber-200">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              <p className="text-[10px] font-bold text-amber-700">Actions with this tool require explicit approval</p>
            </div>
          )}
        </div>
      )}
    </OSCard>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest w-24 shrink-0 mt-0.5">{label}</span>
      <span className={`text-xs text-slate-600 ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  );
}
