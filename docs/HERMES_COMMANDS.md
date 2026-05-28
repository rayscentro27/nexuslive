# Hermes Collaboration Commands
*Updated: 2026-05-28 | Evidence Mode active: NO ARTIFACT = NO CLAIM*

---

## Strategic Conversation (Telegram / Away from Office)

These commands work when Ray is away. Hermes loads real artifacts before answering.

```
Hermes, catch me up.
Hermes, where are we?
Hermes, are we on track?
Hermes, what did Nexus produce since I left?
Hermes, what happened since yesterday?
```
Loads: latest CEO packet

```
Hermes, show me pending handoffs.
Hermes, what do you need my approval on?
Hermes, what are you waiting on me for?
```
Loads: `docs/reports/hermes_handoffs/handoff_*.md`

```
Hermes, what did Hermes decide on its own?
Hermes, show me the decision log.
```
Loads: `docs/reports/hermes_decisions/hermes_decision_log.jsonl`

```
Hermes, what happened with the OANDA demo?
Hermes, show me the last demo order.
```
Loads: `integrations/oanda_demo/reports/demo_execution_packet_*.json`

```
Hermes, what's a free alternative to Beehiiv?
Hermes, show me premium blocker resolutions.
Hermes, how do I replace [paid tool]?
```
Loads: `docs/reports/premium_blockers/blocker_resolution_*.md`

```
Hermes, record lesson: [text]
Hermes, remember this: [text]
Hermes, save feedback: [text]
```
Saves to: `docs/reports/ray_feedback/ray_feedback_*.json`

```
Hermes, what Telegram notifications did you send?
Hermes, show me recent proactive notifications.
```
Loads: `docs/reports/hermes_proactive_notifications.jsonl`

Every Hermes command loads from real saved artifacts. If an artifact is missing, Hermes will say so and provide the command to generate it.

---

## YouTube Source Accountability

Every YouTube channel or video Ray submits is tracked permanently. NO SOURCE DISAPPEARS.

```
Hermes, show me YouTube source status.
Hermes, what YouTube sources do we have?
Hermes, show me the YouTube registry.
```
Loads: `docs/reports/youtube/source_registry.json`

```
python scripts/run_youtube_source_reconciliation.py
```
Creates: `docs/reports/youtube/youtube_source_reconciliation_<ts>.md`

```
python scripts/run_youtube_intelligence_cycle.py --source-id <id>
python scripts/run_youtube_intelligence_cycle.py --all
```
Creates intelligence artifacts for each source.

---

## Evidence Mode

Hermes uses Evidence Mode to ensure every operational claim has a verified artifact.

**Blocked without artifact:**
- "Nexus processed X" → requires CEO packet or workflow_output ID
- "Hermes approved Y" → requires handoff artifact with status=approved
- "Trade executed" → requires OANDA order ID + execution packet
- "YouTube channel analyzed" → requires source_registry.json entry + intelligence report

**Evidence audit:**
```
python scripts/run_hermes_evidence_audit.py
```
Shows: which claim types have artifacts, which are missing, and what to run next.

**Theatrical language blocked:** taps tablet, sharp inhale, tracking live, already pulling up, etc.
**Fake trading blocked:** trade placed, scalp active, order confirmed, pips gained, etc.
**Beehiiv aliases normalized:** beehive, bee hive, behive, behiiv → all route to premium_blocker_resolver.

---

## CEO Packet

```
Hermes, show me the latest CEO monetization packet.
Hermes, summarize what Nexus produced.
Hermes, what finished products can I review?
Hermes, what should I critique first?
```
Loads: `docs/reports/ceo_review/NEXUS_MONETIZATION_CEO_PACKET_*.md`

---

## Risk / Risky Opportunities

```
Hermes, what made this opportunity risky?
Hermes, what can we safely take from it?
Hermes, what risky ideas should we avoid?
Hermes, what risky idea can be reframed into a safe product?
```
Loads: `docs/reports/risky_opportunities/risky_opportunity_analysis_*.md`
Log: `docs/reports/risky_opportunities/risk_learning_log.json`

---

## Learning / Mistakes

```
Hermes, what did you learn from the last run?
Hermes, what mistake are you repeating?
Hermes, what did you downgrade after review?
Hermes, what failed and why?
```
Loads: `docs/reports/hermes_mistake_memory.json`
Critique: `docs/reports/ceo_review/NEXUS_CEO_CRITIQUE_*.md`

---

## Monetization

```
Hermes, what can make money in the next 30 days?
Hermes, which monetization path is fastest?
Hermes, which content should we create first?
Hermes, what offer should we test?
```
Loads: `docs/reports/monetization/30_day_revenue_plan_*.md`

---

## Credit / Funding Strategies

```
Hermes, find a new credit repair strategy.
Hermes, validate this funding readiness strategy.
Hermes, what can Nexus safely teach clients?
Hermes, what requires compliance review?
```
Loads: `docs/reports/learn_by_doing/credit_repair/compliance_review_*.md`

**Important:** No credit/funding strategy is client-safe until a compliance_review artifact exists.

---

## GitHub / System Improvement

```
Hermes, run weekly GitHub trend research.
Hermes, what GitHub repo could improve Nexus this week?
Hermes, is this repo a shiny object or does it improve Nexus?
```
CLI: `python scripts/run_weekly_github_trend_research.py`
Filter: `docs/reports/github_trends/github_trend_ceo_filter_*.md`

---

## Research Queue

```
Hermes, continue research.
Hermes, build the next research queue.
Hermes, what should you research overnight?
```
CLI: `python scripts/run_nexus_monetization_operating_cycle.py --mode continue-research --cost free --focus monetization,learning,system_improvement,credit_repair,business_funding,content --require-artifacts true`
Loads: `docs/reports/ceo_review/NEXUS_CONTINUED_RESEARCH_PACKET_*.md`

---

## Operating Cycle Commands

### Validation run (quick check — all engines)
```
python scripts/run_nexus_monetization_operating_cycle.py \
  --mode validation \
  --cost free \
  --focus monetization,learning,system_improvement,credit_repair \
  --require-artifacts true
```

### Continue-research mode (review prior, find new paths)
```
python scripts/run_nexus_monetization_operating_cycle.py \
  --mode continue-research \
  --cost free \
  --focus monetization,learning,system_improvement,credit_repair,business_funding,content \
  --require-artifacts true
```

### Overnight run (deep multi-domain)
```
python scripts/run_nexus_monetization_operating_cycle.py \
  --mode overnight \
  --cost free \
  --focus monetization,learning,system_improvement,content,trading,credit_repair,business_funding \
  --require-artifacts true \
  --max-runtime-minutes 360
```

### Content pipeline (any topic)
```
python scripts/run_content_pipeline.py \
  --topic "Why most businesses get denied funding and how Nexus helps fix readiness gaps" \
  --platforms youtube newsletter
```

### GitHub trend research
```
python scripts/run_weekly_github_trend_research.py
```

### Credit repair / funding readiness research
```
python scripts/run_nexus_learn_by_doing_cycle.py --domain credit_repair
python scripts/run_nexus_learn_by_doing_cycle.py --domain business_funding
```

### Demo broker test (OANDA practice — dry run)
```
python scripts/test_oanda_demo_execution_loop.py --dry-run
```

### Cycle with proactive Telegram notification
```
python scripts/run_nexus_monetization_operating_cycle.py \
  --mode validation \
  --cost free \
  --focus monetization,learning,system_improvement,credit_repair \
  --require-artifacts true \
  --notify-ray
```

### Cycle with all new flags
```
python scripts/run_nexus_monetization_operating_cycle.py \
  --mode validation \
  --cost free \
  --focus monetization,learning,system_improvement,credit_repair \
  --require-artifacts true \
  --resolve-premium-blockers \
  --include-demo-broker-test \
  --notify-ray \
  --proactive-telegram
```

### Resolve premium blockers only
```
python scripts/run_nexus_monetization_operating_cycle.py \
  --mode validation --resolve-premium-blockers
```

---

## Policy

**Autonomous (no approval needed):**
- Free research, internal testing, paper trading, content drafting, artifact creation, Supabase saving, mistake memory updates

**Requires Ray approval:**
- Spending money, paid APIs, live trading, public publishing, client-facing messages, production deployment, affiliate program signup, legal/financial/health claims, any content going to clients

**Always blocked:**
- Hiding failures, deleting logs, claiming completion without artifacts, guarantees of financial results, labeling strategies client-safe without compliance_review artifact

---

## Artifact Reference

| Artifact | Location |
|---|---|
| CEO packet | `docs/reports/ceo_review/NEXUS_MONETIZATION_CEO_PACKET_*.md` |
| CEO critique | `docs/reports/ceo_review/NEXUS_CEO_CRITIQUE_*.md` |
| Continued research | `docs/reports/ceo_review/NEXUS_CONTINUED_RESEARCH_PACKET_*.md` |
| Risky opportunity | `docs/reports/risky_opportunities/risky_opportunity_analysis_*.md` |
| Risk log | `docs/reports/risky_opportunities/risk_learning_log.json` |
| Mistake memory | `docs/reports/hermes_mistake_memory.json` |
| Compliance review | `docs/reports/learn_by_doing/credit_repair/compliance_review_*.md` |
| 30-day plan | `docs/reports/monetization/30_day_revenue_plan_*.md` |
| GitHub trends | `docs/reports/github_trends/github_trending_research_*.md` |
| GitHub CEO filter | `docs/reports/github_trends/github_trend_ceo_filter_*.md` |
| Content approvals | `docs/content/approval_packets/*.json` |
| Ray feedback | `docs/reports/ray_feedback/ray_feedback_*.json` |
| Hermes handoffs | `docs/reports/hermes_handoffs/handoff_*.md` |
| Decision log | `docs/reports/hermes_decisions/hermes_decision_log.jsonl` |
| Demo exec packets | `integrations/oanda_demo/reports/demo_execution_packet_*.json` |
| Demo orders | `integrations/oanda_demo/reports/demo_orders_<date>.jsonl` |
| Premium blockers | `docs/reports/premium_blockers/blocker_resolution_*.md` |
| Conversations | `docs/reports/hermes_conversations/hermes_conversation_*.json` |
| Artifact memory | `docs/reports/hermes_artifact_memory.jsonl` |
| Proactive notifications | `docs/reports/hermes_proactive_notifications.jsonl` |
| YouTube source registry | `docs/reports/youtube/source_registry.json` |
| YouTube quality reviews | `docs/reports/youtube/quality_review_<id>_<ts>.json` |
| YouTube intelligence | `docs/reports/youtube/youtube_intelligence_report_<id>_<ts>.md` |
| Content intelligence | `docs/reports/youtube/content_intelligence_<id>_<ts>.json` |
| Monetization intelligence | `docs/reports/youtube/monetization_intelligence_<id>_<ts>.json` |
| Nexus improvement | `docs/reports/youtube/nexus_improvement_<id>_<ts>.json` |
| Compliance intelligence | `docs/reports/youtube/compliance_intelligence_<id>_<ts>.json` |
| YouTube reconciliation | `docs/reports/youtube/youtube_source_reconciliation_<ts>.md` |
| Nexus artifact registry | `docs/reports/artifact_registry/nexus_artifact_registry.jsonl` |
| Telegram source intake | `docs/reports/intake/telegram_source_intake.jsonl` |
| Scout dispatch log | `docs/reports/scout_dispatch/scout_dispatch_log.jsonl` |
| Scout handoffs | `docs/reports/scout_dispatch/scout_dispatch_<id>_<ts>.md` |
| Agent handoff log | `docs/reports/agent_handoffs/agent_handoff_log.jsonl` |
| Agent handoffs | `docs/reports/agent_handoffs/agent_handoff_<id>_<ts>.md` |
| AionUi review | `docs/reports/github_trends/aionui_system_improvement_review_<ts>.md` |

---

## Telegram Source Intake

When Ray sends any URL via Telegram, Hermes registers it immediately.

```
# Check what sources Ray has submitted
show source intake

# See what happened to a specific link
what happened to the last link

# Show pending unprocessed sources
show pending source

# Check the full artifact registry
show artifact registry

# Backfill registry with existing unregistered artifacts
python scripts/register_existing_artifacts.py --dry-run
python scripts/register_existing_artifacts.py
```

**Rules:**
- Every URL Ray sends is registered in `telegram_source_intake.jsonl`
- Every YouTube link gets a source_id and a scout dispatch
- NO SOURCE DISAPPEARS — if a URL was submitted, it's in the registry
- Ask "show source intake" to see the full log

---

## Agent Handoffs

When Hermes cannot run a scout directly, it creates a handoff for Claude Code or another agent.

```
# These are created automatically when a source requires processing:
docs/reports/agent_handoffs/agent_handoff_<id>_<ts>.md

# To manually create a handoff for a YouTube source:
python3 -c "
from lib.hermes_agent_handoff_builder import build_youtube_handoff
h = build_youtube_handoff(source_id='<id>', url='<url>')
print(h.file_path)
"

# To see pending handoffs:
python3 -c "
from lib.hermes_agent_handoff_builder import pending_handoffs
for h in pending_handoffs(): print(h.handoff_id, h.target_agent)
"
```

**Rules:**
- Every handoff must list acceptance criteria
- NO ARTIFACT = NO COMPLETION — agent must produce verified files before marking done
- All code tasks require Ray approval before deployment

---

## Artifact Registry Commands

```
# Quick status via Hermes
show artifact registry

# Full registry audit
python scripts/run_hermes_evidence_audit.py

# Backfill unregistered existing files
python scripts/register_existing_artifacts.py

# YouTube source reconciliation (find unregistered YouTube URLs)
python scripts/run_youtube_source_reconciliation.py

# Run intelligence cycle on all pending YouTube sources
python scripts/run_youtube_intelligence_cycle.py --all --dry-run
python scripts/run_youtube_intelligence_cycle.py --all
```
