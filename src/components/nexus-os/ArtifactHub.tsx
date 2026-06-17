import React, { useEffect, useState } from 'react';
import {
  BookOpen, Sparkles, CheckCircle2, AlertTriangle, FileText,
  Loader2, Search, Tag, Clock, ChevronDown, ChevronUp,
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { OSSection, Badge, ConfidenceBar, timeAgo, EmptyState } from './shared';
import type { KnowledgeItem } from './types';

export function ArtifactHub() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  async function load() {
    setLoading(true);
    const { data } = await supabase
      .from('nexus_knowledge_items')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(50);
    if (data) setItems(data as KnowledgeItem[]);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  function toggleExpand(id: string) {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const categories = ['all', ...Array.from(new Set(items.map(i => i.category)))];

  const filtered = items.filter(i => {
    const matchSearch = !search ||
      i.source_title.toLowerCase().includes(search.toLowerCase()) ||
      i.summary.toLowerCase().includes(search.toLowerCase()) ||
      i.category.toLowerCase().includes(search.toLowerCase());
    const matchCat = categoryFilter === 'all' || i.category === categoryFilter;
    return matchSearch && matchCat;
  });

  const approved = items.filter(i => i.approved_for_user_display).length;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Artifact <span className="text-[#5B7CFA]">Hub</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            {items.length} items · {approved} approved for display · From Supabase <code>nexus_knowledge_items</code>
          </p>
        </div>
      </div>

      {/* Search + filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search knowledge..."
            className="pl-8 pr-3 py-1.5 rounded-xl border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#5B7CFA]/20 w-52"
          />
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {categories.map(c => (
            <button
              key={c}
              onClick={() => setCategoryFilter(c)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                categoryFilter === c
                  ? 'bg-[#5B7CFA] text-white'
                  : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Knowledge items */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-slate-300" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState icon={BookOpen} message="No knowledge items found" />
      ) : (
        <div className="space-y-2">
          {filtered.map(item => (
            <KnowledgeCard
              key={item.id}
              item={item}
              expanded={expanded.has(item.id)}
              onToggle={() => toggleExpand(item.id)}
            />
          ))}
        </div>
      )}

      {/* Knowledge graph schema info */}
      <OSSection title="Knowledge Graph Schema" icon={Sparkles}>
        <div className="space-y-3">
          <div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Entity Types</p>
            <div className="flex flex-wrap gap-1.5">
              {[
                'source', 'transcript', 'artifact', 'task', 'agent', 'tool',
                'workflow', 'skill', 'rule', 'client', 'campaign', 'trading_strategy',
                'approval', 'blocker', 'failure', 'decision', 'metric', 'output', 'prompt', 'sop',
              ].map(e => (
                <span key={e} className="px-2 py-0.5 rounded-full bg-slate-100 text-[10px] font-semibold text-slate-600">{e}</span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Relationship Types</p>
            <div className="flex flex-wrap gap-1.5">
              {[
                'produced_by', 'belongs_to', 'supports', 'depends_on', 'blocked_by',
                'approved_by', 'tested_by', 'improves', 'replaces', 'contradicts',
                'deployed_to', 'related_to',
              ].map(r => (
                <span key={r} className="px-2 py-0.5 rounded-full bg-blue-50 text-[10px] font-semibold text-blue-600">{r}</span>
              ))}
            </div>
          </div>
          <p className="text-[10px] text-slate-400 italic">
            Migration for nexus_os_entities + nexus_os_relationships tables is in the migration file.
            Apply via Supabase SQL editor after review.
          </p>
        </div>
      </OSSection>
    </div>
  );
}

function KnowledgeCard({
  item,
  expanded,
  onToggle,
}: {
  item: KnowledgeItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  const takeaways = Array.isArray(item.key_takeaways)
    ? item.key_takeaways
    : typeof item.key_takeaways === 'string'
    ? JSON.parse(item.key_takeaways as unknown as string)
    : [];

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-start gap-3 px-5 py-4 text-left hover:bg-slate-50/50 transition-colors"
      >
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
          item.approved_for_user_display ? 'bg-green-50' : 'bg-slate-100'
        }`}>
          {item.approved_for_user_display
            ? <CheckCircle2 className="w-4 h-4 text-green-500" />
            : <Clock className="w-4 h-4 text-slate-400" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-bold text-[#1A2244] line-clamp-1">{item.source_title}</p>
            <Badge label={item.source_type} variant="default" />
            <Badge label={item.category} variant="info" />
            {item.approved_for_user_display && <Badge label="Approved" variant="success" />}
          </div>
          <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{item.summary}</p>
          <div className="flex items-center gap-3 mt-1">
            {item.confidence_score !== null && item.confidence_score !== undefined && (
              <ConfidenceBar score={item.confidence_score} />
            )}
            <p className="text-[10px] text-slate-400">{timeAgo(item.created_at)}</p>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-slate-400 shrink-0 mt-1" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400 shrink-0 mt-1" />
        )}
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4 space-y-3">
          <div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Summary</p>
            <p className="text-sm text-slate-700 leading-relaxed">{item.summary}</p>
          </div>

          {takeaways.length > 0 && (
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Key Takeaways</p>
              <ul className="space-y-1.5">
                {takeaways.map((t: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-slate-600">
                    <span className="text-[#5B7CFA] font-bold shrink-0 mt-0.5">→</span>
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {item.confidence_score !== null && item.confidence_score !== undefined && (
            <div className="flex items-center gap-2">
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Confidence</p>
              <ConfidenceBar score={item.confidence_score} />
            </div>
          )}

          {item.approved_for_user_display === false && (
            <div className="flex items-center gap-2 p-2 rounded-lg bg-amber-50 border border-amber-100">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              <p className="text-[10px] text-amber-700">Not yet approved for user display</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
