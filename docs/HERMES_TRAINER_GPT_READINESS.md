# Hermes Trainer GPT Readiness

**Created:** 2026-05-29
**Status:** Readiness assessment — API not yet built

---

## What the Trainer GPT Will Do

Ray plans to connect a Nexus ChatGPT Custom GPT to Hermes. This GPT will:

1. **Audit Hermes responses** — check for quality, evidence alignment, and goal alignment
2. **Send Ray's feedback to Hermes** — corrections, preferences, priorities
3. **Register goals** — Ray can push new goals from ChatGPT into Nexus
4. **Create improvement tasks** — flag weak responses for Claude Code to fix
5. **Help Hermes summarize decisions** — translate technical status into CEO language
6. **Push structured corrections into memory** — improve Hermes reasoning over time

---

## Planned Endpoints

These endpoints should be built when Hermes gateway is stable. For now, they are read-only or handled via Telegram commands.

### Status / Discovery
```
GET /health
  Response: { "status": "ok", "version": "...", "timestamp": "..." }

GET /v1/provider-status
  Response: { "active_mode": "reliable|gateway", "providers": [...] }
```

### Goals
```
GET /v1/goals
  Response: [{ "goal_id": "...", "title": "...", "status": "...", "priority": ... }]

POST /v1/goals
  Body: { "title": "...", "category": "...", "description": "...", "success_criteria": [...] }
  Response: { "goal_id": "...", "created": true }
```

### Actions
```
GET /v1/actions
  Query: ?status=open|blocked|needs_approval
  Response: [{ "action_id": "...", "title": "...", "status": "...", "assigned_to": "..." }]

POST /v1/actions
  Body: { "title": "...", "goal_id": "...", "autonomous_allowed": true, "priority": 80 }
  Response: { "action_id": "...", "created": true }
```

### Decisions
```
GET /v1/decisions
  Query: ?limit=20
  Response: [{ "decision_id": "...", "decision": "...", "timestamp": "...", "evidence_used": [...] }]
```

### Feedback
```
POST /v1/feedback
  Body: { "source": "trainer_gpt", "response_id": "...", "feedback_type": "correction|confirmation", "message": "..." }
  Response: { "logged": true, "improvement_task_created": false }
```

### Source Intake
```
POST /v1/source-intake
  Body: { "url": "...", "context": "..." }
  Response: { "intake_id": "...", "assigned_scout": "...", "status": "queued" }
```

### Scout Dispatch
```
POST /v1/scout-dispatch
  Body: { "scout_id": "...", "input": "...", "goal_id": "..." }
  Response: { "dispatch_id": "...", "status": "queued", "artifact_will_be_at": "..." }
```

### Artifacts
```
GET /v1/artifacts/latest
  Query: ?type=handoff|intake|decision|goal|action&limit=5
  Response: [{ "artifact_id": "...", "path": "...", "created_at": "..." }]
```

---

## Current State (Evidence-Only Mode)

Until the full API is built, the Trainer GPT can interact via:

| Action | How |
|--------|-----|
| Check status | `show provider status` via Telegram |
| Review goals | Read `docs/reports/goals/hermes_goal_registry.json` |
| Review actions | Read `docs/reports/actions/hermes_action_queue.jsonl` |
| Review decisions | Read `docs/reports/decisions/hermes_decision_log.jsonl` |
| Register source | Send URL to Hermes via Telegram |
| Push correction | Send feedback to Hermes via Telegram + Ray reviews |

---

## When to Build the Full API

Build the full API when:
1. Hermes Gateway is stable (`HERMES_ALLOW_HERMES_GATEWAY=true` reliable for 7+ days)
2. Goal registry is populated with real-world goals (not just defaults)
3. Action queue has real action records from operating loop runs
4. Decision log has 50+ decisions

---

## Security Notes

- The Trainer GPT API key must be separate from `HERMES_GATEWAY_KEY`
- Never expose `HERMES_GATEWAY_KEY`, `OPENAI_API_KEY`, or any secrets via API responses
- Approval boundaries must be enforced — Trainer GPT cannot create live trading or paid actions
- All Trainer GPT actions are logged in the decision log
