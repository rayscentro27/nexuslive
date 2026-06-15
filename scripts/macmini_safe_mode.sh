#!/bin/bash
# Mac Mini Safe Mode — identify risky workloads
# Usage:
#   bash ~/nexus-ai/scripts/macmini_safe_mode.sh          # dry-run (default)
#   bash ~/nexus-ai/scripts/macmini_safe_mode.sh --dry-run # explicit dry-run
#   bash ~/nexus-ai/scripts/macmini_safe_mode.sh --status  # read-only status
#   bash ~/nexus-ai/scripts/macmini_safe_mode.sh --apply   # apply changes
#
# DEFAULT IS DRY-RUN.  --apply is EXPLICIT and will kill non-allowlisted
# processes, stop services, and free resources.
#
# Protected processes (never killed):
#   - nexus, hermes, thechosenone, python.*nexus, python.*hermes
#   - launchd, kernel_task, syslogd, notifyd, configd
#   - sshd, mds, mds_stores, Finder, Dock, SystemUIServer
#
# Dry-run shows what --apply WOULD do without doing it.

set -euo pipefail

MODE="${1:---dry-run}"

NEXUS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Protection list (never killed) ───────────────────────────────────────────
PROTECTED_PATTERNS=(
  "nexus" "hermes" "thechosenone" "python.*nexus" "python.*hermes"
  "launchd" "kernel_task" "syslogd" "notifyd" "configd"
  "sshd" "mds" "mds_stores" "Finder" "Dock" "SystemUIServer"
  "WindowServer" "loginwindow" "opendirectoryd" "securityd"
)

# ── Allowlist: processes we may kill in --apply mode ─────────────────────────
# Only processes matching these patterns AND not in PROTECTED_PATTERNS qualify.
ALLOWLIST_KILL=(
  "python" "node" "ruby" "perl"
)

# ── Help ──────────────────────────────────────────────────────────────────────
if [ "$MODE" = "--help" ] || [ "$MODE" = "-h" ]; then
  echo "Mac Mini Safe Mode — identify and optionally stop risky local workloads."
  echo ""
  echo "Modes:"
  echo "  (default)  Dry-run — show what would be done"
  echo "  --dry-run  Same as default"
  echo "  --status   Read-only status overview"
  echo "  --apply    Apply safe-mode actions (kill non-allowlisted processes)"
  echo "  --help     This message"
  echo ""
  echo "Protected: ${PROTECTED_PATTERNS[*]}"
  echo "Killable:  ${ALLOWLIST_KILL[*]} (only when not matching protected)"
  echo ""
  echo "WARNING: --apply kills processes. Use with caution."
  exit 0
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MAC MINI SAFE MODE"
echo "  Mode: $MODE"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$MODE" = "--apply" ]; then
  echo ""
  echo "  ⚠️  APPLY MODE — destructive actions may occur."
  echo "  Protected processes will NOT be touched."
  echo ""
fi

_is_protected() {
  local cmd="$1"
  local lowcmd
  lowcmd=$(echo "$cmd" | tr '[:upper:]' '[:lower:]')
  for pat in "${PROTECTED_PATTERNS[@]}"; do
    if echo "$lowcmd" | grep -iqE "$pat"; then
      return 0
    fi
  done
  return 1
}

_is_killable() {
  local cmd="$1"
  local lowcmd
  lowcmd=$(echo "$cmd" | tr '[:upper:]' '[:lower:]')
  for pat in "${ALLOWLIST_KILL[@]}"; do
    if echo "$lowcmd" | grep -iqE "\b$pat\b"; then
      return 0
    fi
  done
  return 1
}

# ── Only --status: light read-only overview ───────────────────────────────────
if [ "$MODE" = "--status" ]; then
  echo ""
  echo "▸ SYSTEM OVERVIEW"
  echo "  Uptime:    $(uptime 2>/dev/null | sed 's/.*up //')"
  echo "  Load avg:  $(sysctl -n vm.loadavg 2>/dev/null || echo 'N/A')"

  echo ""
  echo "▸ NEXUS PROCESSES"
  for pattern in "nexus" "hermes" "thechosenone"; do
    count=$(ps aux 2>/dev/null | grep -i "$pattern" | grep -v grep | wc -l | tr -d ' ' || true)
    echo "  $pattern: $count running"
  done

  echo ""
  echo "▸ OTHER PYTHON / NODE PROCESSES"
  other_count=$(ps aux 2>/dev/null | grep -E "\b(python|node)\b" | grep -iv "grep\|nexus\|hermes\|thechosenone" | wc -l | tr -d ' ' || true)
  echo "  $other_count non-Nexus python/node processes"

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

# ── Scan processes (dry-run or apply) ─────────────────────────────────────────
echo ""
echo "▸ SCANNING PROCESSES"

protected_found=0
killable_found=0
killed=0

while IFS= read -r line; do
  pid=$(echo "$line" | awk '{print $2}')
  cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}' | head -c 100)
  comm=$(echo "$line" | awk '{print $11}' | sed 's/.*\///')

  if _is_protected "$comm" || _is_protected "$cmd"; then
    [ "$protected_found" -eq 0 ] && echo "  Protected (skipped):"
    echo "    🔒 PID $pid  $comm"
    protected_found=$((protected_found + 1))
  elif _is_killable "$comm" || _is_killable "$cmd"; then
    [ "$killable_found" -eq 0 ] && echo "  Killable:"
    echo "    ⚠️  PID $pid  $comm  $cmd"
    killable_found=$((killable_found + 1))

    if [ "$MODE" = "--apply" ]; then
      if kill "$pid" 2>/dev/null; then
        echo "      -> killed"
        killed=$((killed + 1))
      else
        echo "      -> FAILED (permission or already gone)"
      fi
    fi
  fi
done < <(ps aux 2>/dev/null | grep -E "\b(python|node|ruby|perl)\b" | grep -v grep || true)

# Summary
echo ""
echo "▸ SUMMARY"
echo "  Protected processes skipped: $protected_found"
echo "  Killable processes found:    $killable_found"

if [ "$MODE" = "--apply" ]; then
  echo "  Processes killed:           $killed"
elif [ "$killable_found" -gt 0 ]; then
  echo ""
  echo "  ⚠️  $killable_found killable process(es) detected."
  echo "  Re-run with --apply to stop them."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SAFE MODE $MODE COMPLETE"
if [ "$MODE" = "--dry-run" ] || [ "$MODE" = "default" ]; then
  echo "  No processes killed (dry-run)."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
