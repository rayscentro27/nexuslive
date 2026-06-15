# Hermes Advisor — Web Research Policy

Hermes Advisor may help with research, **safely and read-only**.

## Rules
- **No live browsing by default.** `HERMES_ADVISOR_WEB_ENABLED=false`. When off,
  the Advisor **drafts a TheChoseone research task** instead of guessing.
- **No paid APIs** without Ray's explicit approval.
- **Never** mix private Nexus context into an external prompt — queries are
  sanitized (`sanitize_query`) to strip tokens, chat ids, account names, emails.
- **Citation-first:** every web result must include source URL + title.
- **Distinguish** verified web facts from recommendations.
- **Never** apply to affiliate programs, sign up, email, pay, or publish.

## Supported topics
affiliate programs · monetization offers · AI tools/repos · competitor offers ·
credit/funding content examples · trading-education strategy ideas · YouTube/channel
research · platform recommendations.

## Result shape (when a live tool is added)
title · url · summary · relevance_to_nexus · estimated_cost · benefit · risk ·
recommendation · source_date · confidence · fact_vs_recommendation.

## When web is unavailable (today)
Advisor says: "I can't browse directly from this bot yet. I can draft a research
task for TheChoseone." Then drafts:
`run web research: <topic> and return source links, summary, payout/cost, approval requirements, risk, and recommended next step.`

## Two response modes (`respond(topic)`)
- **Mode A — safe live web available + wired:** returns source links, short
  summary, key facts, payout/cost, requirements, risk, Hermes opinion,
  recommended next step, and an optional TheChoseone command. (No provider is
  wired today, so this path is not reachable by default — it never fabricates.)
- **Mode B — direct web unavailable (default):** says plainly "I can't browse
  directly from this bot yet" and hands a ready research task to TheChoseone,
  with the standing "do not apply/email/publish/activate/paid-API" footer.

## Sanitization hardening
`sanitize_query()` now redacts both the key **and its value** (`token=ABC` →
`[redacted]`), plus org names and long numeric ids, so nothing private reaches
an external query or a drafted task.

## Module
`lib/hermes_advisor_web_research.py` — `web_enabled()`, `sanitize_query()`,
`draft_research_task()`, `research()`, `respond()`, `result_template()`.
Tests: `tests/test_hermes_advisor_web_research.py`.
