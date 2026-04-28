-- =============================================================================
-- NEXUS AI — Clean Supabase Schema Migration
-- Run this on a fresh Supabase project to recreate the backend database.
-- 27 tables (down from 345). Only tables the backend actually uses.
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- CORE
-- =============================================================================

CREATE TABLE IF NOT EXISTS tenants (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text        NOT NULL,
  slug        text        UNIQUE NOT NULL,
  status      text        NOT NULL DEFAULT 'active',
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agents (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name             text        NOT NULL,
  division         text,
  role             text,
  status           text        NOT NULL DEFAULT 'testing',
  base_prompt      text,
  system_prompt    text,
  version          integer     NOT NULL DEFAULT 1,
  consolidated_at  timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

-- Worker process registry — all Mac Mini launchd processes report here
CREATE TABLE IF NOT EXISTS worker_heartbeats (
  worker_id         text        PRIMARY KEY,
  worker_type       text        NOT NULL,
  status            text        NOT NULL DEFAULT 'running',
  system_mode       text        NOT NULL DEFAULT 'development',
  current_job_id    uuid,
  in_flight_jobs    integer     NOT NULL DEFAULT 0,
  max_concurrency   integer     NOT NULL DEFAULT 2,
  host              text,
  pid               integer,
  tenant_scope      uuid,
  queue_scope       jsonb,
  meta              jsonb,
  last_heartbeat_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at      timestamptz NOT NULL DEFAULT now(),
  started_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  created_at        timestamptz NOT NULL DEFAULT now()
);

-- Async job queue — all background workers pull from here
CREATE TABLE IF NOT EXISTS job_queue (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type         text        NOT NULL,
  tenant_id        uuid,
  payload          jsonb       NOT NULL DEFAULT '{}',
  status           text        NOT NULL DEFAULT 'pending',
  priority         integer     NOT NULL DEFAULT 5,
  available_at     timestamptz NOT NULL DEFAULT now(),
  leased_at        timestamptz,
  lease_expires_at timestamptz,
  attempt_count    integer     NOT NULL DEFAULT 0,
  max_attempts     integer     NOT NULL DEFAULT 3,
  dedupe_key       text,
  worker_id        text,
  last_error       text,
  completed_at     timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS job_queue_dedupe_idx
  ON job_queue (dedupe_key) WHERE dedupe_key IS NOT NULL AND status != 'completed';

-- =============================================================================
-- RESEARCH PIPELINE
-- =============================================================================

-- Primary research store — YouTube transcripts summarized by AI
CREATE TABLE IF NOT EXISTS research (
  id                 bigserial   PRIMARY KEY,
  source             text,
  title              text,
  content            text,
  embedding          text,         -- vector stored as text; upgrade to pgvector if needed
  ai_enrich_version  text,
  ai_enriched_at     timestamptz,
  ai_enrich_status   text         NOT NULL DEFAULT 'pending',
  ai_review_status   text,
  ai_expires_at      timestamptz,
  schema_version     integer      NOT NULL DEFAULT 1,
  review_status      text,
  expires_at         timestamptz,
  created_at         timestamptz  NOT NULL DEFAULT now()
);

-- Run log for each research job (one per video/source)
CREATE TABLE IF NOT EXISTS research_runs (
  id           bigserial   PRIMARY KEY,
  trace_id     text,
  source_url   text,
  provider     text,
  model        text,
  status       text        NOT NULL DEFAULT 'pending',
  duration_ms  integer,
  cost_usd_est numeric(10,6),
  error        text,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- Raw ingested content before summarization
CREATE TABLE IF NOT EXISTS research_artifacts (
  id                  bigserial   PRIMARY KEY,
  source_url          text,
  title               text,
  channel_name        text,
  published_at        timestamptz,
  summary             text,
  content             text,
  key_points          jsonb,
  tags                jsonb,
  topic               text,
  subtheme            text,
  subthemes           jsonb,
  action_items        jsonb,
  risk_warnings       jsonb,
  opportunity_notes   jsonb,
  confidence          numeric(4,3),
  trace_id            text,
  source_type         text,
  source              text,
  strategy_built      boolean     NOT NULL DEFAULT false,
  created_at          timestamptz NOT NULL DEFAULT now()
);

-- YouTube channels and other sources to pull from
CREATE TABLE IF NOT EXISTS research_sources (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        uuid,
  source_type      text        NOT NULL,   -- 'youtube_channel', 'rss', etc.
  label            text,
  canonical_url    text,
  domain           text,
  status           text        NOT NULL DEFAULT 'active',
  priority         integer     NOT NULL DEFAULT 5,
  active           boolean     NOT NULL DEFAULT true,
  paused           boolean     NOT NULL DEFAULT false,
  schedule_paused  boolean     NOT NULL DEFAULT false,
  schedule_status  text,
  last_run_at      timestamptz,
  next_run_at      timestamptz,
  last_run_status  text,
  last_sync_error  text,
  metadata         jsonb,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

-- Source reliability scores
CREATE TABLE IF NOT EXISTS source_health_scores (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id        uuid        REFERENCES research_sources(id),
  period_start     timestamptz,
  period_end       timestamptz,
  availability_pct numeric(5,2),
  avg_latency_ms   integer,
  error_count      integer     NOT NULL DEFAULT 0,
  duplicate_count  integer     NOT NULL DEFAULT 0,
  items_retrieved  integer     NOT NULL DEFAULT 0,
  score            numeric(5,2),
  metadata         jsonb,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- SIGNAL PIPELINE  (TradingView → Review → Approved)
-- =============================================================================

-- Raw webhooks from TradingView (unprocessed)
CREATE TABLE IF NOT EXISTS tv_raw_alerts (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  source       text,
  ip           text,
  headers      jsonb,
  payload      jsonb,
  secret_valid boolean     NOT NULL DEFAULT false,
  trace_id     text,
  status       text        NOT NULL DEFAULT 'received',
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- Parsed and enriched signals
CREATE TABLE IF NOT EXISTS tv_normalized_signals (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_alert_id uuid        REFERENCES tv_raw_alerts(id),
  symbol       text        NOT NULL,
  timeframe    text,
  side         text,
  strategy_id  text,
  entry_price  numeric,
  stop_loss    numeric,
  take_profit  numeric,
  confidence   numeric,
  session_label text,
  source       text,
  trace_id     text,
  meta         jsonb,
  status       text        NOT NULL DEFAULT 'new',
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- Staged signal candidates awaiting review
CREATE TABLE IF NOT EXISTS signal_candidates (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id           uuid,
  normalized_signal_id uuid       REFERENCES tv_normalized_signals(id),
  source_signal_id    uuid,
  user_id             uuid,
  symbol              text        NOT NULL,
  market_type         text,
  setup_type          text,
  direction           text,
  timeframe           text,
  entry_price         numeric,
  stop_loss           numeric,
  take_profit         numeric,
  rr_ratio            numeric,
  confidence          numeric,
  entry_zone          jsonb,
  stop_zone           jsonb,
  target_zone         jsonb,
  raw_payload         jsonb,
  ai_review           jsonb,
  source              text,
  status              text        NOT NULL DEFAULT 'pending',
  review_status       text        NOT NULL DEFAULT 'pending',
  rejection_reason    text,
  metadata            jsonb,
  published_at        timestamptz,
  expires_at          timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

-- AI scoring results per signal
CREATE TABLE IF NOT EXISTS signal_scores (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             uuid,
  candidate_id          uuid        REFERENCES signal_candidates(id),
  signal_candidate_id   uuid,
  user_id               uuid,
  score_total           numeric,
  score_setup_quality   numeric,
  score_risk_quality    numeric,
  score_confirmation    numeric,
  score_clarity         numeric,
  market_score          numeric,
  technical_score       numeric,
  risk_score            numeric,
  quality_score         numeric,
  rr_ratio              numeric,
  confidence_label      text,
  risk_label            text,
  scoring_version       text,
  score_breakdown       jsonb,
  notes                 text,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

-- Approval/rejection decisions (audit trail)
CREATE TABLE IF NOT EXISTS signal_reviews (
  id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id               uuid,
  candidate_id            uuid        REFERENCES signal_candidates(id),
  signal_candidate_id     uuid,
  score_id                uuid        REFERENCES signal_scores(id),
  reviewer_user_id        uuid,
  reviewer_type           text        NOT NULL DEFAULT 'ai',
  review_status           text        NOT NULL DEFAULT 'pending',
  review_action           text,
  decision_reason         text,
  threshold_score         numeric,
  min_rr_ratio            numeric,
  require_medium_confidence boolean,
  score_total             numeric,
  confidence_label        text,
  risk_label              text,
  notes                   text,
  metadata                jsonb,
  reviewed_at             timestamptz,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now()
);

-- Signals that passed review — published to frontend
CREATE TABLE IF NOT EXISTS approved_signals (
  id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         uuid,
  candidate_id      uuid        REFERENCES signal_candidates(id),
  score_id          uuid        REFERENCES signal_scores(id),
  review_id         uuid        REFERENCES signal_reviews(id),
  user_id           uuid,
  symbol            text        NOT NULL,
  market_type       text,
  setup_type        text,
  direction         text,
  timeframe         text,
  headline          text,
  client_summary    text,
  why_it_matters    text,
  invalidation_note text,
  confidence_label  text,
  risk_label        text,
  score_total       numeric,
  review_status     text        NOT NULL DEFAULT 'approved',
  is_published      boolean     NOT NULL DEFAULT false,
  published_at      timestamptz,
  expires_at        timestamptz,
  metadata          jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- STRATEGY LAB  (research → strategy → backtest → demo trade)
-- =============================================================================

-- Extracted trading strategies from research
CREATE TABLE IF NOT EXISTS strategy_library (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  artifact_id         bigint      REFERENCES research_artifacts(id),
  source_url          text,
  title               text,
  channel_name        text,
  strategy_name       text,
  strategy_id         text        UNIQUE,
  description         text,
  summary             text,
  setup_type          text,
  market              text,
  asset_type          text,
  symbols             jsonb,
  timeframes          jsonb,
  session_bias        jsonb,
  entry_rules         jsonb,
  exit_rules          jsonb,
  risk_rules          jsonb,
  invalidation_rules  jsonb,
  indicators          jsonb,
  prerequisites       jsonb,
  pitfalls            jsonb,
  verification_plan   jsonb,
  confidence          numeric(4,3),
  compliance_level    text,
  tags                jsonb,
  status              text        NOT NULL DEFAULT 'draft',
  version             text,
  created_by          text,
  trace_id            text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

-- Strategy draft candidates before promotion
CREATE TABLE IF NOT EXISTS strategy_candidates (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid,
  source_id       uuid,
  transcript_id   uuid,
  candidate_name  text,
  asset_class     text,
  market_type     text,
  timeframe       text,
  entry_rules     jsonb,
  exit_rules      jsonb,
  risk_rules      jsonb,
  filters_json    jsonb,
  status          text        NOT NULL DEFAULT 'draft',
  created_by      text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- AI scoring of strategies
CREATE TABLE IF NOT EXISTS strategy_scores (
  id                       uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_uuid            uuid        REFERENCES strategy_library(id),
  candidate_id             uuid        REFERENCES strategy_candidates(id),
  strategy_id              text,
  quality_score            numeric,
  risk_score               numeric,
  clarity_score            numeric,
  testability_score        numeric,
  replicability_score      numeric,
  risk_definition_score    numeric,
  asset_fit_score          numeric,
  complexity_score         numeric,
  data_availability_score  numeric,
  penalty_score            numeric,
  total_score              numeric,
  overall_score            numeric,
  reasoning                text,
  recommendation           text,
  evidence                 jsonb,
  scored_by                text,
  trace_id                 text,
  created_at               timestamptz NOT NULL DEFAULT now()
);

-- Sources for strategies (where they came from)
CREATE TABLE IF NOT EXISTS strategy_sources (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid,
  source_type     text,
  source_url      text,
  source_title    text,
  source_author   text,
  asset_class     text,
  collected_by    text,
  collected_at    timestamptz,
  raw_reference   jsonb
);

-- Scoring dimension weights (tuned over time)
CREATE TABLE IF NOT EXISTS scoring_weights (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  scorer_type         text        NOT NULL,
  dimension           text        NOT NULL,
  weight              numeric     NOT NULL DEFAULT 1.0,
  baseline            numeric,
  adjustment_reason   text,
  is_active           boolean     NOT NULL DEFAULT true,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

-- Hermes AI review queue
CREATE TABLE IF NOT EXISTS hermes_review_queue (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  domain        text        NOT NULL,
  entity_type   text        NOT NULL,
  entity_id     uuid        NOT NULL,
  status        text        NOT NULL DEFAULT 'pending',
  attempt_count integer     NOT NULL DEFAULT 0,
  last_error    text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  processed_at  timestamptz
);

-- Hermes AI review decisions
CREATE TABLE IF NOT EXISTS hermes_reviews (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  domain                text        NOT NULL,
  entity_type           text        NOT NULL,
  entity_id             uuid        NOT NULL,
  review_type           text,
  review_score          numeric,
  review_text           text,
  recommendations_json  jsonb,
  created_by            text,
  created_at            timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- PAPER / DEMO TRADING
-- =============================================================================

-- Demo brokerage account connections
CREATE TABLE IF NOT EXISTS demo_accounts (
  id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         uuid,
  owner_user_id     uuid,
  provider          text,         -- 'oanda', 'alpaca', etc.
  account_label     text,
  account_mode      text        NOT NULL DEFAULT 'paper',
  connection_status text        NOT NULL DEFAULT 'disconnected',
  last_sync_at      timestamptz,
  metadata_json     jsonb,
  created_at        timestamptz NOT NULL DEFAULT now()
);

-- Paper trading sessions
CREATE TABLE IF NOT EXISTS demo_trade_runs (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id           uuid,
  demo_account_id     uuid        REFERENCES demo_accounts(id),
  strategy_version_id uuid,
  run_name            text,
  asset_class         text,
  run_status          text        NOT NULL DEFAULT 'active',
  started_at          timestamptz NOT NULL DEFAULT now(),
  completed_at        timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now()
);

-- Individual trade events within a run
CREATE TABLE IF NOT EXISTS demo_trade_events (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id      uuid        REFERENCES demo_trade_runs(id),
  event_type  text        NOT NULL,  -- 'entry', 'exit', 'stop_hit', etc.
  symbol      text,
  side        text,
  quantity    numeric,
  price       numeric,
  event_time  timestamptz NOT NULL DEFAULT now(),
  payload     jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- Aggregate metrics per run
CREATE TABLE IF NOT EXISTS demo_trade_metrics (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id           uuid        UNIQUE REFERENCES demo_trade_runs(id),
  trade_count      integer     NOT NULL DEFAULT 0,
  net_pnl          numeric,
  win_rate         numeric,
  max_drawdown     numeric,
  stability_score  numeric,
  recommendation   text,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- Manual paper trade journal
CREATE TABLE IF NOT EXISTS paper_trading_journal_entries (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id           uuid,
  user_id             uuid,
  strategy_version_id uuid,
  asset_class         text,
  symbol              text,
  timeframe           text,
  thesis              text,
  entry_idea          text,
  stop_loss           numeric,
  target_price        numeric,
  risk_percent        numeric,
  screenshot_urls     jsonb,
  tags                jsonb,
  entry_status        text        NOT NULL DEFAULT 'open',
  opened_at           timestamptz,
  closed_at           timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

-- Trade outcomes (P&L per journal entry)
CREATE TABLE IF NOT EXISTS paper_trading_outcomes (
  id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  journal_entry_id        uuid        REFERENCES paper_trading_journal_entries(id),
  result_label            text,        -- 'win', 'loss', 'breakeven'
  pnl_amount              numeric,
  pnl_percent             numeric,
  max_favorable_excursion numeric,
  max_adverse_excursion   numeric,
  notes                   text,
  created_at              timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_research_status        ON research (ai_enrich_status);
CREATE INDEX IF NOT EXISTS idx_research_created       ON research (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tv_raw_status          ON tv_raw_alerts (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tv_norm_status         ON tv_normalized_signals (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signal_cand_status     ON signal_candidates (review_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signal_cand_tenant     ON signal_candidates (tenant_id);
CREATE INDEX IF NOT EXISTS idx_approved_signals_pub   ON approved_signals (is_published, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_lib_status    ON strategy_library (status);
CREATE INDEX IF NOT EXISTS idx_hermes_queue_status    ON hermes_review_queue (status, created_at);
CREATE INDEX IF NOT EXISTS idx_job_queue_status       ON job_queue (status, available_at);
CREATE INDEX IF NOT EXISTS idx_job_queue_type         ON job_queue (job_type, status);
CREATE INDEX IF NOT EXISTS idx_worker_hb_type         ON worker_heartbeats (worker_type, status);

-- =============================================================================
-- ROW LEVEL SECURITY
-- Enable on tables the frontend will query directly
-- =============================================================================

ALTER TABLE tenants             ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents              ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_heartbeats   ENABLE ROW LEVEL SECURITY;
ALTER TABLE research            ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_artifacts  ENABLE ROW LEVEL SECURITY;
ALTER TABLE tv_normalized_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_candidates   ENABLE ROW LEVEL SECURITY;
ALTER TABLE approved_signals    ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategy_library    ENABLE ROW LEVEL SECURITY;
ALTER TABLE demo_trade_metrics  ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_trading_journal_entries ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS (backend uses this key — no restrictions needed)
-- Frontend uses anon key — add policies as needed when auth is wired up
-- Example read policy (uncomment and adapt when frontend auth is ready):
-- CREATE POLICY "public read approved signals"
--   ON approved_signals FOR SELECT USING (is_published = true);

-- =============================================================================
-- SEED: Insert your tenant
-- =============================================================================

INSERT INTO tenants (id, name, slug, status)
VALUES (
  'ff88f4f5-1e15-4773-8093-ff0e95cfa9d6',
  'Nexus AI',
  'nexus',
  'active'
) ON CONFLICT (id) DO NOTHING;
