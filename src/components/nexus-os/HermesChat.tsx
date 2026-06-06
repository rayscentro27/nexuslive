import React, { useState, useRef, useEffect } from 'react';
import {
  Send, Loader2, Bot, User, AlertCircle, Info, ChevronRight, Sparkles,
} from 'lucide-react';
import { OSCard, Badge, timeAgo } from './shared';
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

export function HermesChat() {
  const [messages, setMessages] = useState<HermesMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "I'm Hermes, your Nexus OS intelligence layer. Ask me anything about system status, approvals, revenue, trading, or what needs your attention right now.",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'unknown' | 'connected' | 'offline'>('unknown');
  const [evidenceUsed, setEvidenceUsed] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const engine = useNexusRecommendations();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function sendMessage(text?: string) {
    const content = (text ?? input).trim();
    if (!content || sending) return;
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
      let userContent = content;
      let usedEvidence = false;
      try {
        const intent = engine.classifyIntent(content);
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

      const res = await fetch('/.netlify/functions/hermes-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          system: SYSTEM_PROMPT,
          messages: [...history, { role: 'user', content: userContent }],
        }),
      });

      if (res.status === 503) {
        setConnectionStatus('offline');
        const assistantMsg: HermesMessage = {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content:
            '⚠️ Hermes gateway is not reachable. Make sure the gateway is running and `HERMES_GATEWAY_URL` is set in your Netlify env vars.\n\n**To connect:**\n1. Start Hermes: `launchctl load ~/Library/LaunchAgents/ai.hermes.gateway.plist`\n2. Set `HERMES_GATEWAY_URL=http://localhost:8642` in `.env`\n3. Set `HERMES_API_KEY=<key from ~/.hermes/config.yaml>`',
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, assistantMsg]);
        return;
      }

      if (!res.ok) {
        throw new Error(`Gateway error ${res.status}`);
      }

      setConnectionStatus('connected');
      const data = await res.json();
      const reply = data.choices?.[0]?.message?.content ?? 'No response from Hermes.';

      const assistantMsg: HermesMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: reply,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      const errMsg: HermesMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Error reaching Hermes: ${String(err)}`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errMsg]);
      setConnectionStatus('offline');
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

  return (
    <div className="flex flex-col h-[calc(100vh-220px)] min-h-[500px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Hermes <span className="text-[#5B7CFA]">Chat</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Routes to Hermes gateway (OpenRouter/Ollama) via local proxy
          </p>
        </div>
        <div className="flex items-center gap-2">
          {evidenceUsed && <Badge label="Evidence used" variant="success" />}
          <ConnectionBadge status={connectionStatus} />
        </div>
      </div>

      {/* Not-connected notice */}
      {connectionStatus === 'offline' && (
        <div className="mb-3 p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-700">
            <p className="font-bold">Hermes gateway not reachable</p>
            <p className="mt-0.5">Set <code className="bg-amber-100 px-1 rounded">HERMES_GATEWAY_URL</code> and <code className="bg-amber-100 px-1 rounded">HERMES_API_KEY</code> in Netlify env vars.</p>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {messages.map(msg => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        {sending && (
          <div className="flex items-center gap-2 p-3">
            <div className="w-7 h-7 rounded-full bg-[#5B7CFA] flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="flex gap-1">
              {[0, 1, 2].map(i => (
                <div
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts */}
      <div className="mt-3 flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {QUICK_PROMPTS.map(p => (
          <button
            key={p}
            onClick={() => sendMessage(p)}
            disabled={sending}
            className="shrink-0 px-3 py-1.5 rounded-full bg-slate-100 hover:bg-blue-50 hover:text-[#5B7CFA] border border-slate-200 text-[11px] font-semibold text-slate-600 transition-all disabled:opacity-40"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="mt-3 flex items-end gap-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={sending}
          placeholder="Ask Hermes anything... (Enter to send, Shift+Enter for new line)"
          rows={2}
          className="flex-1 resize-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-[#5B7CFA]/20 focus:border-[#5B7CFA]/40 disabled:opacity-50 transition-all"
        />
        <button
          onClick={() => sendMessage()}
          disabled={sending || !input.trim()}
          className="h-12 w-12 shrink-0 rounded-2xl bg-[#5B7CFA] text-white flex items-center justify-center shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>

      {/* Setup info */}
      <div className="mt-3 flex items-center gap-1.5 text-[10px] text-slate-400">
        <Info className="w-3 h-3 shrink-0" />
        <span>Hermes uses OpenRouter (meta-llama/llama-3.3-70b). Set <code>HERMES_GATEWAY_URL</code> + <code>HERMES_API_KEY</code> to connect.</span>
      </div>
    </div>
  );
}

function ConnectionBadge({ status }: { status: 'unknown' | 'connected' | 'offline' }) {
  if (status === 'connected') return <Badge label="Hermes Connected" variant="success" />;
  if (status === 'offline') return <Badge label="Not Connected" variant="danger" />;
  return <Badge label="Checking..." variant="default" />;
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
