-- ── grant_opportunities ───────────────────────────────────────────────────────
-- Normalized grant opportunities surfaced by GrantWorker.
-- Run this SQL in your Supabase SQL editor to create the table.
-- ─────────────────────────────────────────────────────────────────────────────

create table if not exists grant_opportunities (
  id                  uuid primary key default gen_random_uuid(),
  artifact_id         bigint references research_artifacts(id) on delete set null,
  source              text,
  title               text not null,
  program_name        text,
  funding_amount      text,           -- raw string e.g. "$50,000" or "up to $500K"
  geography           text,           -- "National / Federal" | "Arizona" | "Local / Regional" | etc.
  target_business_type text,          -- "Small Business" | "Minority-Owned Business" | etc.
  eligibility_notes   text,
  deadline            text,           -- raw string or "Rolling / ongoing"
  confidence          decimal(4,3),   -- 0.0 – 1.0 from topic classifier
  score               integer default 0 check (score >= 0 and score <= 100),
  status              text default 'new' check (status in ('new', 'reviewed', 'applied', 'dismissed')),
  trace_id            text,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);

-- Indexes
create index if not exists grant_opportunities_score_idx  on grant_opportunities (score desc);
create index if not exists grant_opportunities_status_idx on grant_opportunities (status);
create index if not exists grant_opportunities_topic_idx  on grant_opportunities (geography);

-- Auto-update updated_at
create or replace function update_updated_at_column()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger grant_opportunities_updated_at
  before update on grant_opportunities
  for each row execute procedure update_updated_at_column();

-- Validation queries
-- select count(*) from grant_opportunities;
-- select * from grant_opportunities order by score desc limit 10;
-- select * from grant_opportunities where status = 'new' and score >= 60 order by score desc;
-- select geography, count(*) from grant_opportunities group by geography;
