#!/bin/bash
# Mac Mini Safe Mode — identify risky workloads
# Usage:
#   bash ~/nexus-ai/scripts/macmini_safe_mode.sh          # dry-run (default)
#   bash ~/nexus-ai/scripts/macmini_safe_mode.sh --dry-run # explicit dry-run
#   bash ~/nexus-ai/scripts/macmini_safe_mode.sh --status  # read-only status
#   bash ~/nexus-ai/scripts/macmini_safe_mode.sh --apply   # show what would be killed (no-op without --force)
#   bash ~/nexus-ai/scripts/macmini_safe_mode.sh --apply --force  # actually kill
#
# DEFAULT IS DRY-RUN.  --apply with --force kills only EXPLICIT-ALLOWLIST
# processes.  Never kills protected or uncertain processes.

set -euo pipefail

MODE="${1:---dry-run}"
FORCE=false

for arg in "$@"; do
  if [ "$arg" = "--force" ]; then FORCE=true; fi
done

# ── Protection patterns (never killed) ───────────────────────────────────────
# These grep -iE patterns match against the full command line (lowercased).
# Any matching process is protected regardless of killable allowlist.
PROTECTED_GREP='nexus|hermes|chosen|thechosenone|telegram|continuous|operations_center|scheduler\.py|run_nexus_continuous_operations\.py|opencode|launchd|kernel_task|syslogd|notifyd|configd|sshd|mds_stores|WindowServer|loginwindow|opendirectoryd|securityd'

# Word-boundary patterns (only exact process name match for common words)
PROTECTED_WB='\bFinder\b|\bDock\b|\bmds\b|\bSystemUIServer\b'

# Combined
PROTECTED_ALL="$PROTECTED_GREP|$PROTECTED_WB"

# ── Killable patterns (clearly safe to kill) ─────────────────────────────────
# Only processes that are script languages AND match a killable context.
# Generic python/node/bash/zsh are NOT killable.
KILLABLE_GREP='\b(python|node|ruby|perl|bash|zsh)\b'

# Killable context: must match one of these patterns in the full command line
KILLABLE_CONTEXT='install|build|compile|upload|download|eslint|prettier|webpack|vite|tsc|jest|mocha|rspec'

# ── Help ──────────────────────────────────────────────────────────────────────
if [ "$MODE" = "--help" ] || [ "$MODE" = "-h" ]; then
  echo "Mac Mini Safe Mode — identify and optionally stop risky local workloads."
  echo ""
  echo "Modes:"
  echo "  (default)          Dry-run — show classification"
  echo "  --dry-run          Same as default"
  echo "  --status           Read-only status overview"
  echo "  --apply            Show what would be killed (no-op without --force)"
  echo "  --apply --force    Actually kill allowlisted processes"
  echo "  --help             This message"
  echo ""
  echo "Categories:"
  echo "  PROTECTED — never touched (nexus, hermes, chosen, telegram,"
  echo "     continuous, operations_center, opencode, launchd, system daemons)"
  echo "  REVIEW — uncertain, never auto-killed"
  echo "  KILLABLE — allowlisted (build tools, installers only)"
  echo ""
  echo "WARNING: --apply --force kills processes.  Only KILLABLE processes"
  echo "are targeted.  PROTECTED and REVIEW processes are never touched."
  exit 0
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MAC MINI SAFE MODE"
echo "  Mode: $MODE"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$MODE" = "--apply" ] && [ "$FORCE" = true ]; then
  echo ""
  echo "  ⚠️  APPLY + FORCE — destructive actions may occur."
  echo "  Only KILLABLE processes will be touched."
  echo ""
elif [ "$MODE" = "--apply" ]; then
  echo ""
  echo "  🔒  DRY-RUN within --apply (no --force).  Use --apply --force to act."
  echo ""
fi

# ── Only --status: light read-only overview ───────────────────────────────────
if [ "$MODE" = "--status" ]; then
  echo ""
  echo "▸ SYSTEM OVERVIEW"
  echo "  Uptime:    $(uptime 2>/dev/null | sed 's/.*up //')"
  echo "  Load avg:  $(sysctl -n vm.loadavg 2>/dev/null || echo 'N/A')"

  echo ""
  echo "▸ NEXUS PROCESSES"
  for pattern in "nexus" "hermes" "chosen" "thechosenone"; do
    count=$(ps aux 2>/dev/null | grep -i "$pattern" | grep -v grep | wc -l | tr -d ' ' || true)
    echo "  $pattern: $count running"
  done

  echo ""
  echo "▸ OTHER PROCESSES"
  other_count=$(ps aux 2>/dev/null | wc -l | tr -d ' ' || true)
  echo "  $((other_count - 1)) total"

  echo ""
  echo "▸ LAUNCHD PLISTS (nexus/hermes)"
  for dir in ~/Library/LaunchAgents /Library/LaunchAgents /Library/LaunchDaemons; do
    if [ -d "$dir" ]; then
      ls "$dir" 2>/dev/null | grep -iE 'nexus|hermes|thechosenone|continuous' | sed "s|^|  $dir/|" || true
    fi
  done | head -10

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  STATUS COMPLETE (read-only)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
fi

# ── Scan processes ────────────────────────────────────────────────────────────
echo ""
echo "▸ SCANNING PROCESSES"

# Snapshot ps output to a temp file for fast batch grep
PSFILE=$(mktemp)
trap 'rm -f "$PSFILE"' EXIT
ps aux 2>/dev/null | tail -n +2 > "$PSFILE" || true
total=$(wc -l < "$PSFILE")

# Build protected grep: find lines where command (field 11+) matches protected patterns
# We need to match against the full command line (field 11 to end).
# ps aux lines: USER PID %CPU %MEM VSZ RSS TT STAT STARTED TIME COMMAND
# So field 11+ is the command.
# We use a simple approach: grep each line's full text for the protected patterns.
# To avoid matching the USER or PID fields, we match from field 11 onward by
# using a sed to extract the command portion first.

# Extract PID + command (field 2, then fields 11+)
# Pattern: ^\S+\s+(\d+)\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+(.*)$
# Simpler: just grep the raw line - false positives from USER field are unlikely for
# patterns like 'nexus', 'hermes', 'launchd' etc. But to be safe, use the full command only.

# Extract PID and full command line
awk '{pid=$2; cmd=""; for(i=11;i<=NF;i++) cmd=cmd $i " "; print pid "|" cmd}' "$PSFILE" > "${PSFILE}_parsed"

# Classification using grep
# Protected: cmd matches PROTECTED_ALL (case-insensitive)
grep -ivE "$PROTECTED_ALL" "${PSFILE}_parsed" > "${PSFILE}_noprot" || true
grep -iE "$PROTECTED_ALL" "${PSFILE}_parsed" > "${PSFILE}_protected" || true

# From remaining (noprot): check if killable (matches KILLABLE_GREP + KILLABLE_CONTEXT)
# Killable if: matches KILLABLE_GREP AND matches KILLABLE_CONTEXT
grep -iE "$KILLABLE_GREP" "${PSFILE}_noprot" > "${PSFILE}_scripts" || true
grep -iE "$KILLABLE_CONTEXT" "${PSFILE}_scripts" > "${PSFILE}_killable" || true

# Review manually: script processes that didn't match killable context, plus everything else
grep -ivE "$KILLABLE_GREP" "${PSFILE}_noprot" > "${PSFILE}_noncript" || true
# Script but not killable context
comm -23 <(sort "${PSFILE}_scripts") <(sort "${PSFILE}_killable") 2>/dev/null > "${PSFILE}_review_scripts" || true
cat "${PSFILE}_noncript" >> "${PSFILE}_review_scripts" 2>/dev/null || true

protected_count=$(wc -l < "${PSFILE}_protected" | tr -d ' ')
killable_count=$(wc -l < "${PSFILE}_killable" | tr -d ' ')
review_count=$(wc -l < "${PSFILE}_review_scripts" | tr -d ' ')

# Print classification
echo ""
echo "  🔒 Protected (never touched):"
if [ "$protected_count" -eq 0 ]; then
  echo "    (none)"
else
  while IFS='|' read -r pid cmd; do
    comm=$(echo "$cmd" | awk '{print $1}' | sed 's/.*\///')
    echo "    🔒 PID $pid  $comm"
  done < "${PSFILE}_protected"
fi

echo ""
echo "  ❓ Review manually (uncertain, never auto-killed):"
if [ "$review_count" -eq 0 ]; then
  echo "    (none)"
else
  while IFS='|' read -r pid cmd; do
    comm=$(echo "$cmd" | awk '{print $1}' | sed 's/.*\///')
    echo "    ❓ PID $pid  $comm  ${cmd:0:80}"
  done < "${PSFILE}_review_scripts"
fi

echo ""
echo "  ⚠️  Killable by allowlist:"
killed=0
if [ "$killable_count" -eq 0 ]; then
  echo "    (none)"
else
  while IFS='|' read -r pid cmd; do
    comm=$(echo "$cmd" | awk '{print $1}' | sed 's/.*\///')
    echo "    ⚠️  PID $pid  $comm  ${cmd:0:80}"
    if [ "$MODE" = "--apply" ] && [ "$FORCE" = true ]; then
      if kill "$pid" 2>/dev/null; then
        echo "      -> killed"
        killed=$((killed + 1))
      else
        echo "      -> FAILED (permission or already gone)"
      fi
    fi
  done < "${PSFILE}_killable"
fi

# Summary
echo ""
echo "▸ SUMMARY"
echo "  Protected:        $protected_count"
echo "  Review manually:  $review_count"
echo "  Killable:         $killable_count"

if [ "$MODE" = "--apply" ] && [ "$FORCE" = true ]; then
  echo "  Killed:           $killed"
fi

if [ "$killable_count" -gt 0 ] && { [ "$MODE" != "--apply" ] || [ "$FORCE" != true ]; }; then
  echo ""
  echo "  ⚠️  $killable_count killable process(es) detected."
  echo "  Re-run with --apply --force to stop them."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$MODE" = "--apply" ] && [ "$FORCE" = true ]; then
  echo "  SAFE MODE --apply COMPLETE"
else
  echo "  SAFE MODE $MODE COMPLETE"
  echo "  No processes killed (dry-run)."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
