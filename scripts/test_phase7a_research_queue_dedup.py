"""
test_phase7a_research_queue_dedup.py
Phase 7A: Research queue deduplication by normalized question text.
"""
import sys, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_phase7a_research_queue_dedup ===\n")

from hermes_command_router.router import run_command
from lib.hermes_cfo_conversation_layer import (
    _add_to_research_queue, load_research_queue, dedupe_research_queue,
    _normalize_question,
)

# ── _normalize_question strips punctuation and case ──────────────────────────
print("-- normalize_question --")
check("lowercase", _normalize_question("WHAT IS THE BEST?") == "what is the best")
check("strips punctuation", _normalize_question("What is the best?") == "what is the best")
check("same normalized for variants",
      _normalize_question("what is the best offer?") == _normalize_question("What is the best offer"))

# ── Dedup prevents duplicate entries ─────────────────────────────────────────
print("\n-- _add_to_research_queue deduplicates on second call --")
ts = int(time.time())
unique_q = f"phase7a dedup test question {ts}"
e1 = _add_to_research_queue(unique_q, "general_research_scout", ["test evidence"])
e2 = _add_to_research_queue(unique_q, "general_research_scout", ["test evidence"])
check("first call creates entry", e1.get("research_id") is not None)
check("second call returns existing entry (same research_id)", e1.get("research_id") == e2.get("research_id"))

# Variant with different punctuation
e3 = _add_to_research_queue(f"{unique_q}?", "general_research_scout", ["test evidence"])
check("punctuation variant returns existing entry", e1.get("research_id") == e3.get("research_id"))

# ── dedupe_research_queue removes existing duplicates ────────────────────────
print("\n-- dedupe_research_queue removes duplicates from file --")

# Manually add duplicates by writing directly
from lib.hermes_cfo_conversation_layer import _research_queue_path
import json
ts2 = int(time.time()) + 1
dup_q = f"phase7a dup entry for dedup test {ts2}"
dup_entry = {
    "research_id": f"rq_dup_test_{ts2}",
    "question": dup_q,
    "scout": "general_research_scout",
    "evidence_needed": [],
    "status": "open",
    "created_at": "2026-06-03T00:00:00+00:00",
}
path = _research_queue_path()
before_count = sum(1 for l in path.read_text(encoding="utf-8").splitlines() if l.strip())
# Write 3 copies of the dup
with path.open("a", encoding="utf-8") as f:
    for _ in range(3):
        f.write(json.dumps(dup_entry) + "\n")

result = dedupe_research_queue()
check("dedupe_research_queue returns dict", isinstance(result, dict))
check("result has removed key", "removed" in result)
check("result has kept key", "kept" in result)
check("removed > 0 (found and removed duplicates)", result.get("removed", 0) >= 2)
check("kept >= 1", result.get("kept", 0) >= 1)

# ── dedupe_research_queue command via run_command ─────────────────────────────
print("\n-- 'dedupe research queue' command --")
r = run_command("dedupe research queue") or ""
check("RESEARCH QUEUE DEDUPED header", "RESEARCH QUEUE DEDUPED" in r.upper())
check("mentions removed", "removed" in r.lower())
check("no evidence dump", "Evidence:" not in r and "════" not in r[:80])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
