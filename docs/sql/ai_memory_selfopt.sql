-- ============================================================
-- AI Memory Layer + Self-Optimization Engine
-- Run in Supabase SQL editor
-- ============================================================

-- 1. Extend ai_memory with new columns
ALTER TABLE ai_memory
  ADD COLUMN IF NOT EXISTS client_id          text,
  ADD COLUMN IF NOT EXISTS tenant_id          text,
  ADD COLUMN IF NOT EXISTS source_agent       text,
  ADD COLUMN IF NOT EXISTS structured_payload jsonb,
  ADD COLUMN IF NOT EXISTS importance_score   numeric DEFAULT 50,
  ADD COLUMN IF NOT EXISTS last_used_at       timestamptz;

CREATE INDEX IF NOT EXISTS idx_ai_memory_client_id    ON ai_memory(client_id);
CREATE INDEX IF NOT EXISTS idx_ai_memory_source_agent ON ai_memory(source_agent);
CREATE INDEX IF NOT EXISTS idx_ai_memory_importance   ON ai_memory(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_ai_memory_last_used    ON ai_memory(last_used_at DESC NULLS LAST);

-- 2. Memory links (connects memories to tasks / threads / stages)
CREATE TABLE IF NOT EXISTS memory_links (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id         uuid NOT NULL REFERENCES ai_memory(id) ON DELETE CASCADE,
  related_task_id   uuid,
  related_thread_id text,
  related_stage     text,
  related_event_id  uuid,
  created_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_links_memory_id ON memory_links(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_links_task_id   ON memory_links(related_task_id);

-- ============================================================
-- Self-Optimization Outcome Tables
-- ============================================================

-- 3. Recommendation outcomes (what happened after agent made a recommendation)
CREATE TABLE IF NOT EXISTS recommendation_outcomes (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_name     text        NOT NULL,
  client_id      text        NOT NULL,
  event_id       uuid,
  recommendation text        NOT NULL,
  outcome        text        DEFAULT 'pending',
  score_at_time  numeric,
  notes          text,
  meta           jsonb,
  created_at     timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rec_outcomes_agent   ON recommendation_outcomes(agent_name);
CREATE INDEX IF NOT EXISTS idx_rec_outcomes_client  ON recommendation_outcomes(client_id);
CREATE INDEX IF NOT EXISTS idx_rec_outcomes_outcome ON recommendation_outcomes(outcome);
CREATE INDEX IF NOT EXISTS idx_rec_outcomes_created ON recommendation_outcomes(created_at DESC);

-- 4. Task outcomes (what happened with agent-created tasks)
CREATE TABLE IF NOT EXISTS task_outcomes (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id               uuid,
  agent_name            text        NOT NULL,
  client_id             text        NOT NULL,
  task_title            text,
  status                text        DEFAULT 'pending',
  resolution_time_hours numeric,
  client_engaged        boolean     DEFAULT false,
  notes                 text,
  meta                  jsonb,
  created_at            timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_task_outcomes_agent   ON task_outcomes(agent_name);
CREATE INDEX IF NOT EXISTS idx_task_outcomes_client  ON task_outcomes(client_id);
CREATE INDEX IF NOT EXISTS idx_task_outcomes_status  ON task_outcomes(status);
CREATE INDEX IF NOT EXISTS idx_task_outcomes_created ON task_outcomes(created_at DESC);

-- 5. Strategy engagement outcomes
CREATE TABLE IF NOT EXISTS strategy_engagement_outcomes (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id      text,
  strategy_type    text,
  outcome          text,
  engagement_score numeric,
  notes            text,
  meta             jsonb,
  created_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_strat_outcomes_type    ON strategy_engagement_outcomes(strategy_type);
CREATE INDEX IF NOT EXISTS idx_strat_outcomes_created ON strategy_engagement_outcomes(created_at DESC);

-- 6. Signal engagement outcomes
CREATE TABLE IF NOT EXISTS signal_engagement_outcomes (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id  text,
  symbol     text,
  outcome    text,
  pnl_pct    numeric,
  notes      text,
  meta       jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sig_outcomes_symbol  ON signal_engagement_outcomes(symbol);
CREATE INDEX IF NOT EXISTS idx_sig_outcomes_outcome ON signal_engagement_outcomes(outcome);
CREATE INDEX IF NOT EXISTS idx_sig_outcomes_created ON signal_engagement_outcomes(created_at DESC);

-- 7. Communication outcomes (did client engage with comms?)
CREATE TABLE IF NOT EXISTS communication_outcomes (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id          uuid,
  agent_name          text        NOT NULL,
  client_id           text        NOT NULL,
  message_type        text,
  outcome             text        DEFAULT 'pending',
  response_time_hours numeric,
  notes               text,
  meta                jsonb,
  created_at          timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_comm_outcomes_agent   ON communication_outcomes(agent_name);
CREATE INDEX IF NOT EXISTS idx_comm_outcomes_client  ON communication_outcomes(client_id);
CREATE INDEX IF NOT EXISTS idx_comm_outcomes_outcome ON communication_outcomes(outcome);
CREATE INDEX IF NOT EXISTS idx_comm_outcomes_created ON communication_outcomes(created_at DESC);
