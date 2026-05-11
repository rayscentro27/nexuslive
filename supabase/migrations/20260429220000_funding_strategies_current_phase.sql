-- Add current_phase to funding_strategies
-- Migration: 20260429220000_funding_strategies_current_phase.sql

alter table public.funding_strategies
  add column if not exists current_phase      text,
  add column if not exists phase_updated_at   timestamptz;

create index if not exists fs_user_phase_idx
  on public.funding_strategies (user_id, current_phase, strategy_status);
