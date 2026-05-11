-- Funding Strategy Engine — Persisted funding plans
-- Migration: 20260429210000_funding_strategies.sql

create table if not exists public.funding_strategies (
  id                          uuid primary key default gen_random_uuid(),
  tenant_id                   uuid,
  user_id                     uuid not null,
  strategy_status             text not null default 'active',
  strategy_summary            text,
  prequalification_phase      jsonb default '{}',
  relationship_building_phase jsonb default '{}',
  application_sequence        jsonb default '[]',
  optimization_notes          jsonb default '{}',
  estimated_funding_low       numeric(14,2),
  estimated_funding_high      numeric(14,2),
  next_best_action            jsonb default '{}',
  linked_recommendation_ids   jsonb default '[]',
  source_snapshot             jsonb default '{}',
  disclaimer                  text,
  generated_at                timestamptz default now(),
  created_at                  timestamptz default now(),
  updated_at                  timestamptz default now()
);

-- Only one ACTIVE strategy per user/tenant enforced at the application layer.
-- Archived strategies are retained for history.
create index if not exists fs_user_active_idx
  on public.funding_strategies (user_id, strategy_status, updated_at desc);

create index if not exists fs_tenant_user_idx
  on public.funding_strategies (tenant_id, user_id, strategy_status);
