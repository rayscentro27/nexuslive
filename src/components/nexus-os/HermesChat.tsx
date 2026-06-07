import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send, Loader2, Bot, User, AlertCircle, Info, RefreshCw, Sparkles, Trash2,
} from 'lucide-react';
import { OSCard, Badge, StatusPill, timeAgo } from './shared';
import { useNexusRecommendations } from './useNexusRecommendations';
import type { HermesMessage } from './types';

/**
 * Hermes Chat — routes to the Hermes gateway at 127.0.0.1:8642 via the
 * /.netlify/functions/hermes-chat proxy.
 *
 * If HERMES_GATEWAY_URL is not set on Netlify, the proxy returns a 503
 * and the UI shows a clear "Not connected" state with setup instructions.
 *
 * Provider priority: Hermes gateway (OpenRouter/Ollama) → NOT Claude API by default.
 */

const SYSTEM_PROMPT = `You are Hermes, Ray's Nexus OS executive operator and revenue-focused partner.

Voice: fluent, natural, warm, direct — like an operating partner briefing a founder.
Do NOT sound like a database dump. Never open with "Based on Supabase data". Give the
why before the what. Use "Ray" sparingly. Be practical, not exhaustive.

Recommendation behavior: lead with ONE clear recommendation, then at most 2-3 options
if useful (each with a tradeoff). Identify approval needs. Surface the fastest safe path
to revenue when relevant. If an action is obvious and safe, recommend it; if risky,
recommend preparing an approval instead of executing.

Evidence behavior: when the message includes a "NEXUS OS EVIDENCE" block, treat it as
VERIFIED internal evidence and base your answer on it. Do not invent numbers beyond it.
If no evidence is provided and the question needs it, say what you'd need to check.

Safety: no live trading, publishing, email/outreach, ad spend, deploys, or credential
changes without explicit approval. No earnings/results claims without evidence.`;

const QUICK_PROMPTS = [
  'What broke overnight?',
  'What needs my approval?',
  'Where are we with revenue?',
  'What should I do today to make money?',
  'Check if the trading receiver is working.',
  'What did Claude Code finish?',
  'Summarize the system status.',
  'What content should we publish next?',
];

const HISTORY_KEY = 'nexus-os-hermes-history';
const WELCOME_MSG: HermesMessage = {
  id: 'welcome',
  role: 'assistant',
  content:
    "I'm Hermes, your Nexus OS intelligence layer. Ask me anything about system status, approvals, revenue, trading, or what needs your attention right now.",
  timestamp: new Date().toISOString(),
};

// Load persisted history (role/content/timestamp only — no secrets, no raw evidence).
function loadHistory(): HermesMessage[] {
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    if (!raw) return [WELCOME_MSG];
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) return parsed.slice(-50);
  } catch { /* ignore */ }
  return [WELCOME_MSG];
}

export function HermesChat() {
  const [messages, setMessages] = useState<HermesMessage[]>(loadHistory);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [evidenceUsed, setEvidenceUsed] = useState(false);
  const [health, setHealth] = useState<{ status: 'checking' | 'live' | 'degraded' | 'offline'; detail: string }>({ status: 'checking', detail: 'Checking Hermes connection…' });
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── Health check (fast GET) drives the status pill — proves real connectivity ──
  const checkHealth = useCallback(async () => {
    setHealth({ status: 'checking', detail: 'Checking Hermes connection…' });
    try {
      const res = await fetch('/.netlify/functions/hermes-chat', { method: 'GET', signal: AbortSignal.timeout(9000) });
      const data = await res.json();
      const map: Record<string, string> = {
        netlify_env_missing: 'Netlify env missing (HERMES_GATEWAY_URL).',
        auth_key_missing: 'Netlify env missing (HERMES_API_KEY).',
        origin_unhealthy: 'Gateway reachable but unhealthy.',
        tunnel_timeout: 'Tunnel/origin timed out.',
        tunnel_unreachable: 'Tunnel or local Hermes offline.',
        ok: 'Hermes gateway live.',
      };
      setHealth({ status: data.status ?? 'offline', detail: map[data.reason] ?? data.detail ?? 'Unknown state.' });
    } catch {
      setHealth({ status: 'offline', detail: 'Connection check failed (function unreachable).' });
    }
  }, []);

  useEffect(() => { checkHealth(); }, [checkHealth]);
  const engine = useNexusRecommendations();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Persist chat history (last 50, safe fields only) so it survives section
  // switches and refresh. Never wiped by health checks/retry/evidence changes.
  useEffect(() => {
    try {
      const safe = messages.slice(-50).map(m => ({
        id: m.id, role: m.role, content: m.content, timestamp: m.timestamp,
      }));
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(safe));
    } catch { /* ignore quota errors */ }
  }, [messages]);

  function clearChat() {
    setMessages([WELCOME_MSG]);
    try { window.localStorage.removeItem(HISTORY_KEY); } catch { /* ignore */ }
  }

  const lastSentRef = useRef<string>('');

  async function sendMessage(text?: string) {
    const content = (text ?? input).trim();
    if (!content || sending) return;
    lastSentRef.current = content;
    setInput('');

    const userMsg: HermesMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setSending(true);

    try {
      const history = messages
        .filter(m => m.id !== 'welcome')
        .slice(-10)
        .map(m => ({ role: m.role, content: m.content }));

      // ── Selective retrieval: only fetch internal evidence when the intent needs it ──
      // Map engine intent → function intent key (drives compact prompt + skill summary + token budget)
      const INTENT_MAP: Record<string, string> = {
        revenue_recommendation: 'revenue',
        content_recommendation: 'content',
        next_step: 'next_step',
        blocker_diagnosis: 'next_step',
        approval_summary: 'approvals',
        general: 'general',
      };
      let userContent = content;
      let usedEvidence = false;
      let fnIntent = 'general';
      try {
        const intent = engine.classifyIntent(content);
        fnIntent = INTENT_MAP[intent] ?? 'general';
        if (engine.intentNeedsEvidence(intent)) {
          const rec = await engine.recommend(intent);
          const evidence = engine.buildEvidenceContext(rec);
          userContent = `${evidence}\n\n---\nRay asked: ${content}`;
          usedEvidence = true;
        }
      } catch (e) {
        // If evidence gathering fails, fall back to the plain question — never block the chat
        console.warn('[HermesChat] evidence gather skipped:', e);
      }
      setEvidenceUsed(usedEvidence);

      // Function owns the compact system prompt + skill summary by intent — we no
      // longer send a large system prompt, cutting our share of the context.
      const res = await fetch('/.netlify/functions/hermes-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          intent: fnIntent,
          messages: [...history, { role: 'user', content: userContent }],
        }),
      });

      if (!res.ok) {
        // Parse the specific reason the function returned (accurate, not generic)
        let reason = '', detail = '';
        try { const e = await res.json(); reason = e.reason || e.error || ''; detail = e.detail || ''; } catch { /* noop */ }
        const friendly =
          reason === 'model_timeout' || res.status === 504
            ? '⏱️ Hermes origin timed out. It carries a large context (~20K tokens), so replies can be slow. Tap Retry, or ask a shorter question.'
          : reason === 'auth_failed'
            ? '🔑 Gateway auth failed — the API key was rejected. Check HERMES_API_KEY matches the gateway key.'
          : reason === 'tunnel_unreachable'
            ? '🔌 Hermes origin/tunnel is unreachable. The local Hermes process or Cloudflare tunnel may be down.'
          : reason === 'netlify_env_missing'
            ? '⚙️ Netlify env missing (HERMES_GATEWAY_URL).'
            : `⚠️ Hermes error (${res.status}). ${detail}`;
        setMessages(prev => [...prev, { id: `err-${Date.now()}`, role: 'assistant', content: friendly, timestamp: new Date().toISOString() }]);
        setHealth({ status: res.status === 504 ? 'degraded' : 'offline', detail: detail || friendly });
        return;
      }

      const data = await res.json();
      const reply = data.choices?.[0]?.message?.content ?? 'No response from Hermes.';
      setHealth({ status: 'live', detail: 'Hermes gateway live.' });
      setMessages(prev => [...prev, { id: `a-${Date.now()}`, role: 'assistant', content: reply, timestamp: new Date().toISOString() }]);
    } catch (err) {
      const isTimeout = String(err).includes('Timeout') || String(err).includes('abort');
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`, role: 'assistant',
        content: isTimeout
          ? '⏱️ Request timed out before Hermes replied. Tap Retry or ask a shorter question.'
          : `⚠️ Could not reach Hermes: ${String(err)}`,
        timestamp: new Date().toISOString(),
      }]);
      setHealth({ status: 'degraded', detail: 'Last request did not complete.' });
    } finally {
      setSending(false);
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const pillTone = health.status === 'live' ? 'ok' : health.status === 'degraded' ? 'warn' : health.status === 'offline' ? 'danger' : 'muted';
  const pillLabel = health.status === 'live' ? 'Hermes Live' : health.status === 'degraded' ? 'Hermes Degraded' : health.status === 'offline' ? 'Hermes Offline' : 'Checking…';

  return (
    // Centered, compact chat column — never edge-to-edge. Bottom padding clears the dock.
    <div className="mx-auto w-full max-w-[1000px] flex flex-col h-[calc(100vh-260px)] min-h-[460px]">
      {/* Status row */}
      <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
        <div>
          <h2 className="text-lg sm:text-xl font-black text-[#1A2244] leading-tight">
            Hermes <span className="text-[#5B7CFA]">Chat</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">gpt-5.5 via Cloudflare Tunnel · {health.detail}</p>
        </div>
        <div className="flex items-center gap-2">
          {evidenceUsed && <Badge label="Evidence used" variant="success" />}
          <StatusPill label={pillLabel} tone={pillTone} />
          <button onClick={checkHealth} title="Retry connection"
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-500 text-[11px] font-bold hover:bg-slate-50 transition-all">
            <RefreshCw className={`w-3 h-3 ${health.status === 'checking' ? 'animate-spin' : ''}`} /> Retry
          </button>
          <button onClick={clearChat} title="Clear chat history"
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-500 text-[11px] font-bold hover:bg-red-50 hover:text-red-500 hover:border-red-200 transition-all">
            <Trash2 className="w-3 h-3" /> Clear
          </button>
        </div>
      </div>

      {/* Offline/degraded actionable banner — accurate, never generic */}
      {(health.status === 'offline' || health.status === 'degraded') && (
        <div className={`mb-3 p-3 rounded-xl border flex items-start gap-2 ${health.status === 'offline' ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'}`}>
          <AlertCircle className={`w-4 h-4 shrink-0 mt-0.5 ${health.status === 'offline' ? 'text-red-500' : 'text-amber-500'}`} />
          <div className={`text-xs ${health.status === 'offline' ? 'text-red-700' : 'text-amber-700'}`}>
            <p className="font-bold">{health.status === 'offline' ? 'Hermes offline' : 'Hermes degraded'}</p>
            <p className="mt-0.5">{health.detail}</p>
          </div>
        </div>
      )}

      {/* Chat panel */}
      <OSCard className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
          {sending && (
            <div className="flex items-center gap-2 p-1">
              <div className="w-7 h-7 rounded-full bg-[#5B7CFA] flex items-center justify-center shrink-0">
                <Bot className="w-3.5 h-3.5 text-white" />
              </div>
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Prompt chips + input grouped inside the panel */}
        <div className="border-t border-slate-100 p-3 space-y-2.5">
          <div className="flex gap-1.5 overflow-x-auto pb-0.5 scrollbar-hide">
            {QUICK_PROMPTS.map(p => (
              <button key={p} onClick={() => sendMessage(p)} disabled={sending}
                className="shrink-0 px-2.5 py-1 rounded-full bg-slate-100 hover:bg-blue-50 hover:text-[#5B7CFA] border border-slate-200 text-[11px] font-semibold text-slate-600 transition-all disabled:opacity-40">
                {p}
              </button>
            ))}
          </div>
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              disabled={sending}
              placeholder="Ask Hermes… (Enter to send, Shift+Enter for newline)"
              rows={2}
              // Explicit dark text + caret so typing is visible on the light input in BOTH themes
              // (without this, dark mode inherits white text from .nexus-canvas → invisible typing).
              style={{ color: '#1a2244', caretColor: '#5B7CFA', backgroundColor: '#f8fafc' }}
              className="flex-1 resize-none rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm font-medium placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#5B7CFA]/20 focus:border-[#5B7CFA]/40 disabled:opacity-50 transition-all"
            />
            <button onClick={() => sendMessage()} disabled={sending || !input.trim()}
              className="h-11 w-11 shrink-0 rounded-xl bg-[#5B7CFA] text-white flex items-center justify-center shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] disabled:opacity-40 disabled:cursor-not-allowed transition-all">
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </OSCard>

      <p className="mt-2 flex items-center gap-1.5 text-[10px] text-slate-400">
        <Info className="w-3 h-3 shrink-0" />
        Recommendation prompts pull summarized Nexus evidence; large context means replies can take a few seconds.
      </p>
    </div>
  );
}

function MessageBubble({ msg }: { msg: HermesMessage }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
          isUser ? 'bg-slate-200' : 'bg-[#5B7CFA]'
        }`}
      >
        {isUser ? <User className="w-3.5 h-3.5 text-slate-600" /> : <Sparkles className="w-3.5 h-3.5 text-white" />}
      </div>
      <div className={`max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        <OSCard
          className={`px-4 py-3 ${
            isUser
              ? 'bg-[#5B7CFA] border-[#4A6BEB] text-white'
              : 'bg-white'
          }`}
        >
          <p
            className={`text-sm leading-relaxed whitespace-pre-wrap ${isUser ? 'text-white' : 'text-[#1A2244]'}`}
          >
            {msg.content}
          </p>
        </OSCard>
        <span className="text-[9px] text-slate-400 px-1">{timeAgo(msg.timestamp)}</span>
      </div>
    </div>
  );
}
