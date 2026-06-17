import React, { useEffect, useState, useCallback } from 'react';
import {
  Network, Loader2, RefreshCw, Plus, Link2, Search, Database,
  GitBranch, AlertTriangle, CheckCircle2, Archive, Trash2, Info, Sparkles,
} from 'lucide-react';
import { OSSection, OSCard, Badge, timeAgo, EmptyState } from './shared';
import { useKnowledgeGraphActions } from './useKnowledgeGraphActions';
import type { GraphEntity, GraphRelationship, GraphRelationshipType } from './types';

const ENTITY_TYPE_FILTERS = ['all', 'revenue_campaign', 'content_item', 'source', 'approval', 'decision', 'lesson', 'tool'];

const LINK_RELATIONSHIPS: GraphRelationshipType[] = [
  'belongs_to_campaign', 'generated_from_source', 'created_content_for',
  'requires_approval', 'supports', 'blocks', 'derived_from', 'resulted_in',
  'learned_from', 'references', 'related_to', 'recommended_by_hermes',
];

export function KnowledgeGraph() {
  const [entities, setEntities] = useState<GraphEntity[]>([]);
  const [relationships, setRelationships] = useState<GraphRelationship[]>([]);
  const [orphans, setOrphans] = useState<{ campaigns: number; content: number; sources: number; approvals: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [entityFilter, setEntityFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [relFilter, setRelFilter] = useState('all');

  // Link builder state
  const [linkFrom, setLinkFrom] = useState('');
  const [linkTo, setLinkTo] = useState('');
  const [linkRel, setLinkRel] = useState<GraphRelationshipType>('related_to');
  const [linkMsg, setLinkMsg] = useState<string | null>(null);

  const kg = useKnowledgeGraphActions();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [e, r, o] = await Promise.all([
        kg.fetchEntities(false),
        kg.fetchRelationships(),
        kg.findOrphans().catch(() => null),
      ]);
      setEntities(e);
      setRelationships(r);
      setOrphans(o);
    } catch (err) {
      console.error('[KnowledgeGraph] load error:', err);
    } finally {
      setLoading(false);
    }
  }, [kg]);

  useEffect(() => { load(); }, [load]);

  const entityName = useCallback((id: string) => {
    const e = entities.find(x => x.id === id);
    return e ? (e.title || e.name) : id.slice(0, 8);
  }, [entities]);

  async function runSync(kind: 'campaigns' | 'content' | 'sources' | 'approvals') {
    setSyncing(kind);
    setSyncMsg(null);
    try {
      const fn = {
        campaigns: kg.syncCampaigns, content: kg.syncContent,
        sources: kg.syncSources, approvals: kg.syncApprovals,
      }[kind];
      const result = await fn();
      setSyncMsg(`${kind}: ${result.created} created, ${result.skipped} skipped${result.relationships_created ? `, ${result.relationships_created} links` : ''}`);
      await load();
    } catch (err) {
      setSyncMsg(`${kind} sync error: ${String(err)}`);
    } finally {
      setSyncing(null);
    }
  }

  async function handleLink() {
    if (!linkFrom || !linkTo || linkFrom === linkTo) {
      setLinkMsg('Pick two different entities.');
      return;
    }
    try {
      await kg.linkEntities(linkFrom, linkTo, linkRel);
      setLinkMsg(`Linked: ${entityName(linkFrom)} —[${linkRel}]→ ${entityName(linkTo)}`);
      setLinkFrom(''); setLinkTo('');
      await load();
    } catch (err) {
      setLinkMsg(`Link error: ${String(err)}`);
    }
  }

  const filteredEntities = entities.filter(e => {
    if (entityFilter !== 'all' && e.type !== entityFilter) return false;
    if (search && !`${e.name} ${e.title ?? ''} ${e.summary ?? ''}`.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const filteredRels = relationships.filter(r => relFilter === 'all' || r.relationship === relFilter);
  const relStrings: string[] = relationships.map((r): string => String(r.relationship));
  const relTypes: string[] = ['all', ...Array.from(new Set<string>(relStrings))];
  const orphanTotal = orphans ? orphans.campaigns + orphans.content + orphans.sources + orphans.approvals : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Knowledge <span className="text-[#5B7CFA]">Graph</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Live · nexus_os_entities + nexus_os_relationships · relationship-aware memory
          </p>
        </div>
        <button onClick={load} disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 disabled:opacity-50 transition-all">
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />} Refresh
        </button>
      </div>

      {/* Graph Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <OverviewCard icon={Database} label="Entities" value={entities.length} color="blue" />
        <OverviewCard icon={GitBranch} label="Relationships" value={relationships.length} color="purple" />
        <OverviewCard icon={Link2} label="Linked Records" value={entities.filter(e => e.source_table).length} color="green" />
        <OverviewCard icon={AlertTriangle} label="Orphans" value={orphanTotal} color={orphanTotal > 0 ? 'amber' : 'green'} />
      </div>

      {/* Sync helpers */}
      <OSSection title="Sync to Graph" icon={Sparkles} action={
        syncMsg ? <span className="text-[10px] text-slate-500">{syncMsg}</span> : undefined
      }>
        <div className="flex flex-wrap gap-2">
          {([
            { k: 'campaigns', label: 'Sync Revenue Campaigns', orphan: orphans?.campaigns },
            { k: 'content', label: 'Sync Content Items', orphan: orphans?.content },
            { k: 'sources', label: 'Sync Sources', orphan: orphans?.sources },
            { k: 'approvals', label: 'Sync Approvals', orphan: orphans?.approvals },
          ] as const).map(({ k, label, orphan }) => (
            <button key={k} onClick={() => runSync(k)} disabled={syncing !== null}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold hover:bg-slate-200 disabled:opacity-50 transition-all">
              {syncing === k ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
              {label}
              {typeof orphan === 'number' && orphan > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[9px]">{orphan} new</span>
              )}
            </button>
          ))}
        </div>
        <p className="text-[10px] text-slate-400 mt-3">
          Creates a graph entity per source row (deduped by source_table + source_id) and the obvious relationships
          (content→campaign, content→source, approval→target). Never modifies source records.
        </p>
      </OSSection>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Entity Browser */}
        <OSSection title="Entity Browser" icon={Database} action={<Badge label={`${filteredEntities.length}`} variant="info" />}>
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <div className="relative flex-1 min-w-[140px]">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search entities..."
                className="input-base pl-8 text-xs py-1.5" />
            </div>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap mb-3">
            {ENTITY_TYPE_FILTERS.map(t => (
              <button key={t} onClick={() => setEntityFilter(t)}
                className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-all ${
                  entityFilter === t ? 'bg-[#5B7CFA] text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                }`}>{t.replace(/_/g, ' ')}</button>
            ))}
          </div>
          {loading ? <Loader2 className="w-5 h-5 animate-spin text-slate-300 mx-auto my-6" /> :
            filteredEntities.length === 0 ? <EmptyState icon={Database} message="No entities yet — use Sync to Graph" /> : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {filteredEntities.map(e => (
                <div key={e.id} className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-bold text-[#1A2244] truncate">{e.title || e.name}</p>
                    <Badge label={e.type.replace(/_/g, ' ')} variant="default" />
                  </div>
                  {e.summary && <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-1">{e.summary}</p>}
                  <p className="text-[9px] text-slate-400 mt-1 font-mono">
                    {e.source_table ? `${e.source_table.replace('nexus_os_', '')} · ${timeAgo(e.created_at)}` : `manual · ${timeAgo(e.created_at)}`}
                  </p>
                </div>
              ))}
            </div>
          )}
        </OSSection>

        {/* Relationship Browser */}
        <OSSection title="Relationship Browser" icon={GitBranch} action={<Badge label={`${filteredRels.length}`} variant="info" />}>
          <div className="flex items-center gap-1.5 flex-wrap mb-3">
            {relTypes.slice(0, 8).map(t => (
              <button key={t} onClick={() => setRelFilter(t)}
                className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-all ${
                  relFilter === t ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                }`}>{t.replace(/_/g, ' ')}</button>
            ))}
          </div>
          {loading ? <Loader2 className="w-5 h-5 animate-spin text-slate-300 mx-auto my-6" /> :
            filteredRels.length === 0 ? <EmptyState icon={GitBranch} message="No relationships yet" /> : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {filteredRels.map(r => (
                <div key={r.id} className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="flex items-center gap-1.5 text-xs flex-wrap">
                    <span className="font-bold text-[#1A2244] truncate max-w-[110px]">{entityName(r.from_entity_id)}</span>
                    <span className="px-1.5 py-0.5 rounded bg-[#5B7CFA]/10 text-[#5B7CFA] text-[9px] font-bold">{r.relationship.replace(/_/g, ' ')}</span>
                    <span className="font-bold text-[#1A2244] truncate max-w-[110px]">{entityName(r.to_entity_id)}</span>
                  </div>
                  {r.evidence_summary && <p className="text-[10px] text-slate-500 mt-1 line-clamp-1">{r.evidence_summary}</p>}
                </div>
              ))}
            </div>
          )}
        </OSSection>
      </div>

      {/* Link Builder */}
      <OSSection title="Link Builder" icon={Link2}>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2 items-end">
          <div>
            <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">From</label>
            <select value={linkFrom} onChange={e => setLinkFrom(e.target.value)} className="input-base text-xs py-2">
              <option value="">Select entity</option>
              {entities.map(e => <option key={e.id} value={e.id}>{(e.title || e.name).slice(0, 40)}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Relationship</label>
            <select value={linkRel} onChange={e => setLinkRel(e.target.value as GraphRelationshipType)} className="input-base text-xs py-2">
              {LINK_RELATIONSHIPS.map(r => <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">To</label>
            <select value={linkTo} onChange={e => setLinkTo(e.target.value)} className="input-base text-xs py-2">
              <option value="">Select entity</option>
              {entities.map(e => <option key={e.id} value={e.id}>{(e.title || e.name).slice(0, 40)}</option>)}
            </select>
          </div>
          <button onClick={handleLink} disabled={!linkFrom || !linkTo}
            className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black hover:bg-[#4A6BEB] disabled:opacity-40 transition-all">
            <Link2 className="w-3.5 h-3.5" /> Link
          </button>
        </div>
        {linkMsg && <p className="text-[10px] text-slate-500 mt-2 italic">{linkMsg}</p>}
        <p className="text-[10px] text-slate-400 mt-2">Manual links only. No automatic destructive linking.</p>
      </OSSection>

      {/* Orphan Finder */}
      {orphans && orphanTotal > 0 && (
        <OSSection title="Orphan Finder" icon={AlertTriangle}>
          <p className="text-xs text-slate-600 mb-2">
            Records not yet in the graph. Use the Sync buttons above to create entities (deduped, safe).
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <OrphanCell label="Campaigns" count={orphans.campaigns} />
            <OrphanCell label="Content" count={orphans.content} />
            <OrphanCell label="Sources" count={orphans.sources} />
            <OrphanCell label="Approvals" count={orphans.approvals} />
          </div>
        </OSSection>
      )}

      {/* Deferred integrations */}
      <OSSection title="Roadmap — Deferred Integrations" icon={Info}>
        <div className="space-y-2 text-xs text-slate-600">
          <RoadmapRow name="Open Notebook" note="Private NotebookLM-style research workspace" />
          <RoadmapRow name="Knowhere" note="Document parsing / RAG structuring" />
          <RoadmapRow name="Headroom" note="Token / context compression" />
          <RoadmapRow name="System Design 101" note="Architecture review checklist" />
        </div>
        <p className="text-[10px] text-slate-400 mt-3 italic">
          Not implemented yet. This pass is the first practical knowledge graph using existing Supabase tables —
          no vector DB, no external graph DB, no auto-import.
        </p>
      </OSSection>
    </div>
  );
}

function OverviewCard({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: number; color: string }) {
  const map: Record<string, string> = {
    blue: 'bg-blue-50 text-[#5B7CFA]', purple: 'bg-purple-50 text-purple-600',
    green: 'bg-green-50 text-green-600', amber: 'bg-amber-50 text-amber-600',
  };
  return (
    <OSCard className="p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${map[color] ?? map.blue}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-lg font-black text-[#1A2244]">{value}</p>
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
      </div>
    </OSCard>
  );
}

function OrphanCell({ label, count }: { label: string; count: number }) {
  return (
    <div className={`text-center p-2.5 rounded-xl border ${count > 0 ? 'bg-amber-50 border-amber-200' : 'bg-slate-50 border-slate-100'}`}>
      <p className={`text-lg font-black ${count > 0 ? 'text-amber-600' : 'text-slate-400'}`}>{count}</p>
      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
    </div>
  );
}

function RoadmapRow({ name, note }: { name: string; note: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-1.5 h-1.5 rounded-full bg-slate-300 shrink-0" />
      <span className="font-bold text-[#1A2244]">{name}</span>
      <span className="text-slate-400">— {note}</span>
      <Badge label="planned" variant="default" />
    </div>
  );
}
