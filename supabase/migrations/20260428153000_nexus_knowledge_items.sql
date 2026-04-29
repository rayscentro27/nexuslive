create extension if not exists pgcrypto;

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

drop trigger if exists trg_nexus_knowledge_items_touch on public.nexus_knowledge_items;
create trigger trg_nexus_knowledge_items_touch
before update on public.nexus_knowledge_items
for each row execute function public.touch_updated_at();
