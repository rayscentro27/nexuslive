"""test_phase8c_draft_comparison_context_or_clarify.py — draft comparison uses real context or asks which draft."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from lib.hermes_cfo_loop_shadow import run_cfo_limited_primary
from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop
from prototypes import hermes_agentic_cfo_loop as proto

original_resolver = proto._resolve_real_draft_paths

tmpdir = Path(tempfile.mkdtemp(prefix="phase8c_drafts_"))
prev_path = tmpdir / "draft_prev.md"
curr_path = tmpdir / "draft_curr.md"
prev_path.write_text("# Draft\n\n## Start Here\nOld section\n", encoding="utf-8")
curr_path.write_text("# Draft\n\n## Start Here\nNew section\n\n## Compliance\nUpdated note\n", encoding="utf-8")

try:
    proto._resolve_real_draft_paths = lambda: (None, None)
    loop = HermesCFOLoop()
    response, trace = loop.process("what changed in the draft")
    check("intent=draft_comparison", trace["intent"] == "draft_comparison")
    check("clarify when context missing", "which draft should i compare" in response.lower())
    check("does not route to daily plan comparison", "last plan" not in response.lower())

    proto._resolve_real_draft_paths = lambda: (prev_path, curr_path)
    response2, used2 = run_cfo_limited_primary("what changed in the draft")
    text2 = (response2 or "").lower()
    check("limited primary used with draft context", used2 is True)
    check("draft change output present", "updated section" in text2 or "added section" in text2)
    check("no daily plan comparison phrasing", "since last plan" not in text2)
finally:
    proto._resolve_real_draft_paths = original_resolver
    try:
        prev_path.unlink()
        curr_path.unlink()
        tmpdir.rmdir()
    except Exception:
        pass
    os.environ.pop("HERMES_CFO_LOOP_MODE", None)
    os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C draft comparison grounding: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
