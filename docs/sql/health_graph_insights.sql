-- ============================================================
-- Source Health + Duplicates + Coverage + Recommendations
-- Knowledge Graph + Cross-Domain Insights
-- Run in Supabase SQL editor
-- ============================================================

-- 1. Source Health Scores
CREATE TABLE IF NOT EXISTS source_health_scores (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id            uuid        NOT NULL,
  score_total          numeric     DEFAULT 0,
  content_quality_score numeric    DEFAULT 0,
  signal_yield_score   numeric     DEFAULT 0,
  strategy_yield_score numeric     DEFAULT 0,
  freshness_score      numeric     DEFAULT 0,
  noise_score          numeric     DEFAULT 0,
  last_evaluated_at    timestamptz DEFAULT now(),
  created_at           timestamptz DEFAULT now(),
  UNIQUE(source_id)
);

CREATE INDEX IF NOT EXISTS idx_health_scores_source  ON source_health_scores(source_id);
CREATE INDEX IF NOT EXISTS idx_health_scores_total   ON source_health_scores(score_total DESC);
CREATE INDEX IF NOT EXISTS idx_health_scores_updated ON source_health_scores(last_evaluated_at DESC);

-- 2. Source Duplicates
CREATE TABLE IF NOT EXISTS source_duplicates (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id              uuid        NOT NULL,
  duplicate_of_source_id uuid        NOT NULL,
  similarity_score       numeric     DEFAULT 0,
  reason                 text,
  status                 text        DEFAULT 'flagged',
  created_at             timestamptz DEFAULT now(),
  UNIQUE(source_id, duplicate_of_source_id)
);

CREATE INDEX IF NOT EXISTS idx_duplicates_source    ON source_duplicates(source_id);
CREATE INDEX IF NOT EXISTS idx_duplicates_duplicate ON source_duplicates(duplicate_of_source_id);
CREATE INDEX IF NOT EXISTS idx_duplicates_status    ON source_duplicates(status);

-- 3. Research Coverage
CREATE TABLE IF NOT EXISTS research_coverage (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  domain          text        NOT NULL,
  subdomain       text,
  coverage_score  numeric     DEFAULT 0,
  source_count    integer     DEFAULT 0,
  artifact_count  integer     DEFAULT 0,
  signal_count    integer     DEFAULT 0,
  strategy_count  integer     DEFAULT 0,
  last_updated    timestamptz DEFAULT now(),
  UNIQUE(domain, subdomain)
);

CREATE INDEX IF NOT EXISTS idx_coverage_domain  ON research_coverage(domain);
CREATE INDEX IF NOT EXISTS idx_coverage_score   ON research_coverage(coverage_score);
CREATE INDEX IF NOT EXISTS idx_coverage_updated ON research_coverage(last_updated DESC);

-- 4. Source Recommendations
CREATE TABLE IF NOT EXISTS source_recommendations (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommended_source_type text       NOT NULL,
  suggested_domain        text,
  suggested_url           text,
  reason                  text,
  priority                text        DEFAULT 'medium',
  status                  text        DEFAULT 'pending',
  created_at              timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_source_recs_priority ON source_recommendations(priority);
CREATE INDEX IF NOT EXISTS idx_source_recs_status   ON source_recommendations(status);
CREATE INDEX IF NOT EXISTS idx_source_recs_created  ON source_recommendations(created_at DESC);

-- 5. Knowledge Nodes
CREATE TABLE IF NOT EXISTS knowledge_nodes (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  node_type   text        NOT NULL,
  entity_id   uuid,
  label       text        NOT NULL,
  domain      text,
  properties  jsonb       DEFAULT '{}'::jsonb,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knodes_type      ON knowledge_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_knodes_entity_id ON knowledge_nodes(entity_id);
CREATE INDEX IF NOT EXISTS idx_knodes_domain    ON knowledge_nodes(domain);
CREATE INDEX IF NOT EXISTS idx_knodes_label     ON knowledge_nodes(label);

-- 6. Knowledge Edges
CREATE TABLE IF NOT EXISTS knowledge_edges (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  from_node_id uuid        NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
  to_node_id   uuid        NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
  edge_type    text        NOT NULL,
  weight       numeric     DEFAULT 0.5,
  properties   jsonb       DEFAULT '{}'::jsonb,
  created_at   timestamptz DEFAULT now(),
  UNIQUE(from_node_id, to_node_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_kedges_from      ON knowledge_edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_kedges_to        ON knowledge_edges(to_node_id);
CREATE INDEX IF NOT EXISTS idx_kedges_type      ON knowledge_edges(edge_type);
CREATE INDEX IF NOT EXISTS idx_kedges_weight    ON knowledge_edges(weight DESC);

-- 7. Cross-Domain Insights
CREATE TABLE IF NOT EXISTS cross_domain_insights (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  insight_type     text        NOT NULL,
  domain_a         text,
  domain_b         text,
  related_entities jsonb       DEFAULT '[]'::jsonb,
  summary          text        NOT NULL,
  confidence       numeric     DEFAULT 0.5,
  status           text        DEFAULT 'active',
  created_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_xinsights_type      ON cross_domain_insights(insight_type);
CREATE INDEX IF NOT EXISTS idx_xinsights_domains   ON cross_domain_insights(domain_a, domain_b);
CREATE INDEX IF NOT EXISTS idx_xinsights_confidence ON cross_domain_insights(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_xinsights_created   ON cross_domain_insights(created_at DESC);
