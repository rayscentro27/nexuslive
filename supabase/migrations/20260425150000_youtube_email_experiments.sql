-- youtube_email_experiments.sql
-- Stages YouTube research artifacts into draft email experiments.
-- Safe to run multiple times (CREATE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.video_email_experiments (
  id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  research_artifact_id uuid,
  source_url         text,
  video_title        text        NOT NULL,
  topic              text,
  subtheme           text,
  audience           text        NOT NULL DEFAULT 'general_business',
  hypothesis         text,
  primary_angle      text,
  cta                text,
  status             text        NOT NULL DEFAULT 'pending'
                               CHECK (status IN ('pending', 'drafted', 'queued', 'sent', 'analyzed', 'archived')),
  metadata           jsonb       NOT NULL DEFAULT '{}'::jsonb,
  trace_id           text,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS research_artifact_id uuid;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS source_url            text;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS video_title           text;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS topic                 text;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS subtheme              text;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS audience              text;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS hypothesis            text;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS primary_angle         text;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS cta                   text;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS status                text;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS metadata              jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS trace_id              text;
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS created_at            timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.video_email_experiments ADD COLUMN IF NOT EXISTS updated_at            timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_video_email_experiments_artifact
  ON public.video_email_experiments (research_artifact_id);

CREATE INDEX IF NOT EXISTS idx_video_email_experiments_topic
  ON public.video_email_experiments (topic, subtheme);

CREATE INDEX IF NOT EXISTS idx_video_email_experiments_status
  ON public.video_email_experiments (status);

CREATE INDEX IF NOT EXISTS idx_video_email_experiments_created_at
  ON public.video_email_experiments (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_video_email_experiments_metadata
  ON public.video_email_experiments USING GIN (metadata);

COMMENT ON TABLE public.video_email_experiments IS
  'Video-backed email experiment briefs generated from YouTube research artifacts. One row per video chosen for outbound topic testing.';

COMMENT ON COLUMN public.video_email_experiments.hypothesis IS
  'What the operator expects this video/topic to prove in email, e.g. curiosity angle beats tactical angle for agency videos.';

COMMENT ON COLUMN public.video_email_experiments.primary_angle IS
  'Primary framing for the first campaign draft, e.g. contrarian insight, tactical teardown, or case study.';


CREATE TABLE IF NOT EXISTS public.email_campaigns (
  id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id      uuid,
  campaign_name      text        NOT NULL,
  topic              text,
  audience           text,
  send_channel       text        NOT NULL DEFAULT 'manual_review',
  send_status        text        NOT NULL DEFAULT 'draft'
                               CHECK (send_status IN ('draft', 'approved', 'queued', 'sent', 'paused', 'archived')),
  subject_line       text,
  preview_text       text,
  body_markdown      text,
  cta                text,
  metadata           jsonb       NOT NULL DEFAULT '{}'::jsonb,
  trace_id           text,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS experiment_id uuid;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS campaign_name  text;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS topic          text;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS audience       text;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS send_channel   text;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS send_status    text;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS subject_line   text;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS preview_text   text;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS body_markdown  text;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS cta            text;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS metadata       jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS trace_id       text;
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS created_at     timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.email_campaigns ADD COLUMN IF NOT EXISTS updated_at     timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_email_campaigns_experiment
  ON public.email_campaigns (experiment_id);

CREATE INDEX IF NOT EXISTS idx_email_campaigns_status
  ON public.email_campaigns (send_status);

CREATE INDEX IF NOT EXISTS idx_email_campaigns_topic
  ON public.email_campaigns (topic, audience);

CREATE INDEX IF NOT EXISTS idx_email_campaigns_created_at
  ON public.email_campaigns (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_campaigns_metadata
  ON public.email_campaigns USING GIN (metadata);

COMMENT ON TABLE public.email_campaigns IS
  'Draft or sent email campaigns created from video_email_experiments. Usually one base campaign per chosen video topic.';


CREATE TABLE IF NOT EXISTS public.email_variants (
  id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id        uuid,
  variant_label      text        NOT NULL,
  hook_type          text,
  angle_summary      text,
  subject_line       text,
  preview_text       text,
  body_markdown      text,
  cta                text,
  status             text        NOT NULL DEFAULT 'draft'
                               CHECK (status IN ('draft', 'approved', 'queued', 'sent', 'winner', 'loser', 'archived')),
  metadata           jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS campaign_id    uuid;
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS variant_label  text;
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS hook_type      text;
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS angle_summary  text;
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS subject_line   text;
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS preview_text   text;
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS body_markdown  text;
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS cta            text;
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS status         text;
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS metadata       jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS created_at     timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.email_variants ADD COLUMN IF NOT EXISTS updated_at     timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_email_variants_campaign
  ON public.email_variants (campaign_id);

CREATE INDEX IF NOT EXISTS idx_email_variants_status
  ON public.email_variants (status);

CREATE INDEX IF NOT EXISTS idx_email_variants_hook_type
  ON public.email_variants (hook_type);

CREATE INDEX IF NOT EXISTS idx_email_variants_created_at
  ON public.email_variants (created_at DESC);

COMMENT ON TABLE public.email_variants IS
  'A/B or multivariate email drafts for one campaign. Each variant changes the hook, subject line, or framing while keeping the same core video insight.';


CREATE TABLE IF NOT EXISTS public.email_send_events (
  id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id        uuid,
  variant_id         uuid,
  recipient_email    text,
  event_type         text        NOT NULL
                               CHECK (event_type IN ('queued', 'sent', 'delivered', 'opened', 'clicked', 'replied', 'bounced', 'converted', 'unsubscribed')),
  event_at           timestamptz NOT NULL DEFAULT now(),
  metadata           jsonb       NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE public.email_send_events ADD COLUMN IF NOT EXISTS campaign_id     uuid;
ALTER TABLE public.email_send_events ADD COLUMN IF NOT EXISTS variant_id      uuid;
ALTER TABLE public.email_send_events ADD COLUMN IF NOT EXISTS recipient_email text;
ALTER TABLE public.email_send_events ADD COLUMN IF NOT EXISTS event_type      text;
ALTER TABLE public.email_send_events ADD COLUMN IF NOT EXISTS event_at        timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.email_send_events ADD COLUMN IF NOT EXISTS metadata        jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_email_send_events_campaign
  ON public.email_send_events (campaign_id, event_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_send_events_variant
  ON public.email_send_events (variant_id, event_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_send_events_type
  ON public.email_send_events (event_type, event_at DESC);

COMMENT ON TABLE public.email_send_events IS
  'Low-level delivery and engagement events for outbound email experiments. Can be populated manually or by an email provider webhook later.';


CREATE TABLE IF NOT EXISTS public.email_experiment_results (
  id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id        uuid,
  variant_id         uuid,
  metric_window      text        NOT NULL DEFAULT 'lifetime',
  recipients_count   integer     NOT NULL DEFAULT 0,
  delivered_count    integer     NOT NULL DEFAULT 0,
  open_count         integer     NOT NULL DEFAULT 0,
  click_count        integer     NOT NULL DEFAULT 0,
  reply_count        integer     NOT NULL DEFAULT 0,
  conversion_count   integer     NOT NULL DEFAULT 0,
  revenue            numeric     NOT NULL DEFAULT 0,
  notes              text,
  created_at         timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS campaign_id      uuid;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS variant_id       uuid;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS metric_window    text;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS recipients_count integer NOT NULL DEFAULT 0;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS delivered_count  integer NOT NULL DEFAULT 0;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS open_count       integer NOT NULL DEFAULT 0;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS click_count      integer NOT NULL DEFAULT 0;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS reply_count      integer NOT NULL DEFAULT 0;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS conversion_count integer NOT NULL DEFAULT 0;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS revenue          numeric NOT NULL DEFAULT 0;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS notes            text;
ALTER TABLE public.email_experiment_results ADD COLUMN IF NOT EXISTS created_at       timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_email_experiment_results_campaign
  ON public.email_experiment_results (campaign_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_experiment_results_variant
  ON public.email_experiment_results (variant_id, created_at DESC);

COMMENT ON TABLE public.email_experiment_results IS
  'Rollup metrics for email campaigns and variants so operators can compare topics, hooks, and outcomes without scanning raw send events.';
