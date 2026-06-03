"""
test_unknown_answer_scout_dispatch.py
Tests: unknown answer creates research queue item and assigns scout.
"""
import sys, os, json
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


print("=== test_unknown_answer_scout_dispatch ===\n")

from lib.hermes_cfo_conversation_layer import (
    _add_to_research_queue,
    _select_scout,
    _SCOUT_MAP,
    load_research_queue,
    load_scout_assignments,
    create_scout_tasks_for_unknowns,
    _research_queue_path,
    _scout_assignments_path,
)

# ── _select_scout returns valid scout ─────────────────────────────────────────
print("-- _select_scout --")
for category, scouts in _SCOUT_MAP.items():
    selected = _select_scout(category)
    check(f"[{category}] scout selected", bool(selected))
    check(f"[{category}] scout in expected list", selected in scouts)

# ── _add_to_research_queue creates queue entry ────────────────────────────────
print("\n-- _add_to_research_queue --")
question = "What is the best affiliate offer for the funding checklist audience?"
scout = _select_scout("monetization_strategy")
entry = _add_to_research_queue(question, scout, ["Affiliate offer data", "Conversion rates"])
check("entry is dict", isinstance(entry, dict))
check("entry has research_id", "research_id" in entry)
check("entry has question", "question" in entry)
check("entry has scout", "scout" in entry and entry["scout"] == scout)
check("entry has status 'open'", entry.get("status") == "open")
check("entry has created_at", "created_at" in entry)
check("research_id starts with 'rq_'", entry.get("research_id", "").startswith("rq_"))

# ── load_research_queue finds the entry ──────────────────────────────────────
print("\n-- load_research_queue --")
queue = load_research_queue(status="open")
check("queue is list", isinstance(queue, list))
check("queue has at least one entry", len(queue) >= 1)
found = any(e.get("research_id") == entry["research_id"] for e in queue)
check("new entry found in queue", found)

# ── create_scout_tasks_for_unknowns ──────────────────────────────────────────
print("\n-- create_scout_tasks_for_unknowns --")
unknowns = [
    "Which affiliate offer converts best for funding-readiness audience?",
    "How often do Ray's messages fall through to evidence dumps?",
]
tasks = create_scout_tasks_for_unknowns("test message", unknowns)
check("returns list", isinstance(tasks, list))
check("returns correct number of tasks", len(tasks) == len(unknowns))
for t in tasks:
    check(f"task has scout: {t.get('scout','?')[:30]}", bool(t.get("scout")))
    check(f"task has research_question", bool(t.get("research_question")))
    check(f"task has status 'open'", t.get("status") == "open")

# ── load_scout_assignments has assignments ────────────────────────────────────
print("\n-- load_scout_assignments --")
assignments = load_scout_assignments()
check("assignments is list", isinstance(assignments, list))
check("at least some assignments", len(assignments) >= 1)

# ── Research queue file exists ────────────────────────────────────────────────
print("\n-- research queue files exist --")
check("research queue file exists", _research_queue_path().exists())
check("scout assignments file exists", _scout_assignments_path().exists())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
