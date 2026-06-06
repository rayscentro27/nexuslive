-- Approval History & Event Tracking
-- Migration: 20260605000002_approval_history.sql
-- Applied: 2026-06-05
-- Purpose: Track full lifecycle of approval queue items
--          (created → notified → viewed → approved/rejected → completed/failed)

-- ─── nexus_os_approval_events ──────────────────────────────────────────────
-- Append-only event log for each approval item in owner_approval_queue.
-- One row per state transition. Never update, only INSERT.
CREATE TABLE IF NOT EXISTS public.nexus_os_approval_events (
  id              uuid       PRIMARY KEY DEFAULT gen_random_uuid(),
  approval_id     uuid       NOT NULL,   -- references owner_approval_queue(id) — soft FK
  event_type      text       NOT NULL    CHECK (event_type IN (
    'created',       -- item first added to queue
    'notified',      -- Telegram/Supabase notification sent
    'viewed',        -- Ray opened the item in Nexus OS
    'approved',      -- Ray approved
    'rejected',      -- Ray rejected
    'needs_changes', -- Ray requested changes
    'completed',     -- downstream executor confirmed success
    'failed',        -- downstream executor reported failure
    'comment'        -- a review note added without status change
  )),
  changed_by      text,                  -- 'ray' | 'hermes' | 'telegram_gate' | agent name
  comment         text,                  -- optional note
  telegram_sent   boolean    NOT NULL DEFAULT false,
  notification_id uuid,                  -- optional FK to notifications table
  metadata        jsonb      NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS nexus_os_approval_events_approval_idx
  ON public.nexus_os_approval_events(approval_id, created_at DESC);

CREATE INDEX IF NOT EXISTS nexus_os_approval_events_type_idx
  ON public.nexus_os_approval_events(event_type, created_at DESC);

ALTER TABLE public.nexus_os_approval_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nexus_os_approval_events_admin"
  ON public.nexus_os_approval_events
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
    )
  );

-- ─── Function: log_approval_event ──────────────────────────────────────────
-- Convenience RPC for inserting events from the server side.
-- Frontend uses the Netlify function; this is for Python/Hermes side.
CREATE OR REPLACE FUNCTION public.log_approval_event(
  p_approval_id   uuid,
  p_event_type    text,
  p_changed_by    text    DEFAULT 'system',
  p_comment       text    DEFAULT NULL,
  p_telegram_sent boolean DEFAULT false,
  p_metadata      jsonb   DEFAULT '{}'::jsonb
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_id uuid;
BEGIN
  INSERT INTO public.nexus_os_approval_events
    (approval_id, event_type, changed_by, comment, telegram_sent, metadata)
  VALUES
    (p_approval_id, p_event_type, p_changed_by, p_comment, p_telegram_sent, p_metadata)
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$;

-- ─── View: nexus_os_approval_with_history ──────────────────────────────────
-- Joins owner_approval_queue with the latest event for each item.
-- Useful for the Nexus OS Approval Center to show full state.
CREATE OR REPLACE VIEW public.nexus_os_approval_with_history AS
SELECT
  q.id,
  q.action_type,
  q.description,
  q.payload,
  q.requested_by,
  q.priority,
  q.status,
  q.review_notes,
  q.expires_at,
  q.created_at,
  q.reviewed_at,
  -- Aggregated event counts
  COUNT(e.id)                                         AS event_count,
  BOOL_OR(e.event_type = 'notified')                  AS was_notified,
  BOOL_OR(e.event_type = 'viewed')                    AS was_viewed,
  BOOL_OR(e.telegram_sent)                            AS telegram_sent,
  MAX(e.created_at) FILTER (WHERE e.event_type = 'notified') AS last_notified_at,
  MAX(e.created_at) FILTER (WHERE e.event_type = 'viewed')   AS last_viewed_at
FROM public.owner_approval_queue q
LEFT JOIN public.nexus_os_approval_events e ON e.approval_id = q.id
GROUP BY q.id;

-- Note: view inherits RLS from owner_approval_queue and nexus_os_approval_events underlying tables.
-- No OWNER change needed — migration runner role is sufficient.

-- ─── Trigger: auto-log approval status changes ──────────────────────────────
-- When owner_approval_queue.status changes, automatically insert a history event.
CREATE OR REPLACE FUNCTION public._log_approval_status_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  IF (OLD.status IS DISTINCT FROM NEW.status) THEN
    INSERT INTO public.nexus_os_approval_events
      (approval_id, event_type, changed_by, comment)
    VALUES (
      NEW.id,
      CASE NEW.status
        WHEN 'approved'     THEN 'approved'
        WHEN 'rejected'     THEN 'rejected'
        WHEN 'needs_edits'  THEN 'needs_changes'
        ELSE 'comment'
      END,
      'supabase_trigger',
      NEW.review_notes
    );
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_approval_status_change ON public.owner_approval_queue;
CREATE TRIGGER trg_approval_status_change
  AFTER UPDATE OF status ON public.owner_approval_queue
  FOR EACH ROW
  EXECUTE FUNCTION public._log_approval_status_change();
