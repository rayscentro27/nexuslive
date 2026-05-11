create extension if not exists "pgcrypto";

create table if not exists public.research_claims (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  topic text not null,
  subtheme text,
  claim_text text not null,
  claim_type text not null default 'strategy',
  confidence decimal(4,3) not null default 0.5,
  trace_id uuid,
  created_at timestamptz not null default now()
);

alter table public.research_claims add column if not exists source text;
alter table public.research_claims add column if not exists topic text;
alter table public.research_claims add column if not exists subtheme text;
alter table public.research_claims add column if not exists claim_text text;
alter table public.research_claims add column if not exists claim_type text default 'strategy';
alter table public.research_claims add column if not exists confidence decimal(4,3) default 0.5;
alter table public.research_claims add column if not exists trace_id uuid;
alter table public.research_claims add column if not exists created_at timestamptz default now();

create index if not exists research_claims_topic_idx on public.research_claims (topic);
create index if not exists research_claims_claim_type_idx on public.research_claims (claim_type);
create index if not exists research_claims_confidence_idx on public.research_claims (confidence desc);
create index if not exists research_claims_trace_id_idx on public.research_claims (trace_id);
create index if not exists research_claims_created_at_idx on public.research_claims (created_at desc);

create table if not exists public.research_relationships (
  id uuid primary key default gen_random_uuid(),
  from_node text not null,
  from_type text not null,
  to_node text not null,
  to_type text not null,
  relation text not null,
  source text,
  trace_id uuid,
  created_at timestamptz not null default now()
);

create index if not exists research_relationships_from_idx on public.research_relationships (from_node, from_type);
create index if not exists research_relationships_to_idx on public.research_relationships (to_node, to_type);
create index if not exists research_relationships_relation_idx on public.research_relationships (relation);
create index if not exists research_relationships_created_at_idx on public.research_relationships (created_at desc);

create table if not exists public.research_clusters (
  id uuid primary key default gen_random_uuid(),
  cluster_name text not null,
  theme text not null,
  source_count integer default 0,
  summary text,
  key_terms jsonb default '[]'::jsonb,
  confidence numeric,
  created_at timestamptz default now()
);

create index if not exists idx_research_clusters_theme on public.research_clusters (theme);
create index if not exists idx_research_clusters_created_at on public.research_clusters (created_at desc);
create unique index if not exists research_clusters_cluster_name_uidx on public.research_clusters (cluster_name);

alter table public.research_briefs add column if not exists topic text;
alter table public.research_briefs add column if not exists subtheme text;
alter table public.research_briefs add column if not exists lane text;
alter table public.research_briefs add column if not exists source_name text;
alter table public.research_briefs add column if not exists source_url text;
alter table public.research_briefs add column if not exists key_findings jsonb default '[]'::jsonb;
alter table public.research_briefs add column if not exists action_items jsonb default '[]'::jsonb;
alter table public.research_briefs add column if not exists opportunity_notes jsonb default '[]'::jsonb;
alter table public.research_briefs add column if not exists risk_warnings jsonb default '[]'::jsonb;
alter table public.research_briefs add column if not exists confidence decimal(4,3) default 0.5;
alter table public.research_briefs add column if not exists trace_id uuid;

create index if not exists idx_research_briefs_topic on public.research_briefs (topic);
create index if not exists idx_research_briefs_lane on public.research_briefs (lane);
create index if not exists idx_research_briefs_trace_id on public.research_briefs (trace_id);

select pg_notify('pgrst', 'reload schema');
