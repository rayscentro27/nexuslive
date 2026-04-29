-- Proposed only. Do not apply without confirmation.
create table if not exists public.nexus_knowledge_items (
  id uuid primary key default gen_random_uuid(),
  source_title text not null,
  source_type text not null,
  category text not null,
  summary text not null,
  key_takeaways jsonb not null default '[]'::jsonb,
  recommended_user_stage text,
  risk_compliance_notes text,
  created_by_agent text,
  confidence_score numeric(4,3),
  approved_for_user_display boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
