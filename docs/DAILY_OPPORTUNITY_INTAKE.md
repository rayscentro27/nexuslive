# Daily Opportunity Intake + Monetization Decision Cycle

**What it does:** Nexus automatically collects opportunity signals from YouTube, GitHub,
web keywords, social trend research, and monetization categories. Every source is registered,
scored, and assigned to the correct scout or runner. Hermes sends Ray ONE concise digest —
not individual messages for each source.

**Core rules:**
- NO SOURCE DISAPPEARS
- NO FAKE RESULTS — fallback tasks created if API unavailable
- NO PAID APIS without approval
- NO PUBLIC PUBLISHING without approval
- NO LIVE TRADING without approval
- FREE RESEARCH IS AUTONOMOUS

---

## How to Run

### Validation (safe, dry-run, recommended first run)
```bash
python3 scripts/run_daily_opportunity_intake.py \
  --mode validation \
  --cost free \
  --max-sources 20 \
  --register-artifacts true
```

### Daily mode (creates real action queue entries)
```bash
python3 scripts/run_daily_opportunity_intake.py \
  --mode daily \
  --max-sources 50 \
  --no-dry-run
```

### Standalone monetization decision cycle
```bash
python3 scripts/run_monetization_decision_cycle.py --mode validation --top-n 10
```

### Prerequisite check
```bash
python3 scripts/run_daily_engine_prerequisite_check.py
```

---

## How It Coordinates Existing Runners

| Daily Engine Does | Existing Runner Used |
|---|---|
| Collects YouTube sources | `run_youtube_intelligence_cycle.py`, `run_youtube_source_reconciliation.py` |
| Finds GitHub tools | `run_weekly_github_trend_research.py` |
| Content opportunities | `run_content_pipeline.py` (via action handoff, not direct launch) |
| Credit/funding research | `run_nexus_learn_by_doing_cycle.py` (via scout dispatch) |
| Monetization decisions | `run_nexus_monetization_operating_cycle.py` (integration) |
| Decision logging | `lib/hermes_action_queue.py`, `lib/hermes_decision_log.py` |
| Artifact registration | `lib/nexus_artifact_registry.py` |

---

## Telegram Commands

Say to @Nexuschosenbot:
- `Hermes, what did you find today?`
- `Hermes, what can make money this week?`
- `Hermes, show top monetization actions.`
- `Hermes, show rejected opportunities.`
- `Hermes, what sources are pending?`
- `Hermes, what scouts are working?`
- `Hermes, show daily research review.`
- `Hermes, what should I review first?`
- `Hermes, build content from the best opportunity.`
- `Hermes, what needs my approval?`
- `Hermes, continue research while I am out.`

---

## Anti-Spam Rules

Hermes sends Ray a message only for:
1. Daily digest (one per cycle)
2. Approval needed (paid tool, public publish, live trade)
3. Blocker (source unavailable, runner failing)
4. High-value opportunity (score ≥ 75)

Silent (no Telegram): source_registered, source_rejected, scout_assigned, artifact_created

---

## Approval Boundaries

**Autonomous (no approval needed):**
- Free research, source intake, artifact creation
- Source registration and scoring
- Content drafts (internal)
- Funnel plans (internal)
- Backtesting / paper trading / demo-only
- Telegram summaries to Ray

**Requires Ray approval:**
- Paid APIs or tools
- Public publishing
- Client-facing messages
- Affiliate signup
- Stripe / payment activation
- Live trading
- Production deployment

---

## Artifacts Produced

- `docs/reports/intake/daily_opportunity_intake_<ts>.json` — intake records
- `docs/reports/intake/daily_opportunity_intake_<ts>.md` — human-readable
- `docs/reports/monetization/monetization_decision_cycle_<ts>.json` — decisions
- `docs/reports/monetization/top_monetization_actions_<ts>.md` — top 5 actions
- `docs/reports/monetization/rejected_opportunities_<ts>.json` — rejected log
- `docs/reports/review/daily_research_review_<ts>.md` — full trust review
- `docs/reports/evidence/daily_engine_prerequisite_check_<ts>.md` — system check

---

## Source Config

Edit `config/opportunity_intake_sources.yaml` to:
- Add YouTube channel IDs
- Add keyword searches
- Adjust scoring weights
- Add monetization categories

---

## Scheduler

**NOT ENABLED.** Ray must approve before daily automation starts.
See `docs/DAILY_OPPORTUNITY_SCHEDULER_PLAN.md` for the schedule plan.
