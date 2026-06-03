"""
test_revenue_asset_fixer_no_evidence_dump.py
Tests: Phase 6F command phrases are in _EVIDENCE_DUMP_BLOCKED_PHRASES;
       handlers return structured responses, not evidence dumps.
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


def is_evidence_dump(text: str) -> bool:
    DUMP_MARKERS = [
        "evidence inventory", "artifact dump", "handoff dump",
        "stale executive memory", "full artifact list",
        "--- evidence ---",
    ]
    text_lower = (text or "").lower()
    return any(m in text_lower for m in DUMP_MARKERS)


print("=== test_revenue_asset_fixer_no_evidence_dump ===\n")

from hermes_command_router.router import _EVIDENCE_DUMP_BLOCKED_PHRASES
from hermes_command_router.router import run_command

# ── Phase 6F phrases in blocked set ──────────────────────────────────────────
print("-- Phase 6F phrases in _EVIDENCE_DUMP_BLOCKED_PHRASES --")

PHASE6F_PHRASES = [
    "fix revenue packet assets",
    "apply safe asset fixes",
    "fix packet gaps",
    "fix revenue asset gaps",
    "clean revenue assets",
    "fix revenue assets",
    "apply internal fixes",
    "fix content assets",
    "remove unsafe promises from assets",
    "soften unsafe language",
    "fix unsafe promise language",
    "remove guarantees from assets",
    "add cta to revenue assets",
    "add cta to assets",
    "add compliance notes to assets",
    "add compliance note to assets",
    "add disclaimer to assets",
    "add compliance notes",
    "show asset fix report",
    "asset fix report",
    "show fix report",
    "what was fixed",
    "rescore after fixes",
    "rescore packet after fixes",
    "update score after fixes",
    "refresh score after fixes",
]

for phrase in PHASE6F_PHRASES:
    check(f"'{phrase[:50]}' in blocked phrases", phrase in _EVIDENCE_DUMP_BLOCKED_PHRASES)

# ── Handlers do not produce evidence dumps ───────────────────────────────────
print("\n-- handlers do not produce evidence dumps --")

for phrase in ("fix revenue packet assets", "show asset fix report", "rescore after fixes"):
    try:
        response = run_command(phrase) or ""
        check(f"'{phrase[:40]}' response is not evidence dump", not is_evidence_dump(response))
    except Exception as exc:
        check(f"'{phrase[:40]}' did not raise", False)
        print(f"  Error: {exc!s:.100}")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
