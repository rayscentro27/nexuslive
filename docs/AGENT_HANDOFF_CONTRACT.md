# Agent Handoff Contract
*Every Nexus agent must follow this contract. NO ARTIFACT = NO COMPLETION.*

---

## Rule

When any agent (Claude Code, Codex, OpenCode, Hermes, or a Nexus worker) finishes a task, it MUST:

1. Register an artifact in `lib/nexus_artifact_registry.py`
2. Create a handoff record using `lib/hermes_action_handoff.py`
3. Update the relevant source registry (YouTube, GitHub, etc.)
4. Notify Hermes via `lib/hermes_proactive_notifier.py` if configured

**No task is marked "complete" without a verifiable artifact on disk or in Supabase.**

---

## Required Handoff Fields

```
AGENT HANDOFF:
  agent_name:          <who did the work>
  task:                <what was done>
  source_input:        <URL(s) or text that was processed>
  artifact_paths:      <list of files created or modified>
  summary:             <what was found / produced>
  what_hermes_should_know: <context for future Hermes responses>
  next_action:         <what should happen next>
  requires_ray_approval: <true/false>
  approval_reason:     <why approval is needed, if any>
  what_failed:         <errors or incomplete items, or "none">
```

---

## Example Handoffs

### 1. YouTube Research — Claude Code

```
AGENT HANDOFF:
agent_name: Claude Code
task: YouTube channel research
source_input:
  - https://youtube.com/@CreditSweepPro
artifact_paths:
  - docs/reports/youtube/youtube_intelligence_report_yt_abc123_20260528.md
  - docs/reports/youtube/content_intelligence_yt_abc123_20260528.json
  - docs/reports/youtube/monetization_intelligence_yt_abc123_20260528.json
  - docs/reports/youtube/compliance_intelligence_yt_abc123_20260528.json
summary:
  Processed 1 channel. Quality score 8.2/10 (high_value).
  Extracted 6 hooks, 3 monetization angles, 0 compliance flags.
what_hermes_should_know:
  Use this source for credit repair content ideas. Safe to reference.
  Source ID: yt_abc12345678
next_action:
  Create content packet using top 3 hooks.
requires_ray_approval: false
what_failed: none
```

### 2. Credit Repair Strategy Research

```
AGENT HANDOFF:
agent_name: claude_code
task: Credit repair strategy discovery
source_input:
  - learn_by_doing domain: credit_repair
artifact_paths:
  - docs/reports/learn_by_doing/credit_repair/new_strategy_discovery_20260528.md
  - docs/reports/learn_by_doing/credit_repair/compliance_review_20260528.md
summary:
  Discovered "medical debt removal via HIPAA privacy letter" strategy.
  Compliance reviewed — safe for educational content only.
  Compliance level: approved_for_internal_testing
what_hermes_should_know:
  Strategy passed compliance check. Not client-safe yet — needs source_verification first.
next_action:
  Upgrade to source_verified once primary source is documented.
requires_ray_approval: false
what_failed: none
```

### 3. Monetization Packet

```
AGENT HANDOFF:
agent_name: hermes
task: 30-day monetization plan
source_input:
  - operating_cycle run_id: cycle_20260528_001
artifact_paths:
  - docs/reports/monetization/30_day_revenue_plan_20260528.md
  - docs/reports/ceo_review/NEXUS_MONETIZATION_CEO_PACKET_20260528.md
summary:
  3 revenue paths identified: credit repair consulting, affiliate (Credit Karma),
  YouTube ad revenue. Projected 30-day ceiling: $2,400 (conservative).
what_hermes_should_know:
  Credit repair consulting path requires Ray's license review before client outreach.
next_action:
  Ray reviews CEO packet → approve/reject top path.
requires_ray_approval: true
approval_reason: Revenue path includes client-facing service; Ray must approve before launch.
what_failed: none
```

### 4. Trading Backtest

```
AGENT HANDOFF:
agent_name: vibe_trading_worker
task: EUR/USD RSI(14) backtest
source_input:
  - strategy: RSI_14_crossover_EURUSD
  - mode: paper_only
artifact_paths:
  - integrations/vibe_trading/results/backtest_EURUSD_RSI14_20260528.json
  - integrations/vibe_trading/reports/backtest_report_EURUSD_RSI14_20260528.md
summary:
  14-day backtest. Win rate: 57%. Max drawdown: 4.2%. Net P&L: +$38 paper.
what_hermes_should_know:
  Paper results only. No live trading. Requires Ray approval before OANDA demo.
next_action:
  Ray reviews results → approves OANDA demo test if win rate holds.
requires_ray_approval: true
approval_reason: Live demo trading requires Ray's explicit approval.
what_failed: none
```

### 5. OANDA Demo Test

```
AGENT HANDOFF:
agent_name: oanda_demo_adapter
task: OANDA practice account order test
source_input:
  - OANDA_ENVIRONMENT=practice
  - OANDA_DEMO_ENABLED=true (Ray-approved)
artifact_paths:
  - integrations/oanda_demo/reports/demo_execution_packet_20260528.json
  - integrations/oanda_demo/reports/demo_orders_20260528.jsonl
summary:
  1 micro-unit test order placed on EUR/USD. Filled at 1.0832.
  Order ID: 12345678. Practice account only.
what_hermes_should_know:
  Verify order ID 12345678 before citing any trade results.
  OANDA_ALLOW_LIVE=false confirmed.
next_action:
  Ray reviews execution packet.
requires_ray_approval: false
what_failed: none
```

### 6. GitHub Trend Research

```
AGENT HANDOFF:
agent_name: github_trend_researcher
task: Weekly GitHub trend research
source_input:
  - GitHub trending: python, AI, fintech (past 7 days)
artifact_paths:
  - docs/reports/github_trends/github_trending_research_20260528.md
  - docs/reports/github_trends/github_trending_recommendations_20260528.md
  - docs/reports/github_trends/github_trend_ceo_filter_20260528.md
summary:
  15 repos evaluated. 3 recommended (passed shiny-object filter).
  Top pick: langchain-tools for Hermes LLM routing.
what_hermes_should_know:
  2 repos flagged as shiny objects (reject_shiny_object status).
  1 repo may improve Nexus citation tracking.
next_action:
  Ray reviews CEO filter → approve integration sandbox test.
requires_ray_approval: false
what_failed: none
```

### 7. Premium Blocker Resolution

```
AGENT HANDOFF:
agent_name: premium_blocker_resolver
task: Beehiiv newsletter platform alternative research
source_input:
  - blocked_tool: beehiiv
  - reason: paid tier required for API/automation
artifact_paths:
  - docs/reports/premium_blockers/blocker_resolution_beehiiv_20260528.md
  - docs/reports/premium_blockers/blocker_resolution_beehiiv_20260528.json
summary:
  Top free alternative: Ghost self-hosted on Oracle ARM (free tier).
  ConvertKit free tier also viable for < 1,000 subscribers.
what_hermes_should_know:
  Ghost requires self-hosted setup. Ray must approve before deploying.
next_action:
  Ray approves Ghost → Hermes creates setup handoff for Claude Code.
requires_ray_approval: true
approval_reason: Self-hosted deployment needs Ray's infrastructure approval.
what_failed: none
```

### 8. Code Implementation

```
AGENT HANDOFF:
agent_name: Claude Code
task: Implement evidence gating for Hermes strategic routes
source_input:
  - 17-part Evidence Mode directive from Ray
artifact_paths:
  - lib/hermes_evidence_mode.py
  - lib/telegram_router.py (modified)
  - hermes_command_router/router.py (modified)
  - scripts/test_hermes_evidence_mode.py
summary:
  Created evidence engine with 16 claim types, theatrical language blocker,
  fake trading claim blocker, Beehiiv alias normalization.
  All 10 test scripts passing.
what_hermes_should_know:
  Evidence mode is active. Import from lib/hermes_evidence_mode.py.
  Call verified_status_block() for project status responses.
next_action:
  Ray reviews → approve commit and push.
requires_ray_approval: true
approval_reason: Ray requested explicit approval before commit/push.
what_failed: none
```

### 9. Failed Task

```
AGENT HANDOFF:
agent_name: youtube_transcript_worker
task: Download transcript for https://youtube.com/watch?v=abc123
source_input:
  - https://youtube.com/watch?v=abc123
artifact_paths: []
summary:
  FAILED — transcript not available (captions disabled on this video).
what_hermes_should_know:
  Source yt_def456 has transcript_status=not_available.
  Do NOT claim transcript was collected for this source.
next_action:
  Use video description + title for intelligence extraction.
  Mark source as transcript_not_available in registry.
requires_ray_approval: false
what_failed:
  YouTube transcript download failed: HTTPError 403 (captions disabled).
  Source registry updated: transcript_status=not_available.
```

---

## Enforcement

- Hermes will not report a task as "completed", "processed", or "analyzed" without an artifact record
- If Ray asks "did Claude Code process the YouTube channel?", Hermes checks `nexus_artifact_registry.jsonl` first
- If no artifact record exists, Hermes says: "I do not have a verified artifact for that task."
- Missing handoffs can be backfilled using: `python scripts/register_existing_artifacts.py`

---

## Artifact Registry CLI

```
# Register a new artifact
from lib.nexus_artifact_registry import register_artifact
register_artifact(
    agent_name="claude_code",
    agent_type="claude_code",
    source_input="https://youtube.com/@example",
    source_type="youtube_channel",
    artifact_type="markdown_report",
    title="YouTube Intelligence Report — example",
    file_path="docs/reports/youtube/youtube_intelligence_report_yt_abc_20260528.md",
)

# Find artifacts by URL
from lib.nexus_artifact_registry import find_by_source_url
arts = find_by_source_url("https://youtube.com/@example")
```
