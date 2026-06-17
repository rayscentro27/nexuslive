/**
 * useKnowledgeGraphActions — CRUD + safe sync for the Nexus OS knowledge graph
 * (nexus_os_entities + nexus_os_relationships).
 *
 * Safety contract:
 *   - Read-only against source tables except graph entity/relationship writes.
 *   - Never modifies revenue/content/approval source records.
 *   - Dedups via (source_table, source_id) on entities and
 *     (from,to,relationship) on edges.
 *   - No external data import, no scraping, no executors.
 */
import { useCallback, useMemo } from 'react';
import { supabase } from '../../lib/supabase';
import type { GraphEntity, GraphRelationship, GraphSyncResult, GraphEntityType, GraphRelationshipType } from './types';

function normEntity(row: Record<string, unknown>): GraphEntity {
  return {
    ...(row as unknown as GraphEntity),
    metadata: (row.metadata && typeof row.metadata === 'object' ? row.metadata : {}) as Record<string, unknown>,
    tags: Array.isArray(row.tags) ? (row.tags as string[]) : [],
    archived: !!row.archived,
  };
}

export function useKnowledgeGraphActions() {
  // ── Reads ────────────────────────────────────────────────────────────────
  const fetchEntities = useCallback(async (includeArchived = false): Promise<GraphEntity[]> => {
    let q = supabase.from('nexus_os_entities').select('*').order('created_at', { ascending: false }).limit(500);
    if (!includeArchived) q = q.eq('archived', false);
    const { data, error } = await q;
    if (error) throw error;
    return (data ?? []).map(normEntity);
  }, []);

  const fetchRelationships = useCallback(async (): Promise<GraphRelationship[]> => {
    const { data, error } = await supabase
      .from('nexus_os_relationships')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(1000);
    if (error) throw error;
    return (data ?? []) as GraphRelationship[];
  }, []);

  // ── Entity writes ──────────────────────────────────────────────────────────
  const createEntity = useCallback(async (e: {
    type: GraphEntityType; name: string; title?: string; summary?: string;
    description?: string; source_table?: string; source_id?: string;
    status?: string; confidence?: number; tags?: string[]; metadata?: Record<string, unknown>;
  }): Promise<GraphEntity> => {
    const { data, error } = await supabase
      .from('nexus_os_entities')
      .insert({
        type: e.type,
        name: e.name,
        title: e.title ?? e.name,
        summary: e.summary ?? e.description ?? null,
        description: e.description ?? e.summary ?? null,
        source_table: e.source_table ?? null,
        source_id: e.source_id ?? null,
        status: e.status ?? 'active',
        confidence: e.confidence ?? null,
        tags: e.tags ?? [],
        metadata: e.metadata ?? {},
        archived: false,
      })
      .select()
      .single();
    if (error) throw error;
    return normEntity(data as Record<string, unknown>);
  }, []);

  const updateEntity = useCallback(async (id: string, changes: Partial<GraphEntity>): Promise<void> => {
    const { error } = await supabase.from('nexus_os_entities').update(changes).eq('id', id);
    if (error) throw error;
  }, []);

  const archiveEntity = useCallback(async (id: string): Promise<void> => {
    const { error } = await supabase.from('nexus_os_entities').update({ archived: true }).eq('id', id);
    if (error) throw error;
  }, []);

  // ── Relationship writes ────────────────────────────────────────────────────
  // Idempotent: upsert on (from,to,relationship) unique index.
  const createRelationship = useCallback(async (r: {
    from_entity_id: string; to_entity_id: string; relationship: GraphRelationshipType;
    weight?: number; evidence_summary?: string; source_table?: string; source_id?: string;
    metadata?: Record<string, unknown>;
  }): Promise<GraphRelationship | null> => {
    const { data, error } = await supabase
      .from('nexus_os_relationships')
      .upsert({
        from_entity_id: r.from_entity_id,
        to_entity_id: r.to_entity_id,
        relationship: r.relationship,
        weight: r.weight ?? 1.0,
        evidence_summary: r.evidence_summary ?? null,
        source_table: r.source_table ?? null,
        source_id: r.source_id ?? null,
        metadata: r.metadata ?? {},
      }, { onConflict: 'from_entity_id,to_entity_id,relationship', ignoreDuplicates: true })
      .select()
      .maybeSingle();
    if (error) {
      // ignoreDuplicates returns no row on conflict — that is fine
      console.warn('[KG] relationship upsert note:', error.message);
      return null;
    }
    return (data as GraphRelationship) ?? null;
  }, []);

  // Prefer archive-style safety: relationships have no archived col, so deleteRelationship
  // is exposed but should be used sparingly (manual cleanup only).
  const deleteRelationship = useCallback(async (id: string): Promise<void> => {
    const { error } = await supabase.from('nexus_os_relationships').delete().eq('id', id);
    if (error) throw error;
  }, []);

  // ── Entity lookup by source ────────────────────────────────────────────────
  const findEntityBySource = useCallback(async (source_table: string, source_id: string): Promise<GraphEntity | null> => {
    const { data } = await supabase
      .from('nexus_os_entities')
      .select('*')
      .eq('source_table', source_table)
      .eq('source_id', source_id)
      .maybeSingle();
    return data ? normEntity(data as Record<string, unknown>) : null;
  }, []);

  // Ensure an entity exists for a source row (create if missing). Returns its id.
  const ensureEntity = useCallback(async (e: {
    type: GraphEntityType; name: string; source_table: string; source_id: string;
    summary?: string; status?: string;
  }): Promise<{ id: string; created: boolean }> => {
    const existing = await findEntityBySource(e.source_table, e.source_id);
    if (existing) return { id: existing.id, created: false };
    const created = await createEntity(e);
    return { id: created.id, created: true };
  }, [findEntityBySource, createEntity]);

  // ── Sync helpers (Phase 4) ──────────────────────────────────────────────────

  const syncCampaigns = useCallback(async (): Promise<GraphSyncResult> => {
    const { data } = await supabase
      .from('nexus_os_revenue_campaigns')
      .select('id,program_name,niche,priority,application_status')
      .eq('archived', false);
    let created = 0, skipped = 0;
    for (const c of data ?? []) {
      const r = await ensureEntity({
        type: 'revenue_campaign',
        name: c.program_name,
        source_table: 'nexus_os_revenue_campaigns',
        source_id: c.id,
        summary: `${c.niche} · ${c.priority} priority · ${c.application_status}`,
        status: c.application_status,
      });
      r.created ? created++ : skipped++;
    }
    return { table: 'nexus_os_revenue_campaigns', created, skipped, relationships_created: 0 };
  }, [ensureEntity]);

  const syncContent = useCallback(async (): Promise<GraphSyncResult> => {
    const { data } = await supabase
      .from('nexus_os_content_items')
      .select('id,title,content_type,status,related_campaign_id,source_artifact_id,source_url')
      .eq('archived', false);
    let created = 0, skipped = 0, rels = 0;
    for (const item of data ?? []) {
      const ent = await ensureEntity({
        type: 'content_item',
        name: item.title,
        source_table: 'nexus_os_content_items',
        source_id: item.id,
        summary: `${item.content_type} · ${item.status}`,
        status: item.status,
      });
      ent.created ? created++ : skipped++;

      // content belongs_to_campaign revenue_campaign
      if (item.related_campaign_id) {
        const campEnt = await findEntityBySource('nexus_os_revenue_campaigns', item.related_campaign_id);
        if (campEnt) {
          const rel = await createRelationship({
            from_entity_id: ent.id,
            to_entity_id: campEnt.id,
            relationship: 'belongs_to_campaign',
            evidence_summary: `Content "${item.title}" is linked to its campaign via related_campaign_id.`,
            source_table: 'nexus_os_content_items',
            source_id: item.id,
          });
          if (rel) rels++;
        }
      }

      // content generated_from_source source (only if a source entity exists)
      if (item.source_artifact_id) {
        const srcEnt = await findEntityBySource('nexus_os_sources', item.source_artifact_id);
        if (srcEnt) {
          const rel = await createRelationship({
            from_entity_id: ent.id,
            to_entity_id: srcEnt.id,
            relationship: 'generated_from_source',
            evidence_summary: `Content "${item.title}" was generated from a linked source.`,
            source_table: 'nexus_os_content_items',
            source_id: item.id,
          });
          if (rel) rels++;
        }
      }
    }
    return { table: 'nexus_os_content_items', created, skipped, relationships_created: rels };
  }, [ensureEntity, findEntityBySource, createRelationship]);

  const syncSources = useCallback(async (): Promise<GraphSyncResult> => {
    const { data } = await supabase
      .from('nexus_os_sources')
      .select('id,title,type,status,summary')
      .neq('status', 'archived');
    let created = 0, skipped = 0;
    for (const s of data ?? []) {
      const r = await ensureEntity({
        type: 'source',
        name: s.title,
        source_table: 'nexus_os_sources',
        source_id: s.id,
        summary: s.summary ?? `${s.type} · ${s.status}`,
        status: s.status,
      });
      r.created ? created++ : skipped++;
    }
    return { table: 'nexus_os_sources', created, skipped, relationships_created: 0 };
  }, [ensureEntity]);

  const syncApprovals = useCallback(async (): Promise<GraphSyncResult> => {
    const { data } = await supabase
      .from('owner_approval_queue')
      .select('id,action_type,description,status,payload')
      .order('created_at', { ascending: false })
      .limit(100);
    let created = 0, skipped = 0, rels = 0;
    for (const a of data ?? []) {
      const ent = await ensureEntity({
        type: 'approval',
        name: a.action_type,
        source_table: 'owner_approval_queue',
        source_id: a.id,
        summary: a.description?.slice(0, 200) ?? a.action_type,
        status: a.status,
      });
      ent.created ? created++ : skipped++;

      // approval requires_approval content_item / revenue_campaign from payload
      const payload = (a.payload ?? {}) as Record<string, unknown>;
      const contentId = payload.content_item_id as string | undefined;
      const campaignId = payload.campaign_id as string | undefined;
      if (contentId) {
        const target = await findEntityBySource('nexus_os_content_items', contentId);
        if (target) {
          const rel = await createRelationship({
            from_entity_id: target.id, to_entity_id: ent.id,
            relationship: 'requires_approval',
            evidence_summary: `Content requires approval "${a.action_type}".`,
            source_table: 'owner_approval_queue', source_id: a.id,
          });
          if (rel) rels++;
        }
      }
      if (campaignId) {
        const target = await findEntityBySource('nexus_os_revenue_campaigns', campaignId);
        if (target) {
          const rel = await createRelationship({
            from_entity_id: target.id, to_entity_id: ent.id,
            relationship: 'requires_approval',
            evidence_summary: `Campaign requires approval "${a.action_type}".`,
            source_table: 'owner_approval_queue', source_id: a.id,
          });
          if (rel) rels++;
        }
      }
    }
    return { table: 'owner_approval_queue', created, skipped, relationships_created: rels };
  }, [ensureEntity, findEntityBySource, createRelationship]);

  // ── Manual link builders (Phase 3D) ─────────────────────────────────────────
  const linkEntities = useCallback(async (
    fromId: string, toId: string, relationship: GraphRelationshipType, note?: string,
  ): Promise<GraphRelationship | null> => {
    return createRelationship({
      from_entity_id: fromId, to_entity_id: toId, relationship,
      evidence_summary: note ?? `Manually linked by admin.`,
    });
  }, [createRelationship]);

  // ── Graph for a single entity (Phase 3F) ────────────────────────────────────
  const getGraphForEntity = useCallback(async (entityId: string): Promise<{
    outgoing: GraphRelationship[]; incoming: GraphRelationship[];
  }> => {
    const [out, inc] = await Promise.all([
      supabase.from('nexus_os_relationships').select('*').eq('from_entity_id', entityId),
      supabase.from('nexus_os_relationships').select('*').eq('to_entity_id', entityId),
    ]);
    return {
      outgoing: (out.data ?? []) as GraphRelationship[],
      incoming: (inc.data ?? []) as GraphRelationship[],
    };
  }, []);

  // ── Orphan finder (Phase 3E) ─────────────────────────────────────────────────
  const findOrphans = useCallback(async (): Promise<{
    campaigns: number; content: number; sources: number; approvals: number;
  }> => {
    const entities = await fetchEntities(false);
    const linked = new Set(entities.filter(e => e.source_table && e.source_id).map(e => `${e.source_table}:${e.source_id}`));
    const [camps, content, sources, approvals] = await Promise.all([
      supabase.from('nexus_os_revenue_campaigns').select('id').eq('archived', false),
      supabase.from('nexus_os_content_items').select('id').eq('archived', false),
      supabase.from('nexus_os_sources').select('id').neq('status', 'archived'),
      supabase.from('owner_approval_queue').select('id').limit(100),
    ]);
    const countOrphans = (rows: Array<{ id: string }> | null, table: string) =>
      (rows ?? []).filter(r => !linked.has(`${table}:${r.id}`)).length;
    return {
      campaigns: countOrphans(camps.data, 'nexus_os_revenue_campaigns'),
      content: countOrphans(content.data, 'nexus_os_content_items'),
      sources: countOrphans(sources.data, 'nexus_os_sources'),
      approvals: countOrphans(approvals.data, 'owner_approval_queue'),
    };
  }, [fetchEntities]);

  // Memoized so consumer effects don't re-fetch every render (stuck-spinner fix).
  return useMemo(() => ({
    fetchEntities, fetchRelationships,
    createEntity, updateEntity, archiveEntity,
    createRelationship, deleteRelationship, linkEntities,
    findEntityBySource, ensureEntity,
    syncCampaigns, syncContent, syncSources, syncApprovals,
    getGraphForEntity, findOrphans,
  }), [fetchEntities, fetchRelationships, createEntity, updateEntity, archiveEntity, createRelationship, deleteRelationship, linkEntities, findEntityBySource, ensureEntity, syncCampaigns, syncContent, syncSources, syncApprovals, getGraphForEntity, findOrphans]);
}
