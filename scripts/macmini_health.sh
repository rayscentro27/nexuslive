#!/bin/bash
# Mac Mini Health — read-only diagnostics
# Usage: bash ~/nexus-ai/scripts/macmini_health.sh
#
# This script is READ-ONLY. It never modifies state, stops services,
# kills processes, or writes outside stdout/stderr.

set -euo pipefail

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MAC MINI HEALTH DIAGNOSTICS"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── System load ───────────────────────────────────────────────────────────────
echo ""
echo "▸ SYSTEM LOAD"

if command -v sysctl &>/dev/null; then
  load=$(sysctl -n vm.loadavg 2>/dev/null || echo "unavailable")
  echo "  Load avg:  $load"
fi

if command -v memory_pressure &>/dev/null; then
  echo "  Memory:"
  memory_pressure 2>/dev/null | head -5 | sed 's/^/    /'
fi

echo "  Uptime:    $(uptime 2>/dev/null | sed 's/.*up //')"

# ── Disk ──────────────────────────────────────────────────────────────────────
echo ""
echo "▸ DISK"

if command -v df &>/dev/null; then
  df -h / /tmp 2>/dev/null | sed 's/^/  /'
fi

# ── Temperature / fans (Apple Silicon) ───────────────────────────────────────
echo ""
echo "▸ THERMAL"

if command -v pmset &>/dev/null; then
  pmset -g therm 2>/dev/null | sed 's/^/  /'
fi

# ── Top memory consumers ──────────────────────────────────────────────────────
echo ""
echo "▸ TOP MEMORY PROCESSES (by %MEM)"

if command -v ps &>/dev/null; then
  (ps aux --sort=-%mem 2>/dev/null || ps -eo pid,ppid,%mem,%cpu,rss,comm -r 2>/dev/null) | head -12 | sed 's/^/  /'
fi

# ── Nexus/Hermes/Chosen processes ─────────────────────────────────────────────
echo ""
echo "▸ NEXUS / HERMES / CHOSEN PROCESSES"

for pattern in "nexus" "hermes" "thechosenone" "python.*nexus" "python.*hermes"; do
  matches=$(ps aux 2>/dev/null | grep -i "$pattern" | grep -v grep || true)
  if [ -n "$matches" ]; then
    echo "  [$pattern]"
    echo "$matches" | while IFS= read -r line; do
      pid=$(echo "$line" | awk '{print $2}')
      mem=$(echo "$line" | awk '{print $4}')
      cpu=$(echo "$line" | awk '{print $3}')
      cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}' | head -c 80)
      echo "    PID $pid  CPU $cpu%  MEM $mem%  $cmd"
    done
  fi
done

# ── launchd jobs ──────────────────────────────────────────────────────────────
echo ""
echo "▸ LAUNCHD PLISTS (nexus/hermes)"

for dir in ~/Library/LaunchAgents /Library/LaunchAgents /Library/LaunchDaemons; do
  if [ -d "$dir" ]; then
    ls "$dir" 2>/dev/null | grep -iE 'nexus|hermes|thechosenone|continuous' | sed "s|^|  $dir/|" || true
  fi
done | head -10

# ─── python/node processes not under Nexus ────────────────────────────────────
echo ""
echo "▸ OTHER PYTHON / NODE PROCESSES"
others=$(ps aux 2>/dev/null | grep -E "\b(python|node)\b" | grep -iv "grep\|nexus\|hermes\|thechosenone" || true)
if [ -n "$others" ]; then
  echo "$others" | while IFS= read -r line; do
    pid=$(echo "$line" | awk '{print $2}')
    cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}' | head -c 80)
    echo "  PID $pid  $cmd"
  done
else
  echo "  (none)"
fi

# ── Network listeners ─────────────────────────────────────────────────────────
echo ""
echo "▸ LISTENING PORTS"

if command -v lsof &>/dev/null; then
  lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | awk 'NR>1{print "  " $1, $9}' | sort -u | head -20
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  HEALTH CHECK COMPLETE (read-only)"
echo "  No services stopped, no processes killed."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
