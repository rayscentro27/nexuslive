-- ─────────────────────────────────────────────────────────────────────────────
-- Migration: strategy_reviews + approved_strategies
-- Run from: Supabase Dashboard → SQL Editor
-- Created:  2026-04-02
-- ─────────────────────────────────────────────────────────────────────────────

-- strategy_reviews: immutable audit trail for every approve/reject/expire decision
create table if not exists public.strategy_reviews (
    id               uuid primary key default gen_random_uuid(),
    candidate_id     uuid references public.strategy_candidates(id) on delete cascade,
    score_id         uuid,
    review_action    text not null check (review_action in ('approve','reject','expire','override')),
    review_status    text not null check (review_status in ('approved','rejected','expired','overridden')),
    reviewer_type    text not null default 'system' check (reviewer_type in ('system','ai','human')),
    score_total      numeric(5,2),
    confidence_label text,
    difficulty_level text,
    notes            text,
    created_at       timestamptz not null default now()
);

create index if not exists idx_strategy_reviews_candidate_id
    on public.strategy_reviews(candidate_id);

alter table public.strategy_reviews enable row level security;

create policy "service role full access" on public.strategy_reviews
    using (true) with check (true);

-- approved_strategies: portal-facing educational strategy records
create table if not exists public.approved_strategies (
    id               uuid primary key default gen_random_uuid(),
    candidate_id     uuid unique references public.strategy_candidates(id) on delete cascade,
    title            text not null,
    strategy_type    text,
    summary          text,
    when_it_works    text,
    when_it_fails    text,
    risk_note        text,
    difficulty_level text,
    confidence_label text,
    score_total      numeric(5,2),
    is_published     boolean not null default true,
    review_status    text not null default 'approved',
    published_at     timestamptz,
    expires_at       timestamptz,
    updated_at       timestamptz not null default now(),
    created_at       timestamptz not null default now()
);

create index if not exists idx_approved_strategies_is_published
    on public.approved_strategies(is_published);
create index if not exists idx_approved_strategies_strategy_type
    on public.approved_strategies(strategy_type);
create index if not exists idx_approved_strategies_expires_at
    on public.approved_strategies(expires_at);

alter table public.approved_strategies enable row level security;

create policy "service role full access" on public.approved_strategies
    using (true) with check (true);

-- Allow anon read for published strategies (portal display)
create policy "anon read published" on public.approved_strategies
    for select using (is_published = true);
