# Credential Readiness — Windows / AFinalChapter Handoff Contract
# Mac Mini defines checks. Windows creates tables and UI.
# Generated: 2026-03-24

## RULE
All SQL below must be created and applied from AFinalChapter (Windows).
Mac Mini (nexus-ai) does NOT apply migrations.

---

## 1. REQUIRED TABLE: integration_readiness

Mac Mini writes one row per check (upsert on integration_key + check_key).
Dashboard reads for Credential Management UI.

```sql
CREATE TABLE IF NOT EXISTS integration_readiness (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  integration_key  text        NOT NULL,  -- e.g. 'supabase', 'telegram', 'openclaw'
  check_key        text        NOT NULL,  -- e.g. 'connectivity', 'bot_token', 'gateway'
  status           text        NOT NULL,  -- ok | degraded | missing | blocked
  severity         text        DEFAULT 'medium',  -- critical | high | medium | low
  message          text,                  -- human-readable, NO raw secrets
  last_checked_at  timestamptz DEFAULT now(),
  UNIQUE(integration_key, check_key)
);

CREATE INDEX IF NOT EXISTS idx_readiness_integration ON integration_readiness(integration_key);
CREATE INDEX IF NOT EXISTS idx_readiness_status      ON integration_readiness(status);
CREATE INDEX IF NOT EXISTS idx_readiness_severity    ON integration_readiness(severity);
CREATE INDEX IF NOT EXISTS idx_readiness_checked     ON integration_readiness(last_checked_at DESC);
```

---

## 2. REQUIRED: executive_briefings table (if not created from previous contract)

Readiness worker also writes readiness briefings here.
Schema already defined in NEXUS_ONE_WINDOWS_CONTRACT.md.

If not yet created:

```sql
CREATE TABLE IF NOT EXISTS executive_briefings (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  briefing_type  text        NOT NULL DEFAULT 'daily',
  content        text        NOT NULL,
  urgency        text        DEFAULT 'low',
  generated_by   text        DEFAULT 'nexus_one',
  org_id         uuid,
  created_at     timestamptz DEFAULT now()
);
```

---

## 3. SECRET SAFETY CONTRACT (enforced on Mac Mini side)

The following fields are NEVER stored in any table or log:
- Raw API keys / tokens
- Supabase service role keys
- OAuth tokens
- Private keys or credentials of any kind

Only stored:
- `present` / `missing` (env var presence)
- `set (N chars)` — length hint only, never value
- `configured` / `verified` / `degraded` — integration state
- Human-readable issue descriptions (no values)

This contract is enforced in `readiness/integration_checks.py` via `_env_hint()`.

---

## 4. CREDENTIAL MANAGEMENT UI CONTRACT (AFinalChapter to build)

The Windows dashboard Credential Management panel should:

### Read
```
GET /api/readiness                   — latest status per integration
GET /api/readiness/:integration_key  — history for one integration
GET /api/readiness/blockers          — critical + pilot-blocking items only
```

### Display columns (from integration_readiness table)
| Column | Display As |
|--------|-----------|
| integration_key | Integration name |
| check_key | Check type |
| status | Status badge (ok=green, degraded=yellow, blocked/missing=red) |
| severity | Priority badge |
| message | Issue description |
| last_checked_at | Last checked time |

### Write (credential entry — Windows-side only)
```
POST /api/credentials/set   — store credential in environment/secrets manager
```
Mac Mini NEVER receives raw secrets through the dashboard.
Credentials are set directly on the Mac Mini via `.env` file or launchd env.

---

## 5. INTEGRATION CHECK MANIFEST

Mac Mini runs these checks. Status stored in `integration_readiness`.

### Required (pilot-blocking if critical status)

| integration_key | check_key | severity | what it checks |
|---|---|---|---|
| supabase | connectivity | critical | REST API reachable + authenticated |
| supabase | tables | critical | All required tables accessible |
| telegram | bot_token | critical | Bot token valid via getMe |
| telegram | chat_id | high | TELEGRAM_CHAT_ID env var set |
| openclaw | gateway | high | Gateway running at localhost:18789 |
| workers | recent_runs | high | agent_run_summaries has recent entries |
| command_ingestion | table_access | high | admin_commands table accessible |
| source_registry | table_access | medium | sources table accessible |
| self_healing | table_access | medium | improvement_experiments accessible |
| nexus_one | runtime | critical | All Nexus One prerequisites met |

### Optional (degraded only — not pilot-blocking)

| integration_key | check_key | severity | what it checks |
|---|---|---|---|
| oanda | credentials | medium | OANDA_API_KEY + OANDA_ACCOUNT_ID set |
| tradingview | signal_router | medium | Signal router on :8000 |
| manus | briefing_access | low | executive_briefings readable |

---

## 6. CRON SCHEDULE

Add to Mac Mini crontab:

```cron
# Readiness check — every 30 min during setup/pilot
*/30 * * * *  cd /Users/raymonddavis/nexus-ai && /usr/bin/env python3 -m readiness.readiness_worker --silent >> /Users/raymonddavis/logs/readiness.log 2>&1

# Daily Telegram readiness report at 7am
0 7 * * *  cd /Users/raymonddavis/nexus-ai && /usr/bin/env python3 -m readiness.readiness_worker >> /Users/raymonddavis/logs/readiness.log 2>&1
```

---

## 7. SUMMARY — NEW TABLES TO CREATE (1 required, 1 if not already done)

| Table | Priority |
|---|---|
| `integration_readiness` | HIGH — required for credential management system |
| `executive_briefings` | HIGH — already in NEXUS_ONE_WINDOWS_CONTRACT.md |
