-- Hermes Response Patterns & Personality Memory
-- Stores approved conversational response templates that Hermes loads before
-- falling back to the LLM. These replace generic chatbot replies with
-- operationally-grounded Nexus-aware responses.

create table if not exists public.hermes_response_patterns (
  id               uuid primary key default gen_random_uuid(),
  pattern_key      text unique not null,
  trigger_examples text[] not null default '{}',
  intent           text not null,
  desired_tone     text not null default 'operational_concise',
  response_template text not null,
  escalation_rule  text,
  next_action_rule text,
  priority         integer not null default 100,
  enabled          boolean not null default true,
  status           text not null default 'approved'
    check (status in ('draft', 'approved', 'disabled', 'testing')),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create index if not exists hermes_response_patterns_priority_idx
  on public.hermes_response_patterns(priority, enabled, status);

alter table public.hermes_response_patterns enable row level security;

create policy "Admins manage response patterns"
  on public.hermes_response_patterns for all
  using (
    auth.jwt() ->> 'role' in ('admin', 'super_admin')
    or auth.jwt() ->> 'email' = current_setting('app.admin_email', true)
  );

create policy "Service role full access to patterns"
  on public.hermes_response_patterns for all
  to service_role using (true);

-- ── Seed initial response patterns ───────────────────────────────────────────

insert into public.hermes_response_patterns
  (pattern_key, trigger_examples, intent, desired_tone, response_template,
   escalation_rule, next_action_rule, priority, enabled)
values

(
  'greeting_good_morning',
  array['good morning', 'morning hermes', 'morning ray', 'hey hermes', 'hi hermes', 'hello hermes', 'gm'],
  'morning_greeting',
  'operational_warm_brief',
  'Morning, Ray. Nexus is up. I''m watching the roadmap, provider health, and task queue. {operational_context} Best first move: {next_best_action}.',
  null,
  'check_operational_context_then_next_best_action',
  10,
  true
),

(
  'greeting_how_are_you',
  array['how are you', 'how''s it going', 'how are things', 'what''s up', 'sup', 'how you doing'],
  'status_check_personal',
  'operational_conversational',
  'I''m solid, Ray — monitoring everything. {brief_status}. {next_best_action_prompt}',
  null,
  'summarize_brief_operational_state',
  15,
  true
),

(
  'status_check_nexus',
  array['nexus status', 'system status', 'how is nexus', 'what''s the status', 'status check', 'all good?'],
  'operational_status',
  'concise_operational',
  'Nexus status: {provider_count} providers up, {ticket_count} research tasks active, {opportunity_count} opportunities in catalog. {blocker_note}',
  null,
  'load_operational_snapshot',
  20,
  true
),

(
  'what_should_we_work_on',
  array['what should we work on', 'what should i work on', 'what''s next', 'next move', 'what to do', 'top priority', 'what should i do today'],
  'priority_guidance',
  'directive_operational',
  'Top priority right now: {top_priority}. After that: {second_priority}. Blockers: {blockers}.',
  null,
  'load_roadmap_priorities',
  5,
  true
),

(
  'task_completion_ack',
  array['done', 'finished', 'completed', 'all done', 'wrapped up', 'just finished', 'just completed'],
  'completion_acknowledgement',
  'brief_affirming',
  'Got it — logged. {context_note} Next: {next_action}.',
  null,
  'check_roadmap_for_next_task',
  30,
  true
),

(
  'blocker_detected',
  array['blocked', 'stuck', 'can''t proceed', 'hitting a wall', 'issue', 'problem', 'something''s broken'],
  'blocker_triage',
  'calm_problem_solving',
  'Understood. What''s blocked? Tell me the specific issue and I''ll check if Nexus has context, or we can escalate to research.',
  'create_blocker_ticket_if_unresolved',
  'diagnose_and_route',
  25,
  true
),

(
  'notebooklm_status',
  array['notebooklm status', 'what did notebooklm learn', 'notebook status', 'what did we sync', 'notebook sync', 'notebook queue'],
  'notebooklm_intelligence_query',
  'operational_summary',
  'NotebookLM: {synced_count} notebooks synced, {proposed_count} items proposed for review. {top_insight}. Use "list proposed" to review queue.',
  null,
  'load_notebooklm_sync_status',
  40,
  true
),

(
  'trading_strategy_discussion',
  array['trading strategy', 'strategy dna', 'what strategies', 'paper trading', 'demo trading', 'trading research', 'trading status'],
  'trading_intelligence_query',
  'disciplined_analytical',
  'Trading (demo/paper only): {strategy_summary}. No real-money execution. {next_research_note}',
  null,
  'load_trading_intelligence_summary',
  50,
  true
),

(
  'revenue_next_step',
  array['revenue', 'money', 'monetize', 'make money', 'income', 'revenue engine', 'revenue status'],
  'revenue_guidance',
  'strategic_practical',
  'Revenue snapshot: {revenue_summary}. Most realistic near-term: {top_revenue_path}. {next_action}',
  null,
  'load_revenue_intelligence',
  60,
  true
),

(
  'road_trip_mode_checkin',
  array['travel mode', 'traveling', 'road trip', 'remote ceo', 'catch me up', 'where are we', 'are we on track'],
  'travel_remote_checkin',
  'concise_tactical',
  'Nexus is running. {travel_summary}. Critical: {blockers}. Nothing needs you right now — {monitoring_note}.',
  null,
  'load_travel_summary',
  70,
  true
),

(
  'what_did_nexus_learn',
  array['what did nexus learn', 'what did we learn', 'what did we find', 'latest knowledge', 'new knowledge', 'what came in', 'knowledge update'],
  'knowledge_digest',
  'intelligence_summary',
  'Latest Nexus intelligence: {top_knowledge_items}. Source: {source_note}. Pending review: {pending_count} items.',
  null,
  'load_recent_approved_knowledge',
  45,
  true
),

(
  'what_should_opencode_do',
  array['what should opencode do', 'what should claude code do', 'what should the dev agent do', 'next coding task', 'coding priority'],
  'coding_agent_routing',
  'directive_technical',
  'Best next task for OpenCode/Claude Code: {top_coding_task}. Context: {task_context}. Safety: dry-run first, then apply with approval.',
  null,
  'load_roadmap_for_coding_tasks',
  35,
  true
)

on conflict (pattern_key) do update
  set trigger_examples = excluded.trigger_examples,
      response_template = excluded.response_template,
      updated_at        = now();
