#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

CHROME_APP="${CHROME_APP:-/Applications/Google Chrome.app}"
CHROME_BIN="${CHROME_BIN:-$CHROME_APP/Contents/MacOS/Google Chrome}"
CDP_HOST="${CDP_HOST:-127.0.0.1}"
CDP_PORT="${CDP_PORT:-9222}"
CHROME_PROFILE_DIR="${CHROME_PROFILE_DIR:-/tmp/chrome-cdp-$CDP_PORT}"
CHROME_LOG="${CHROME_LOG:-/tmp/chrome-cdp-$CDP_PORT.log}"
CHROME_EXTRA_ARGS="${CHROME_EXTRA_ARGS:-}"
ANTIGRAVITY_BIN="${ANTIGRAVITY_BIN:-antigravity}"
ANTIGRAVITY_LOG="${ANTIGRAVITY_LOG:-/tmp/antigravity.log}"
WAIT_SECONDS="${WAIT_SECONDS:-15}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

cdp_url() {
  echo "http://$CDP_HOST:$CDP_PORT/json/version"
}

cdp_ready() {
  curl --silent --fail --max-time 2 "$(cdp_url)" >/dev/null 2>&1 || \
    lsof -nP -iTCP:"$CDP_PORT" -sTCP:LISTEN 2>/dev/null | grep -q "$CDP_HOST:$CDP_PORT"
}

start_chrome() {
  if [[ ! -x "$CHROME_BIN" ]]; then
    log "Chrome binary not found: $CHROME_BIN"
    exit 1
  fi

  mkdir -p "$CHROME_PROFILE_DIR"
  log "Starting Chrome with CDP on $CDP_HOST:$CDP_PORT"
  nohup "$CHROME_BIN" \
    --remote-debugging-address="$CDP_HOST" \
    --remote-debugging-port="$CDP_PORT" \
    --user-data-dir="$CHROME_PROFILE_DIR" \
    $CHROME_EXTRA_ARGS \
    >"$CHROME_LOG" 2>&1 &
}

wait_for_cdp() {
  local elapsed=0
  while (( elapsed < WAIT_SECONDS )); do
    if cdp_ready; then
      log "CDP is responding at $(cdp_url)"
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done

  log "CDP did not respond within ${WAIT_SECONDS}s"
  log "Chrome log: $CHROME_LOG"
  return 1
}

start_antigravity() {
  if ! command -v "$ANTIGRAVITY_BIN" >/dev/null 2>&1; then
    log "Antigravity binary not found on PATH: $ANTIGRAVITY_BIN"
    log "CDP is up. Start Antigravity manually after fixing PATH."
    return 0
  fi

  if pgrep -f "$ANTIGRAVITY_BIN" >/dev/null 2>&1; then
    log "Antigravity already appears to be running"
    return 0
  fi

  log "Starting Antigravity"
  nohup "$ANTIGRAVITY_BIN" "$@" >"$ANTIGRAVITY_LOG" 2>&1 &
  log "Antigravity log: $ANTIGRAVITY_LOG"
}

main() {
  if cdp_ready; then
    log "CDP already responding at $(cdp_url)"
  else
    start_chrome
    wait_for_cdp
  fi

  start_antigravity "$@"
  log "Next step: run 'remoat doctor'"
}

main "$@"
