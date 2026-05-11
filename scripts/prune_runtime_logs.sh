#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
ARCHIVE_DIR="$LOG_DIR/archive"
STAMP="$(date '+%Y%m%d-%H%M%S')"
MAX_SIZE_BYTES=$((5 * 1024 * 1024))

mkdir -p "$ARCHIVE_DIR"

archive_and_truncate() {
  local file="$1"
  local reason="$2"
  [ -f "$file" ] || return 0
  [ -s "$file" ] || return 0

  local base
  base="$(basename "$file")"
  local archive="$ARCHIVE_DIR/${base}.${STAMP}"
  cp "$file" "$archive"
  : > "$file"
  printf 'pruned %s -> %s (%s)\n' "$file" "$archive" "$reason"
}

prune_stale_error_log() {
  local err_file="$1"
  local ok_file="$2"
  [ -f "$err_file" ] || return 0
  [ -s "$err_file" ] || return 0
  [ -f "$ok_file" ] || return 0

  local err_mtime ok_mtime
  err_mtime="$(stat -f '%m' "$err_file")"
  ok_mtime="$(stat -f '%m' "$ok_file")"

  if [ "$ok_mtime" -gt "$err_mtime" ]; then
    archive_and_truncate "$err_file" "stale error log with newer healthy output"
  fi
}

prune_oversized_log() {
  local file="$1"
  [ -f "$file" ] || return 0
  [ -s "$file" ] || return 0

  local size
  size="$(stat -f '%z' "$file")"
  if [ "$size" -gt "$MAX_SIZE_BYTES" ]; then
    archive_and_truncate "$file" "size ${size} exceeds ${MAX_SIZE_BYTES}"
  fi
}

prune_stale_error_log "$LOG_DIR/opportunity-worker.error.log" "$LOG_DIR/opportunity-worker.log"
prune_stale_error_log "$LOG_DIR/grant-worker.error.log" "$LOG_DIR/grant-worker.log"
prune_stale_error_log "$LOG_DIR/ops-control-worker.error.log" "$LOG_DIR/ops-control-worker.log"
prune_stale_error_log "$LOG_DIR/nexus-orchestrator.error.log" "$LOG_DIR/nexus-orchestrator.log"
prune_stale_error_log "$LOG_DIR/research-orchestrator-transcript.error.log" "$LOG_DIR/research-orchestrator-transcript.log"
prune_stale_error_log "$LOG_DIR/research-orchestrator-grants-browser.error.log" "$LOG_DIR/research-orchestrator-grants-browser.log"
prune_stale_error_log "$LOG_DIR/strategy_lab.err.log" "$LOG_DIR/strategy_lab.log"
prune_stale_error_log "$LOG_DIR/trading_engine.err.log" "$LOG_DIR/trading_engine.log"

for file in \
  "$LOG_DIR/coordination_worker.log" \
  "$LOG_DIR/grant-worker.log" \
  "$LOG_DIR/nexus-research-worker.log" \
  "$LOG_DIR/nexus-orchestrator.log" \
  "$LOG_DIR/ops-control-worker.log" \
  "$LOG_DIR/opportunity-worker.log" \
  "$LOG_DIR/research-orchestrator-transcript.log" \
  "$LOG_DIR/research-orchestrator-grants-browser.log" \
  "$LOG_DIR/signal_review.log"; do
  prune_oversized_log "$file"
done

printf 'runtime log pruning complete\n'
