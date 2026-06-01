"""
test_memory_classification_blocks_stale_defaults.py
Verifies that all known stale Executive Memory defaults are classified
as blocked_from_live or deprecated in the Phase 3 audit.
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"

PASS = 0; FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")

print("=== test_memory_classification_blocks_stale_defaults ===\n")

# ── 1. Classification rules doc blocks stale defaults ─────────────────────
print("-- Classification rules doc --")
rules = (ROOT / "docs" / "HERMES_MEMORY_CLASSIFICATION_RULES.md").read_text()
stale_defaults = [
    "Ollama OFFLINE", "Beehiiv pending", "YouTube Studio pending",
    "OpenRouter not configured", "NitroTrades",
    "[artifact_inventory]", "[revenue_plan]",
]
for marker in stale_defaults:
    check(f"rules block '{marker}'", marker in rules)

# ── 2. Local file .hermes_executive_memory.json is classified blocked ──────
print("\n-- Local exec memory file classified blocked --")
local_files = sorted(MEMORY_DIR.glob("local_memory_classification_*.json"))
if local_files:
    data = json.loads(local_files[-1].read_text())
    exec_mem_file = next(
        (f for f in data.get("files", []) if ".hermes_executive_memory.json" in f.get("path", "")),
        None
    )
    check("exec memory file found in classification", exec_mem_file is not None)
    if exec_mem_file:
        check("exec memory file classified blocked_from_live",
              exec_mem_file.get("classification") == "blocked_from_live")

# ── 3. Fallback audit blocks format_evidence_response for monetization ─────
print("\n-- Fallback audit: format_evidence_response blocked --")
fallback_files = sorted(MEMORY_DIR.glob("fallback_response_pattern_audit_*.json"))
if fallback_files:
    data = json.loads(fallback_files[-1].read_text())
    evidence_formatter = next(
        (p for p in data.get("patterns", []) if "evidence_summary_formatter" in p.get("location", "")),
        None
    )
    check("evidence formatter found in audit", evidence_formatter is not None)
    if evidence_formatter:
        check("evidence formatter classified blocked_from_live",
              evidence_formatter.get("classification") == "blocked_from_live")
        check("evidence formatter stale_markers listed",
              len(evidence_formatter.get("stale_markers", [])) > 0)

# ── 4. Old monetization handler classified deprecated ─────────────────────
print("\n-- Old exec memory monetization handler deprecated --")
if fallback_files:
    data = json.loads(fallback_files[-1].read_text())
    old_handler = next(
        (p for p in data.get("patterns", []) if "(patched)" in p.get("location", "") or p.get("active") == False),
        None
    )
    check("old monetization handler found", old_handler is not None)
    if old_handler:
        check("old handler classified deprecated or blocked",
              old_handler.get("classification") in ("deprecated", "blocked_from_live"))
        check("old handler is not active", old_handler.get("active") == False)

# ── 5. Active memory reader stale markers match ───────────────────────────
print("\n-- hermes_active_memory_reader stale markers --")
active_reader = ROOT / "lib" / "hermes_active_memory_reader.py"
if active_reader.exists():
    src = active_reader.read_text()
    for marker in ["Ollama", "Beehiiv", "YouTube Studio", "OpenRouter", "NitroTrades"]:
        check(f"stale marker '{marker}' in _STALE_MARKERS", f'"{marker}"' in src or f"'{marker}'" in src)

# ── 6. hermes_monetization_today not blocked ─────────────────────────────
print("\n-- hermes_monetization_today is active (not blocked) --")
source_map_files = sorted(MEMORY_DIR.glob("hermes_memory_source_map_*.json"))
if source_map_files:
    data = json.loads(source_map_files[-1].read_text())
    monetization_today = next(
        (c for c in data.get("code_fallbacks", []) if "hermes_monetization_today" in c.get("location", "")),
        None
    )
    check("hermes_monetization_today found in source map", monetization_today is not None)
    if monetization_today:
        check("hermes_monetization_today classified active_live_answer",
              monetization_today.get("classification") == "active_live_answer")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
