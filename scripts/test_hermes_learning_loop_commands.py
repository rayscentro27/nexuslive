"""
test_hermes_learning_loop_commands.py
Tests: all lesson intents in classify_intent and run_command routing.
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


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(resp: str) -> bool:
    DUMP_MARKERS = [
        "artifact_inventory", "Executive Memory",
        "I can answer from verified artifacts",
        "Quality escalation fallback", "═══",
    ]
    return not any(m in resp for m in DUMP_MARKERS)


print("=== test_hermes_learning_loop_commands ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS

# ── Intent classification ─────────────────────────────────────────────────────
print("-- Intent classification --")
INTENT_CASES = [
    ("record this lesson: check evidence first",         "lesson_record"),
    ("remember this lesson: never guess",                "lesson_record"),
    ("learn this: always ask Ray before publishing",     "lesson_record"),
    ("use this lesson next time: log gaps",              "lesson_record"),
    ("show pending lessons",                             "lesson_pending"),
    ("list pending lessons",                             "lesson_pending"),
    ("show active lessons",                              "lesson_active"),
    ("what lessons are active",                          "lesson_active"),
    ("approve lesson lesson_abc123",                     "lesson_approve"),
    ("reject lesson lesson_xyz456",                      "lesson_reject"),
    ("deprecate lesson lesson_mem789",                   "lesson_deprecate"),
    ("what did you learn from that",                     "lesson_learned"),
    ("show last lesson proposal",                        "lesson_learned"),
    ("where did that lesson come from",                  "lesson_source"),
    ("why did you use that memory",                      "lesson_source"),
    ("lesson source",                                    "lesson_source"),
    ("generate gap lessons",                             "lesson_gap_generate"),
    ("create lessons from gaps",                         "lesson_gap_generate"),
]
for phrase, expected_intent in INTENT_CASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase[:40]!r}) == {expected_intent}", intent == expected_intent)

# ── All lesson intents in _PLAIN_INTENTS ─────────────────────────────────────
print("\n-- All lesson intents in _PLAIN_INTENTS --")
LESSON_INTENTS = [
    "lesson_record", "lesson_pending", "lesson_active",
    "lesson_approve", "lesson_reject", "lesson_deprecate",
    "lesson_learned", "lesson_source", "lesson_gap_generate",
]
for li in LESSON_INTENTS:
    check(f"{li} in _PLAIN_INTENTS", li in _PLAIN_INTENTS)
    check(f"{li} handler is callable", callable(_PLAIN_INTENTS.get(li)))

# ── run_command returns non-empty, no dump, no HERMES REPORT wrapper ──────────
print("\n-- run_command returns clean responses --")
import lib.hermes_learning_loop as _ll
_tmp_dir = Path(tempfile.mkdtemp())
_orig_proposals = _ll.PROPOSALS_FILE

try:
    _ll.PROPOSALS_FILE = _tmp_dir / "test_proposals.jsonl"
    _ll.LEARNING_DIR   = _tmp_dir

    COMMAND_CASES = [
        ("show pending lessons",                     "PENDING LESSONS"),
        ("show active lessons",                      "ACTIVE LESSONS"),
        ("what did you learn from that",             "LAST LESSON"),
        ("where did that lesson come from",          "LESSON SOURCE"),
        ("generate gap lessons",                     "LESSON"),
        ("lesson:",                                  "LESSON"),
        ("record this lesson: always check evidence", "LESSON"),
    ]
    for phrase, expected_header in COMMAND_CASES:
        resp = run_command(phrase, source="cli")
        check(f"'{phrase[:40]}': non-empty",           bool(resp))
        check(f"'{phrase[:40]}': no evidence dump",    no_dump(resp))
        check(f"'{phrase[:40]}': no ═══ wrapper",      "═══" not in resp)
        check(f"'{phrase[:40]}': contains {expected_header!r}",
              expected_header in resp)

    # ── record lesson creates a proposal ─────────────────────────────────────
    print("\n-- record lesson creates a proposal --")
    resp = run_command(
        "record this lesson: use current artifacts before reporting status to Ray",
        source="cli",
    )
    check("record lesson: response non-empty", bool(resp))
    check("record lesson: mentions LESSON",    "LESSON" in resp)
    check("record lesson: no evidence dump",   no_dump(resp))
    # Either PROPOSAL CREATED or BLOCKED
    check("record lesson: meaningful response",
          "PROPOSAL CREATED" in resp or "BLOCKED" in resp or "LESSON RECORD" in resp)

    # ── approve / reject usage hints work without an id ───────────────────────
    print("\n-- approve/reject without id show usage hints --")
    approve_resp = run_command("approve lesson", source="cli")
    check("approve without id: shows usage", "Usage:" in approve_resp or "lesson_id" in approve_resp.lower())

    reject_resp = run_command("reject lesson", source="cli")
    check("reject without id: shows usage", "Usage:" in reject_resp or "lesson_id" in reject_resp.lower())

finally:
    _ll.PROPOSALS_FILE = _orig_proposals
    shutil.rmtree(_tmp_dir, ignore_errors=True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
