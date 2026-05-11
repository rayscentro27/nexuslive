-- ── research_relationships ────────────────────────────────────────────────────
-- Phase 7: Nexus Brain Research Ingestion Lab
-- Lightweight knowledge graph: topic → subtheme → claim_type → source edges.
-- Used by graph_enricher.js to build relationship chains across research domains.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS research_relationships (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  from_node   TEXT        NOT NULL,
  from_type   TEXT        NOT NULL CHECK (from_type IN (
    'topic', 'subtheme', 'claim_type', 'source', 'strategy', 'workflow'
  )),
  to_node     TEXT        NOT NULL,
  to_type     TEXT        NOT NULL CHECK (to_type IN (
    'topic', 'subtheme', 'claim_type', 'source', 'strategy', 'workflow'
  )),
  relation    TEXT        NOT NULL CHECK (relation IN (
    'contains', 'sourced_from', 'extracted_from', 'related_to', 'contradicts'
  )),
  source      TEXT,
  trace_id    UUID,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS research_relationships_from_idx
  ON research_relationships (from_node, from_type);

CREATE INDEX IF NOT EXISTS research_relationships_to_idx
  ON research_relationships (to_node, to_type);

CREATE INDEX IF NOT EXISTS research_relationships_relation_idx
  ON research_relationships (relation);

CREATE INDEX IF NOT EXISTS research_relationships_created_at_idx
  ON research_relationships (created_at DESC);

-- Validation:
-- SELECT from_node, relation, to_node, COUNT(*) FROM research_relationships
--   GROUP BY from_node, relation, to_node ORDER BY COUNT(*) DESC LIMIT 20;
-- SELECT DISTINCT from_type, relation, to_type FROM research_relationships;
