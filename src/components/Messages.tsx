import React, { useState, useRef, useEffect } from 'react';
import { Search, Send, MoreVertical, Phone, Video, Paperclip, Smile, Loader2, TrendingUp, Target, Zap, ArrowRight } from 'lucide-react';
import { cn } from '../lib/utils';
import { getChatResponse } from '../services/geminiService';
import { botConfig, BotType } from './BotAvatar';

interface Message {
  id: string;
  sender: string;
  text: string;
  time: string;
  isMe: boolean;
}

const initialContacts = [
  { id: 'advisor', name: 'James Mitchell', role: 'Advisor', avatar: 'https://api.dicebear.com/7.x/notionists/svg?seed=James&backgroundColor=c5c9f7', active: true, type: 'advisor' as BotType },
  { id: 'funding', name: 'Funding Bot', role: 'Capital Strategist', avatar: 'https://picsum.photos/seed/funding/400/400', active: true, type: 'funding' as BotType },
  { id: 'setup', name: 'Setup Bot', role: 'Business Formation', avatar: 'https://picsum.photos/seed/setup/400/400', active: true, type: 'setup' as BotType },
  { id: 'trading', name: 'Trading Bot', role: 'Strategy & Signals', avatar: 'https://picsum.photos/seed/trading/400/400', active: true, type: 'trading' as BotType },
];

export function Messages() {
  const [selectedContact, setSelectedContact] = useState(initialContacts[0]);
  const [msgInput, setMsgInput] = useState('');
  const [chatHistory, setChatHistory] = useState<Record<string, Message[]>>({
    advisor: [
      { id: '1', sender: 'James Mitchell', text: 'Hello! I\'m James, your Capital Strategist. How can I help you scale today?', time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), isMe: false }
    ]
  });
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatHistory, selectedContact.id]);

  const handleSend = async () => {
    if (!msgInput.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'Me',
      text: msgInput,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isMe: true
    };

    const currentHistory = chatHistory[selectedContact.id] || [];
    setChatHistory(prev => ({
      ...prev,
      [selectedContact.id]: [...currentHistory, userMsg]
    }));
    setMsgInput('');
    setIsLoading(true);

    // Format history for Gemini
    const geminiHistory = currentHistory.map(m => ({
      role: m.isMe ? 'user' as const : 'model' as const,
      parts: [{ text: m.text }]
    }));

    const responseText = await getChatResponse(msgInput, selectedContact.role, geminiHistory);

    const botMsg: Message = {
      id: (Date.now() + 1).toString(),
      sender: selectedContact.name,
      text: responseText,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isMe: false
    };

    setChatHistory(prev => ({
      ...prev,
      [selectedContact.id]: [...(prev[selectedContact.id] || []), botMsg]
    }));
    setIsLoading(false);
  };

  const currentMessages = chatHistory[selectedContact.id] || [];

  return (
    <div className="p-4 h-full flex gap-4 overflow-hidden">
      {/* Contacts List - Reduced width by ~20% */}
      <div className="w-52 flex flex-col gap-3 shrink-0">
        <h2 className="text-lg font-black text-[#1A2244] px-1">Messages</h2>
        
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search" 
            className="w-full bg-slate-50 border border-slate-100 rounded-xl py-1.5 pl-9 pr-3 text-[10px] font-bold focus:outline-none focus:ring-4 focus:ring-blue-500/5 transition-all"
          />
        </div>

        <div className="flex-1 glass-card overflow-hidden flex flex-col border-slate-100">
          <div className="p-2.5 border-b border-slate-50 bg-slate-50/50">
            <span className="text-[7px] font-black text-slate-400 uppercase tracking-widest">AI Specialists</span>
          </div>
          <div className="flex-1 overflow-y-auto no-scrollbar">
            {initialContacts.map((contact) => (
              <button
                key={contact.id}
                onClick={() => setSelectedContact(contact)}
                className={cn(
                  "w-full p-2.5 flex gap-2 items-start hover:bg-slate-50 transition-colors border-b border-slate-50",
                  selectedContact.id === contact.id && "bg-blue-50/50"
                )}
              >
                <div className="w-7 h-7 rounded-lg bg-[#C5C9F7] overflow-hidden shrink-0 relative shadow-sm">
                  <img 
                    src={contact.avatar} 
                    alt={contact.name} 
                    className="w-full h-full object-cover"
                  />
                  {contact.active && (
                    <div className="absolute bottom-0 right-0 w-1.5 h-1.5 bg-green-500 border border-white rounded-full" />
                  )}
                </div>
                <div className="flex-1 text-left min-w-0">
                  <p className="text-[10px] font-black text-[#1A2244] truncate">{contact.name}</p>
                  <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest mt-0.5 truncate">{contact.role}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chat Area - Center Panel */}
      <div className="flex-1 glass-card flex flex-col overflow-hidden border-slate-100">
        {/* Chat Header */}
        <div className="p-3 border-b border-slate-100 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#C5C9F7] overflow-hidden shadow-sm">
              <img 
                src={selectedContact.avatar} 
                alt={selectedContact.name} 
                className="w-full h-full object-cover"
              />
            </div>
            <div>
              <p className="text-xs font-black text-[#1A2244] leading-tight">{selectedContact.name}</p>
              <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">{selectedContact.role}</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button className="p-2 text-slate-400 hover:text-[#5B7CFA] hover:bg-slate-50 rounded-lg transition-all"><Phone className="w-3.5 h-3.5" /></button>
            <button className="p-2 text-slate-400 hover:text-[#5B7CFA] hover:bg-slate-50 rounded-lg transition-all"><Video className="w-3.5 h-3.5" /></button>
            <button className="p-2 text-slate-400 hover:text-[#5B7CFA] hover:bg-slate-50 rounded-lg transition-all"><MoreVertical className="w-3.5 h-3.5" /></button>
          </div>
        </div>

        {/* Messages Display */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/30 no-scrollbar">
          {currentMessages.map((msg) => (
            <div key={msg.id} className={cn("flex gap-2.5 max-w-[85%]", msg.isMe ? "ml-auto flex-row-reverse" : "")}>
              {!msg.isMe && (
                <div className="w-7 h-7 rounded-lg bg-[#C5C9F7] overflow-hidden shrink-0 mt-auto shadow-sm">
                  <img 
                    src={selectedContact.avatar} 
                    alt="Avatar" 
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="space-y-1">
                <div className={cn(
                  "p-2.5 rounded-xl text-[11px] font-medium leading-relaxed shadow-sm",
                  msg.isMe 
                    ? "bg-[#5B7CFA] text-white rounded-tr-none" 
                    : "bg-white text-[#1A2244] rounded-tl-none border border-slate-100"
                )}>
                  {msg.text}
                </div>
                <p className={cn("text-[7px] font-black text-slate-400 uppercase tracking-widest", msg.isMe ? "text-right" : "")}>
                  {msg.time}
                </p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-2.5 max-w-[85%]">
              <div className="w-7 h-7 rounded-lg bg-[#C5C9F7] overflow-hidden shrink-0 mt-auto shadow-sm flex items-center justify-center">
                <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
              </div>
              <div className="bg-white text-[#1A2244] p-2.5 rounded-xl rounded-tl-none border border-slate-100 shadow-sm">
                <div className="flex gap-1">
                  <div className="w-1 h-1 bg-slate-300 rounded-full animate-bounce" />
                  <div className="w-1 h-1 bg-slate-300 rounded-full animate-bounce [animation-delay:0.2s]" />
                  <div className="w-1 h-1 bg-slate-300 rounded-full animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area - Sticky at bottom */}
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          className="p-3 bg-white border-t border-slate-100 shrink-0"
        >
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-xl p-1 pl-2 shadow-inner">
            <button type="button" className="text-slate-400 hover:text-[#5B7CFA] transition-colors"><Paperclip className="w-3.5 h-3.5" /></button>
            <input 
              type="text" 
              placeholder="Write a message..." 
              value={msgInput}
              onChange={(e) => setMsgInput(e.target.value)}
              disabled={isLoading}
              className="flex-1 bg-transparent border-none focus:outline-none text-[11px] font-medium py-1.5 disabled:opacity-50"
            />
            <button type="button" className="text-slate-400 hover:text-[#5B7CFA] transition-colors"><Smile className="w-3.5 h-3.5" /></button>
            <button 
              type="submit"
              disabled={!msgInput.trim() || isLoading}
              className="bg-[#5B7CFA] text-white py-1.5 px-3 rounded-lg font-black shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:hover:bg-[#5B7CFA]"
            >
              <span className="text-[10px] uppercase tracking-widest">Send</span>
              <Send className="w-3 h-3" />
            </button>
          </div>
        </form>
      </div>

      {/* Context Panel - Right Panel */}
      <div className="w-60 flex flex-col gap-4 shrink-0">
        <div className="glass-card p-4 space-y-4 border-slate-100 bg-gradient-to-br from-white to-blue-50/20">
          <div className="space-y-1">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">User Readiness</h3>
            <div className="flex items-end justify-between">
              <span className="text-2xl font-black text-[#5B7CFA]">65%</span>
              <span className="text-[9px] font-bold text-green-600 uppercase tracking-widest flex items-center gap-1">
                <TrendingUp className="w-3 h-3" /> +12% this week
              </span>
            </div>
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden mt-1">
              <div className="h-full bg-[#5B7CFA] w-[65%] rounded-full" />
            </div>
          </div>

          <div className="space-y-1.5">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Current Goal</h3>
            <div className="p-2.5 rounded-xl bg-white border border-slate-100 shadow-sm flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA] shrink-0">
                <Target className="w-4 h-4" />
              </div>
              <p className="text-[10px] font-black text-[#1A2244] leading-tight">Unlock $50k Capital</p>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Suggested Actions</h3>
            <div className="space-y-1.5">
              {[
                { label: 'Complete EIN Setup', impact: '+8%' },
                { label: 'Upload ID Docs', impact: '+4%' }
              ].map((action, i) => (
                <button key={i} className="w-full p-2 rounded-lg border border-slate-100 bg-white hover:border-[#5B7CFA]/30 transition-all flex items-center justify-between group">
                  <span className="text-[9px] font-bold text-slate-600">{action.label}</span>
                  <div className="flex items-center gap-1">
                    <span className="text-[8px] font-black text-green-500">{action.impact}</span>
                    <ArrowRight className="w-2.5 h-2.5 text-slate-300 group-hover:text-[#5B7CFA] transition-colors" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="glass-card p-4 flex-1 border-slate-100 bg-slate-50/30 flex flex-col items-center justify-center text-center space-y-2 opacity-60">
          <Zap className="w-6 h-6 text-slate-300" />
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-tight">Advisor notes will appear here</p>
        </div>
      </div>
    </div>
  );
}
