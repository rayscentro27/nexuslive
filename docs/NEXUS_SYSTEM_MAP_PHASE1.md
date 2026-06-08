# Nexus System Map — Phase 1 (Audit, Map, Store)

Read-only operating inventory so Hermes can route tasks efficiently. Phase 1 is
**audit + map + store**. The autonomous dispatcher is intentionally **not** built yet.

## What exists now

- **Scanner:** `scripts/nexus_system_map_scan.py` (read-only by default; `--apply` writes to Supabase)
- **Migration (NOT applied):** `supabase/migrations/20260607000001_nexus_system_map.sql`
- **Reports:** `reports/system_map/nexus_system_map_<ts>.md` (+ `.json` with `--json`)

## Table strategy (reuse first)

| Need | Decision | Table |
|------|----------|-------|
| AI providers | **reuse** | `model_providers` |
| AI model routing | **reuse** | `model_routing_rules` |
| CLI registry | **reuse + extend** | `nexus_cli_tools` (+ version/path/installed/health/network_risk/cost_risk/can_run_locally/last_scanned_at) |
| Agent capabilities | **reuse** | `agent_capabilities` |
| Git repos | **new** | `nexus_system_repos` |
| OS processes/services | **new** | `nexus_system_processes` |
| Task→tool/repo routing | **new** | `nexus_task_routing_rules` |

All new tables: RLS enabled, admin-only (`user_profiles.role in ('admin','super_admin')`),
matching the `nexus_os_*` convention.

## Hermes integration plan (Phase 9 — deferred until tables applied)

Once `--apply` lands the data, extend the Hermes evidence builder
(`src/components/nexus-os/useNexusRecommendations.ts`) with a **summary-only**
system-map context for routing intents (e.g. "which tool/agent/repo should…"):

- installed CLIs (name + category + cost/network risk + approval) — names only, not raw rows
- active services (name + status + safety + approval) — top N by relevance
- AI provider health (configured/healthy + cost tier + best_for) + fallback order
- matching `nexus_task_routing_rules` for the detected task type

**Constraints:** never inject the full raw map; summarize to ~8–12 lines. Reuse the
existing intent classifier; add a `routing` intent that pulls this summary. No
dispatcher, no auto-execution — Hermes recommends; Ray approves risky actions.

Questions Hermes will then answer from verified data:
- What tools do we have? Which agent/CLI should do this? What repo owns it?
- What process is running / what's broken? What's the cheapest (local) path?
- What requires approval vs. what's safe to automate?

## Safety

Scanner never restarts/kills/installs anything, never prints secret values
(env-var **names** only), never runs trading/publishing/deploy commands, and writes
to Supabase **only** with `--apply`. Live trading remains disabled by default.

## Next action

Review the latest `reports/system_map/*.md`. To persist the map, approve:
`python3 scripts/nexus_system_map_scan.py --section all --apply`
(after the migration `20260607000001_nexus_system_map.sql` is applied).
