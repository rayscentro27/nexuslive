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
# run_and_grep caches the script output before grepping, avoiding the
# SIGPIPE + pipefail race that `script | grep -q` is prone to.
echo "--- 2. --help flag ---"
if run_and_grep "macmini_safe_mode.sh" "PROTECTED" --help; then pass; else fail "--help missing PROTECTED category"; fi
if run_and_grep "macmini_safe_mode.sh" "KILLABLE" --help; then pass; else fail "--help missing KILLABLE category"; fi

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
if run_and_grep "macmini_safe_mode.sh" "WARNING:" --help; then pass; else fail "Missing --apply warning in help"; fi

# 7. Health script is read-only (check for no destructive commands)
echo "--- 7. Health script read-only ---"
if grep -q "kill " "$SCRIPTS/macmini_health.sh"; then fail "Health script contains kill command"; else pass; fi
if grep -q "launchctl.*stop\|launchctl.*unload\|launchctl.*remove" "$SCRIPTS/macmini_health.sh"; then fail "Health script modifies launchd"; else pass; fi
if grep -qw "rm" "$SCRIPTS/macmini_health.sh"; then fail "Health script contains rm"; else pass; fi

# 8. Scripts don't contain secrets
# Match real credential VALUES, not service names. The safe-mode script
# legitimately lists "telegram" (and may reference supabase/stripe) as
# protected process-name patterns, so bare service names must not trip this.
echo "--- 8. Secrets scan ---"
SECRET_RE='sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|[0-9]{8,}:[A-Za-z0-9_-]{30,}|(api[_-]?key|secret|password|access[_-]?token|bearer)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9/_+.-]{16,}'
for f in "$SCRIPTS/macmini_health.sh" "$SCRIPTS/macmini_safe_mode.sh"; do
  if grep -qiE "$SECRET_RE" "$f"; then
    fail "Secrets found in $f"
  else
    pass
  fi
done

# 9. Generic interpreters are NOT auto-killable (must match a build/install context)
echo "--- 9. Generic interpreters not killable ---"
# (a) Killable classification must be gated by an explicit context allowlist.
if grep -q "KILLABLE_CONTEXT" "$SCRIPTS/macmini_safe_mode.sh"; then pass; else fail "No KILLABLE_CONTEXT gate"; fi
# (b) The killable set must be derived by filtering script-language matches
#     through that context — a bare python/node/bash alone can never qualify.
if grep -qE 'KILLABLE_CONTEXT".*_scripts' "$SCRIPTS/macmini_safe_mode.sh"; then pass; else fail "Killable set not gated by context filter"; fi
# (c) Behavioral: every process listed as Killable in --dry-run must carry a
#     build/install context keyword (proves generic interpreters land elsewhere).
dry_out=$(bash "$SCRIPTS/macmini_safe_mode.sh" --dry-run 2>/dev/null) || true
killable_block=$(echo "$dry_out" | awk '/Killable by allowlist/{f=1;next} /▸ SUMMARY/{f=0} f')
bad_killable=0
while IFS= read -r kline; do
  case "$kline" in
    *PID*)
      if ! echo "$kline" | grep -qiE 'install|build|compile|upload|download|eslint|prettier|webpack|vite|tsc|jest|mocha|rspec'; then
        bad_killable=1
      fi
      ;;
  esac
done <<< "$killable_block"
if [ "$bad_killable" -eq 0 ]; then pass; else fail "Killable list contains a process with no build/install context (generic interpreter leaked)"; fi

echo ""
echo "━━━━━ RESULTS ━━━━━"
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
