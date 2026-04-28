# Nexus One — Windows / AFinalChapter Handoff Contract
# Mac Mini defines. Windows creates and applies.
# Generated: 2026-03-23

## RULE
All SQL below must be created and applied from AFinalChapter (Windows).
Mac Mini (nexus-ai) does NOT apply migrations.

---

## 1. REQUIRED TABLE: executive_briefings

Nexus One stores every generated briefing here.
Mac Mini writes. Oracle/dashboard reads.

```sql
CREATE TABLE IF NOT EXISTS executive_briefings (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  briefing_type  text        NOT NULL DEFAULT 'daily',  -- daily | executive | alert | readiness
  content        text        NOT NULL,
  urgency        text        DEFAULT 'low',              -- low | medium | high | critical
  generated_by   text        DEFAULT 'nexus_one',
  org_id         uuid,
  created_at     timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_briefings_type    ON executive_briefings(briefing_type);
CREATE INDEX IF NOT EXISTS idx_briefings_urgency ON executive_briefings(urgency);
CREATE INDEX IF NOT EXISTS idx_briefings_created ON executive_briefings(created_at DESC);
```

---

## 2. REQUIRED TABLE: admin_commands (if not already exists)

Nexus One routes interpreted commands here.
Mac Mini writes. Oracle/dashboard reads and executes.

```sql
CREATE TABLE IF NOT EXISTS admin_commands (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_command   text        NOT NULL,
  command_type  text        NOT NULL,  -- source_add | analysis_run | pipeline_control | approve | override | etc.
  risk_level    text        DEFAULT 'low',   -- low | medium | high
  status        text        DEFAULT 'queued', -- queued | pending_approval | approved | executing | completed | rejected
  payload       jsonb       DEFAULT '{}'::jsonb,
  submitted_by  text        DEFAULT 'super_admin',
  approved_by   text,
  executed_at   timestamptz,
  result        jsonb,
  org_id        uuid,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_commands_status  ON admin_commands(status);
CREATE INDEX IF NOT EXISTS idx_admin_commands_type    ON admin_commands(command_type);
CREATE INDEX IF NOT EXISTS idx_admin_commands_risk    ON admin_commands(risk_level);
CREATE INDEX IF NOT EXISTS idx_admin_commands_created ON admin_commands(created_at DESC);
```

---

## 3. REQUIRED TABLE: system_readiness (optional — for structured readiness tracking)

```sql
CREATE TABLE IF NOT EXISTS system_readiness (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  check_name   text        NOT NULL,
  status       text        NOT NULL,  -- ok | degraded | blocked
  details      jsonb       DEFAULT '{}'::jsonb,
  checked_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_readiness_check   ON system_readiness(check_name);
CREATE INDEX IF NOT EXISTS idx_readiness_status  ON system_readiness(status);
CREATE INDEX IF NOT EXISTS idx_readiness_checked ON system_readiness(checked_at DESC);
```

---

## 4. ORACLE API — Required Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/api/nexus-one/brief`        | Latest executive briefing |
| GET    | `/api/nexus-one/attention`    | Items requiring operator attention |
| GET    | `/api/nexus-one/readiness`    | Current system readiness state |
| GET    | `/api/nexus-one/pending`      | All pending approvals (decisions, variants, commands) |
| POST   | `/api/nexus-one/command`      | Submit plain-language command |
| POST   | `/api/admin/commands/:id/approve` | Approve a pending command |
| POST   | `/api/admin/commands/:id/reject`  | Reject a pending command |

---

## 5. TELEGRAM WEBHOOK (if moving to webhook mode)

Current: polling mode via telegram_bot.py (launchd service)
Future: Telegram webhook → Oracle API → Nexus One command_interpreter

Webhook path to register with Telegram:
  `POST https://api.goclearonline.cc/api/telegram/webhook`

Payload forwarding:
  Oracle receives Telegram update → extracts `message.text` →
  calls Nexus One command_interpreter → returns formatted ack text →
  Oracle replies via `sendMessage` API

This keeps Nexus One command logic on Mac Mini.
Oracle is the transport layer only.

---

## 6. DASHBOARD SURFACES (AFinalChapter to build)

| Surface | Data Source | Priority |
|---------|-------------|----------|
| Executive Brief panel | `executive_briefings` table | HIGH |
| Pending Approvals panel | `admin_commands` + `instance_decisions` + `candidate_variants` | HIGH |
| Readiness checklist | `/api/nexus-one/readiness` | MEDIUM |
| Command input box | `POST /api/nexus-one/command` | MEDIUM |
| Improvement variants table | `candidate_variants` where status=scored | MEDIUM |
| Empire overview | `empire_entities` + `capital_deployments` | LOW |

---

## 7. MANUS DESKTOP READ CONTRACT

Manus Desktop may read (read-only):
- `executive_briefings` — latest briefings
- `candidate_variants` where `status=scored` — pending review
- `instance_decisions` where `status=pending` — pending decisions
- `system_readiness` — current readiness state

Manus Desktop must NOT:
- Write to any production table directly
- Call approve/reject endpoints
- Bypass admin_commands approval flow

Implementation: expose read-only API key in Oracle with restricted scopes.

---

## 8. SUMMARY — NEW TABLES TO CREATE (3 total)

| Table | Owner | Priority |
|---|---|---|
| `executive_briefings` | nexus-one writes, dashboard reads | HIGH |
| `admin_commands` | nexus-one writes, Oracle approves/executes | HIGH |
| `system_readiness` | nexus-one writes, dashboard reads | LOW |
