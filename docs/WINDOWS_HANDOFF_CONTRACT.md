# Windows / AFinalChapter Handoff Contract
# Mac Mini → Windows SQL + API Requirements
# Generated: 2026-03-23

## RULE
All SQL below must be created and applied from AFinalChapter (Windows).
Mac Mini (nexus-ai) does NOT apply migrations.

---

## 1. IMPROVEMENT ENGINE — Self-Healing System

```sql
-- improvement_experiments — proposed experiments from optimization observations
CREATE TABLE IF NOT EXISTS improvement_experiments (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  domain           text        NOT NULL,   -- strategy | signal | funding_logic | communication | source
  title            text        NOT NULL,
  hypothesis       text,
  baseline_config  jsonb       DEFAULT '{}'::jsonb,
  proposed_by      text        DEFAULT 'system',
  status           text        DEFAULT 'proposed', -- proposed | testing | scored | approved | promoted | rejected
  org_id           uuid,
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_imp_exp_domain  ON improvement_experiments(domain);
CREATE INDEX IF NOT EXISTS idx_imp_exp_status  ON improvement_experiments(status);
CREATE INDEX IF NOT EXISTS idx_imp_exp_created ON improvement_experiments(created_at DESC);

-- candidate_variants — variant configs awaiting human review + approval
CREATE TABLE IF NOT EXISTS candidate_variants (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id    uuid        NOT NULL REFERENCES improvement_experiments(id) ON DELETE CASCADE,
  variant_name     text        NOT NULL,
  variant_config   jsonb       DEFAULT '{}'::jsonb,
  rationale        text,
  generated_by     text        DEFAULT 'system',
  status           text        DEFAULT 'candidate', -- candidate | testing | scored | approved | promoted | rejected
  sim_score        numeric,                          -- 0.0–1.0 simulation/backtest score
  sim_notes        text,
  approved_by      text,
  approval_notes   text,
  rejection_reason text,
  approved_at      timestamptz,
  promoted_at      timestamptz,
  updated_at       timestamptz DEFAULT now(),
  created_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_variants_experiment ON candidate_variants(experiment_id);
CREATE INDEX IF NOT EXISTS idx_variants_status     ON candidate_variants(status);
CREATE INDEX IF NOT EXISTS idx_variants_score      ON candidate_variants(sim_score DESC NULLS LAST);
```

---

## 2. EMPIRE INTELLIGENCE — Entities, Capital, Workforce, Regions

```sql
-- empire_entities — legal entities in the ownership structure
CREATE TABLE IF NOT EXISTS empire_entities (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name              text        NOT NULL,
  entity_type       text        NOT NULL,  -- llc | trust | holding | operating | fund | partnership
  state             text        DEFAULT 'TX',
  purpose           text,
  status            text        DEFAULT 'active',
  parent_entity_id  uuid,                  -- for ownership hierarchy
  org_id            uuid,
  metadata          jsonb       DEFAULT '{}'::jsonb,
  created_at        timestamptz DEFAULT now(),
  updated_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_entities_type   ON empire_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_status ON empire_entities(status);
CREATE INDEX IF NOT EXISTS idx_entities_parent ON empire_entities(parent_entity_id);

-- capital_deployments — capital flow tracking for decision support
CREATE TABLE IF NOT EXISTS capital_deployments (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  amount       numeric     NOT NULL,
  source       text        NOT NULL,  -- revenue | funding | trading_profit | investment | reinvestment
  use          text        NOT NULL,  -- operations | marketing | technology | hiring | expansion | reserve
  description  text,
  period       text        NOT NULL,  -- YYYY-MM
  status       text        DEFAULT 'logged',
  entity_id    uuid        REFERENCES empire_entities(id),
  instance_id  uuid        REFERENCES nexus_instances(id),
  approved_by  text,
  created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_capital_period   ON capital_deployments(period DESC);
CREATE INDEX IF NOT EXISTS idx_capital_source   ON capital_deployments(source);
CREATE INDEX IF NOT EXISTS idx_capital_use      ON capital_deployments(use);
CREATE INDEX IF NOT EXISTS idx_capital_entity   ON capital_deployments(entity_id);

-- empire_workforce — AI agents and human operators registry
CREATE TABLE IF NOT EXISTS empire_workforce (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name         text        NOT NULL,
  role         text        NOT NULL,  -- ai_agent | human_operator | va | closer | researcher | developer
  capacity     integer     DEFAULT 100,  -- % capacity 0-100
  status       text        DEFAULT 'active',
  entity_id    uuid        REFERENCES empire_entities(id),
  instance_id  uuid        REFERENCES nexus_instances(id),
  metadata     jsonb       DEFAULT '{}'::jsonb,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workforce_role   ON empire_workforce(role);
CREATE INDEX IF NOT EXISTS idx_workforce_status ON empire_workforce(status);

-- empire_regions — geographic expansion scoring
CREATE TABLE IF NOT EXISTS empire_regions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  region_name       text        NOT NULL UNIQUE,
  market_size_score numeric     DEFAULT 0,   -- 0-100
  competition_score numeric     DEFAULT 0,   -- 0-100 (lower = less competition)
  regulatory_score  numeric     DEFAULT 0,   -- 0-100 (higher = easier)
  total_score       numeric     DEFAULT 0,   -- weighted composite
  existing_presence boolean     DEFAULT false,
  status            text        DEFAULT 'candidate',  -- candidate | active | deprioritized
  notes             text,
  created_at        timestamptz DEFAULT now(),
  updated_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_regions_score  ON empire_regions(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_regions_status ON empire_regions(status);
```

---

## 3. REQUIRED FIELD ADDITIONS TO EXISTING TABLES

```sql
-- Add org_id to compliance_records if not present (for multi-tenant compliance)
ALTER TABLE compliance_records ADD COLUMN IF NOT EXISTS org_id uuid;

-- Add growth_rate to revenue_streams if not present
ALTER TABLE revenue_streams ADD COLUMN IF NOT EXISTS growth_rate numeric DEFAULT 0;

-- Add approved_at / promoted_at to candidate_variants (already in CREATE above)
-- No additional alters needed if tables are new.
```

---

## 4. ORACLE API — Required Endpoints (for AFinalChapter to build)

The following endpoints are expected by Mac Mini workers via Supabase REST.
Oracle/Fastify layer may proxy or enrich these:

| Table / Resource | Mac Mini Usage |
|---|---|
| `improvement_experiments` | POST (propose), GET (list by domain/status) |
| `candidate_variants` | POST (add variant), PATCH (score/approve/promote) |
| `empire_entities` | POST (register), GET (tree) |
| `capital_deployments` | POST (log event), GET (by period) |
| `empire_workforce` | POST (register), GET (by status/role) |
| `empire_regions` | POST (score), GET (order by total_score) |

---

## 5. WINDOWS API CONTRACT — Admin Endpoints Needed

Mac Mini admin command parser produces structured command payloads.
AFinalChapter Oracle layer should expose:

```
POST /api/admin/commands          — receive parsed admin commands from Telegram
POST /api/admin/approve/:id       — approve a pending decision/variant
POST /api/admin/override/:id      — override a decision
GET  /api/portfolio/snapshot      — latest portfolio state for dashboard
GET  /api/empire/state            — full empire state for CEO dashboard
GET  /api/improvement/pending     — variants awaiting human review
POST /api/improvement/approve/:id — approve a candidate variant
GET  /api/compliance/summary/:id  — client compliance summary
```

---

## 6. SUPABASE RLS NOTES

All new tables should inherit standard RLS pattern used by existing tables:
- `anon` key: read-only on non-sensitive tables
- `service_role` key: full access for Mac Mini workers
- Sensitive tables (candidate_variants, empire_entities, capital_deployments):
  restrict anon reads, require service_role for writes

---

## 7. SUMMARY — NEW TABLES TO CREATE (6 total)

| Table | Owner | Priority |
|---|---|---|
| improvement_experiments | nexus-ai reads/writes | HIGH — needed for self-healing engine |
| candidate_variants | nexus-ai reads/writes | HIGH — needed for self-healing engine |
| empire_entities | nexus-ai reads/writes | MEDIUM — empire intelligence |
| capital_deployments | nexus-ai reads/writes | MEDIUM — empire intelligence |
| empire_workforce | nexus-ai reads/writes | MEDIUM — empire intelligence |
| empire_regions | nexus-ai reads/writes | LOW — expansion planning |
