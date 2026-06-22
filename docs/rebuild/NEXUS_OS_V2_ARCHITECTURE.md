# Nexus OS v2 — Architecture

Built from day one around three goals: **Communication · Monetization · Automation.**
One ledger, one runner, one scheduler, one dashboard. No file-as-state, no duplicate jobs.

```
                         ┌──────────────────────────────┐
                         │        Nexus OS (UI)         │  one dashboard
                         │ Comms·Money·Auto·Trading·    │
                         │ Social·Approvals·Proof Log   │
                         └───────────────▲──────────────┘
                                         │ reads/writes
        ┌────────────────────────────────┴────────────────────────────────┐
        │                       nexus_events (ledger)                      │  ← single source of truth
        │  append-only: {id, ts, type, actor, payload, status, dedup_key}  │
        └───▲────────▲────────────▲───────────────▲───────────────▲────────┘
            │        │            │               │               │
   ┌────────┴──┐ ┌───┴─────┐ ┌────┴──────┐ ┌──────┴──────┐ ┌──────┴───────┐
   │  Comms    │ │  Money  │ │ Automation│ │  Approvals  │ │  nexus_runner│  one job runner
   │  layer    │ │  layer  │ │   layer   │ │   system    │ │ + scheduler  │
   └───────────┘ └─────────┘ └───────────┘ └─────────────┘ └──────────────┘
```

## A. One event ledger — `nexus_events`
Append-only store (Supabase table or SQLite). Every action writes an event:
`{id, ts, type, actor, payload, status, dedup_key, correlation_id}`.
- The ledger **is** the state. Reports/UI are read-only *projections*.
- `dedup_key` gives idempotency for free (guards, schedulers, publishes).

## B. One job runner — `nexus_runner`
Small registered jobs (`research`, `creative`, `publish_facebook`, `demo_trade`, `brief`).
Each job: reads ledger → does work → writes events. One `run_lock` per job (idempotent).
No job sends Telegram directly — it emits an event the comms layer may relay.

## C. One communication layer — Hermes Advisor + TheChoseone + War Room
- **Hermes Advisor**: live AI when gateway/tunnel up, else honest snapshot (keep current pattern).
- **TheChoseone**: command interface (approve/reject/status) — read-only by default.
- **War Room**: digest sender. ALL outbound goes through `telegram_send_guard` (dedup/rate/purpose). One summary, never per-event bursts.

## D. One monetization layer
`offers` ($97 → $197 → $297 ladder) · `content` · `landing_pages` · `social_publishing` ·
`leads`. Each is a ledger producer/consumer. The $97 funnel is the spine.

## E. One automation layer
`research` → `creative generation` → `publishing` → `trading demo`. Jobs only; ledger-driven;
quality gate + compliance filter before anything is queued/published.

## F. One approval system
States: `draft → needs_review → approved → published` (or `rejected`/`revise`).
Approvals are ledger events; UI buttons emit them; real publish requires `approved`.
No one-click real publish; no faked approvals.

## G. One scheduler
Exactly one scheduler process (launchd OR cron OR systemd — pick one per host) that invokes
`nexus_runner <job>`. No duplicate jobs across checkouts. Times documented in one place.
`run_lock` + ledger `dedup_key` prevent double-runs.

## H. One dashboard — Nexus OS home
Tabs: **Communication · Monetization · Automation · Trading · Social · Approvals · Proof Log.**
Every tab is a projection of `nexus_events`. Proof Log = the audit trail Ray actually trusts.

## Cross-cutting
- **Secrets**: only in `.env` (gitignored) + host secret store; never in repo, never in plists.
- **Tokens**: Facebook via the proven exchange → non-expiring page token.
- **Branch discipline**: main is source of truth; protected; deploy from main.
- **Honesty**: every capability reports working/partial/failed/rebuild-needed from real events.
