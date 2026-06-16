#!/bin/bash
# Repo hygiene guard — block runtime/generated/secret-prone files from being committed.
#
# Usage:
#   scripts/check_repo_hygiene.sh            # inspect STAGED files (default)
#   scripts/check_repo_hygiene.sh --staged   # explicit: staged files
#   scripts/check_repo_hygiene.sh --all      # inspect all tracked + staged paths
#   scripts/check_repo_hygiene.sh --files a b # inspect an explicit list of paths
#
# READ-ONLY: never deletes/modifies files, never touches the network, never
# prints file contents (so it cannot leak secrets). Exits non-zero on violation.

set -uo pipefail

MODE="--staged"
EXPLICIT=()
case "${1:-}" in
  --staged|"") MODE="--staged" ;;
  --all)       MODE="--all" ;;
  --files)     MODE="--files"; shift; EXPLICIT=("$@") ;;
  -h|--help)
    grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'
    exit 0 ;;
  *) echo "Unknown argument: $1" >&2; exit 2 ;;
esac

# ── Collect the candidate file list ────────────────────────────────────────
collect() {
  case "$MODE" in
    --staged) git diff --cached --name-only 2>/dev/null ;;
    --all)    { git ls-files 2>/dev/null; git diff --cached --name-only 2>/dev/null; } | sort -u ;;
    --files)  printf '%s\n' ${EXPLICIT[@]+"${EXPLICIT[@]}"} ;;
  esac
}

# Read into an array portably (bash 3.2 has no `mapfile`).
FILES=()
while IFS= read -r _line; do
  FILES+=("$_line")
done < <(collect)

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "✓ repo-hygiene: no files to inspect (nothing staged)."
  exit 0
fi

# ── Forbidden patterns (extended regex, matched against the path) ───────────
# Each entry: a regex. A path matching any of these is a violation — UNLESS it
# is on the allowlist below.
FORBIDDEN=(
  '\.env$'
  '\.env\.[^/]+$'
  '\.lock$'
  '\.pid$'
  '(^|/)logs/'
  '(^|/)reports/'
  '(^|/)artifacts/'
  '(^|/)research-engine/.*\.vtt$'
  '(^|/)research-engine/.*\.summary$'
  '(^|/)docs/content/'
  '(^|/)tool-lab/'
  '(^|/)test-results/'
  '(^|/)supabase/\.temp/'
  '(^|/)node_modules/'
  '(^|/)dist/'
  '(^|/)build/'
  '(^|/)\.cache/'
  '\.png$'
  '\.jpg$'
  '\.jpeg$'
  '\.webp$'
  '(^|/)\.telegram'
  '(^|/)\.hermes.*_memory\.json$'
  '(^|/)\.circuit_breaker_state\.json$'
  '(^|/)\.hermes_cli_handoffs\.json$'
  '(^|/)\.telegram_update_offset$'
)

# ── Allowlist (always permitted even if a forbidden pattern would match) ────
ALLOW=(
  '(^|/)\.env\.example$'
)

is_allowed() {
  local f="$1" a
  for a in "${ALLOW[@]}"; do
    if printf '%s' "$f" | grep -qE "$a"; then return 0; fi
  done
  return 1
}

violations=0
for f in "${FILES[@]}"; do
  [ -z "$f" ] && continue
  if is_allowed "$f"; then continue; fi
  for pat in "${FORBIDDEN[@]}"; do
    if printf '%s' "$f" | grep -qE "$pat"; then
      echo "✗ FORBIDDEN: $f  (matches /$pat/)"
      violations=$((violations + 1))
      break
    fi
  done
done

echo ""
if [ "$violations" -gt 0 ]; then
  echo "✗ repo-hygiene: $violations forbidden path(s) in $MODE set."
  echo "  Runtime/generated/secret-prone files must not be committed."
  echo "  See docs/REPO_HYGIENE_POLICY.md for where these belong."
  exit 1
fi

echo "✓ repo-hygiene: ${#FILES[@]} path(s) checked, no forbidden paths."
exit 0
