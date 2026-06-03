# Hermes Command Test Results

Timestamp: 20260603_164722

- total commands found: 1108
- commands tested: 35
- commands skipped: 1073
- commands passing: 35
- commands failing: 0
- commands producing evidence dump: 0
- commands producing quality fallback: 0

## Tested Commands

### what is today's date
- intent: date_time_question
- handler: _plain_date_time
- output header: Today is Wednesday, June 3, 2026.
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: Today is Wednesday, June 3, 2026.

Nexus context:
- Memory v2 mode: preview for structured memory
- Live answers still prioritize current artifacts, actions, decisions, source intake, and provider policy

I can give the system date from the

### show last daily plan
- intent: show_last_daily_plan
- handler: _plain_show_last_daily_plan
- output header: LAST DAILY PLAN
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: LAST DAILY PLAN

Plan date: 2026-06-03 (saved 0m ago)

Top priority: Build a Credit/Funding Readiness Checklist lead magnet (free to draft, no approval needed)

Why: Ready-to-produce product: checklist, template, or audit offer.

Money move

### run daily operating cycle
- intent: daily_operating_cycle
- handler: _plain_daily_operating_cycle
- output header: TODAY'S NEXUS PLAN — 2026-06-03
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: TODAY'S NEXUS PLAN — 2026-06-03

Top priority:
Build a Credit/Funding Readiness Checklist lead magnet (free to draft, no approval needed)

Why: Ready-to-produce product: checklist, template, or audit offer.

1. Money move

   Advance conten

### show approval queue
- intent: show_approval_queue
- handler: _plain_show_approval_queue
- output header: APPROVAL QUEUE
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: APPROVAL QUEUE

Pending approval items (10):

1. Lesson: When Ray asks for external real-time info like weather, news, or live prices, I 
   Category: lesson approval
   Risk: low
   Needed for: Lesson must be approved before it enters memo

### continue while i am out
- intent: daily_continue_while_out
- handler: _plain_daily_continue_while_out
- output header: CONTINUE WHILE YOU ARE OUT
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: CONTINUE WHILE YOU ARE OUT

I can safely continue internal work only.

I will:

1. Review latest source intake
2. Score monetization opportunities
3. Prepare draft improvements
4. Assign internal scout tasks
5. Update action queue
6. Log kn

### 30 day revenue plan
- intent: thirty_day_revenue_plan
- handler: _plain_thirty_day_revenue_plan
- output header: 30-DAY NEXUS REVENUE PLAN — June 03, 2026
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: 30-DAY NEXUS REVENUE PLAN — June 03, 2026

Goal:
  Generate $1,000/week in recurring or repeatable revenue.

Best starting asset: lead magnet / funding readiness checklist

Week 1 — Build and approve the asset packet
  - finalize lead magne

### show today's top revenue move
- intent: daily_top_revenue_move
- handler: _plain_daily_top_revenue_move
- output header: TODAY'S TOP MONEY MOVE — 2026-06-03
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: TODAY'S TOP MONEY MOVE — 2026-06-03

Best move: Advance content draft: credit_funding_readiness_checklist_draft_20260531_213740_862_lead_magnet.md

Why this is first: Highest-value content asset ready for next step toward 30-Day Revenue Goa

### show today's blockers
- intent: daily_blockers
- handler: _plain_daily_blockers
- output header: TODAY'S BLOCKERS — 2026-06-03
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: TODAY'S BLOCKERS — 2026-06-03

Critical blockers:

- No critical blockers found.

Operational blockers:

- Open knowledge gaps: external_info_question, external_info_question, external_info_question
  Fix: Send sources or links via Telegram

### what did you do while i was out
- intent: while_out_summary
- handler: _plain_while_out_summary
- output header: WHILE YOU WERE OUT
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: WHILE YOU WERE OUT

Last plan: 2026-06-03 (0m ago)

Still pending (5):
  - [blocker] Open knowledge gaps: external_info_question, external_info_question, external_info_question
  - [safe_action] Review and score latest source intake records

### show pending items
- intent: pending_daily_items
- handler: _plain_pending_daily_items
- output header: PENDING DAILY ITEMS — 2026-06-03
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: PENDING DAILY ITEMS — 2026-06-03

Blockers (1):
  - Open knowledge gaps: external_info_question, external_info_question, external_info_question
    Fix: Send sources or links via Telegram to close gaps.

Safe internal items (4):
  - Review 

### compare since last plan
- intent: compare_since_last_plan
- handler: _plain_compare_since_last_plan
- output header: WHAT CHANGED SINCE THE LAST PLAN
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: WHAT CHANGED SINCE THE LAST PLAN

Comparing: 2026-06-03 → 2026-06-03

Changes:
  - No significant changes detected.

Approval boundary:
  I will not publish, email, sell, deploy, spend money, or trade live without Ray approval.

### what happens if i approve
- intent: approval_impact
- handler: _plain_approval_impact
- output header: IF APPROVED — ITEM ?
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: IF APPROVED — ITEM ?

Please specify an item number.

### show research queue
- intent: show_research_queue
- handler: _plain_show_research_queue
- output header: RESEARCH QUEUE
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: RESEARCH QUEUE

17 open question(s):

ID:       rq_20260603_061954
Question: What is the best affiliate offer for the funding checklist audience?
Scout:    monetization_scout
Status:   open
Created:  2026-06-03T06:19:54

ID:       rq_202606

### show scout assignments
- intent: show_scout_assignments
- handler: _plain_show_scout_assignments
- output header: SCOUT ASSIGNMENTS
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: SCOUT ASSIGNMENTS

4 assignment(s):

Scout:    monetization_scout
Question: Which affiliate offer converts best for funding-readiness audience?
Status:   open
Created:  2026-06-03T06:19:55

Scout:    general_research_scout
Question: How oft

### what are you still trying to figure out
- intent: show_unresolved_questions
- handler: _plain_show_unresolved_questions
- output header: UNRESOLVED QUESTIONS
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: UNRESOLVED QUESTIONS

15 open:

  - What is the best affiliate offer for the funding checklist audience?
    Status: open  |  2026-06-03T06:19:54

  - Test: what is the best affiliate offer?
    Status: open  |  2026-06-03T06:20:46

  - Tes

### show active operating rules
- intent: active_operating_rules
- handler: _plain_active_operating_rules
- output header: ACTIVE OPERATING RULES
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: ACTIVE OPERATING RULES

Hermes is currently following these live-answer rules:

1. Evidence first.
2. Do not invent task status, counts, commits, approvals, or source processing.
3. Use current artifacts/actions/decisions/source intake befo

### show memory v2 preview
- intent: memory_v2_preview
- handler: _plain_memory_v2_preview
- output header: HERMES MEMORY V2 PREVIEW
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: HERMES MEMORY V2 PREVIEW

Status:
Preview only — not the live Telegram primary reader.

Rows:
- active/live_answer records: 0
- operating rules: 0
- ray preferences: 0
- approval policys: 0
- project contexts: 0

What Hermes would read:
  (

### show memory v2 status
- intent: memory_v2_status
- handler: _plain_memory_v2_status
- output header: HERMES MEMORY V2 STATUS
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: HERMES MEMORY V2 STATUS

Status: preview reader unavailable — Supabase credentials not configured in this environment.

The v2 reader module is loaded but cannot connect to Supabase.
Live Telegram reader has NOT been switched to v2.

### show memory v2 primary status
- intent: memory_v2_primary_status
- handler: _plain_memory_v2_primary_status
- output header: HERMES MEMORY V2 PRIMARY STATUS
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: HERMES MEMORY V2 PRIMARY STATUS

Mode: preview (primary not active)

Rows: unavailable (credentials not in this env)

Safety:
  archived/deprecated/blocked/debug records excluded
  stale strings excluded
  provider snapshots not used as cur

### show memory v2 shadow status
- intent: memory_v2_shadow_status
- handler: _plain_memory_v2_shadow_status
- output header: HERMES MEMORY V2 SHADOW STATUS
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: HERMES MEMORY V2 SHADOW STATUS

Mode: preview

Live Telegram reader: current active reader
Memory v2: preview mode

Rows: unavailable (credentials not in local env)

Last shadow comparison: none yet

Important: Shadow mode does not change H

### is memory v2 live
- intent: memory_v2_live_check
- handler: _plain_memory_v2_live_check
- output header: Memory v2 is preview only. Live answers use current reader.
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: Memory v2 is preview only. Live answers use current reader.

### show memory sources again
- intent: memory_sources_again
- handler: _plain_memory_sources
- output header: HERMES MEMORY SOURCES
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: HERMES MEMORY SOURCES

Live answer sources:
- Current conversation context
- Latest content artifacts
- Action queue
- Decision log
- Source intake records
- Active operating rules
- hermes_memory_v2 active/live_answer records when preview/

### show memory sources
- intent: memory_sources
- handler: _plain_memory_sources
- output header: HERMES MEMORY SOURCES
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: HERMES MEMORY SOURCES

Live answer sources:
- Current conversation context
- Latest content artifacts
- Action queue
- Decision log
- Source intake records
- Active operating rules
- hermes_memory_v2 active/live_answer records when preview/

### where did that answer come from
- intent: answer_source
- handler: _plain_answer_source
- output header: ANSWER SOURCE
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: ANSWER SOURCE

I answered from the current active context.

Most recent evidence:
- Latest content artifact: /Users/raymonddavis/nexus-ai/docs/reports/review/daily_research_review_20260530_035332.json
- Latest action: /Users/raymonddavis/ne

### show decision log
- intent: telegram_continuity_exact
- handler: self._cmd_decision_log
- output header: DECISION LOG
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: DECISION LOG

Recent Hermes decisions (10 shown):

1. Created simplified revision artifact
   When: 2026-06-03 — Ray requested: simplified revision of checklist draft
   Why: Internal draft revision per Ray's instruction
   Evidence: docs/r

### show approval policy
- intent: telegram_continuity_exact
- handler: self._cmd_approval_policy
- output header: APPROVAL POLICY
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: APPROVAL POLICY

Autonomous allowed:
  - free research
  - source intake
  - scoring opportunities
  - assigning scouts
  - internal drafts
  - internal reports
  - action queue / decision log updates
  - demo/paper testing under caps

Ray 

### show action queue
- intent: telegram_continuity_exact
- handler: self._cmd_action_queue
- output header: ACTION QUEUE
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: ACTION QUEUE

I have 103 open action records, 93 are duplicates. The top work is:

1. build a credit/funding readiness checklist lead magnet (free to draft, no approv
   Why it matters: fastest reviewable revenue asset.
   Scout: content_in

### what changed
- intent: telegram_continuity_exact
- handler: self._cmd_compare_draft_versions
- output header: DRAFT COMPARISON
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: DRAFT COMPARISON

Here is what changed in the draft:

  Updated section: Compliance Note

Next safe step: Review the latest draft or ask for a specific revision.

Approval boundary:
  I will not publish, email, spend money, apply to affilia

### show cfo shadow status
- intent: cfo_shadow_command
- handler: format_shadow_status
- output header: CFO LOOP SHADOW STATUS
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: CFO LOOP SHADOW STATUS

Mode: limited_primary
Provider: mock
Live response changed: NO

Recent traces: 31
Last intent: draft_comparison
Last selected tool: compare_drafts
Would-have-fixed count: 0/31
Errors: 0

Safety:
  Shadow mode does no

### show cfo loop mode
- intent: cfo_shadow_command
- handler: format_shadow_status
- output header: CFO LOOP SHADOW STATUS
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: CFO LOOP SHADOW STATUS

Mode: limited_primary
Provider: mock
Live response changed: NO

Recent traces: 31
Last intent: draft_comparison
Last selected tool: compare_drafts
Would-have-fixed count: 0/31
Errors: 0

Safety:
  Shadow mode does no

### show cfo shadow traces
- intent: cfo_shadow_command
- handler: lambda: format_recent_shadow_traces(10)
- output header: CFO SHADOW TRACES
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: CFO SHADOW TRACES

Recent traces (last 10):

  1. Message: review the funding readiness launch packet and give me the a
     Intent: unknown_answer
     Tool: plain_acknowledgement
     Would have fixed live issue: no
     Confidence: 50%



### compare cfo shadow
- intent: cfo_shadow_command
- handler: compare_live_vs_shadow
- output header: CFO LIVE VS SHADOW COMPARISON
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: CFO LIVE VS SHADOW COMPARISON

Message: what changed

Live response:
  None

CFO Loop would have:
  Intent: draft_comparison
  Tool: compare_drafts
  Preview: DRAFT COMPARISON

Here is what changed in the draft:

  Updated section: Complian

### show cfo limited primary status
- intent: cfo_shadow_command
- handler: format_limited_primary_status
- output header: CFO LOOP LIMITED PRIMARY STATUS
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: CFO LOOP LIMITED PRIMARY STATUS

Mode: limited_primary
Provider: mock

Primary used count: 22
Mock-blocked count: 0
Grounded count: 31
Fallback count: 9

Allowlisted intents:
  - acknowledgement_check
  - approval_bulk_request
  - clarifyin

### show cfo primary status
- intent: cfo_shadow_command
- handler: format_limited_primary_status
- output header: CFO LOOP LIMITED PRIMARY STATUS
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: CFO LOOP LIMITED PRIMARY STATUS

Mode: limited_primary
Provider: mock

Primary used count: 22
Mock-blocked count: 0
Grounded count: 31
Fallback count: 9

Allowlisted intents:
  - acknowledgement_check
  - approval_bulk_request
  - clarifyin

### rollback cfo loop to shadow
- intent: cfo_shadow_command
- handler: format_rollback_instructions
- output header: CFO LOOP ROLLED BACK TO SHADOW
- passed: True
- evidence dump: False
- quality fallback: False
- mock output: False
- preview: CFO LOOP ROLLED BACK TO SHADOW

Manual rollback steps:

  1. Edit the plist:
     ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist

  2. Set HERMES_CFO_LOOP_MODE to: shadow

  3. Unload the service:
     launchctl unload ~/Libra

## Skipped Commands

- list dev agents (list_dev_agents): intent outside safe deterministic whitelist
- which coding agents (list_dev_agents): intent outside safe deterministic whitelist
- coding agents available (list_dev_agents): intent outside safe deterministic whitelist
- what agents (list_dev_agents): intent outside safe deterministic whitelist
- dev agents (list_dev_agents): intent outside safe deterministic whitelist
- available agents (list_dev_agents): intent outside safe deterministic whitelist
- agent bridge (list_dev_agents): intent outside safe deterministic whitelist
- run dev agent status (list_dev_agents): intent outside safe deterministic whitelist
- ask gemini (prepare_dev_handoff): approval-required
- prepare a prompt for gemini (prepare_dev_handoff): approval-required
- use gemini (prepare_dev_handoff): approval-required
- gemini review (prepare_dev_handoff): approval-required
- gemini analyze (prepare_dev_handoff): approval-required
- ask opencode (prepare_dev_handoff): approval-required
- prepare a prompt for opencode (prepare_dev_handoff): approval-required
- use opencode (prepare_dev_handoff): approval-required
- opencode implement (prepare_dev_handoff): approval-required
- ask claude cli (prepare_dev_handoff): approval-required
- prepare a prompt for claude (prepare_dev_handoff): approval-required
- claude cli review (prepare_dev_handoff): approval-required
- ask codex (prepare_dev_handoff): approval-required
- prepare a prompt for codex (prepare_dev_handoff): approval-required
- use codex (prepare_dev_handoff): approval-required
- codex patch (prepare_dev_handoff): approval-required
- recommend agent (recommend_dev_agent): intent outside safe deterministic whitelist
- which agent should (recommend_dev_agent): intent outside safe deterministic whitelist
- what agent should (recommend_dev_agent): intent outside safe deterministic whitelist
- best agent for (recommend_dev_agent): intent outside safe deterministic whitelist
- which cli agent (recommend_dev_agent): intent outside safe deterministic whitelist
- suggest agent (recommend_dev_agent): intent outside safe deterministic whitelist
- which coding agent (recommend_dev_agent): intent outside safe deterministic whitelist
- did you get enough sleep (small_talk): not useful for deterministic audit
- did you sleep (small_talk): not useful for deterministic audit
- do you sleep (small_talk): not useful for deterministic audit
- did you rest (small_talk): not useful for deterministic audit
- are you rested (small_talk): not useful for deterministic audit
- how are you (small_talk): not useful for deterministic audit
- how are you doing (small_talk): not useful for deterministic audit
- how you doing (small_talk): not useful for deterministic audit
- are you awake (small_talk): not useful for deterministic audit
- are you online (small_talk): not useful for deterministic audit
- you good (small_talk): not useful for deterministic audit
- good morning (small_talk): not useful for deterministic audit
- good afternoon (small_talk): not useful for deterministic audit
- good evening (small_talk): not useful for deterministic audit
- good night (small_talk): not useful for deterministic audit
- hey hermes (small_talk): not useful for deterministic audit
- hi hermes (small_talk): not useful for deterministic audit
- you there (small_talk): not useful for deterministic audit
- you still there (small_talk): not useful for deterministic audit
- what is todays date (date_time_question): duplicate intent coverage
- what's today's date (date_time_question): duplicate intent coverage
- what's todays date (date_time_question): duplicate intent coverage
- what day is it (date_time_question): duplicate intent coverage
- what day is today (date_time_question): duplicate intent coverage
- what is the date (date_time_question): duplicate intent coverage
- what's the date (date_time_question): duplicate intent coverage
- today's date (date_time_question): duplicate intent coverage
- what time is it (date_time_question): duplicate intent coverage
- what is the time (date_time_question): duplicate intent coverage
- current date (date_time_question): duplicate intent coverage
- what is today (date_time_question): duplicate intent coverage
- what do you have planned for tomorrow (tomorrow_plan): intent outside safe deterministic whitelist
- what are we doing tomorrow (tomorrow_plan): intent outside safe deterministic whitelist
- what should we work on tomorrow (tomorrow_plan): intent outside safe deterministic whitelist
- tomorrow plan (tomorrow_plan): intent outside safe deterministic whitelist
- plan for tomorrow (tomorrow_plan): intent outside safe deterministic whitelist
- what's planned for tomorrow (tomorrow_plan): intent outside safe deterministic whitelist
- what is planned for tomorrow (tomorrow_plan): intent outside safe deterministic whitelist
- what's the plan for tomorrow (tomorrow_plan): intent outside safe deterministic whitelist
- tomorrows plan (tomorrow_plan): intent outside safe deterministic whitelist
- tomorrow's plan (tomorrow_plan): intent outside safe deterministic whitelist
- what if you don't know (unknown_handling): not useful for deterministic audit
- what if you dont know (unknown_handling): not useful for deterministic audit
- what if you dont have the answer (unknown_handling): not useful for deterministic audit
- what if you don't have the answer (unknown_handling): not useful for deterministic audit
- what if you cannot answer (unknown_handling): not useful for deterministic audit
- what if you can't answer (unknown_handling): not useful for deterministic audit
- what happens if you don't know (unknown_handling): not useful for deterministic audit
- what happens if you dont know (unknown_handling): not useful for deterministic audit
- how do you handle unknowns (unknown_handling): not useful for deterministic audit
- how do you handle not knowing (unknown_handling): not useful for deterministic audit
- what do you do when you don't know (unknown_handling): not useful for deterministic audit
- what do you do when you dont know (unknown_handling): not useful for deterministic audit
- are we ready (pilot_readiness): intent outside safe deterministic whitelist
- ready for pilot (pilot_readiness): intent outside safe deterministic whitelist
- 10-user pilot (pilot_readiness): intent outside safe deterministic whitelist
- 10 user pilot (pilot_readiness): intent outside safe deterministic whitelist
- pilot ready (pilot_readiness): intent outside safe deterministic whitelist
- pilot launch (pilot_readiness): intent outside safe deterministic whitelist
- ready to launch (pilot_readiness): intent outside safe deterministic whitelist
- ready for launch (pilot_readiness): intent outside safe deterministic whitelist
- show last plan (show_last_daily_plan): duplicate intent coverage
- what was the last plan (show_last_daily_plan): duplicate intent coverage
- show previous plan (show_last_daily_plan): duplicate intent coverage
- what was yesterday's plan (show_last_daily_plan): duplicate intent coverage
- show me the last daily plan (show_last_daily_plan): duplicate intent coverage
- what was the last daily plan (show_last_daily_plan): duplicate intent coverage
- last nexus plan (show_last_daily_plan): duplicate intent coverage
- previous daily plan (show_last_daily_plan): duplicate intent coverage
- show the last plan (show_last_daily_plan): duplicate intent coverage
- what did the last plan say (show_last_daily_plan): duplicate intent coverage
- hermes run daily operating cycle (daily_operating_cycle): duplicate intent coverage
- hermes, run daily operating cycle (daily_operating_cycle): duplicate intent coverage
- daily operating cycle (daily_operating_cycle): duplicate intent coverage
- run daily cycle (daily_operating_cycle): duplicate intent coverage
- what should i work on today (daily_operating_cycle): duplicate intent coverage
- what should we work on today (daily_operating_cycle): duplicate intent coverage
- what should i focus on today (daily_operating_cycle): duplicate intent coverage
- what should we focus on today (daily_operating_cycle): duplicate intent coverage
- show today's nexus plan (daily_operating_cycle): duplicate intent coverage
- show today's plan (daily_operating_cycle): duplicate intent coverage
- show today nexus plan (daily_operating_cycle): duplicate intent coverage
- nexus plan today (daily_operating_cycle): duplicate intent coverage
- today's nexus plan (daily_operating_cycle): duplicate intent coverage
- todays nexus plan (daily_operating_cycle): duplicate intent coverage
- todays plan (daily_operating_cycle): duplicate intent coverage
- show nexus plan (daily_operating_cycle): duplicate intent coverage
- daily plan (daily_operating_cycle): duplicate intent coverage
- show items needing approval (show_approval_queue): duplicate intent coverage
- approval queue (show_approval_queue): duplicate intent coverage
- what is waiting for my approval (show_approval_queue): duplicate intent coverage
- show approval needed (show_approval_queue): duplicate intent coverage
- what needs ray approval (show_approval_queue): duplicate intent coverage
- show what needs approval (show_approval_queue): duplicate intent coverage
- what needs my approval (show_approval_queue): duplicate intent coverage
- pending approvals (show_approval_queue): duplicate intent coverage
- approval needed (show_approval_queue): duplicate intent coverage
- what is waiting for approval (show_approval_queue): duplicate intent coverage
- what requires approval (show_approval_queue): duplicate intent coverage
- what is pending approval (show_approval_queue): duplicate intent coverage
- continue while i'm out (daily_continue_while_out): duplicate intent coverage
- keep working while i am out (daily_continue_while_out): duplicate intent coverage
- keep working while i'm out (daily_continue_while_out): duplicate intent coverage
- what can you do while i am gone (daily_continue_while_out): duplicate intent coverage
- what can you do while i'm gone (daily_continue_while_out): duplicate intent coverage
- what can you do while i am away (daily_continue_while_out): duplicate intent coverage
- work while i am out (daily_continue_while_out): duplicate intent coverage
- keep going while i am out (daily_continue_while_out): duplicate intent coverage
- continue work (daily_continue_while_out): duplicate intent coverage
- continue while i am gone (daily_continue_while_out): duplicate intent coverage
- work while i am away (daily_continue_while_out): duplicate intent coverage
- 30-day revenue plan (thirty_day_revenue_plan): duplicate intent coverage
- plan to make money this month (thirty_day_revenue_plan): duplicate intent coverage
- how do we make money this month (thirty_day_revenue_plan): duplicate intent coverage
- make money in the next 30 days (thirty_day_revenue_plan): duplicate intent coverage
- 30 day plan (thirty_day_revenue_plan): duplicate intent coverage
- get to 1000 a week (thirty_day_revenue_plan): duplicate intent coverage
- get to $1000 a week (thirty_day_revenue_plan): duplicate intent coverage
- how do we get to 1000 a week (thirty_day_revenue_plan): duplicate intent coverage
- how to make 1000 a week (thirty_day_revenue_plan): duplicate intent coverage
- revenue plan for the month (thirty_day_revenue_plan): duplicate intent coverage
- monthly revenue plan (thirty_day_revenue_plan): duplicate intent coverage
- we need to come up with a plan to make money (thirty_day_revenue_plan): duplicate intent coverage
- show today's top money move (daily_top_revenue_move): duplicate intent coverage
- top revenue move (daily_top_revenue_move): duplicate intent coverage
- top money move today (daily_top_revenue_move): duplicate intent coverage
- best revenue move today (daily_top_revenue_move): duplicate intent coverage
- what is the top revenue move (daily_top_revenue_move): duplicate intent coverage
- today's top money move (daily_top_revenue_move): duplicate intent coverage
- today's top revenue move (daily_top_revenue_move): duplicate intent coverage
- show top money move (daily_top_revenue_move): duplicate intent coverage
- show revenue move (daily_top_revenue_move): duplicate intent coverage
- what can make money today (daily_top_revenue_move): duplicate intent coverage
- how do we make money today (daily_top_revenue_move): duplicate intent coverage
- todays top revenue move (daily_top_revenue_move): duplicate intent coverage
- todays top money move (daily_top_revenue_move): duplicate intent coverage
- show blockers (daily_blockers): duplicate intent coverage
- what is blocked (daily_blockers): duplicate intent coverage
- what is stopping us (daily_blockers): duplicate intent coverage
- show current blockers (daily_blockers): duplicate intent coverage
- what are the blockers (daily_blockers): duplicate intent coverage
- today's blockers (daily_blockers): duplicate intent coverage
- current blockers (daily_blockers): duplicate intent coverage
- what's blocked (daily_blockers): duplicate intent coverage
- blockers today (daily_blockers): duplicate intent coverage
- todays blockers (daily_blockers): duplicate intent coverage
- what happened while i was out (while_out_summary): duplicate intent coverage
- while i was out (while_out_summary): duplicate intent coverage
- while i was away (while_out_summary): duplicate intent coverage
- while i was gone (while_out_summary): duplicate intent coverage
- what did hermes do while i was out (while_out_summary): duplicate intent coverage
- catch me up from last plan (while_out_summary): duplicate intent coverage
- what have you been doing (while_out_summary): duplicate intent coverage
- what did you get done (while_out_summary): duplicate intent coverage
- while you were running (while_out_summary): duplicate intent coverage
- what did you work on (while_out_summary): duplicate intent coverage
- what is pending (pending_daily_items): duplicate intent coverage
- pending cycle items (pending_daily_items): duplicate intent coverage
- what needs doing (pending_daily_items): duplicate intent coverage
- show what is pending (pending_daily_items): duplicate intent coverage
- list pending items (pending_daily_items): duplicate intent coverage
- pending daily items (pending_daily_items): duplicate intent coverage
- what items are pending (pending_daily_items): duplicate intent coverage
- show pending daily items (pending_daily_items): duplicate intent coverage
- pending tasks (pending_daily_items): duplicate intent coverage
- what still needs to be done (pending_daily_items): duplicate intent coverage
- what needs attention (pending_daily_items): duplicate intent coverage
- still pending (pending_daily_items): duplicate intent coverage
- pending from today (pending_daily_items): duplicate intent coverage
