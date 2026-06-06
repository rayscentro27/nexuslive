-- Content Studio: additive columns for nexus_os_content_items
-- Migration: 20260605000004_content_studio_columns.sql
-- Applied: 2026-06-06
-- Purpose: Add fields required for full Content Studio functionality.
--          ADDITIVE ONLY — no existing columns dropped, no CHECK constraints removed.
--          The existing 'type' column is left intact; 'content_type' replaces it in UI.

-- source_type: the format of the raw source material
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS source_type text DEFAULT 'manual';

-- source_url: URL of the source (YouTube link, article URL, etc.)
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS source_url text;

-- source_artifact_id: optional soft FK to nexus_os_sources
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS source_artifact_id uuid;

-- related_campaign_id: soft FK to nexus_os_revenue_campaigns
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS related_campaign_id uuid;

-- content_type: extended type set for UI (replaces old 'type' in frontend)
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS content_type text DEFAULT 'other'
    CHECK (content_type IN (
      'short_video','linkedin_post','newsletter','blog','x_thread',
      'instagram','facebook','youtube_short','script','landing_page_copy',
      'tiktok','other'
    ));

-- platform_targets: JSON list of platform names targeted for this item
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS platform_targets jsonb NOT NULL DEFAULT '[]'::jsonb;

-- global_draft: the main draft body before platform-specific adaptation
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS global_draft text;

-- compliance_status: overall compliance review state
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS compliance_status text NOT NULL DEFAULT 'not_reviewed'
    CHECK (compliance_status IN ('not_reviewed','in_review','approved','blocked'));

-- disclosure_added: confirmation that affiliate/sponsored disclosure is added
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS disclosure_added boolean NOT NULL DEFAULT false;

-- no_earnings_claims: confirms no earnings/income guarantees in copy
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS no_earnings_claims boolean NOT NULL DEFAULT false;

-- no_guarantees: confirms no result/approval/credit guarantees
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS no_guarantees boolean NOT NULL DEFAULT false;

-- approval_status: tracks approval lifecycle (separate from owner_approval_queue status)
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS approval_status text NOT NULL DEFAULT 'not_required'
    CHECK (approval_status IN ('not_required','pending_review','approved','blocked'));

-- priority: owner-set focus level
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS priority text NOT NULL DEFAULT 'medium'
    CHECK (priority IN ('high','medium','low'));

-- next_action: what to do next with this item
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS next_action text;

-- notes: internal notes and compliance observations
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS notes text;

-- archived: soft delete
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS archived boolean NOT NULL DEFAULT false;

-- Metrics (real values only — never estimated/fake)
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS views integer;
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS clicks integer;
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS conversions integer;
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS revenue_attributed numeric(12,2);
ALTER TABLE public.nexus_os_content_items
  ADD COLUMN IF NOT EXISTS performance_summary text;

-- Useful indexes for common filters
CREATE INDEX IF NOT EXISTS nexus_os_content_items_campaign_idx
  ON public.nexus_os_content_items(related_campaign_id);

CREATE INDEX IF NOT EXISTS nexus_os_content_items_priority_idx
  ON public.nexus_os_content_items(priority, status);

CREATE INDEX IF NOT EXISTS nexus_os_content_items_archived_idx
  ON public.nexus_os_content_items(archived, status);

CREATE INDEX IF NOT EXISTS nexus_os_content_items_compliance_idx
  ON public.nexus_os_content_items(compliance_status, approval_status);
