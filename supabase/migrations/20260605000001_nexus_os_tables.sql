-- Nexus OS Foundation Tables
-- Migration: 20260605000001_nexus_os_tables.sql
-- Applied: 2026-06-05
-- Purpose: Tables for Nexus OS operating layer (tool registry, content items,
--          revenue campaigns, OS artifacts, knowledge graph entities)
-- Note: owner_approval_queue, notifications, nexus_knowledge_items already exist.
--       This migration adds NEW tables only. Does not modify existing RLS.

-- Idempotent: uses CREATE TABLE IF NOT EXISTS throughout

-- ─── nexus_os_tool_registry ────────────────────────────────────────────────
-- Stores live/configurable tool registry entries (vs. static frontend registry)
CREATE TABLE IF NOT EXISTS public.nexus_os_tool_registry (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL UNIQUE,
  type          text NOT NULL CHECK (type IN ('ai_model','platform','integration','service','agent')),
  status        text NOT NULL DEFAULT 'unknown' CHECK (status IN ('online','offline','limited','unknown')),
  best_use      text,
  cost_level    text NOT NULL DEFAULT 'unknown' CHECK (cost_level IN ('free','low','medium','high','unknown')),
  auth_method   text,
  allowed_actions jsonb NOT NULL DEFAULT '[]'::jsonb,
  approval_required boolean NOT NULL DEFAULT false,
  log_path      text,
  notes         text,
  last_success  timestamptz,
  last_failure  timestamptz,
  last_checked  timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS nexus_os_tool_registry_status_idx ON public.nexus_os_tool_registry(status);
ALTER TABLE public.nexus_os_tool_registry ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nexus_os_tool_registry_admin" ON public.nexus_os_tool_registry
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role IN ('admin','super_admin'))
  );

-- ─── nexus_os_content_items ────────────────────────────────────────────────
-- Content draft queue for the Content Studio
CREATE TABLE IF NOT EXISTS public.nexus_os_content_items (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title                 text NOT NULL,
  type                  text NOT NULL,   -- youtube_short | tiktok | instagram | linkedin | newsletter | blog | x
  status                text NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','approval_needed','approved','scheduled','published','archived')),
  source_id             uuid,            -- references a source asset if available
  source_description    text,
  content_body          text,
  platform_variations   jsonb NOT NULL DEFAULT '[]'::jsonb,
  compliance_note       text,
  disclosure_required   boolean NOT NULL DEFAULT true,
  approval_id           uuid,            -- references owner_approval_queue if approval was requested
  scheduled_at          timestamptz,
  published_at          timestamptz,
  analytics_url         text,
  lesson_stored         boolean NOT NULL DEFAULT false,
  created_by_agent      text,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS nexus_os_content_items_status_idx ON public.nexus_os_content_items(status);
CREATE INDEX IF NOT EXISTS nexus_os_content_items_created_at_idx ON public.nexus_os_content_items(created_at DESC);
ALTER TABLE public.nexus_os_content_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nexus_os_content_items_admin" ON public.nexus_os_content_items
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role IN ('admin','super_admin'))
  );

-- ─── nexus_os_revenue_campaigns ────────────────────────────────────────────
-- Affiliate and revenue campaign registry
CREATE TABLE IF NOT EXISTS public.nexus_os_revenue_campaigns (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  program_name          text NOT NULL,
  niche                 text NOT NULL,
  application_status    text NOT NULL DEFAULT 'not_applied'
    CHECK (application_status IN ('not_applied','applied','pending','approved','rejected','paused')),
  link_status           text NOT NULL DEFAULT 'none'
    CHECK (link_status IN ('none','pending','active','expired')),
  affiliate_link        text,            -- stored securely; never exposed in public policy
  landing_page_status   text NOT NULL DEFAULT 'none'
    CHECK (landing_page_status IN ('none','draft','review','ready')),
  landing_page_url      text,
  compliance_ok         boolean NOT NULL DEFAULT false,
  disclosure_ok         boolean NOT NULL DEFAULT false,
  traffic_source        text,
  content_queue_count   integer NOT NULL DEFAULT 0,
  clicks                integer,
  conversions           integer,
  revenue_usd           numeric(12,2),
  next_action           text,
  notes                 text,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS nexus_os_revenue_campaigns_status_idx ON public.nexus_os_revenue_campaigns(application_status);
ALTER TABLE public.nexus_os_revenue_campaigns ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nexus_os_revenue_campaigns_admin" ON public.nexus_os_revenue_campaigns
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role IN ('admin','super_admin'))
  );

-- ─── nexus_os_sources ──────────────────────────────────────────────────────
-- Source intake assets for the Content Studio / Knowledge Hub
CREATE TABLE IF NOT EXISTS public.nexus_os_sources (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title           text NOT NULL,
  type            text NOT NULL CHECK (type IN ('transcript','article','video','document','session_notes','url','audio')),
  status          text NOT NULL DEFAULT 'ingested'
    CHECK (status IN ('ingested','summarized','ideas_generated','drafts_ready','archived')),
  content_url     text,
  file_path       text,
  raw_text        text,
  summary         text,
  ideas           jsonb NOT NULL DEFAULT '[]'::jsonb,
  tags            jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_by      text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS nexus_os_sources_status_idx ON public.nexus_os_sources(status);
CREATE INDEX IF NOT EXISTS nexus_os_sources_created_at_idx ON public.nexus_os_sources(created_at DESC);
ALTER TABLE public.nexus_os_sources ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nexus_os_sources_admin" ON public.nexus_os_sources
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role IN ('admin','super_admin'))
  );

-- ─── nexus_os_entities ─────────────────────────────────────────────────────
-- Knowledge graph nodes
CREATE TABLE IF NOT EXISTS public.nexus_os_entities (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  type        text NOT NULL CHECK (type IN (
    'source','transcript','artifact','task','agent','tool','workflow',
    'skill','rule','client','campaign','trading_strategy','approval',
    'blocker','failure','decision','metric','output','prompt','sop'
  )),
  description text,
  metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
  tags        jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS nexus_os_entities_type_idx ON public.nexus_os_entities(type);
CREATE INDEX IF NOT EXISTS nexus_os_entities_name_idx ON public.nexus_os_entities(name);
ALTER TABLE public.nexus_os_entities ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nexus_os_entities_admin" ON public.nexus_os_entities
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role IN ('admin','super_admin'))
  );

-- ─── nexus_os_relationships ────────────────────────────────────────────────
-- Knowledge graph edges
CREATE TABLE IF NOT EXISTS public.nexus_os_relationships (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  from_entity_id  uuid NOT NULL REFERENCES public.nexus_os_entities(id) ON DELETE CASCADE,
  to_entity_id    uuid NOT NULL REFERENCES public.nexus_os_entities(id) ON DELETE CASCADE,
  relationship    text NOT NULL CHECK (relationship IN (
    'produced_by','belongs_to','supports','depends_on','blocked_by',
    'approved_by','tested_by','improves','replaces','contradicts',
    'deployed_to','related_to'
  )),
  metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS nexus_os_relationships_from_idx ON public.nexus_os_relationships(from_entity_id);
CREATE INDEX IF NOT EXISTS nexus_os_relationships_to_idx ON public.nexus_os_relationships(to_entity_id);
ALTER TABLE public.nexus_os_relationships ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nexus_os_relationships_admin" ON public.nexus_os_relationships
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role IN ('admin','super_admin'))
  );

-- ─── nexus_os_provider_events ──────────────────────────────────────────────
-- Log of tool/provider health events (pings, failures, rate limit hits)
CREATE TABLE IF NOT EXISTS public.nexus_os_provider_events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider    text NOT NULL,
  event_type  text NOT NULL CHECK (event_type IN ('ping','success','failure','rate_limit','timeout','config_change')),
  detail      text,
  metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS nexus_os_provider_events_provider_idx ON public.nexus_os_provider_events(provider, created_at DESC);
ALTER TABLE public.nexus_os_provider_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nexus_os_provider_events_admin" ON public.nexus_os_provider_events
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role IN ('admin','super_admin'))
  );

-- ─── Updated_at triggers ───────────────────────────────────────────────────
-- Reuse existing touch_updated_at() function if present

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'touch_updated_at') THEN
    -- tool registry
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_nexus_os_tool_registry_touch') THEN
      EXECUTE 'CREATE TRIGGER trg_nexus_os_tool_registry_touch
        BEFORE UPDATE ON public.nexus_os_tool_registry
        FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at()';
    END IF;
    -- content items
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_nexus_os_content_items_touch') THEN
      EXECUTE 'CREATE TRIGGER trg_nexus_os_content_items_touch
        BEFORE UPDATE ON public.nexus_os_content_items
        FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at()';
    END IF;
    -- revenue campaigns
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_nexus_os_revenue_campaigns_touch') THEN
      EXECUTE 'CREATE TRIGGER trg_nexus_os_revenue_campaigns_touch
        BEFORE UPDATE ON public.nexus_os_revenue_campaigns
        FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at()';
    END IF;
    -- sources
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_nexus_os_sources_touch') THEN
      EXECUTE 'CREATE TRIGGER trg_nexus_os_sources_touch
        BEFORE UPDATE ON public.nexus_os_sources
        FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at()';
    END IF;
    -- entities
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_nexus_os_entities_touch') THEN
      EXECUTE 'CREATE TRIGGER trg_nexus_os_entities_touch
        BEFORE UPDATE ON public.nexus_os_entities
        FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at()';
    END IF;
  END IF;
END;
$$;
