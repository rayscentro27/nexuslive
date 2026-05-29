"""
test_greeting_no_stale_status.py
Verifies greeting does not claim Ollama/provider/task status without evidence,
and does not use stale default memory.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_greeting_no_stale_status ===")

from lib.hermes_internal_first import _build_operational_context_brief, try_internal_first

ctx = _build_operational_context_brief()

# 1. Context must not contain unsourced provider/infra claims
BANNED_CLAIMS = [
    "ollama",
    "netcup",
    "localhost:11555",
    "content falls back to templates",
    "oracle vm",
    "llm-worker service status unknown",
    "watching roadmap",
    "provider health",
    "task queue",
    "Nexus is up",
    "Nexus is running",
    "remediate 7 false completions",
    "get content engine running",
    "beehiiv and youtube studio",
    "route daily content through openrouter",
]

for claim in BANNED_CLAIMS:
    check(f"context does NOT claim: {claim[:50]}", claim.lower() not in ctx.lower())

# 2. Context either mentions verified evidence OR safe command suggestions
check("context mentions verified evidence or ask commands",
      "verified" in ctx.lower() or "ask:" in ctx.lower() or "ask me" in ctx.lower())

# 3. Greeting pattern: try greeting messages
GREETING_QUERIES = [
    "hello good morning",
    "morning hermes",
    "good morning",
    "gm",
    "hi hermes",
]

for q in GREETING_QUERIES:
    result = try_internal_first(q)
    if result is None:
        # Allowed — greeting may fall through
        PASS += 1; print(f"  ✅ greeting returns None (falls to pattern match): {q}")
        continue
    for claim in BANNED_CLAIMS[:6]:  # Check only most critical
        check(f"greeting reply no '{claim[:30]}': {q}", claim.lower() not in result.text.lower())

# 4. Greeting response must not contain static demo provider strings
from lib.hermes_response_patterns import match_pattern, fill_template
pattern = match_pattern("good morning")
if pattern:
    tmpl = pattern.get("response_template", "")
    filled = fill_template(tmpl, {
        "operational_context": ctx,
        "brief_status": ctx,
        "next_best_action": "",
        "next_best_action_prompt": "",
    })
    check("filled greeting does not mention Ollama offline", "ollama" not in filled.lower() or "verified" in filled.lower())
    check("filled greeting does not mention netcup", "netcup" not in filled.lower())
    check("filled greeting does not mention 'watching roadmap, providers'", "watching roadmap, providers" not in filled.lower())
    check("filled greeting mentions evidence or ask", "verified" in filled.lower() or "ask" in filled.lower())
else:
    PASS += 1; print("  ✅ no pattern match (patterns from Supabase, skipping template check)")

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
