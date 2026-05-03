import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Loader2, ChevronDown } from 'lucide-react';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthProvider';
import { isFeatureEnabled } from '../lib/featureFlags';

interface ChatMsg {
  id: string;
  content: string;
  is_user: boolean;
  created_at: string;
}

const PAGE_CHIPS: Record<string, string[]> = {
  home:          ['What should I do first?', 'Explain my readiness score', 'How do I improve my funding odds?'],
  'action-center': ['What is my next best action?', 'Help me prioritize tasks', 'Why is this task important?'],
  credit:        ['Explain my utilization', 'Help me dispute this item', 'How does Rental Kharma work?', 'What should I do next?'],
  'business-setup': ['Help me create my LLC', 'How do I get an EIN?', 'Which NAICS code should I use?'],
  funding:       ['Am I ready to apply?', 'Why is this tier locked?', 'Explain approval odds'],
  grants:        ['Am I eligible?', 'What documents do I need?', 'Submit this grant for review'],
  trading:       ['Explain this strategy', 'How do I paper trade?', 'What is the risk?'],
  messages:      ['How do I send a message?', 'Can I talk to a real advisor?'],
};

function timeStr(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

interface FloatingChatProps {
  activeTab: string;
}

export function FloatingChat({ activeTab }: FloatingChatProps) {
  const { user, profile } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  if (!isFeatureEnabled('floating_chat') || !user) return null;

  const chips = PAGE_CHIPS[activeTab] ?? PAGE_CHIPS.home;

  const initConversation = async () => {
    if (conversationId) return conversationId;
    const contactId = 'nexus-support';
    const { data: existing } = await supabase
      .from('chat_conversations')
      .select('*')
      .eq('user_id', user.id)
      .eq('contact_id', contactId)
      .single();
    if (existing) {
      setConversationId(existing.id);
      return existing.id;
    }
    const { data: created } = await supabase
      .from('chat_conversations')
      .insert({
        user_id: user.id,
        contact_id: contactId,
        contact_name: 'Nexus Support',
        contact_role: 'AI Assistant',
        contact_type: 'ai',
      })
      .select()
      .single();
    if (created) {
      setConversationId(created.id);
      return created.id;
    }
    return null;
  };

  const loadMessages = async (convId: string) => {
    const { data } = await supabase
      .from('chat_messages')
      .select('*')
      .eq('conversation_id', convId)
      .order('created_at', { ascending: true })
      .limit(50);
    if (data) {
      setMessages(data.map(m => ({
        id: m.id,
        content: m.content,
        is_user: m.is_user_message,
        created_at: m.created_at,
      })));
    }
  };

  useEffect(() => {
    if (open && !conversationId) {
      initConversation().then(id => { if (id) loadMessages(id); });
    } else if (open && conversationId) {
      loadMessages(conversationId);
    }
  }, [open]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || sending) return;
    setSending(true);
    setInput('');

    const convId = conversationId ?? await initConversation();
    if (!convId) { setSending(false); return; }

    const userName = profile?.full_name ?? user.email?.split('@')[0] ?? 'Client';

    // Insert user message
    const { data: userMsg } = await supabase
      .from('chat_messages')
      .insert({
        conversation_id: convId,
        sender_id: user.id,
        sender_name: userName,
        content: text.trim(),
        is_user_message: true,
      })
      .select()
      .single();

    if (userMsg) {
      setMessages(prev => [...prev, { id: userMsg.id, content: userMsg.content, is_user: true, created_at: userMsg.created_at }]);
    }

    // Update conversation timestamp
    await supabase.from('chat_conversations').update({
      last_message_at: new Date().toISOString(),
    }).eq('id', convId);

    // Auto-acknowledge (AI draft created, admin reviews)
    setTimeout(async () => {
      const ackContent = `Thanks for your message! Our team has received it and will respond shortly. In the meantime, check your Action Center for immediate next steps.`;
      const { data: ackMsg } = await supabase
        .from('chat_messages')
        .insert({
          conversation_id: convId,
          sender_id: 'nexus-support',
          sender_name: 'Nexus Support',
          content: ackContent,
          is_user_message: false,
        })
        .select()
        .single();
      if (ackMsg) {
        setMessages(prev => [...prev, { id: ackMsg.id, content: ackMsg.content, is_user: false, created_at: ackMsg.created_at }]);
      }
      setSending(false);
    }, 800);
  };

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          style={{
            position: 'fixed', bottom: 90, right: 16, zIndex: 300,
            width: 52, height: 52, borderRadius: '50%',
            background: 'linear-gradient(135deg, #3d5af1, #6366f1)',
            border: 'none', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 8px 24px rgba(61,90,241,0.4), 0 2px 8px rgba(0,0,0,0.1)',
            transition: 'all 0.2s',
            color: '#fff',
          }}
          aria-label="Open chat"
        >
          <MessageSquare size={22} />
        </button>
      )}

      {/* Chat drawer */}
      {open && (
        <div style={{
          position: 'fixed', bottom: 90, right: 16, zIndex: 300,
          width: 340, borderRadius: 20,
          background: '#fff',
          border: '1px solid #e8e9f2',
          boxShadow: '0 20px 60px rgba(60,80,180,0.18), 0 4px 16px rgba(0,0,0,0.08)',
          display: 'flex', flexDirection: 'column',
          maxHeight: '70vh',
          overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{
            padding: '14px 16px',
            background: 'linear-gradient(135deg, #3d5af1, #6366f1)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            color: '#fff',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 34, height: 34, borderRadius: 10, background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <MessageSquare size={16} />
              </div>
              <div>
                <p style={{ fontSize: 14, fontWeight: 800, margin: 0 }}>Nexus Support</p>
                <p style={{ fontSize: 11, opacity: 0.8, margin: 0 }}>Typically replies in minutes</p>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              style={{ background: 'rgba(255,255,255,0.2)', border: 'none', cursor: 'pointer', color: '#fff', borderRadius: 8, padding: 6, display: 'flex', alignItems: 'center' }}
            >
              <ChevronDown size={16} />
            </button>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8, minHeight: 200 }}>
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <p style={{ fontSize: 13, color: '#8b8fa8', fontWeight: 500 }}>
                  Hi {profile?.full_name?.split(' ')[0] ?? 'there'}! How can we help?
                </p>
              </div>
            )}
            {messages.map(msg => (
              <div key={msg.id} style={{
                display: 'flex',
                justifyContent: msg.is_user ? 'flex-end' : 'flex-start',
              }}>
                <div style={{
                  maxWidth: '80%',
                  padding: '8px 12px',
                  borderRadius: msg.is_user ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                  background: msg.is_user ? '#3d5af1' : '#f0f4ff',
                  color: msg.is_user ? '#fff' : '#1a1c3a',
                  fontSize: 13, lineHeight: 1.5,
                }}>
                  {msg.content}
                  <div style={{ fontSize: 10, opacity: 0.6, marginTop: 4, textAlign: 'right' }}>
                    {timeStr(msg.created_at)}
                  </div>
                </div>
              </div>
            ))}
            {sending && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <div style={{ padding: '8px 12px', borderRadius: '14px 14px 14px 4px', background: '#f0f4ff', display: 'flex', gap: 4, alignItems: 'center' }}>
                  <Loader2 size={12} color="#3d5af1" style={{ animation: 'spin 1s linear infinite' }} />
                  <span style={{ fontSize: 12, color: '#8b8fa8' }}>Sending...</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Quick chips */}
          <div style={{ padding: '6px 14px', display: 'flex', gap: 6, overflowX: 'auto', borderTop: '1px solid #f0f0f8' }}>
            {chips.slice(0, 3).map(chip => (
              <button
                key={chip}
                onClick={() => sendMessage(chip)}
                style={{
                  flexShrink: 0, padding: '5px 10px', borderRadius: 20,
                  background: '#eef0fd', border: '1px solid #e8e9f2',
                  fontSize: 11, fontWeight: 600, color: '#3d5af1',
                  cursor: 'pointer', whiteSpace: 'nowrap',
                }}
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Input */}
          <div style={{ padding: '10px 14px', borderTop: '1px solid #f0f0f8', display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
              placeholder="Type a message..."
              rows={1}
              style={{
                flex: 1, padding: '8px 12px', borderRadius: 12,
                border: '1.5px solid #e8e9f2', outline: 'none',
                fontSize: 13, color: '#1a1c3a', resize: 'none',
                fontFamily: 'inherit', lineHeight: 1.5,
              }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || sending}
              style={{
                width: 36, height: 36, borderRadius: 10,
                background: '#3d5af1', border: 'none', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff', flexShrink: 0,
                opacity: !input.trim() || sending ? 0.5 : 1,
              }}
            >
              <Send size={15} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
