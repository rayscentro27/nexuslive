-- Research Requests — AI Employee Knowledge Gap Escalation
-- When an AI employee cannot answer from internal knowledge, it creates a research ticket.
-- Safe: service-role writes only; users read own tickets; no autonomous execution.

create table if not exists public.research_requests (
  id                       uuid primary key default gen_random_uuid(),
  user_id                  uuid references auth.users(id) on delete cascade,

  -- Classification
  department               text not null,
    -- trading_intelligence | grants_research | funding_intelligence
    -- business_opportunities | credit_research | marketing_intelligence | operations
  request_type             text not null default 'knowledge_gap',
    -- knowledge_gap | strategy_review | opportunity_evaluation | compliance_check
  priority                 text not null default 'normal',
    -- low | normal | high | urgent

  -- Content
  topic                    text not null,
  original_question        text not null,
  normalized_query         text,
  source_context           jsonb,
    -- {employee_role, conversation_id, prior_sources_checked, confidence_at_submission}

  -- Workflow
  status                   text not null default 'submitted',
    -- submitted | queued | researching | needs_review | completed | rejected | archived
  confidence_gap           integer,
    -- 0–100: how confident was the AI? low confidence = higher priority
  estimated_completion_hours integer,
  assigned_worker          text,
  risk_level               text not null default 'unknown',
    -- low | medium | high | unknown

  -- Results (filled when completed)
  research_summary         text,
  recommended_action       text,
  knowledge_record_id      uuid references public.knowledge_items(id),

  -- Client visibility
  client_visible_status    text not null default 'researching',
    -- submitted | researching | under_review | completed
  notify_user_when_ready   boolean not null default true,
  notified_at              timestamptz,

  -- Timestamps
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  completed_at             timestamptz
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

create index if not exists idx_research_req_user_id
  on public.research_requests (user_id);

create index if not exists idx_research_req_status
  on public.research_requests (status);

create index if not exists idx_research_req_department
  on public.research_requests (department);

create index if not exists idx_research_req_priority
  on public.research_requests (priority, created_at desc);

create index if not exists idx_research_req_topic
  on public.research_requests (topic);

-- ── updated_at trigger ────────────────────────────────────────────────────────

drop trigger if exists research_requests_updated_at on public.research_requests;
create trigger research_requests_updated_at
  before update on public.research_requests
  for each row execute function public.set_updated_at();

-- ── Row-Level Security ────────────────────────────────────────────────────────

alter table public.research_requests enable row level security;

-- Users see only their own tickets
create policy "users_read_own_research_requests"
  on public.research_requests
  for select
  using (auth.uid() = user_id);

-- Service role (AI workers) can manage all rows
create policy "service_role_manage_research_requests"
  on public.research_requests
  for all
  using (auth.jwt() ->> 'role' = 'service_role');
