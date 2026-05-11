# CEO Auto-Routing

## Purpose

When a task comes in without a predefined AI employee role, the CEO auto-router reads the task and decides which specialist should handle it.

This is **opt-in only**. No existing behavior changes unless a job explicitly sets `use_ceo_auto_routing: true`.

---

## How Routing Works

1. Job payload arrives with `use_ceo_auto_routing: true`
2. `classify_task(payload)` scores the task text against keyword tables
3. The role with the most keyword matches wins
4. Routing metadata is attached to a **child job payload**
5. The child job is enqueued for the routed AI employee

Classification is **keyword-based and deterministic** — no LLM call required, zero extra cost, always fast.

For higher-quality classification, `build_ceo_routing_prompt(payload)` builds an LLM prompt you can pass through the model router.

---

## Supported Roles

| Role | Triggers On |
|---|---|
| `credit_analyst` | credit scores, FICO, utilization, negative items, derogatory marks |
| `credit_repair_letter_agent` | dispute letters, certified mail, Docupost, goodwill letters |
| `business_formation` | LLC, EIN, DUNS, NAICS, registered agent, business address |
| `funding_strategist` | Tier 1/2 funding, SBA, 0% business credit cards, funding roadmap |
| `grant_researcher` | grants, SBIR, federal/state small business programs |
| `opportunity_agent` | business ideas, leads, income opportunities, niche research |
| `trading_education` | forex, stocks, options, crypto, technical analysis |
| `marketing_strategist` | campaigns, funnels, email marketing, audience targeting |
| `content_creator` | TikTok, Instagram, YouTube scripts, captions, social content |
| `ad_copy_agent` | paid ad headlines, copy, CTAs, Facebook/Google ads |
| `compliance_reviewer` | FTC compliance, misleading claims, content approval |
| `hermes_ops` | system status, worker health, gateway, terminal operations |
| `research_analyst` | summarize, collect data, YouTube transcripts, market research |
| `unknown` | no keyword matches — routes to human review |

---

## How to Enable for One Job

Add `use_ceo_auto_routing: true` to the job payload:

```json
{
  "use_ceo_auto_routing": true,
  "use_nexus_super_prompt": true,
  "message": "Create a TikTok script explaining why entrepreneurs should become fundable before applying for business credit.",
  "source": "admin_portal",
  "channel": "portal",
  "created_from": "manual_test"
}
```

Expected routing: `content_creator` (TikTok + script + fundable keywords match)

---

## Child Job Payload

When a job is routed, the child payload looks like:

```json
{
  "parent_job_id": "original-job-uuid",
  "routed_by": "ceo_agent",
  "recommended_role": "content_creator",
  "routing_confidence": 0.90,
  "routing_reason": "Matched 3 keyword(s) for 'content_creator'",
  "task_type": "short_form_content",
  "requires_human_review": false,
  "requires_compliance_review": true,
  "use_nexus_super_prompt": true,
  "task_description": "Create a TikTok script explaining...",
  "original_payload": { ... }
}
```

API keys and sensitive fields are stripped before the child job is built.

---

## Self-Running Loop

`lib/ceo_routing_loop.py` is the autonomous daemon that polls Supabase and routes jobs automatically. It runs independently of any existing worker and only touches events it explicitly claims.

### Event contract

| Field | Value |
|---|---|
| Table | `system_events` |
| Claim filter | `event_type = 'ceo_route_request'` + `status = 'pending'` |
| Claim status | `routing` (prevents double-routing) |
| Routed status | `routed` |
| Failed status | `routing_failed` |
| Child `event_type` | `ceo_routed` |
| Child `payload` | full `build_child_job_payload()` output |

Downstream role workers listen for `event_type = 'ceo_routed'` and filter by `payload->>'recommended_role'`.

### Run

```bash
# Daemon mode (polls every 15 seconds):
python3 /Users/raymonddavis/nexus-ai/lib/ceo_routing_loop.py

# One cycle only (useful for cron or testing):
python3 /Users/raymonddavis/nexus-ai/lib/ceo_routing_loop.py --once

# Offline classification test — no Supabase writes:
python3 /Users/raymonddavis/nexus-ai/lib/ceo_routing_loop.py --test \
  "Create a TikTok script about becoming fundable."
```

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `CEO_ROUTING_POLL_INTERVAL` | `15` | Seconds between poll cycles |
| `CEO_ROUTING_BATCH_SIZE` | `10` | Max events per cycle |
| `CEO_ROUTING_DRY_RUN` | `false` | Classify without writing to Supabase |

### How to submit a job to the loop

Insert a row into `system_events`:

```json
{
  "event_type": "ceo_route_request",
  "status": "pending",
  "payload": {
    "use_ceo_auto_routing": true,
    "message": "Create a TikTok script explaining why entrepreneurs need business credit."
  }
}
```

---

## Manual Integration Point

For one-off routing inside any existing handler (without the daemon):

```python
from lib.ceo_auto_router import classify_task, build_child_job_payload

def process_job(payload: dict, job_id: str):
    if payload.get("use_ceo_auto_routing"):
        classification = classify_task(payload)
        child = build_child_job_payload(payload, classification, parent_job_id=job_id)
        # enqueue child via your existing job_queue writer
        enqueue_job(child)
        return

    # ... existing job handling unchanged
```

Jobs without `use_ceo_auto_routing` flow through the existing path with zero changes.

---

## How to Disable Instantly

**Per-job:** Remove `use_ceo_auto_routing: true` from the payload.

**Loop only:** Stop the `ceo_routing_loop.py` process (SIGTERM — it finishes the current batch then exits cleanly).

**System-wide:** The router is a pure function module — it has no hooks, no background processes, no listeners unless you start the loop. Deleting or not importing `ceo_auto_router.py` disables it completely. Nothing else breaks.

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Wrong role classification | Low | Keyword matching is transparent; check `routing_reason` in child payload |
| Low confidence routes | Medium | `routing_confidence < 0.5` indicates ambiguity; check `requires_human_review` flag |
| Double-routing | None | Loop claims with unique `routing` status before processing — concurrent loops skip claimed events |
| Child job not enqueued | Low | Parent marked `routing_failed`; inspect `error_msg`; re-submit with `status='pending'` |
| API keys in payload | None | `build_child_job_payload` strips `api_key`, `token`, `password`, `secret`, `ssn`, `dob`, `credit_card` |

---

## Test Commands

```bash
# Run all unit tests (no network, no DB):
python3 /Users/raymonddavis/nexus-ai/lib/ceo_auto_router_test.py

# Offline loop test (classify only, no writes):
python3 /Users/raymonddavis/nexus-ai/lib/ceo_routing_loop.py --test \
  "Help me dispute a collection account and write a goodwill letter."

# One poll cycle (reads/writes live Supabase):
python3 /Users/raymonddavis/nexus-ai/lib/ceo_routing_loop.py --once

# Dry-run daemon (classifies without writing):
CEO_ROUTING_DRY_RUN=true python3 /Users/raymonddavis/nexus-ai/lib/ceo_routing_loop.py
```

---

## Rollback

1. Stop the `ceo_routing_loop.py` process.
2. Stop passing `event_type: ceo_route_request` in new events.
3. No other files need reverting — nothing imports `ceo_routing_loop` automatically.
