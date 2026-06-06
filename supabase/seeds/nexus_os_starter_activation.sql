-- Nexus OS Starter Data Activation
-- File: supabase/seeds/nexus_os_starter_activation.sql
-- Purpose: Seed starter revenue campaigns + content drafts + source notes,
--          then sync the knowledge graph. Idempotent and re-runnable.
--
-- SAFETY:
--   - All campaigns/content start in safe pre-launch statuses.
--   - No published/scheduled content. No affiliate URLs. No fake metrics.
--   - No earnings claims, no guarantees. Disclosure flags honest.
--   - Graph sync writes only to nexus_os_entities / nexus_os_relationships;
--     source records are never modified.
--   - Dedup: campaigns/content by name/title NOT EXISTS; entities by
--     (source_table, source_id); relationships by (from, to, relationship).

-- ============================================================================
-- PHASE 1 — STARTER REVENUE CAMPAIGNS
-- ============================================================================

INSERT INTO public.nexus_os_revenue_campaigns
  (program_name, niche, campaign_type, priority, application_status, link_status,
   landing_page_status, compliance_ok, disclosure_ok, approval_status,
   content_queue_count, clicks, conversions, revenue_usd, estimated_value,
   next_action, notes, archived)
SELECT v.* FROM (VALUES
  ('Nav', 'Business Credit & Funding', 'affiliate', 'high',
   'not_applied','none','draft', false, false, 'not_required',
   0, 0, 0, 0, NULL::numeric,
   'Prepare compliance-safe affiliate/content funnel and create first content drafts.',
   'High-fit business credit audience. Affiliate disclosure required. No earnings/approval claims. No affiliate URL stored yet.',
   false),
  ('LegalZoom', 'Business Formation & Legal', 'affiliate', 'medium',
   'not_applied','none','draft', false, false, 'not_required',
   0, 0, 0, 0, NULL,
   'Prepare business formation content and compliance-safe CTA.',
   'Pairs with LLC/EIN content. Compliance review required. No guarantees. No affiliate URL stored yet.',
   false),
  ('Newsletter Platform (Beehiiv TBD)', 'Creator / Newsletter Tools', 'content', 'medium',
   'not_applied','none','draft', false, false, 'not_required',
   0, 0, 0, 0, NULL,
   'Decide whether Beehiiv or an alternative newsletter platform is the best fit.',
   'Evaluate Beehiiv vs alternatives before committing. Content-first.',
   false),
  ('Business Credit Builder', 'Business Credit / Education', 'content', 'high',
   'not_applied','none','draft', false, false, 'not_required',
   0, 0, 0, 0, NULL,
   'Create educational business-credit checklist content.',
   'Educational first. No score/approval guarantees. Disclosure if any affiliate tool mentioned.',
   false),
  ('Paydex Education', 'Business Credit Education', 'content', 'high',
   'not_applied','none','draft', false, false, 'not_required',
   0, 0, 0, 0, NULL,
   'Create educational PAYDEX explainer content with no guarantees.',
   'Explainer only. No guaranteed results. Educational framing throughout.',
   false)
) AS v(program_name, niche, campaign_type, priority, application_status, link_status,
   landing_page_status, compliance_ok, disclosure_ok, approval_status,
   content_queue_count, clicks, conversions, revenue_usd, estimated_value,
   next_action, notes, archived)
WHERE NOT EXISTS (
  SELECT 1 FROM public.nexus_os_revenue_campaigns c WHERE lower(c.program_name) = lower(v.program_name)
);

-- ============================================================================
-- PHASE 3 — SOURCE NOTES (created before content so content can optionally link)
-- ============================================================================

INSERT INTO public.nexus_os_sources (title, type, status, summary, ideas, tags, created_by)
SELECT v.* FROM (VALUES
  ('Nexus OS starter revenue activation', 'session_notes', 'ingested',
   'Activation pass: seed campaigns + content drafts + graph links to move Nexus OS from empty infrastructure to a working starter revenue engine.',
   '[]'::jsonb, '["nexus-os","activation","revenue"]'::jsonb, 'ray'),
  ('Ray goal: turn Nexus OS into a revenue generator', 'session_notes', 'ingested',
   'Primary objective is monetization via affiliate + content campaigns, approval-gated, no feature detours.',
   '[]'::jsonb, '["goal","revenue","strategy"]'::jsonb, 'ray'),
  ('Compliance guardrail: no publishing/outreach without approval', 'session_notes', 'ingested',
   'All publishing, scheduling, outreach, and affiliate activation require explicit approval. No earnings claims. Disclosure required.',
   '[]'::jsonb, '["compliance","guardrail","safety"]'::jsonb, 'ray'),
  ('Content strategy: campaign -> content draft -> approval -> publish later', 'session_notes', 'ingested',
   'Workflow: create campaign, draft content linked to it, request approval, publish only after approval.',
   '[]'::jsonb, '["content","workflow","strategy"]'::jsonb, 'ray')
) AS v(title, type, status, summary, ideas, tags, created_by)
WHERE NOT EXISTS (
  SELECT 1 FROM public.nexus_os_sources s WHERE s.title = v.title
);

-- ============================================================================
-- PHASE 2 — STARTER CONTENT DRAFTS (linked to campaigns via related_campaign_id)
-- ============================================================================
-- Helper: resolve campaign id by name at insert time.

INSERT INTO public.nexus_os_content_items
  (title, type, content_type, status, related_campaign_id, global_draft,
   platform_targets, platform_variations, compliance_status, disclosure_required,
   disclosure_added, no_earnings_claims, no_guarantees, approval_status, priority,
   next_action, notes, lesson_stored, archived, scheduled_at, published_at)
SELECT
  d.title, d.content_type, d.content_type, 'draft',
  (SELECT id FROM public.nexus_os_revenue_campaigns WHERE lower(program_name) = lower(d.campaign) LIMIT 1),
  d.global_draft, d.platform_targets, d.platform_variations,
  'not_reviewed', d.disclosure_required, d.disclosure_added, true, true,
  'not_required', d.priority, d.next_action, d.notes, false, false, NULL, NULL
FROM (VALUES
  -- ── Nav ──
  ('Nav — How business credit separates your personal and business finances (LinkedIn)',
   'Nav', 'linkedin_post', 'high',
   'Most new owners mix personal and business credit and never realize the cost. Here is a compliance-safe breakdown of why separating them matters and how to start. Educational only — no guaranteed outcomes. Affiliate disclosure applies.',
   '["LinkedIn"]'::jsonb,
   '[{"platform":"LinkedIn","draft_text":"Why business credit matters for new owners — and the first 3 steps. Educational, no guarantees.","caption":"Business credit basics","hashtags":["#businesscredit","#smallbusiness"],"cta":"Follow for more business credit basics","disclosure_note":"May contain affiliate links. Educational only, no guaranteed results.","status":"draft","approval_required":true}]'::jsonb,
   true, true,
   'Finish draft, run compliance review, add disclosure to final, then request approval.',
   'Affiliate-related. Disclosure included in draft. No earnings/approval claims.'),
  ('Nav — Business credit basics in 30 seconds (Short script)',
   'Nav', 'youtube_short', 'high',
   'Hook: "Your business has its own credit score." 30-second explainer on what business credit is and why separating it from personal matters. Educational. No guarantees. Affiliate disclosure on screen + description.',
   '["YouTube Shorts","TikTok"]'::jsonb,
   '[{"platform":"YouTube Shorts","draft_text":"Your business has its own credit score. Here is what that means in 30 seconds.","caption":"Business credit explained","hashtags":["#businesscredit","#entrepreneur"],"cta":"Save this for later","disclosure_note":"Educational only. May include affiliate links. No guaranteed results.","status":"draft","approval_required":true}]'::jsonb,
   true, true,
   'Record rough cut after script approval. Add on-screen disclosure.',
   'Short-form. Disclosure noted. No guarantees.'),
  ('Nav — Newsletter blurb: start your business credit file',
   'Nav', 'newsletter', 'medium',
   'Short newsletter section introducing business credit and one concrete first step. Educational framing. Disclosure included. No earnings or approval guarantees.',
   '["Newsletter"]'::jsonb,
   '[{"platform":"Newsletter","draft_text":"This week: what a business credit file is and one step to start one. Educational only.","caption":"","hashtags":[],"cta":"Reply with questions","disclosure_note":"This email may contain affiliate links. Educational only.","status":"draft","approval_required":true}]'::jsonb,
   true, true,
   'Finalize copy, confirm disclosure, request approval before any send.',
   'Newsletter blurb. Not scheduled. Disclosure included.'),
  -- ── LegalZoom ──
  ('LegalZoom — Should you form an LLC yourself or use a service? (LinkedIn)',
   'LegalZoom', 'linkedin_post', 'medium',
   'Balanced, compliance-safe comparison of DIY LLC formation vs using a service. Educational. No legal advice. Disclosure applies for any affiliate mention.',
   '["LinkedIn"]'::jsonb,
   '[{"platform":"LinkedIn","draft_text":"DIY LLC vs formation service: a balanced look. Not legal advice.","caption":"LLC formation","hashtags":["#LLC","#smallbusiness"],"cta":"Follow for business setup tips","disclosure_note":"May contain affiliate links. Not legal advice. Educational only.","status":"draft","approval_required":true}]'::jsonb,
   true, true,
   'Compliance review for legal-advice language, add disclosure, request approval.',
   'Avoid legal-advice phrasing. Disclosure included.'),
  ('LegalZoom — Forming your business entity (Short script)',
   'LegalZoom', 'youtube_short', 'medium',
   '30-second explainer on the basic steps to form a business entity. Educational, not legal advice. Disclosure on screen + description.',
   '["YouTube Shorts","TikTok"]'::jsonb,
   '[{"platform":"YouTube Shorts","draft_text":"Forming a business entity: the basic steps in 30 seconds. Not legal advice.","caption":"Business formation","hashtags":["#LLC","#startup"],"cta":"Save for later","disclosure_note":"Educational only, not legal advice. May include affiliate links.","status":"draft","approval_required":true}]'::jsonb,
   true, true,
   'Record after script approval.',
   'Not legal advice. Disclosure noted.'),
  -- ── Business Credit Builder ──
  ('Business Credit Builder — 7-step starter checklist (post)',
   'Business Credit Builder', 'linkedin_post', 'high',
   'Checklist-style educational post: 7 concrete steps to begin building business credit. No guarantees of approval or score increases. Educational framing throughout.',
   '["LinkedIn","Blog"]'::jsonb,
   '[{"platform":"LinkedIn","draft_text":"7 steps to start building business credit (educational checklist, no guarantees).","caption":"Business credit checklist","hashtags":["#businesscredit","#entrepreneur"],"cta":"Save this checklist","disclosure_note":"Educational only. No guaranteed results. May include affiliate links.","status":"draft","approval_required":true}]'::jsonb,
   true, true,
   'Compliance review for guarantee-free language, request approval.',
   'Checklist. No score/approval guarantees.'),
  ('Business Credit Builder — Checklist explainer (Short script)',
   'Business Credit Builder', 'youtube_short', 'medium',
   '30-second walkthrough of the first 3 checklist steps. Educational. No guarantees.',
   '["YouTube Shorts","TikTok"]'::jsonb,
   '[{"platform":"YouTube Shorts","draft_text":"First 3 steps to build business credit. Educational, no guarantees.","caption":"Business credit steps","hashtags":["#businesscredit"],"cta":"Follow for the full checklist","disclosure_note":"Educational only. No guaranteed results.","status":"draft","approval_required":true}]'::jsonb,
   true, true,
   'Record after approval.',
   'Short-form checklist. No guarantees.'),
  -- ── Paydex Education ──
  ('Paydex Education — What is a PAYDEX score? (Explainer post)',
   'Paydex Education', 'linkedin_post', 'high',
   'Plain-language explainer of what a PAYDEX score is and how it is generally understood. Educational only. No guarantees of any specific score outcome.',
   '["LinkedIn","Blog"]'::jsonb,
   '[{"platform":"LinkedIn","draft_text":"What is a PAYDEX score? A plain-language explainer. Educational, no guarantees.","caption":"PAYDEX explained","hashtags":["#PAYDEX","#businesscredit"],"cta":"Follow for more explainers","disclosure_note":"Educational only. No guaranteed results.","status":"draft","approval_required":true}]'::jsonb,
   true, true,
   'Compliance review to keep it guarantee-free, request approval.',
   'Explainer. No guaranteed score outcomes.'),
  ('Paydex Education — PAYDEX in 30 seconds (Short script)',
   'Paydex Education', 'youtube_short', 'medium',
   '30-second explainer defining PAYDEX simply. Educational. No guarantees.',
   '["YouTube Shorts","TikTok"]'::jsonb,
   '[{"platform":"YouTube Shorts","draft_text":"PAYDEX score explained in 30 seconds. Educational, no guarantees.","caption":"PAYDEX basics","hashtags":["#PAYDEX"],"cta":"Save this","disclosure_note":"Educational only. No guaranteed results.","status":"draft","approval_required":true}]'::jsonb,
   true, true,
   'Record after approval.',
   'Short explainer. No guarantees.'),
  -- ── Newsletter Platform (optional) ──
  ('Newsletter — Launch announcement blurb',
   'Newsletter Platform (Beehiiv TBD)', 'newsletter', 'low',
   'Short announcement introducing the newsletter and what subscribers will get. Educational/value framing. No earnings claims.',
   '["Newsletter","LinkedIn"]'::jsonb,
   '[{"platform":"Newsletter","draft_text":"Introducing the newsletter: practical business credit and funding education, no hype.","caption":"","hashtags":[],"cta":"Subscribe for weekly tips","disclosure_note":"Educational only. May include affiliate links.","status":"draft","approval_required":true}]'::jsonb,
   true, true,
   'Decide platform first, then finalize and request approval before any send.',
   'Announcement draft. Not scheduled. Platform TBD.')
) AS d(title, campaign, content_type, priority, global_draft, platform_targets,
       platform_variations, disclosure_required, disclosure_added, next_action, notes)
WHERE NOT EXISTS (
  SELECT 1 FROM public.nexus_os_content_items ci WHERE ci.title = d.title
);

-- ============================================================================
-- PHASE 4 — KNOWLEDGE GRAPH SYNC (entities + relationships; graph tables only)
-- ============================================================================

-- Campaign entities
INSERT INTO public.nexus_os_entities (type, name, title, summary, source_table, source_id, status)
SELECT 'revenue_campaign', program_name, program_name,
       niche || ' · ' || priority || ' priority', 'nexus_os_revenue_campaigns', id, application_status
FROM public.nexus_os_revenue_campaigns WHERE NOT archived
ON CONFLICT (source_table, source_id) WHERE source_table IS NOT NULL AND source_id IS NOT NULL DO NOTHING;

-- Content entities
INSERT INTO public.nexus_os_entities (type, name, title, summary, source_table, source_id, status)
SELECT 'content_item', title, title,
       content_type || ' · ' || status, 'nexus_os_content_items', id, status
FROM public.nexus_os_content_items WHERE NOT archived
ON CONFLICT (source_table, source_id) WHERE source_table IS NOT NULL AND source_id IS NOT NULL DO NOTHING;

-- Source entities
INSERT INTO public.nexus_os_entities (type, name, title, summary, source_table, source_id, status)
SELECT 'source', title, title, COALESCE(summary, type), 'nexus_os_sources', id, status
FROM public.nexus_os_sources WHERE status != 'archived'
ON CONFLICT (source_table, source_id) WHERE source_table IS NOT NULL AND source_id IS NOT NULL DO NOTHING;

-- Relationship: content belongs_to_campaign revenue_campaign
INSERT INTO public.nexus_os_relationships
  (from_entity_id, to_entity_id, relationship, evidence_summary, source_table, source_id)
SELECT ce.id, cae.id, 'belongs_to_campaign',
       'Content linked to its campaign via related_campaign_id.',
       'nexus_os_content_items', ci.id
FROM public.nexus_os_content_items ci
JOIN public.nexus_os_entities ce  ON ce.source_table = 'nexus_os_content_items'  AND ce.source_id = ci.id
JOIN public.nexus_os_entities cae ON cae.source_table = 'nexus_os_revenue_campaigns' AND cae.source_id = ci.related_campaign_id
WHERE ci.related_campaign_id IS NOT NULL AND NOT ci.archived
ON CONFLICT (from_entity_id, to_entity_id, relationship) DO NOTHING;

-- Relationship: source supports campaign (the strategy/goal sources support all campaigns)
INSERT INTO public.nexus_os_relationships
  (from_entity_id, to_entity_id, relationship, evidence_summary, source_table, source_id)
SELECT se.id, cae.id, 'supports',
       'Starter strategy/goal source supports the revenue campaign.',
       'nexus_os_sources', s.id
FROM public.nexus_os_sources s
JOIN public.nexus_os_entities se ON se.source_table = 'nexus_os_sources' AND se.source_id = s.id
JOIN public.nexus_os_entities cae ON cae.source_table = 'nexus_os_revenue_campaigns'
WHERE s.title = 'Ray goal: turn Nexus OS into a revenue generator' AND s.status != 'archived'
ON CONFLICT (from_entity_id, to_entity_id, relationship) DO NOTHING;
