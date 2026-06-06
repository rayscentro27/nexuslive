-- Revenue Hub: additive columns for nexus_os_revenue_campaigns
-- Migration: 20260605000003_revenue_hub_columns.sql
-- Applied: 2026-06-05
-- Purpose: Add missing fields for full Revenue Hub functionality.
--          ADDITIVE ONLY — no existing columns dropped or altered.
--          No RLS changes — existing admin-only policy is sufficient.

-- campaign_type: affiliate | direct | partnership | content | referral_program
ALTER TABLE public.nexus_os_revenue_campaigns
  ADD COLUMN IF NOT EXISTS campaign_type text NOT NULL DEFAULT 'affiliate'
    CHECK (campaign_type IN ('affiliate','direct','partnership','content','referral_program'));

-- offer_url: public URL of the offer/product page (non-sensitive)
ALTER TABLE public.nexus_os_revenue_campaigns
  ADD COLUMN IF NOT EXISTS offer_url text;

-- priority: owner-set priority for focus
ALTER TABLE public.nexus_os_revenue_campaigns
  ADD COLUMN IF NOT EXISTS priority text NOT NULL DEFAULT 'medium'
    CHECK (priority IN ('high','medium','low'));

-- estimated_value: owner's estimated revenue potential (USD) — not a guarantee
ALTER TABLE public.nexus_os_revenue_campaigns
  ADD COLUMN IF NOT EXISTS estimated_value numeric(12,2);

-- approval_status: tracks whether this campaign has been reviewed and approved for launch prep
ALTER TABLE public.nexus_os_revenue_campaigns
  ADD COLUMN IF NOT EXISTS approval_status text NOT NULL DEFAULT 'not_required'
    CHECK (approval_status IN ('not_required','pending_review','approved','blocked'));

-- archived: soft delete — hides from active list without deleting data
ALTER TABLE public.nexus_os_revenue_campaigns
  ADD COLUMN IF NOT EXISTS archived boolean NOT NULL DEFAULT false;

-- Index for common filters
CREATE INDEX IF NOT EXISTS nexus_os_revenue_campaigns_priority_idx
  ON public.nexus_os_revenue_campaigns(priority, application_status);

CREATE INDEX IF NOT EXISTS nexus_os_revenue_campaigns_archived_idx
  ON public.nexus_os_revenue_campaigns(archived, application_status);
