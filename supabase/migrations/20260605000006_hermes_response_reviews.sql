-- Hermes Training Center: response review/feedback table
-- Migration: 20260605000006_hermes_response_reviews.sql
-- Applied: 2026-06-06
-- Purpose: Capture Ray's feedback on Hermes recommendations so the voice/skills
--          can be tuned over time. Admin-only RLS, consistent with Nexus OS.

CREATE TABLE IF NOT EXISTS public.nexus_os_hermes_response_reviews (
  id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt                    text NOT NULL,
  response                  text NOT NULL,
  category                  text,           -- good | too_generic | too_long | not_enough_evidence | wrong_priority | robotic | useful
  evidence_checked          boolean NOT NULL DEFAULT false,
  clear_recommendation      boolean NOT NULL DEFAULT false,
  actionable_next_step      boolean NOT NULL DEFAULT false,
  unnecessary_question      boolean NOT NULL DEFAULT false,
  approval_identified       boolean NOT NULL DEFAULT false,
  revenue_impact_considered boolean NOT NULL DEFAULT false,
  safety_respected          boolean NOT NULL DEFAULT true,
  tone_natural              boolean NOT NULL DEFAULT false,
  ray_rating                integer,        -- 1-5
  ray_feedback              text,
  intent                    text,           -- classified intent at request time
  created_at                timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS nexus_os_hermes_reviews_category_idx
  ON public.nexus_os_hermes_response_reviews(category, created_at DESC);

CREATE INDEX IF NOT EXISTS nexus_os_hermes_reviews_created_idx
  ON public.nexus_os_hermes_response_reviews(created_at DESC);

ALTER TABLE public.nexus_os_hermes_response_reviews ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nexus_os_hermes_reviews_admin"
  ON public.nexus_os_hermes_response_reviews
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role IN ('admin','super_admin'))
  );
