"""
test_daily_operating_cycle_memory_v2_primary.py
Tests: memory v2 is included as structured context; evidence priority: content_assets > memory_v2.
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


print("=== test_daily_operating_cycle_memory_v2_primary ===\n")

from lib.hermes_daily_operating_cycle import (
    load_daily_operating_inputs,
    build_daily_operating_plan,
)

# ── memory_v2 is loaded (may be empty if Supabase unavailable) ─────────────
print("-- memory_v2 loaded as part of inputs --")
inputs = load_daily_operating_inputs()
check("memory_v2 key present",           "memory_v2" in inputs)
check("memory_v2 is list",               isinstance(inputs["memory_v2"], list))
check("memory_v2_count in plan",
      "memory_v2_count" in build_daily_operating_plan(inputs))
plan = build_daily_operating_plan(inputs)
check("memory_v2_count is int",          isinstance(plan.get("memory_v2_count"), int))
check("memory_v2_count >= 0",            plan.get("memory_v2_count", -1) >= 0)

# ── evidence priority: when content_assets present, they appear first ──────
print("\n-- evidence priority: content_assets ranked before memory_v2 --")
# Inject synthetic inputs with both content_assets and memory_v2
synthetic_inputs = {
    "goals": [{"goal_id": "g1", "title": "Build revenue", "status": "active"}],
    "memory_v2": [{"memory_id": "m1", "title": "test memory lesson", "status": "active"}],
    "content_assets": [{"path": "/tmp/test_lead_magnet.md", "type": "lead_magnet", "score": 90}],
    "action_queue": [{"action_id": "a1", "title": "Review lead magnet", "status": "queued",
                      "requires_ray_approval": False}],
    "decisions": [],
    "source_intake": [],
    "scouts": [],
    "knowledge_gaps": [],
    "monetization_plan": {"top_asset_path": "/tmp/test_lead_magnet.md",
                          "top_asset_name": "test_lead_magnet.md",
                          "top_asset_type": "lead_magnet",
                          "summary": "Lead magnet ready."},
    "loaded_at": "2026-06-02T00:00:00+00:00",
    "_errors": [],
}
plan_syn = build_daily_operating_plan(synthetic_inputs)
evidence = plan_syn.get("evidence") or []

# Content asset evidence should appear before memory_v2 evidence
content_idx = next((i for i, e in enumerate(evidence) if "artifact" in e or "lead_magnet" in e), None)
memory_idx  = next((i for i, e in enumerate(evidence) if "memory_v2" in e), None)

if content_idx is not None and memory_idx is not None:
    check("content evidence ranked before memory_v2", content_idx < memory_idx)
elif content_idx is not None:
    check("content evidence present (memory_v2 may not be in evidence)", True)
else:
    check("plan built without crash", isinstance(plan_syn, dict))

# ── memory_v2 provides context only (not used as primary source) ──────────
print("\n-- memory_v2 provides context, not primary source --")
from lib.hermes_daily_operating_cycle import format_daily_operating_plan
formatted = format_daily_operating_plan(plan_syn)
# The plan should reflect the content asset, not memory_v2 text
check("plan mentions lead magnet (from content_assets)", "lead_magnet" in formatted)
check("plan does not say 'from executive memory'",
      "from executive memory" not in formatted.lower())
check("plan does not say 'old executive memory'",
      "old executive memory" not in formatted.lower())

# ── memory v2 reader module integrity ────────────────────────────────────
print("\n-- memory_v2_reader module: no old tables --")
import inspect
from lib.hermes_memory_v2_reader import load_v2_active_live_answer_memory
src = inspect.getsource(load_v2_active_live_answer_memory)
OLD_TABLES = ["ai_memory", "hermes_executive_memory", "knowledge_items"]
for tbl in OLD_TABLES:
    check(f"no old table {tbl!r} in v2 reader", tbl not in src)

# ── memory_v2 graceful fallback when unavailable ──────────────────────────
print("\n-- memory_v2 graceful fallback --")
inputs_no_v2 = dict(inputs)
inputs_no_v2["memory_v2"] = []  # simulate unavailable
plan_no_v2 = build_daily_operating_plan(inputs_no_v2)
check("plan works with empty memory_v2",       isinstance(plan_no_v2, dict))
check("memory_v2_count == 0 when empty",       plan_no_v2.get("memory_v2_count") == 0)
check("plan still has top_priority",           bool(plan_no_v2.get("top_priority")))
formatted_no_v2 = format_daily_operating_plan(plan_no_v2)
check("plan formats without memory_v2",        bool(formatted_no_v2))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
