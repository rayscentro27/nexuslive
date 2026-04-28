# CEO Routed Workers

## Purpose

After CEO auto-routing classifies a job and creates a `ceo_routed` event, these workers pick up the event, generate an AI draft using the appropriate role prompt, and write the result to `workflow_outputs` for human review.

**Nothing is published, sent, or executed externally.** Every output lands in `workflow_outputs` with `status = 'pending_review'`. A human/admin must approve before any user-facing or external action is taken.

---

## Safety Guarantees

| Guarantee | Implementation |
|---|---|
| Disabled by default | `ENABLE_CEO_ROUTED_WORKERS=true` required to activate |
| Draft only | Outputs written to `workflow_outputs` with `status='pending_review'` |
| No external actions | Handlers contain no publish/send/post/execute paths |
| Forbidden key check | Tests assert `publish`, `send`, `post_to`, `execute`, `submit`, `dispatch_external` never appear in any handler output |
| Atomic event claim | PATCH-with-filter on `status=pending` prevents double-drafting |
| LLM failure safe | Missing/unreachable Ollama writes a placeholder draft; never crashes |
| Non-breaking | Zero existing files modified; existing job_queue and workflow behavior unchanged |
| Max iterations | `CEO_WORKER_MAX_ITERATIONS` enforces hard stop on the loop |

---

## How to Enable

Add to `nexus-ai/.env` or your environment:

```bash
ENABLE_CEO_ROUTED_WORKERS=true
```

Without this flag, the worker process exits immediately. `run_cycle()` returns `{disabled: true}`. No events are touched.

---

## How to Disable

**Immediately:** Remove `ENABLE_CEO_ROUTED_WORKERS=true` or set it to any other value. Send SIGTERM to the process — it finishes the current batch then exits cleanly.

**Permanently:** Stop the process. No other files need changes. The event dispatcher and all other workers are unaffected.

---

## Event Lifecycle

```
system_events
  pending         ← ceo_routing_loop created this row (event_type='ceo_routed')
      ↓
  claimed         ← ceo_routed_worker atomically claimed it
      ↓
  drafted         ← draft written to workflow_outputs
  draft_failed    ← error logged in error_msg column
```

The worker only ever touches events with `event_type='ceo_routed'` and `status='pending'`. It never modifies events it didn't claim.

---

## Draft Output Schema (workflow_outputs)

```json
{
  "workflow_type":            "ceo_routed_draft",
  "subject_type":             "content_creator",
  "subject_id":               "<event_id>",
  "status":                   "pending_review",
  "primary_action_key":       "review_draft",
  "primary_action_title":     "Review Content Creator Draft",
  "readiness_level":          "draft",
  "priority":                 "high | medium | low",
  "source_job_id":            "<event_id>",
  "summary":                  "<first 200 chars of draft>",
  "raw_output": {
    "role":              "content_creator",
    "draft_content":     "<full AI-generated draft>",
    "model_used":        "llama3.2:3b",
    "fallback_used":     false,
    "routing_confidence": 0.90,
    "requires_human_review": false
  }
}
```

Admin panels that already read `workflow_outputs` will see these rows automatically — filter on `workflow_type='ceo_routed_draft'` to isolate them.

---

## Supported Roles

| Role | Handler | Prompt File |
|---|---|---|
| `content_creator` | `handle_content_creator` | `skills/roles/content_creator.md` |
| `compliance_reviewer` | `handle_compliance_reviewer` | `skills/roles/compliance_reviewer.md` |
| `marketing_strategist` | `handle_marketing_strategist` | `skills/roles/marketing_strategist.md` |
| `credit_analyst` | `handle_credit_analyst` | `skills/roles/credit_analyst.md` |
| `business_formation` | `handle_business_formation` | `skills/roles/business_formation.md` |
| `funding_strategist` | `handle_funding_strategist` | `skills/roles/funding_strategist.md` |
| `research_analyst` | `handle_research_analyst` | `skills/roles/research_analyst.md` |
| `unknown` (fallback) | `handle_unknown` | `skills/roles/default.md` |

Any role not in the table uses `handle_unknown` — produces a generic draft, never crashes.

---

## Run Commands

```bash
# Daemon (polls every 20 seconds):
ENABLE_CEO_ROUTED_WORKERS=true python3 lib/ceo_routed_worker.py

# One cycle only (for cron or manual trigger):
ENABLE_CEO_ROUTED_WORKERS=true python3 lib/ceo_routed_worker.py --once

# Offline handler test — no Supabase, no real LLM:
python3 lib/ceo_routed_worker.py --test content_creator "Create a TikTok script about business credit."

# Dry-run daemon (classifies + drafts but never writes to Supabase):
ENABLE_CEO_ROUTED_WORKERS=true CEO_ROUTING_DRY_RUN=true python3 lib/ceo_routed_worker.py

# Run tests:
python3 lib/ceo_routed_worker_test.py
```

---

## Environment Variables

| Variable | Default | Effect |
|---|---|---|
| `ENABLE_CEO_ROUTED_WORKERS` | *(unset)* | Must be `"true"` to activate |
| `CEO_WORKER_POLL_INTERVAL` | `20` | Seconds between poll cycles |
| `CEO_WORKER_BATCH_SIZE` | `5` | Max events per cycle |
| `CEO_WORKER_MAX_ITERATIONS` | `0` | Hard stop after N iterations (`0` = unlimited) |
| `CEO_ROUTING_DRY_RUN` | *(unset)* | `"true"` = classify and draft, but skip all Supabase writes |

---

## Full Pipeline: End to End

```
1. Job arrives as system_event with event_type='ceo_route_request'
         ↓
2. ceo_routing_loop.py classifies it → creates child event (event_type='ceo_routed')
         ↓
3. ceo_routed_worker.py claims child event, runs role handler
         ↓
4. Handler calls PromptBuilder(role).build(task) → sends to Ollama (Netcup)
         ↓
5. Draft written to workflow_outputs (status='pending_review')
         ↓
6. Admin reviews draft in workflow_outputs panel
         ↓
7. Admin approves → downstream execution (NOT handled by this worker)
```

---

## Adding a New Role

1. Create `skills/roles/{role}.md` with the output format
2. Add a handler in `lib/ceo_routed_worker.py`:
   ```python
   def handle_grant_researcher(task, payload, *, llm_fn=None):
       return _make_draft("grant_researcher", "grant_research", task, payload, llm_fn=llm_fn)
   ```
3. Register in `_HANDLERS`:
   ```python
   "grant_researcher": handle_grant_researcher,
   ```
4. Add tests in `ceo_routed_worker_test.py`

No other files need to change.

---

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Ollama unavailable | Low | Placeholder draft written; event marked `drafted`; re-run when Ollama recovers |
| workflow_outputs schema mismatch | Low | `_sb_post` logs warning and returns None; event marked `draft_failed` |
| Double-draft | None | Atomic claim via PATCH-with-filter on `status=pending` |
| Accidental external action | None | No publish/send/execute paths exist in any handler |
| Existing workers disrupted | None | Zero existing files modified; new event_type is invisible to existing agents |
