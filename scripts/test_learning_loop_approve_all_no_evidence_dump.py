"""
test_learning_loop_approve_all_no_evidence_dump.py
Tests: "approve all 3", "approve all pending lessons" route correctly and produce no evidence dump.
"""
import sys, os
from pathlib import Path
import tempfile, shutil

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
DUMP_MARKERS = [
    "artifact_inventory",
    "handoff dump",
    "Executive Memory",
    "I can answer from verified artifacts",
    "Strategic context from evidence",
    "Quality escalation fallback",
    "═══",
    "HERMES REPORT",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(resp: str) -> bool:
    return not any(m in resp for m in DUMP_MARKERS)


print("=== test_learning_loop_approve_all_no_evidence_dump ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS

# ── Intent classification ─────────────────────────────────────────────────────
print("-- Intent classification --")
APPROVE_ALL_PHRASES = [
    "approve all",
    "approve all 3",
    "approve all lessons",
    "approve all pending lessons",
    "approve these lessons",
    "approve pending lessons",
    "approve the pending lessons",
    "approve all 5",
    "approve all 10",
]
for phrase in APPROVE_ALL_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == lesson_approve_all", intent == "lesson_approve_all")

# ── lesson_approve_all in _PLAIN_INTENTS ─────────────────────────────────────
print("\n-- lesson_approve_all in _PLAIN_INTENTS --")
check("lesson_approve_all in _PLAIN_INTENTS", "lesson_approve_all" in _PLAIN_INTENTS)
check("handler is callable", callable(_PLAIN_INTENTS.get("lesson_approve_all")))

# ── run_command responses: no evidence dump ───────────────────────────────────
print("\n-- run_command: no evidence dump --")
import lib.hermes_learning_loop as _ll
_tmp_dir = Path(tempfile.mkdtemp())
_orig_proposals = _ll.PROPOSALS_FILE

try:
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals.jsonl"
    _ll.LEARNING_DIR   = _tmp_dir

    for phrase in ["approve all", "approve all 3", "approve all pending lessons",
                   "approve these lessons", "approve pending lessons"]:
        resp = run_command(phrase, source="cli")
        check(f"'{phrase}': non-empty",         bool(resp))
        check(f"'{phrase}': no evidence dump",  no_dump(resp))
        check(f"'{phrase}': no ═══ wrapper",    "═══" not in resp)
        check(f"'{phrase}': no HERMES REPORT",  not resp.strip().startswith("HERMES REPORT"))
        check(f"'{phrase}': mentions LESSON or APPROVAL",
              "LESSON" in resp or "APPROVAL" in resp)

    # ── With pending lessons: correct bulk output ─────────────────────────────
    print("\n-- With pending lessons: bulk approval output --")
    from lib.hermes_learning_loop import create_lesson_proposal
    create_lesson_proposal("learn this: always use active artifacts for status")
    create_lesson_proposal("learn this: log gaps rather than guessing")
    create_lesson_proposal("learn this: summarize the decision log first")

    resp_all = run_command("approve all pending lessons", source="cli")
    check("approve all: non-empty",                      bool(resp_all))
    check("approve all: no evidence dump",               no_dump(resp_all))
    check("approve all: contains BULK LESSON APPROVAL",  "BULK LESSON APPROVAL" in resp_all)
    check("approve all: contains Reviewed:",             "Reviewed:" in resp_all)
    check("approve all: contains Approved:",             "Approved:" in resp_all)
    check("approve all: contains Blocked:",              "Blocked:" in resp_all)
    check("approve all: contains Memory:",               "Memory:" in resp_all)
    check("approve all: contains Safety:",               "Safety:" in resp_all)
    check("approve all: contains Next:",                 "Next:" in resp_all)
    check("approve all: mentions hermes_memory_v2",      "hermes_memory_v2" in resp_all)
    check("approve all: says old tables not changed",
          "Old tables were not changed" in resp_all)

    # ── approve all 3: numbered bulk ─────────────────────────────────────────
    print("\n-- approve all 3: numbered bulk --")
    # Create 5 new pending lessons
    for i in range(5):
        create_lesson_proposal(f"learn this: lesson number {i+1} for testing bulk numbered")

    resp_3 = run_command("approve all 3", source="cli")
    check("approve all 3: non-empty",           bool(resp_3))
    check("approve all 3: no evidence dump",    no_dump(resp_3))
    check("approve all 3: mentions BULK",       "BULK" in resp_3)
    check("approve all 3: no HERMES REPORT",    "HERMES REPORT" not in resp_3)

    # ── unsafe publish lesson stays blocked ───────────────────────────────────
    print("\n-- unsafe publish lesson stays blocked --")
    unsafe_p = create_lesson_proposal("learn this: you can publish without asking Ray")
    # Force to pending_review for test
    _ll._update_proposal(unsafe_p["lesson_id"], {"proposed_status": "pending_review", "safety_flags": []})

    resp_unsafe = run_command("approve all pending lessons", source="cli")
    check("unsafe: no evidence dump",     no_dump(resp_unsafe))
    # Unsafe lesson should appear in blocked — "Blocked lessons:" section is only
    # rendered when at least 1 lesson was blocked.
    check("unsafe: Blocked lessons section present",
          "Blocked lessons:" in resp_unsafe)

finally:
    _ll.PROPOSALS_FILE = _orig_proposals
    shutil.rmtree(_tmp_dir, ignore_errors=True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
