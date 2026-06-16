#!/bin/bash
# Tests for the repo hygiene guardrails.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HYGIENE="$ROOT/scripts/check_repo_hygiene.sh"
PRSIZE="$ROOT/scripts/check_pr_size.sh"
AGENTS="$ROOT/AGENTS.md"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }

echo "━━━━━ REPO HYGIENE POLICY TESTS ━━━━━"

# 1. bash -n syntax on both guard scripts
echo "--- 1. bash -n syntax ---"
if bash -n "$HYGIENE" 2>/dev/null; then pass; else fail "check_repo_hygiene.sh syntax"; fi
if bash -n "$PRSIZE" 2>/dev/null; then pass; else fail "check_pr_size.sh syntax"; fi

# 2. Forbidden paths are detected (via --files mode, no real staging needed)
echo "--- 2. forbidden path detection ---"
for bad in \
  ".env" "config/app.env.local" "x.lock" "worker.pid" \
  "logs/run.log" "reports/audit.md" "artifacts/x.done" \
  "research-engine/strategies/foo.en.vtt" "research-engine/strategies/foo.summary" \
  "docs/content/x_posts/post.md" "tool-lab/exp/a.py" "test-results/out.xml" \
  "supabase/.temp/cli-latest" "node_modules/pkg/index.js" "dist/bundle.js" \
  "build/out.o" ".cache/blob" "shot.png" "pic.jpeg" "image.webp" \
  ".telegram_bot.lock" ".hermes_ops_memory.json" ".circuit_breaker_state.json" \
  ".hermes_cli_handoffs.json" ".telegram_update_offset" ; do
  if bash "$HYGIENE" --files "$bad" >/dev/null 2>&1; then
    fail "did NOT flag forbidden path: $bad"
  else
    pass
  fi
done

# 3. Allowed paths pass cleanly
echo "--- 3. allowed paths pass ---"
for ok in ".env.example" "scripts/foo.py" "tests/test_foo.py" "docs/guide.md" \
          "lib/module.py" "scripts/run.sh" ; do
  if bash "$HYGIENE" --files "$ok" >/dev/null 2>&1; then pass; else fail "wrongly flagged allowed path: $ok"; fi
done

# 4. Mixed set fails if ANY forbidden path is present
echo "--- 4. mixed set fails ---"
if bash "$HYGIENE" --files "lib/ok.py" "logs/bad.log" >/dev/null 2>&1; then
  fail "mixed set with logs/bad.log should fail"
else
  pass
fi

# 5. AGENTS.md documents the git add . / git add -A prohibition
echo "--- 5. AGENTS.md staging prohibition ---"
if grep -q 'git add \.' "$AGENTS" && grep -q 'git add -A' "$AGENTS"; then pass; else fail "AGENTS.md missing git add ./-A prohibition"; fi

# 6. PR size script has a 60-file threshold
echo "--- 6. PR size threshold ---"
if grep -qE 'MAX_FILES=60' "$PRSIZE"; then pass; else fail "check_pr_size.sh missing 60-file threshold"; fi

# 7. Guard scripts are read-only (no delete/modify/network constructs).
# Note: redirecting to /dev/null is read-only-safe, so it is not flagged.
echo "--- 7. guard scripts read-only ---"
for s in "$HYGIENE" "$PRSIZE"; do
  if grep -qE '\brm\b|truncate|\bmv \b|\bcp \b|git +(add|commit|push|checkout|reset|clean|rebase)\b|curl|wget|requests\.' "$s"; then
    fail "guard script may not be read-only: $s"
  else
    pass
  fi
done

# 8. .env.example explicitly allowed even though .env.* is forbidden
echo "--- 8. .env.example allowlist ---"
if bash "$HYGIENE" --files ".env.example" >/dev/null 2>&1; then pass; else fail ".env.example should be allowed"; fi
if bash "$HYGIENE" --files ".env.production" >/dev/null 2>&1; then fail ".env.production should be forbidden"; else pass; fi

# 9. Guard scripts do not delete files (run on a temp file, confirm it survives)
echo "--- 9. guard does not delete files ---"
TMP="$(mktemp)"
echo "x" > "$TMP"
bash "$HYGIENE" --files "$TMP" >/dev/null 2>&1 || true
if [ -f "$TMP" ]; then pass; else fail "hygiene guard deleted a file"; fi
rm -f "$TMP"

echo ""
echo "━━━━━ RESULTS ━━━━━"
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
