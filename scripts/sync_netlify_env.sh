#!/usr/bin/env bash
# sync_netlify_env.sh
# Safely syncs approved Nexus OS env vars from .env to Netlify.
# Does NOT print secret values. Skips vars not in .env.
# Run: bash scripts/sync_netlify_env.sh
#
# Prerequisites:
#   1. npm install -g netlify-cli
#   2. netlify login
#   3. netlify link  (run inside nexus-ai/)

set -euo pipefail

ENV_FILE=".env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

if [ ! -f "$ROOT_DIR/$ENV_FILE" ]; then
  echo "ERROR: $ROOT_DIR/$ENV_FILE not found"
  exit 1
fi

# Read a var from .env without printing it
get_env() {
  local var="$1"
  grep "^${var}=" "$ROOT_DIR/$ENV_FILE" 2>/dev/null | cut -d= -f2-
}

# Approved vars for Nexus OS approval/notification flow
APPROVED_VARS=(
  SUPABASE_SERVICE_ROLE_KEY
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
  TELEGRAM_APPROVAL_NOTIFICATIONS_ENABLED
  TELEGRAM_CRITICAL_ALERTS_ENABLED
  HERMES_GATEWAY_URL
  HERMES_API_KEY
  NEXUS_DASHBOARD_URL
)

echo "=== Nexus OS Netlify ENV Sync ==="
echo "Reading from: $ROOT_DIR/$ENV_FILE"
echo ""

# Check netlify CLI
if ! command -v netlify &>/dev/null; then
  echo "ERROR: netlify CLI not found. Install with: npm install -g netlify-cli"
  echo "Then run: netlify login && netlify link"
  exit 1
fi

for var in "${APPROVED_VARS[@]}"; do
  val=$(get_env "$var")
  if [ -z "$val" ]; then
    echo "  SKIP  $var  (not in .env or empty)"
    continue
  fi

  # Warn about localhost gateway — can't be reached from Netlify
  if [ "$var" = "HERMES_GATEWAY_URL" ]; then
    prefix="${val:0:16}"
    if [[ "$prefix" == "http://127"* ]] || [[ "$prefix" == "http://localhost"* ]]; then
      echo "  WARN  $var = localhost — Netlify cannot reach local machine."
      echo "        Set up a tunnel (ngrok / Cloudflare) or use Oracle VM."
      echo "        Skipping — set manually when remote URL is available."
      continue
    fi
  fi

  # TELEGRAM_APPROVAL_NOTIFICATIONS_ENABLED safety gate
  if [ "$var" = "TELEGRAM_APPROVAL_NOTIFICATIONS_ENABLED" ]; then
    if [ "$val" != "true" ] && [ "$val" != "1" ]; then
      echo "  SKIP  $var = not true — keeping disabled (safe default)"
      continue
    fi
  fi

  echo -n "  SET   $var ... "
  if netlify env:set "$var" "$val" --force 2>/dev/null; then
    echo "done"
  else
    echo "ERROR — check netlify link status"
  fi
done

echo ""
echo "=== Sync complete. Redeploy for changes to take effect: netlify deploy --prod ==="
