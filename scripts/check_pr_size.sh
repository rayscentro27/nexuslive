#!/bin/bash
# PR size guard — prevent monster branches.
#
# Usage:
#   scripts/check_pr_size.sh [base]            # compare current branch to base (default: main)
#   scripts/check_pr_size.sh main --override   # bypass the hard file-count limit
#
# Thresholds:
#   * HARD FAIL  if changed files > 60   (unless --override)
#   * WARN       if added lines  > 8000  (unless --override)
#
# READ-ONLY: never modifies files, never touches the network.

set -uo pipefail

BASE="main"
OVERRIDE=false
for arg in "$@"; do
  case "$arg" in
    --override) OVERRIDE=true ;;
    -h|--help)
      grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    --*) echo "Unknown flag: $arg" >&2; exit 2 ;;
    *) BASE="$arg" ;;
  esac
done

MAX_FILES=60
WARN_ADDS=8000

# Resolve a comparison ref: prefer the merge-base with the base branch.
if git rev-parse --verify --quiet "$BASE" >/dev/null; then
  REF="$BASE"
elif git rev-parse --verify --quiet "origin/$BASE" >/dev/null; then
  REF="origin/$BASE"
else
  echo "✗ pr-size: base ref '$BASE' not found (tried '$BASE' and 'origin/$BASE')." >&2
  exit 2
fi

MERGE_BASE=$(git merge-base HEAD "$REF" 2>/dev/null || echo "$REF")

# Count changed files and line stats vs the merge-base.
FILES=$(git diff --name-only "$MERGE_BASE"...HEAD 2>/dev/null | grep -c . || true)
read -r ADDS DELS < <(git diff --numstat "$MERGE_BASE"...HEAD 2>/dev/null \
  | awk '{ a += ($1 == "-" ? 0 : $1); d += ($2 == "-" ? 0 : $2) } END { print a+0, d+0 }')

echo "▸ PR SIZE  (HEAD vs $REF @ ${MERGE_BASE:0:8})"
echo "  Changed files: $FILES   (limit $MAX_FILES)"
echo "  Additions:     $ADDS    (warn > $WARN_ADDS)"
echo "  Deletions:     $DELS"
echo ""

status=0

if [ "$FILES" -gt "$MAX_FILES" ]; then
  if [ "$OVERRIDE" = true ]; then
    echo "⚠️  $FILES files exceeds limit $MAX_FILES — allowed by --override."
  else
    echo "✗ pr-size: $FILES files exceeds hard limit of $MAX_FILES."
    echo "  Split into smaller single-purpose PRs, or pass --override with Ray's approval."
    status=1
  fi
fi

if [ "$ADDS" -gt "$WARN_ADDS" ]; then
  if [ "$OVERRIDE" = true ]; then
    echo "⚠️  $ADDS additions exceeds warn threshold $WARN_ADDS — allowed by --override."
  else
    echo "⚠️  pr-size WARNING: $ADDS additions exceeds $WARN_ADDS. Consider splitting."
  fi
fi

if [ "$status" -eq 0 ]; then
  echo "✓ pr-size: within limits."
fi
exit "$status"
