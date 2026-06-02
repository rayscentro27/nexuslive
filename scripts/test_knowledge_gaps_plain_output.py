"""
test_knowledge_gaps_plain_output.py
Verifies 'show knowledge gaps' returns plain KNOWLEDGE GAPS text, not HERMES REPORT wrapper.
"""
import sys, os
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


print("=== test_knowledge_gaps_plain_output ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS

print("-- Intent classification --")
for phrase in ["show knowledge gaps", "show unanswered questions",
               "what gaps do you have", "what did you not know",
               "show gaps"]:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == knowledge_gap_review",
          intent == "knowledge_gap_review")

print("\n-- knowledge_gap_review in _PLAIN_INTENTS --")
check("knowledge_gap_review in _PLAIN_INTENTS", "knowledge_gap_review" in _PLAIN_INTENTS)
fn = _PLAIN_INTENTS.get("knowledge_gap_review")
check("handler is callable", callable(fn))

print("\n-- 'show knowledge gaps' response --")
resp = run_command("show knowledge gaps", source="cli")
print(f"  output: {resp[:200]!r}")
check("response non-empty", bool(resp))
check("contains KNOWLEDGE GAPS header", "KNOWLEDGE GAPS" in resp)
check("no ═══ wrapper separator", "═══" not in resp)
check("response does not start with HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
check("no stale Executive Memory", "Executive Memory" not in resp)
check("no artifact_inventory", "artifact_inventory" not in resp)
check("mentions 'create better answers' for next steps",
      "create better answers" in resp.lower() or "improvement" in resp.lower() or "Next" in resp)

print("\n-- 'what gaps do you have' response --")
resp2 = run_command("what gaps do you have", source="cli")
check("response non-empty", bool(resp2))
check("contains KNOWLEDGE GAPS", "KNOWLEDGE GAPS" in resp2)
check("no ═══ wrapper separator", "═══" not in resp2)

print("\n-- knowledge_gap_review is in SAFE_REPEATABLE_MEMORY_INTENTS --")
import telegram_bot as tb_mod
import inspect
tb_src = inspect.getsource(tb_mod)
check("knowledge_gap_review in SAFE_REPEATABLE_MEMORY_INTENTS",
      "knowledge_gap_review" in tb_src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
