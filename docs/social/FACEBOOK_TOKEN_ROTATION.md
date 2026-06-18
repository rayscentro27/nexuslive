# Facebook / Instagram Token Rotation

How to keep the Nexus Facebook Page publishing path working without ever committing a secret.

## Golden rules
- **Never commit tokens.** The real token lives only in `~/nexus-ai/.env` and
  `~/nexus-ai-worker/.env` (both gitignored via `.env.*` with a `!.env.example` exception).
- The repo gets **code + docs + empty placeholders** only.
- Graph API Explorer often shows **misleading expiry** — a token can look fine in Meta's UI
  but actually be **short-lived (~1–2 hours)**. Always verify with the script below.

## Required env vars (real values go in `.env`, never the repo)
- `META_APP_ID`
- `META_APP_SECRET`
- `META_PAGE_ID`            (Clear Credentials = `131069194210954`)
- `META_PAGE_ACCESS_TOKEN`  (must be a **type=PAGE** token with publish scopes)
- `META_INSTAGRAM_ACCOUNT_ID` (`17841480265043148`)

A publish-ready Page token has scopes **`pages_manage_posts`** + **`pages_read_engagement`**.

## Verify a token (never prints the token)
```
python3 scripts/facebook_token_status.py
# → token_present=True type=PAGE valid=True long_lived=False expires=... publish_scopes=True page=131069194210954
```
If `long_lived=False`, the token will expire within hours — rotate it with `--exchange`.

## Make the token durable (exchange a USER token → non-expiring Page token)
The key fact: a **Page** token derived from a **long-lived USER** token is effectively
non-expiring. So you exchange a *user* token (not the page token).

1. Get a USER token (Graph API Explorer → your app → Get User Access Token, with
   `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`).
2. Exchange it and write the Page token into both env files — token never printed/logged:

```
# Preferred: hidden stdin (keeps the token out of shell history)
python3 scripts/facebook_token_status.py --exchange --user-token-stdin \
    --target-page-id 131069194210954 --write-local-env --write-worker-env --json

# Or via an env var you set inline:
META_USER_ACCESS_TOKEN='<USER_TOKEN>' python3 scripts/facebook_token_status.py \
    --exchange --user-token-env META_USER_ACCESS_TOKEN \
    --target-page-id 131069194210954 --write-local-env --write-worker-env --json
```
The script: validates the input is a USER token → `fb_exchange_token` for a long-lived user
token → `/me/accounts` → extracts the target Page token → verifies type/scopes/identity →
writes only the `META_PAGE_ACCESS_TOKEN=` line in each `.env`. No backups are created and no
token value is ever printed. Use `--dry-run` to preview without writing.

## Publishing path (after a valid token)
```
python3 scripts/social_queue_approve.py --item-id <ID> --ray-approved
python3 scripts/social_publish_facebook_queue_item.py --item-id <ID> --dry-run
SOCIAL_PUBLISHING_ENABLED=true SOCIAL_DRY_RUN=false \
  python3 scripts/social_publish_facebook_queue_item.py --item-id <ID> --confirm-real-publish
```

## Optional: production (Netlify)
Only if server-side publishing is added. Set the same `META_*` names as Netlify env vars.
The current web app does not call Meta directly, so this is optional.
