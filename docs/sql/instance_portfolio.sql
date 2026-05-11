-- ============================================================
-- Instance Replication + Niche Discovery + Funnel Deployment
-- Revenue Orchestration + Portfolio + Kill/Scale Engine
-- Run in Supabase SQL editor
-- ============================================================

-- 1. Nexus Instances
CREATE TABLE IF NOT EXISTS nexus_instances (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  niche              text        NOT NULL,
  display_name       text,
  status             text        DEFAULT 'testing',
  config             jsonb       DEFAULT '{}'::jsonb,
  parent_instance_id uuid,
  created_at         timestamptz DEFAULT now(),
  updated_at         timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_instances_niche   ON nexus_instances(niche);
CREATE INDEX IF NOT EXISTS idx_instances_status  ON nexus_instances(status);
CREATE INDEX IF NOT EXISTS idx_instances_created ON nexus_instances(created_at DESC);

-- 2. Instance Configs
CREATE TABLE IF NOT EXISTS instance_configs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instance_id  uuid        NOT NULL REFERENCES nexus_instances(id) ON DELETE CASCADE,
  config_key   text        NOT NULL,
  config_value text,
  created_at   timestamptz DEFAULT now(),
  UNIQUE(instance_id, config_key)
);

CREATE INDEX IF NOT EXISTS idx_instance_configs_instance ON instance_configs(instance_id);
CREATE INDEX IF NOT EXISTS idx_instance_configs_key      ON instance_configs(config_key);

-- 3. Niche Candidates
CREATE TABLE IF NOT EXISTS niche_candidates (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name               text        NOT NULL UNIQUE,
  demand_score       numeric     DEFAULT 0,
  competition_score  numeric     DEFAULT 0,
  monetization_score numeric     DEFAULT 0,
  total_score        numeric     DEFAULT 0,
  status             text        DEFAULT 'candidate',
  research_sources   jsonb       DEFAULT '[]'::jsonb,
  notes              text,
  created_at         timestamptz DEFAULT now(),
  updated_at         timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_niches_status ON niche_candidates(status);
CREATE INDEX IF NOT EXISTS idx_niches_score  ON niche_candidates(total_score DESC);

-- 4. Funnels
CREATE TABLE IF NOT EXISTS funnels (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instance_id uuid        REFERENCES nexus_instances(id),
  niche       text,
  funnel_name text        NOT NULL,
  funnel_type text        DEFAULT 'lead_gen',
  status      text        DEFAULT 'draft',
  config      jsonb       DEFAULT '{}'::jsonb,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_funnels_instance ON funnels(instance_id);
CREATE INDEX IF NOT EXISTS idx_funnels_niche    ON funnels(niche);
CREATE INDEX IF NOT EXISTS idx_funnels_status   ON funnels(status);
CREATE INDEX IF NOT EXISTS idx_funnels_type     ON funnels(funnel_type);

-- 5. Funnel Steps
CREATE TABLE IF NOT EXISTS funnel_steps (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  funnel_id  uuid        NOT NULL REFERENCES funnels(id) ON DELETE CASCADE,
  step_name  text        NOT NULL,
  step_order integer     NOT NULL,
  step_type  text        DEFAULT 'message',
  content    text,
  config     jsonb       DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  UNIQUE(funnel_id, step_order)
);

CREATE INDEX IF NOT EXISTS idx_funnel_steps_funnel ON funnel_steps(funnel_id);

-- 6. Revenue Streams
CREATE TABLE IF NOT EXISTS revenue_streams (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instance_id  uuid        REFERENCES nexus_instances(id),
  stream_type  text        NOT NULL,
  period       text        NOT NULL,
  revenue      numeric     DEFAULT 0,
  transactions integer     DEFAULT 0,
  growth_rate  numeric     DEFAULT 0,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now(),
  UNIQUE(instance_id, stream_type, period)
);

CREATE INDEX IF NOT EXISTS idx_revenue_instance ON revenue_streams(instance_id);
CREATE INDEX IF NOT EXISTS idx_revenue_type     ON revenue_streams(stream_type);
CREATE INDEX IF NOT EXISTS idx_revenue_period   ON revenue_streams(period DESC);

-- 7. Portfolio Summary (append-only snapshots)
CREATE TABLE IF NOT EXISTS portfolio_summary (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  total_revenue     numeric     DEFAULT 0,
  monthly_revenue   numeric     DEFAULT 0,
  active_instances  integer     DEFAULT 0,
  testing_instances integer     DEFAULT 0,
  scaled_instances  integer     DEFAULT 0,
  killed_instances  integer     DEFAULT 0,
  top_performers    jsonb       DEFAULT '[]'::jsonb,
  underperformers   jsonb       DEFAULT '[]'::jsonb,
  snapshot_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshot ON portfolio_summary(snapshot_at DESC);

-- 8. Instance Decisions
CREATE TABLE IF NOT EXISTS instance_decisions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  instance_id uuid        NOT NULL REFERENCES nexus_instances(id),
  decision    text        NOT NULL,
  reason      text,
  confidence  numeric     DEFAULT 0.7,
  status      text        DEFAULT 'pending',
  executed_at timestamptz,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_inst_decisions_instance ON instance_decisions(instance_id);
CREATE INDEX IF NOT EXISTS idx_inst_decisions_status   ON instance_decisions(status);
CREATE INDEX IF NOT EXISTS idx_inst_decisions_decision ON instance_decisions(decision);
CREATE INDEX IF NOT EXISTS idx_inst_decisions_created  ON instance_decisions(created_at DESC);
