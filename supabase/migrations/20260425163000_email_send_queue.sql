-- email_send_queue.sql
-- Adds an explicit approval/queue layer for outbound email experiment drafts.
-- Safe to run multiple times (CREATE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.email_send_queue (
  id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id        uuid,
  variant_id         uuid,
  send_channel       text        NOT NULL DEFAULT 'manual_review',
  queue_status       text        NOT NULL DEFAULT 'approved'
                               CHECK (queue_status IN ('approved', 'queued', 'sent', 'cancelled', 'failed')),
  scheduled_for      timestamptz,
  approved_at        timestamptz,
  sent_at            timestamptz,
  approval_note      text,
  metadata           jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS campaign_id    uuid;
ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS variant_id     uuid;
ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS send_channel   text;
ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS queue_status   text;
ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS scheduled_for  timestamptz;
ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS approved_at    timestamptz;
ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS sent_at        timestamptz;
ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS approval_note  text;
ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS metadata       jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS created_at     timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.email_send_queue ADD COLUMN IF NOT EXISTS updated_at     timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_email_send_queue_campaign
  ON public.email_send_queue (campaign_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_send_queue_variant
  ON public.email_send_queue (variant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_email_send_queue_status
  ON public.email_send_queue (queue_status, scheduled_for);

CREATE INDEX IF NOT EXISTS idx_email_send_queue_metadata
  ON public.email_send_queue USING GIN (metadata);

COMMENT ON TABLE public.email_send_queue IS
  'Explicit approval and queue records for email experiment variants before they are sent through a real provider.';

COMMENT ON COLUMN public.email_send_queue.queue_status IS
  'Approval and send lifecycle: approved, queued, sent, cancelled, failed.';
