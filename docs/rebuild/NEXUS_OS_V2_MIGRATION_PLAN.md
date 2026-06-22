# Nexus OS v2 — Migration Plan

How to move from `~/nexus-ai` to `~/nexus-os-v2` without losing what works or leaking secrets.

## Copy (port nearly verbatim — "keep" items)
- `lib/telegram_send_guard.py`, `lib/run_lock.py`
- `scripts/facebook_token_status.py` (+ `docs/social/FACEBOOK_TOKEN_ROTATION.md`)
- `lib/social_connection_resolver.py`
- `scripts/social_copy_quality_check.py`
- `netlify/functions/hermes-chat.js` + `scripts/build_hermes_fallback_snapshot.py`
- `signal-router/tradingview_router.py`
- FB publish core from `content_employee/publisher.py` (the Graph feed + IG container functions)
- `scripts/run_monetization_scout.py` + `lib/hermes_monetization_scout.py`

## Rewrite (carry the contract, not the file)
- Social queue → ledger-backed `social` events (not JSONL).
- Operator Core → `nexus_runner` jobs + a `brief` projection.
- Showroom/Nexus OS UI → fresh dashboard reading the ledger (drop the static manifest).
- $97 funnel/proof automation → offer model + ledger events.
- Oanda/vibe executor → rebuild from scratch (source is gone).

## Leave behind
- Diverged `~/nexus-ai-worker` (keep its launchd jobs disabled).
- All `reports/*` and `outputs/*` as-state patterns (keep as history only).
- Duplicate launchd/cron jobs; static manifests; old branch/preview logic.

## Secrets discipline
- Real values only in `~/nexus-os-v2/.env` (gitignored) + host secret store.
- Ship `.env.example` with empty placeholders (incl. `META_*`, `OANDA_*`, `TELEGRAM_*`).
- **Migrate launchd jobs to load from `.env`** — do NOT copy the current plists' embedded
  secrets (OANDA_API_KEY, SUPABASE_SERVICE_ROLE_KEY, NEXUS_LLM_API_KEY, HERMES_GATEWAY_KEY).
- Secret-scan every commit; never `git add .`/`-A`.

## Preserve working Facebook token handling
- Bring `facebook_token_status.py --exchange` (USER token → long-lived → non-expiring Page token).
- Same env names: `META_APP_ID/SECRET`, `META_PAGE_ID`, `META_PAGE_ACCESS_TOKEN`, `META_INSTAGRAM_ACCOUNT_ID`.
- Page: Clear Credentials `131069194210954`; IG `17841480265043148`.

## Avoid duplicate schedulers
- Exactly ONE scheduler in v2 (one host, one mechanism). Document times in
  `docs/operations/`. Every scheduled job uses `run_lock` + ledger `dedup_key`.
- Before v2 goes live, disable the old Nexus schedulers (don't run both).

## Preserve main branch discipline
- v2 is main-only; protect main; deploy from main (Netlify).
- Small commits, secret-scanned, pushed; no long-lived preview branches.

## Cutover
1. Build v2 to MVP (7-day plan) while old Nexus runs read-only/limited.
2. Move Facebook publishing + token to v2 first (highest proven value).
3. Disable old schedulers as each v2 job replaces them.
4. Old Nexus stays as reference/history until v2 proves an overnight loop.
