# Nexus OS v2 — 7-Day Build Plan

One scheduler, one ledger, main-only. Each day ends with a working, demoable slice.

## Day 1 — Repo + event ledger + dashboard shell
- `git init ~/nexus-os-v2`, main-only, `.gitignore` (`.env`, `outputs/`, `logs/`), `.env.example`.
- `nexus_events` ledger (SQLite to start; Supabase table adapter behind an interface).
- Dashboard shell with 7 tabs reading the ledger (empty states OK).
- **Done:** events can be appended + viewed.

## Day 2 — Communication layer + Hermes/TheChoseone proof
- Port `telegram_send_guard` + `run_lock` (keep).
- Hermes Advisor status + snapshot fallback (port `hermes-chat` pattern).
- TheChoseone command stub (status/approve/reject) → ledger events.
- **Done:** one guarded War Room summary sends; no bursts.

## Day 3 — Facebook publishing + social queue
- Port FB publisher (`content_employee/publisher.py` idea) + token tools (`facebook_token_status.py` keep).
- Social queue backed by ledger; approve → dry-run → publish.
- **Done:** a real FB post publishes from an approved ledger item.

## Day 4 — Creative Studio v1
- Angle-varied generator + quality/compliance gate; writes `content` events as `draft`.
- **Done:** a batch of distinct (non-duplicate) scored posts enters the queue.

## Day 5 — $97 funnel + landing/newsletter assets
- Offer model + ladder; content → checklist CTA → $97 review mapping.
- Landing section + newsletter generators.
- **Done:** funnel assets produced and linked to the offer.

## Day 6 — Oanda demo executor v1
- Rebuild executor consuming signal-router; SL/TP required; **$500 demo loss cap**; demo/practice only.
- One guarded `demo_trading_report` summary.
- **Done:** a demo trade executes (or clean no-trade) under the cap.

## Day 7 — Overnight operating loop + proof report
- One scheduler invokes `nexus_runner` jobs (research → creative → publish → demo → brief).
- Daily proof report projection.
- **Done:** an overnight run executes all three goals and reports honestly.

## Guardrails every day
- main is source of truth; commit/push small, secret-scan first.
- No paid ads / Stripe / live trading. Demo cap $500. No IG until media v1.
