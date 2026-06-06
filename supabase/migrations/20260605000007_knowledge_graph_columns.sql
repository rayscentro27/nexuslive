-- Knowledge Graph: additive columns + widened CHECK constraints
-- Migration: 20260605000007_knowledge_graph_columns.sql
-- Applied: 2026-06-06
-- Purpose: Make nexus_os_entities + nexus_os_relationships practical for the
--          Nexus OS knowledge graph layer. ADDITIVE ONLY. Existing CHECK values
--          are preserved (union) so no existing rows can break. RLS unchanged.

-- ── nexus_os_entities: new columns ──────────────────────────────────────────
ALTER TABLE public.nexus_os_entities
  ADD COLUMN IF NOT EXISTS title text;            -- human title (falls back to name)
ALTER TABLE public.nexus_os_entities
  ADD COLUMN IF NOT EXISTS summary text;          -- short summary (falls back to description)
ALTER TABLE public.nexus_os_entities
  ADD COLUMN IF NOT EXISTS source_table text;     -- e.g. nexus_os_revenue_campaigns
ALTER TABLE public.nexus_os_entities
  ADD COLUMN IF NOT EXISTS source_id uuid;        -- id in the source table
ALTER TABLE public.nexus_os_entities
  ADD COLUMN IF NOT EXISTS status text DEFAULT 'active';
ALTER TABLE public.nexus_os_entities
  ADD COLUMN IF NOT EXISTS confidence numeric(4,3);
ALTER TABLE public.nexus_os_entities
  ADD COLUMN IF NOT EXISTS archived boolean NOT NULL DEFAULT false;

-- Dedup key: one graph entity per (source_table, source_id). Partial unique index
-- so manually-created entities (null source) are unaffected.
CREATE UNIQUE INDEX IF NOT EXISTS nexus_os_entities_source_uq
  ON public.nexus_os_entities(source_table, source_id)
  WHERE source_table IS NOT NULL AND source_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS nexus_os_entities_archived_idx
  ON public.nexus_os_entities(archived, type);

-- ── nexus_os_relationships: new columns ─────────────────────────────────────
ALTER TABLE public.nexus_os_relationships
  ADD COLUMN IF NOT EXISTS weight numeric(4,3) DEFAULT 1.0;
ALTER TABLE public.nexus_os_relationships
  ADD COLUMN IF NOT EXISTS evidence_summary text;
ALTER TABLE public.nexus_os_relationships
  ADD COLUMN IF NOT EXISTS source_table text;
ALTER TABLE public.nexus_os_relationships
  ADD COLUMN IF NOT EXISTS source_id uuid;

-- Dedup key: avoid duplicate identical edges
CREATE UNIQUE INDEX IF NOT EXISTS nexus_os_relationships_edge_uq
  ON public.nexus_os_relationships(from_entity_id, to_entity_id, relationship);

-- ── Widen entity type CHECK (union of existing + new) ────────────────────────
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'nexus_os_entities_type_check') THEN
    ALTER TABLE public.nexus_os_entities DROP CONSTRAINT nexus_os_entities_type_check;
  END IF;
END;
$$;

ALTER TABLE public.nexus_os_entities
  ADD CONSTRAINT nexus_os_entities_type_check
  CHECK (type IN (
    -- original values (migration 000001)
    'source','transcript','artifact','task','agent','tool','workflow',
    'skill','rule','client','campaign','trading_strategy','approval',
    'blocker','failure','decision','metric','output','prompt','sop',
    -- knowledge graph additions
    'revenue_campaign','content_item','notification','lesson',
    'provider','repo_reference'
  ));

-- ── Widen relationship CHECK (union of existing + new) ───────────────────────
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'nexus_os_relationships_relationship_check') THEN
    ALTER TABLE public.nexus_os_relationships DROP CONSTRAINT nexus_os_relationships_relationship_check;
  END IF;
END;
$$;

ALTER TABLE public.nexus_os_relationships
  ADD CONSTRAINT nexus_os_relationships_relationship_check
  CHECK (relationship IN (
    -- original values (migration 000001)
    'produced_by','belongs_to','supports','depends_on','blocked_by',
    'approved_by','tested_by','improves','replaces','contradicts',
    'deployed_to','related_to',
    -- knowledge graph additions
    'derived_from','blocks','created_content_for','requires_approval',
    'resulted_in','learned_from','references','belongs_to_campaign',
    'generated_from_source','recommended_by_hermes'
  ));
