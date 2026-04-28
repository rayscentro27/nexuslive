-- ── business_opportunities ────────────────────────────────────────────────────
-- Normalized business opportunities surfaced by OpportunityWorker.
-- Run this SQL in your Supabase SQL editor to create the table.
-- ─────────────────────────────────────────────────────────────────────────────

create table if not exists business_opportunities (
  id                  uuid primary key default gen_random_uuid(),
  artifact_id         uuid references research_artifacts(id) on delete set null,
  source              text,
  title               text not null,
  opportunity_type    text check (opportunity_type in (
                        'saas', 'automation_agency', 'ai_product', 'content_creator',
                        'service_business', 'acquisition', 'ecommerce', 'local_business', 'other'
                      )),
  niche               text,           -- "CRM Automation" | "Credit Services" | "Real Estate" | etc.
  description         text,           -- 2-4 sentence summary
  evidence_summary    text,           -- key points / proof from source
  monetization_hint   text,           -- "Recurring revenue" | "One-time sale" | "Retainer" | etc.
  urgency             text default 'medium' check (urgency in ('high', 'medium', 'low')),
  confidence          decimal(4,3),   -- 0.0 – 1.0 from topic classifier
  score               integer default 0 check (score >= 0 and score <= 100),
  status              text default 'new' check (status in ('new', 'reviewed', 'actioned', 'dismissed')),
  trace_id            text,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);

-- Indexes
create index if not exists business_opp_score_idx      on business_opportunities (score desc);
create index if not exists business_opp_type_idx       on business_opportunities (opportunity_type);
create index if not exists business_opp_urgency_idx    on business_opportunities (urgency);
create index if not exists business_opp_niche_idx      on business_opportunities (niche);
create index if not exists business_opp_status_idx     on business_opportunities (status);

-- Auto-update updated_at (reuses function from grant_opportunities.sql if already created)
create trigger if not exists business_opportunities_updated_at
  before update on business_opportunities
  for each row execute procedure update_updated_at_column();

-- Useful views
create or replace view top_business_opportunities as
  select * from business_opportunities
  where status = 'new' and score >= 60
  order by score desc, urgency desc;

-- Validation queries
-- select count(*) from business_opportunities;
-- select * from top_business_opportunities limit 10;
-- select opportunity_type, count(*), avg(score) from business_opportunities group by opportunity_type;
-- select niche, count(*) as mentions from business_opportunities group by niche order by mentions desc;
-- select * from business_opportunities where urgency = 'high' order by score desc;
