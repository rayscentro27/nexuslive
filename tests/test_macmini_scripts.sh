#!/bin/bash
# Lightweight validation for macmini health/safe-mode scripts
set -euo pipefail

SCRIPTS="$(cd "$(dirname "$0")/.." && pwd)/scripts"
PASS=0
FAIL=0

pass()  { PASS=$((PASS + 1)); }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }

echo "━━━━━ MAC MINI SCRIPT TESTS ━━━━━"

# 1. bash -n syntax check
echo "--- 1. bash -n syntax ---"
if bash -n "$SCRIPTS/macmini_health.sh" 2>/dev/null; then pass; else fail "macmini_health.sh syntax"; fi
if bash -n "$SCRIPTS/macmini_safe_mode.sh" 2>/dev/null; then pass; else fail "macmini_safe_mode.sh syntax"; fi

# Helper: run script, cache output, then grep
run_and_grep() {
  local script="$1"; shift
  local pattern="$1"; shift
  local output
  output=$(bash "$SCRIPTS/$script" "$@" 2>/dev/null) || true
  echo "$output" | grep -q "$pattern"
}

# 2. --help output
echo "--- 2. --help flag ---"
if run_and_grep "macmini_safe_mode.sh" "Protected:" --help; then pass; else fail "--help missing Protected"; fi
if run_and_grep "macmini_safe_mode.sh" "Killable:" --help; then pass; else fail "--help missing Killable"; fi

# 3. --status is read-only
echo "--- 3. --status read-only ---"
if run_and_grep "macmini_safe_mode.sh" "STATUS COMPLETE" --status; then pass; else fail "--status missing completion"; fi
if run_and_grep "macmini_safe_mode.sh" "killed" --status; then fail "--status should not kill"; else pass; fi
if run_and_grep "macmini_safe_mode.sh" "killable" --status; then fail "--status should not show killable processes"; else pass; fi

# 4. --dry-run does not kill
echo "--- 4. --dry-run does not kill ---"
if run_and_grep "macmini_safe_mode.sh" "COMPLETE" --dry-run; then pass; else fail "--dry-run missing completion"; fi
if run_and_grep "macmini_safe_mode.sh" "No processes killed" --dry-run; then pass; else fail "--dry-run should say no processes killed"; fi

# 5. Protected patterns exist in script
echo "--- 5. Protected process patterns ---"
if grep -q "nexus" "$SCRIPTS/macmini_safe_mode.sh" && grep -q "hermes" "$SCRIPTS/macmini_safe_mode.sh" && grep -q "thechosenone" "$SCRIPTS/macmini_safe_mode.sh"; then pass; else fail "Missing protected pattern"; fi

# 6. --apply warning banner
echo "--- 6. --apply warning ---"
if bash "$SCRIPTS/macmini_safe_mode.sh" --help 2>/dev/null | grep -q "WARNING:"; then pass; else fail "Missing --apply warning in help"; fi

# 7. Health script is read-only (check for no destructive commands)
echo "--- 7. Health script read-only ---"
if grep -q "kill " "$SCRIPTS/macmini_health.sh"; then fail "Health script contains kill command"; else pass; fi
if grep -q "launchctl.*stop\|launchctl.*unload\|launchctl.*remove" "$SCRIPTS/macmini_health.sh"; then fail "Health script modifies launchd"; else pass; fi
if grep -qw "rm" "$SCRIPTS/macmini_health.sh"; then fail "Health script contains rm"; else pass; fi

# 8. Scripts don't contain secrets
echo "--- 8. Secrets scan ---"
for f in "$SCRIPTS/macmini_health.sh" "$SCRIPTS/macmini_safe_mode.sh"; do
  if grep -qE '(sk-|api_key=|token=|SUPABASE|STRIPE|telegram|TELEGRAM|ghp_|gho_|github_pat)' "$f"; then
    fail "Secrets found in $f"
  else
    pass
  fi
done

echo ""
echo "━━━━━ RESULTS ━━━━━"
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
