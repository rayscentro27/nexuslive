-- Revenue Hub: starter campaign seed data
-- File: supabase/seeds/revenue_hub_starter_campaigns.sql
--
-- HOW TO USE:
--   Do NOT run automatically. Review and run manually via:
--   Supabase Dashboard → SQL Editor → paste and run
--   OR trigger from the Nexus OS Revenue Hub "Create Starter Campaigns" button.
--
-- COMPLIANCE NOTES:
--   - No earnings claims. No guarantees. No misleading copy.
--   - Affiliate disclosure required before any public use.
--   - No publishing, outreach, or link activation without Ray's approval.
--   - Estimated values are planning estimates only, not projections.

-- Idempotent: uses ON CONFLICT DO NOTHING on program_name uniqueness
-- (Requires unique index on program_name — added below if not present)

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE tablename = 'nexus_os_revenue_campaigns'
    AND indexname = 'nexus_os_revenue_campaigns_program_name_uq'
  ) THEN
    CREATE UNIQUE INDEX nexus_os_revenue_campaigns_program_name_uq
      ON public.nexus_os_revenue_campaigns(lower(program_name));
  END IF;
END;
$$;

INSERT INTO public.nexus_os_revenue_campaigns (
  program_name, niche, campaign_type, priority,
  application_status, link_status, landing_page_status,
  compliance_ok, disclosure_ok, traffic_source,
  offer_url, next_action, notes, estimated_value,
  approval_status
) VALUES
(
  'Nav Business Credit',
  'Business Credit & Funding',
  'affiliate',
  'high',
  'not_applied',
  'none',
  'none',
  false,
  false,
  'Content / SEO / YouTube',
  'https://nav.com',
  'Apply to Nav affiliate program, add disclosure page, draft 3 content pieces',
  'High relevance to existing audience. Affiliate disclosure required on all pages. No earnings claims.',
  NULL,
  'not_required'
),
(
  'Beehiiv Newsletter Platform',
  'Creator / Newsletter Tools',
  'affiliate',
  'medium',
  'not_applied',
  'none',
  'none',
  false,
  false,
  'YouTube / Social',
  'https://beehiiv.com',
  'Apply to Beehiiv affiliate program',
  'Good fit for content-first strategy. Research commission structure before applying.',
  NULL,
  'not_required'
),
(
  'LegalZoom Business Formation',
  'Business Formation & Legal',
  'affiliate',
  'medium',
  'not_applied',
  'none',
  'none',
  false,
  false,
  'Content / SEO',
  'https://legalzoom.com',
  'Research affiliate program terms, verify commission, apply',
  'Natural pairing with LLC/business credit content. Compliance review required.',
  NULL,
  'not_required'
),
(
  'Business Credit Builder Tools',
  'Business Credit / Paydex',
  'affiliate',
  'high',
  'not_applied',
  'none',
  'draft',
  false,
  false,
  'YouTube / Email',
  NULL,
  'Identify top business credit tool program, verify compliance, apply',
  'High-intent audience. Do not make earnings or score improvement claims. Disclosure required.',
  NULL,
  'not_required'
),
(
  'AI / SaaS Tools (TBD)',
  'AI & Productivity Tools',
  'affiliate',
  'low',
  'not_applied',
  'none',
  'none',
  false,
  false,
  'YouTube / Content',
  NULL,
  'Identify 2-3 AI tool programs relevant to Nexus audience, research terms',
  'Opportunity to align with existing AI-forward positioning.',
  NULL,
  'not_required'
),
(
  'Paydex / Business Credit Resources',
  'Business Credit Education',
  'content',
  'high',
  'not_applied',
  'none',
  'none',
  false,
  false,
  'YouTube / SEO',
  NULL,
  'Create educational content series on Paydex. Identify monetization path.',
  'Educational content first. No score guarantees. No financial outcome claims.',
  NULL,
  'not_required'
)
ON CONFLICT DO NOTHING;
