import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Heart,
  Code,
  Plus,
  Building2,
  MessageSquare,
  MessageCircle,
  Mail,
  CheckCircle2,
  Clock,
  Lock,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';
import { GrantResearchRequest } from './GrantResearchRequest';
import { supabase } from '../lib/supabase';
import { useAnalytics } from '../hooks/useAnalytics';

interface CatalogGrant {
  id: string;
  title: string;
  description: string | null;
  grantor: string | null;
  category: string;
  amount_min: number | null;
  amount_max: number | null;
  deadline: string | null;
  official_url: string | null;
  eligibility: string | null;
  states: string[] | null;
}

function formatAmount(min: number | null, max: number | null) {
  if (!min && !max) return 'Varies';
  if (!max) return `$${min!.toLocaleString()}+`;
  if (!min) return `Up to $${max.toLocaleString()}`;
  if (min === max) return `$${min.toLocaleString()}`;
  return `$${min.toLocaleString()} – $${max.toLocaleString()}`;
}

const CATEGORIES = ['All', 'federal', 'state', 'local', 'nonprofit', 'business'];

const STATIC_GRANTS: CatalogGrant[] = [
  { id: 's1', title: 'Women Entrepreneurs Fund',    description: 'Funding for women-owned small businesses.',  grantor: 'SBA', category: 'federal',   amount_min: 5000,  amount_max: 25000,  deadline: null, official_url: null, eligibility: 'Women-owned businesses', states: null },
  { id: 's2', title: 'Small Business Growth Grant', description: 'For businesses under 5 years old.',          grantor: 'NASE', category: 'nonprofit', amount_min: 10000, amount_max: 50000,  deadline: null, official_url: null, eligibility: 'Businesses under 5 years', states: null },
  { id: 's3', title: 'Minority Business Initiative', description: 'Minority-owned business development fund.', grantor: 'MBDA', category: 'federal',   amount_min: 15000, amount_max: 15000,  deadline: null, official_url: null, eligibility: 'Minority-owned businesses', states: null },
  { id: 's4', title: 'InnovateTech Startup Grant',  description: 'Tech startups in STEM sectors.',             grantor: 'NSF',  category: 'federal',   amount_min: 25000, amount_max: 100000, deadline: null, official_url: null, eligibility: 'STEM-focused startups', states: null },
];

export function GrantsFinder() {
  const { emit } = useAnalytics();
  const [activeSection,   setActiveSection]   = useState<'grants' | 'research'>('grants');
  const [catalogGrants,   setCatalogGrants]   = useState<CatalogGrant[]>([]);
  const [loading,         setLoading]         = useState(true);
  const [search,          setSearch]          = useState('');
  const [activeCategory,  setActiveCategory]  = useState('All');

  useEffect(() => {
    supabase.from('grants_catalog').select('*').eq('is_active', true).order('created_at', { ascending: false }).limit(40)
      .then(({ data }) => {
        setCatalogGrants(data && data.length > 0 ? (data as CatalogGrant[]) : STATIC_GRANTS);
        setLoading(false);
      });
  }, []);

  const visibleGrants = catalogGrants.filter(g => {
    const matchesCategory = activeCategory === 'All' || g.category === activeCategory;
    const matchesSearch = !search || g.title.toLowerCase().includes(search.toLowerCase()) || (g.grantor ?? '').toLowerCase().includes(search.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const opportunities = visibleGrants.slice(0, 4).map(g => ({
    title: g.title,
    date: g.deadline ? new Date(g.deadline).toLocaleDateString() : 'Open',
    amount: formatAmount(g.amount_min, g.amount_max),
    status: 'In-Progress' as const,
  }));
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto h-full flex flex-col">
      <div className="flex items-center justify-between shrink-0">
        <div className="space-y-0.5">
          <h2 className="text-2xl font-bold text-[#1A2244]">Grants Finder</h2>
          <p className="text-xs text-slate-500 font-medium">Discover and apply for grants to grow your business.</p>
        </div>
        <button className="bg-[#5B7CFA] text-white px-6 py-2 rounded-xl text-xs font-bold shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Save Search
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide space-y-6 pr-1">
        {/* Hero Banner */}
        <div className="glass-card p-6 flex flex-col md:flex-row items-center justify-between bg-gradient-to-br from-blue-50 to-purple-50 border-slate-100 overflow-hidden relative shrink-0">
          <div className="space-y-4 relative z-10 max-w-2xl">
            <h3 className="text-2xl font-black text-[#1A2244] leading-tight">
              30 new grant opportunities found <br />
              <span className="text-[#5B7CFA]">for ACE Resources LLC</span>
            </h3>
            <p className="text-xs text-slate-500 font-medium leading-relaxed">Based on your business profile and funding needs, we've identified high-potential grants you qualify for.</p>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map(cat => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={cn(
                    "px-3 py-1 rounded-lg text-[8px] font-bold uppercase tracking-widest transition-all",
                    activeCategory === cat
                      ? "bg-[#5B7CFA] text-white"
                      : "bg-white text-slate-600 border border-slate-100 shadow-sm hover:bg-slate-50"
                  )}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
          <div className="w-32 h-32 relative z-10 mt-4 md:mt-0">
            <BotAvatar type="grants" size="xl" className="bg-transparent shadow-none" />
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex gap-3 shrink-0">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search grants by title or grantor..."
              className="w-full bg-white border border-slate-200 rounded-xl py-2.5 pl-10 pr-4 text-xs font-medium focus:outline-none focus:ring-4 focus:ring-blue-500/5 transition-all shadow-sm"
            />
          </div>
          <button className="p-2.5 bg-white border border-slate-200 text-slate-400 hover:text-[#5B7CFA] rounded-xl shadow-sm transition-all"><Heart className="w-5 h-5" /></button>
          <button className="px-4 py-2.5 bg-white border border-slate-200 text-slate-700 hover:text-[#5B7CFA] flex items-center gap-2 rounded-xl shadow-sm transition-all">
            <Code className="w-4 h-4" />
            <span className="text-xs font-bold">Code</span>
          </button>
        </div>

        {/* Recommended Grants Grid */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-[#1A2244]">
              {activeCategory === 'All' ? 'Recommended Grants' : `${activeCategory.charAt(0).toUpperCase() + activeCategory.slice(1)} Grants`}
            </h3>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{visibleGrants.length} results</span>
          </div>

          {loading ? (
            <div className="py-12 flex justify-center">
              <Loader2 className="animate-spin text-slate-400" size={24} />
            </div>
          ) : visibleGrants.length === 0 ? (
            <div className="py-12 text-center">
              <Search className="w-8 h-8 text-slate-300 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No grants match your search. Try a different term or category.</p>
            </div>
          ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {visibleGrants.map((grant) => (
              <div key={grant.id} className="glass-card p-4 flex gap-4 group hover:border-[#5B7CFA]/30 transition-all">
                <div className="w-20 h-20 rounded-xl bg-[#eef0fd] overflow-hidden shrink-0 relative shadow-md flex items-center justify-center">
                  <Building2 className="w-8 h-8 text-[#5B7CFA]" />
                </div>
                <div className="flex-1 space-y-2">
                  <div className="space-y-0.5">
                    <h4 className="text-xs font-bold text-[#1A2244] line-clamp-2">{grant.title}</h4>
                    {grant.grantor && <p className="text-[10px] text-slate-400">{grant.grantor}</p>}
                    <p className="text-lg font-black text-[#1A2244]">{formatAmount(grant.amount_min, grant.amount_max)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-widest bg-[#eef0fd] text-[#3d5af1]">
                      {grant.category}
                    </span>
                    {grant.deadline && (
                      <span className="px-2 py-0.5 rounded-md text-[8px] font-bold bg-amber-50 text-amber-600">
                        Due {new Date(grant.deadline).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-50">
                    <p className="text-[8px] text-slate-400 font-medium">{grant.states?.join(', ') || 'Nationwide'}</p>
                    {grant.official_url ? (
                      <a
                        href={grant.official_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={() => emit('grant_viewed', { event_name: 'grant_apply_clicked', feature: 'grants', metadata: { grant_id: grant.id, grant_title: grant.title, category: grant.category } })}
                        className="px-4 py-1.5 text-[10px] font-black rounded-lg bg-[#5B7CFA] text-white shadow-blue-500/10 hover:bg-[#4A6BEB] transition-all flex items-center gap-1"
                      >
                        Apply <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    ) : (
                      <button className="px-4 py-1.5 text-[10px] font-black rounded-lg bg-slate-100 text-slate-400 cursor-default">
                        View
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          )}
        </div>

        {/* Bottom Section: Opportunities & Saved */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 glass-card p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#1A2244]">Grant Opportunities</h3>
              <span className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">Recent Updates</span>
            </div>
            <div className="space-y-3">
              {opportunities.map((opp, idx) => (
                <div key={idx} className="flex items-center gap-4 p-4 bg-slate-50 border border-slate-100 rounded-xl hover:bg-white hover:border-slate-200 transition-all group cursor-pointer">
                  <div className="w-10 h-10 rounded-lg bg-white border border-slate-100 flex items-center justify-center shrink-0 shadow-sm">
                    <Building2 className="w-5 h-5 text-[#5B7CFA]" />
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-bold text-[#1A2244] group-hover:text-[#5B7CFA] transition-colors">{opp.title}</p>
                    <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">{opp.date}</p>
                  </div>
                  <div className="text-right space-y-1">
                    <p className="text-xs font-black text-[#1A2244]">{opp.amount}</p>
                    <span className={cn(
                      "px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-widest inline-block",
                      opp.status === 'In-Progress' ? "bg-blue-50 text-[#5B7CFA]" : 
                      opp.status === 'Registered' ? "bg-green-50 text-green-600" : 
                      "bg-amber-50 text-amber-600"
                    )}>
                      {opp.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#1A2244]">Saved Grants</h3>
              <button className="text-[8px] font-bold text-[#5B7CFA] uppercase tracking-widest hover:underline">View All</button>
            </div>
            <div className="space-y-4">
              {opportunities.map((opp, idx) => (
                <div key={idx} className="flex items-center gap-3 group cursor-pointer">
                  <div className="w-10 h-10 rounded-lg bg-slate-50 flex items-center justify-center shrink-0 border border-slate-100 group-hover:bg-white transition-colors">
                    <Building2 className="w-5 h-5 text-slate-300 group-hover:text-[#5B7CFA]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-bold text-[#1A2244] truncate group-hover:text-[#5B7CFA] transition-colors">{opp.title}</p>
                    <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">{opp.date} • <span className="text-green-600">In-Progress</span></p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* AI Assistant Banner */}
        <div className="glass-card p-6 flex flex-col lg:flex-row items-center justify-between bg-white border-slate-100 shadow-xl shrink-0">
          <div className="flex flex-col md:flex-row items-center gap-6 text-center md:text-left">
            <div className="w-20 h-20 bg-[#C5C9F7] rounded-2xl flex items-center justify-center shrink-0 overflow-hidden shadow-lg">
              <img 
                src="https://api.dicebear.com/7.x/bottts-neutral/svg?seed=NexusBotSmall&backgroundColor=c5c9f7&eyes=frame2" 
                alt="Bot" 
                className="w-14 h-14 object-contain drop-shadow-2xl"
              />
            </div>
            <div className="space-y-3">
              <h3 className="text-xl font-black text-[#1A2244] leading-tight">
                Our AI Assistant <br />
                <span className="text-[#5B7CFA] font-bold text-lg">can guide you through the process.</span>
              </h3>
              <div className="flex flex-wrap justify-center md:justify-start gap-2">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-100 rounded-lg shadow-sm hover:bg-white transition-colors">
                  <Mail className="w-3 h-3 text-[#5B7CFA]" />
                  <span className="text-[8px] font-bold text-[#1A2244] uppercase tracking-widest">Email</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-100 rounded-lg shadow-sm hover:bg-white transition-colors">
                  <MessageSquare className="w-3 h-3 text-[#5B7CFA]" />
                  <span className="text-[8px] font-bold text-[#1A2244] uppercase tracking-widest">SMS</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-100 rounded-lg shadow-sm hover:bg-white transition-colors">
                  <MessageCircle className="w-3 h-3 text-[#5B7CFA]" />
                  <span className="text-[8px] font-bold text-[#1A2244] uppercase tracking-widest">WhatsApp</span>
                </div>
              </div>
            </div>
          </div>
          <button className="mt-4 lg:mt-0 bg-[#5B7CFA] text-white px-6 py-3 rounded-xl text-sm font-black shadow-xl shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">
            Talk to Your AI
          </button>
        </div>
      </div>

      {/* Grant Research Request section */}
      <div style={{ background: '#fff', borderRadius: 20, padding: 24, border: '1px solid #e8e9f2', boxShadow: '0 2px 8px rgba(60,80,180,0.06)' }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button
            onClick={() => setActiveSection('grants')}
            style={{ padding: '7px 16px', borderRadius: 20, border: '1.5px solid', cursor: 'pointer', fontSize: 12, fontWeight: 700, background: activeSection === 'grants' ? '#3d5af1' : '#fff', color: activeSection === 'grants' ? '#fff' : '#3d5af1', borderColor: activeSection === 'grants' ? '#3d5af1' : '#c7d2fe' }}
          >Catalog</button>
          <button
            onClick={() => setActiveSection('research')}
            style={{ padding: '7px 16px', borderRadius: 20, border: '1.5px solid', cursor: 'pointer', fontSize: 12, fontWeight: 700, background: activeSection === 'research' ? '#3d5af1' : '#fff', color: activeSection === 'research' ? '#fff' : '#3d5af1', borderColor: activeSection === 'research' ? '#3d5af1' : '#c7d2fe' }}
          >Research Requests</button>
        </div>
        {activeSection === 'research' && <GrantResearchRequest />}
        {activeSection === 'grants' && (
          <div style={{ padding: '24px 0', textAlign: 'center' }}>
            <p style={{ fontSize: 14, color: '#8b8fa8', marginBottom: 12 }}>Browse curated grants in the main view above, or submit a custom research request.</p>
            <button
              onClick={() => setActiveSection('research')}
              style={{ padding: '10px 24px', borderRadius: 10, border: 'none', background: '#3d5af1', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}
            >Request Custom Grant Research</button>
          </div>
        )}
      </div>
    </div>
  );
}
