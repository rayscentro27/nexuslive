import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare, Instagram, Send, RefreshCw, Zap, AlertCircle, Bot, Clock, Circle
} from 'lucide-react';
import { cn } from '../../lib/utils';

const PAGE_TOKEN = import.meta.env.VITE_META_PAGE_ACCESS_TOKEN || '';
const PAGE_ID = import.meta.env.VITE_META_PAGE_ID || '';
const IG_ID = import.meta.env.VITE_META_IG_ACCOUNT_ID || '';

type Channel = 'messenger' | 'instagram';

interface Conversation {
  id: string;
  name: string;
  snippet: string;
  updated: string;
  unread: number;
  channel: Channel;
  recipientId?: string;
}

interface Message {
  id: string;
  from: string;
  message: string;
  created_time: string;
  isOwn: boolean;
}

async function apiFetch(url: string) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

async function fetchMessengerConversations(): Promise<Conversation[]> {
  if (!PAGE_TOKEN || !PAGE_ID) return [];
  const data = await apiFetch(
    `https://graph.facebook.com/v19.0/${PAGE_ID}/conversations?fields=id,participants,snippet,updated_time,unread_count&access_token=${PAGE_TOKEN}`
  );
  if (!data?.data) return [];
  return data.data.map((c: any) => {
    const other = c.participants?.data?.find((p: any) => p.id !== PAGE_ID);
    return {
      id: c.id,
      name: other?.name || 'Unknown',
      snippet: c.snippet || '',
      updated: c.updated_time,
      unread: c.unread_count || 0,
      channel: 'messenger' as Channel,
      recipientId: other?.id,
    };
  });
}

async function fetchInstagramConversations(): Promise<Conversation[]> {
  if (!PAGE_TOKEN || !IG_ID) return [];
  const data = await apiFetch(
    `https://graph.facebook.com/v19.0/${IG_ID}/conversations?fields=id,participants,snippet,updated_time,unread_count&platform=instagram&access_token=${PAGE_TOKEN}`
  );
  if (!data?.data) return [];
  return data.data.map((c: any) => {
    const other = c.participants?.data?.find((p: any) => p.id !== IG_ID);
    return {
      id: c.id,
      name: other?.name || other?.username || 'Unknown',
      snippet: c.snippet || '',
      updated: c.updated_time,
      unread: c.unread_count || 0,
      channel: 'instagram' as Channel,
      recipientId: other?.id,
    };
  });
}

async function fetchMessages(convId: string): Promise<Message[]> {
  if (!PAGE_TOKEN) return [];
  const data = await apiFetch(
    `https://graph.facebook.com/v19.0/${convId}/messages?fields=id,from,message,created_time&access_token=${PAGE_TOKEN}`
  );
  if (!data?.data) return [];
  return data.data.map((m: any) => ({
    id: m.id,
    from: m.from?.name || 'Unknown',
    message: m.message || '',
    created_time: m.created_time,
    isOwn: m.from?.id === PAGE_ID || m.from?.id === IG_ID,
  })).reverse();
}

async function sendReply(recipientId: string, text: string, channel: Channel): Promise<boolean> {
  if (!PAGE_TOKEN || !recipientId) return false;
  const senderId = channel === 'instagram' ? IG_ID : PAGE_ID;
  try {
    const r = await fetch(`https://graph.facebook.com/v19.0/${senderId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${PAGE_TOKEN}` },
      body: JSON.stringify({ recipient: { id: recipientId }, message: { text }, messaging_type: 'RESPONSE' }),
    });
    return r.ok;
  } catch { return false; }
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function getAISuggestion(message: string): string {
  const lower = message.toLowerCase();
  if (lower.match(/hi|hello|hey/)) return "Hi! Thanks for reaching out to Nexus. I'm here to help you access business funding, build credit, and grow your company. How can I assist you today?";
  if (lower.match(/fund|loan|grant|capital|credit/)) return "Great question! Nexus can match you with grants, SBA loans, and credit lines based on your business profile. I'd love to set up a free consultation — are you available this week?";
  if (lower.match(/price|cost|how much|plan/)) return "We have plans starting free, with Pro at $50/mo including AI grant matching and priority advisor access, and Elite at $100/mo for dedicated capital strategist support. Want the full details?";
  if (lower.match(/schedule|call|meet|book/)) return "Absolutely! I can connect you with one of our capital strategists. What's your timezone and the best time to reach you?";
  return "Thanks for your message! A Nexus team member will follow up shortly. In the meantime, explore your options at nexuslive.netlify.app";
}

export function AdminMessaging() {
  const [channel, setChannel] = useState<Channel>('messenger');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [reply, setReply] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState('');
  const [autoReply, setAutoReply] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isConfigured = !!(PAGE_TOKEN && PAGE_ID);

  useEffect(() => { loadConversations(); }, [channel]);

  useEffect(() => {
    if (selected) loadMessages(selected.id);
  }, [selected?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    if (messages.length > 0) {
      const last = messages[messages.length - 1];
      if (!last.isOwn) {
        const suggestion = getAISuggestion(last.message);
        setAiSuggestion(suggestion);
        if (autoReply && selected?.recipientId) {
          sendReply(selected.recipientId, suggestion, channel).then(ok => {
            if (ok) setMessages(prev => [...prev, { id: Date.now().toString(), from: 'Nexus AI', message: suggestion, created_time: new Date().toISOString(), isOwn: true }]);
          });
        }
      }
    }
  }, [messages]);

  async function loadConversations() {
    setLoading(true);
    setError('');
    const convs = channel === 'messenger' ? await fetchMessengerConversations() : await fetchInstagramConversations();
    setConversations(convs);
    if (convs.length > 0 && !selected) setSelected(convs[0]);
    setLoading(false);
  }

  async function loadMessages(convId: string) {
    const msgs = await fetchMessages(convId);
    setMessages(msgs);
  }

  async function handleSend(text = reply) {
    if (!text.trim() || !selected?.recipientId) return;
    setSending(true);
    setError('');
    const ok = await sendReply(selected.recipientId, text, channel);
    if (ok) {
      setMessages(prev => [...prev, { id: Date.now().toString(), from: 'You', message: text, created_time: new Date().toISOString(), isOwn: true }]);
      setReply('');
      setAiSuggestion('');
    } else {
      setError('Send failed — token may need refreshing');
    }
    setSending(false);
  }

  return (
    <div className="flex h-full bg-slate-50/50 overflow-hidden">
      {/* Conversations panel */}
      <div className="w-80 bg-white border-r border-slate-200 flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-100">
          <h2 className="text-sm font-black text-[#1A2244] mb-3">Social Inbox</h2>
          <div className="flex gap-2">
            {(['messenger', 'instagram'] as Channel[]).map(ch => (
              <button key={ch} onClick={() => { setChannel(ch); setSelected(null); setMessages([]); }}
                className={cn(
                  "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
                  channel === ch
                    ? ch === 'messenger' ? "bg-blue-500 text-white" : "bg-gradient-to-r from-purple-500 to-pink-500 text-white"
                    : "bg-slate-50 text-slate-400 hover:bg-slate-100"
                )}>
                {ch === 'messenger' ? <MessageSquare className="w-3 h-3" /> : <Instagram className="w-3 h-3" />}
                {ch === 'messenger' ? 'Messenger' : 'Instagram'}
              </button>
            ))}
          </div>
        </div>

        <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="w-3.5 h-3.5 text-[#5B7CFA]" />
            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">AI Auto-Reply</span>
          </div>
          <div onClick={() => setAutoReply(v => !v)}
            className={cn("w-9 h-5 rounded-full cursor-pointer transition-colors", autoReply ? "bg-[#5B7CFA]" : "bg-slate-200")}>
            <div className={cn("w-4 h-4 bg-white rounded-full shadow mt-0.5 transition-transform", autoReply ? "translate-x-4" : "translate-x-0.5")} />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {!isConfigured && (
            <div className="p-5 text-center">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 text-amber-400" />
              <p className="text-xs text-slate-500 font-medium">Add Meta env vars to Netlify to connect your inbox.</p>
              <p className="text-[10px] text-slate-400 mt-2 font-mono">VITE_META_PAGE_ACCESS_TOKEN<br />VITE_META_PAGE_ID<br />VITE_META_IG_ACCOUNT_ID</p>
            </div>
          )}
          {loading && <div className="flex justify-center py-12"><RefreshCw className="w-5 h-5 text-[#5B7CFA] animate-spin" /></div>}
          {!loading && isConfigured && conversations.length === 0 && (
            <div className="p-6 text-center text-xs text-slate-400 font-medium">No conversations yet</div>
          )}
          {conversations.map(conv => (
            <button key={conv.id} onClick={() => setSelected(conv)}
              className={cn("w-full p-4 flex items-start gap-3 border-b border-slate-50 text-left transition-all", selected?.id === conv.id ? "bg-blue-50" : "hover:bg-slate-50")}>
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#5B7CFA] to-[#4A6BEB] flex items-center justify-center text-white text-xs font-black shrink-0">
                {conv.name[0]?.toUpperCase() || '?'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-black text-[#1A2244] truncate">{conv.name}</span>
                  <span className="text-[9px] text-slate-400 font-medium shrink-0 ml-1">{timeAgo(conv.updated)}</span>
                </div>
                <p className="text-[10px] text-slate-400 truncate font-medium">{conv.snippet || 'No preview'}</p>
              </div>
              {conv.unread > 0 && (
                <span className="w-4 h-4 bg-[#5B7CFA] text-white text-[8px] font-black rounded-full flex items-center justify-center shrink-0">{conv.unread}</span>
              )}
            </button>
          ))}
        </div>

        <button onClick={loadConversations}
          className="p-3 border-t border-slate-100 flex items-center justify-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest hover:text-[#5B7CFA] hover:bg-slate-50 transition-all">
          <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Thread panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {!selected ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-3">
              <MessageSquare className="w-12 h-12 text-slate-200 mx-auto" />
              <p className="text-sm font-black text-slate-400">Select a conversation</p>
              <p className="text-xs text-slate-300 font-medium">Your {channel} messages will appear here</p>
            </div>
          </div>
        ) : (
          <>
            <div className="px-6 py-4 bg-white border-b border-slate-200 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#5B7CFA] to-[#4A6BEB] flex items-center justify-center text-white text-sm font-black">
                  {selected.name[0]?.toUpperCase()}
                </div>
                <div>
                  <h3 className="text-sm font-black text-[#1A2244]">{selected.name}</h3>
                  <div className="flex items-center gap-1.5">
                    {selected.channel === 'messenger' ? <MessageSquare className="w-3 h-3 text-blue-500" /> : <Instagram className="w-3 h-3 text-pink-500" />}
                    <span className="text-[10px] text-slate-400 font-medium capitalize">{selected.channel}</span>
                    <Circle className="w-1.5 h-1.5 fill-green-400 text-green-400" />
                    <span className="text-[10px] text-green-500 font-bold">Active</span>
                  </div>
                </div>
              </div>
              <button onClick={() => loadMessages(selected.id)} className="p-2 text-slate-400 hover:text-[#5B7CFA] hover:bg-blue-50 rounded-xl transition-all">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-3">
              {messages.length === 0 && <div className="text-center text-xs text-slate-400 py-8">No messages loaded — click refresh</div>}
              {messages.map(msg => (
                <div key={msg.id} className={cn("flex gap-2 max-w-[75%]", msg.isOwn ? "ml-auto flex-row-reverse" : "")}>
                  {!msg.isOwn && (
                    <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-xs font-black text-slate-500 shrink-0 mt-1">
                      {msg.from[0]?.toUpperCase()}
                    </div>
                  )}
                  <div>
                    <div className={cn("px-4 py-2.5 rounded-2xl text-sm font-medium leading-relaxed",
                      msg.isOwn ? "bg-[#5B7CFA] text-white rounded-tr-sm" : "bg-white border border-slate-200 text-slate-700 rounded-tl-sm shadow-sm"
                    )}>{msg.message}</div>
                    <div className={cn("flex items-center gap-1 mt-1", msg.isOwn ? "justify-end" : "")}>
                      <Clock className="w-2.5 h-2.5 text-slate-300" />
                      <span className="text-[9px] text-slate-300 font-medium">{timeAgo(msg.created_time)}</span>
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {aiSuggestion && (
              <div className="mx-4 mb-2 p-3 bg-blue-50 border border-blue-100 rounded-xl flex items-start gap-3">
                <div className="w-6 h-6 rounded-lg bg-[#5B7CFA] flex items-center justify-center shrink-0">
                  <Zap className="w-3 h-3 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[9px] font-black text-[#5B7CFA] uppercase tracking-widest mb-1">AI Suggested Reply</p>
                  <p className="text-xs text-slate-600 font-medium leading-relaxed">{aiSuggestion}</p>
                </div>
                <button onClick={() => { setReply(aiSuggestion); setAiSuggestion(''); }}
                  className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest shrink-0 hover:underline px-2 py-1 bg-white rounded-lg border border-blue-100">
                  Use
                </button>
              </div>
            )}

            {error && (
              <div className="mx-4 mb-2 p-3 bg-red-50 border border-red-100 rounded-xl text-xs text-red-600 font-medium flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />{error}
              </div>
            )}

            <div className="p-4 bg-white border-t border-slate-200 shrink-0">
              <div className="flex gap-3">
                <textarea value={reply} onChange={e => setReply(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                  placeholder={`Reply via ${selected.channel}… (Enter to send)`}
                  rows={2}
                  className="flex-1 px-4 py-3 border border-slate-200 rounded-2xl text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#5B7CFA]/30 resize-none" />
                <button onClick={() => handleSend()} disabled={sending || !reply.trim()}
                  className="w-12 h-12 bg-[#5B7CFA] text-white rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all disabled:opacity-50 self-end">
                  {sending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-[9px] text-slate-400 font-medium mt-2 text-center">
                AI Auto-Reply is {autoReply ? <span className="text-green-500">ON</span> : <span className="text-slate-400">OFF</span>}
                {autoReply && ' — Nexus AI will respond to new messages automatically'}
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
