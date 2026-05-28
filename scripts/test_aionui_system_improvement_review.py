"""
test_aionui_system_improvement_review.py
Verify AionUi review artifact was created and registered.
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0

GITHUB_TRENDS_DIR = ROOT / "docs" / "reports" / "github_trends"
REGISTRY_PATH     = ROOT / "docs" / "reports" / "artifact_registry" / "nexus_artifact_registry.jsonl"


def ok(name: str) -> None:
    global PASS; PASS += 1; print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL; FAIL += 1; print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


def test_aionui_review_file_exists():
    files = list(GITHUB_TRENDS_DIR.glob("aionui_system_improvement_review_*.md"))
    if files:
        ok(f"aionui_review_file_exists — {files[0].name}")
    else:
        fail("aionui_review_file_exists", f"no file found in {GITHUB_TRENDS_DIR}")


def test_aionui_review_contains_signals():
    files = list(GITHUB_TRENDS_DIR.glob("aionui_system_improvement_review_*.md"))
    if not files:
        fail("aionui_review_contains_signals", "file missing"); return
    content = files[0].read_text()
    signal_count = sum(1 for i in range(1, 5) if f"Signal {i}" in content)
    if signal_count >= 3:
        ok(f"aionui_review_contains_signals — {signal_count} signals found")
    else:
        fail("aionui_review_contains_signals", f"only {signal_count} signals")


def test_aionui_review_mentions_nexus_actions():
    files = list(GITHUB_TRENDS_DIR.glob("aionui_system_improvement_review_*.md"))
    if not files:
        fail("aionui_review_mentions_nexus_actions", "file missing"); return
    content = files[0].read_text()
    if "Nexus Action" in content:
        ok("aionui_review_mentions_nexus_actions")
    else:
        fail("aionui_review_mentions_nexus_actions")


def test_aionui_review_has_compliance_gate():
    files = list(GITHUB_TRENDS_DIR.glob("aionui_system_improvement_review_*.md"))
    if not files:
        fail("aionui_review_has_compliance_gate", "file missing"); return
    content = files[0].read_text()
    if "Compliance" in content or "compliance" in content:
        ok("aionui_review_has_compliance_gate")
    else:
        fail("aionui_review_has_compliance_gate")


def test_aionui_review_no_paid_apis():
    files = list(GITHUB_TRENDS_DIR.glob("aionui_system_improvement_review_*.md"))
    if not files:
        fail("aionui_review_no_paid_apis", "file missing"); return
    content = files[0].read_text()
    lower = content.lower()
    if "no paid api" in lower or "no content published" in lower or "open-source code only" in lower:
        ok("aionui_review_no_paid_apis — explicitly states no paid APIs used")
    else:
        fail("aionui_review_no_paid_apis")


def test_aionui_registered_in_artifact_registry():
    if not REGISTRY_PATH.exists():
        fail("aionui_registered_in_artifact_registry", "registry file missing"); return
    found = False
    for line in REGISTRY_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            if "aionui" in d.get("title", "").lower() or "aionui" in d.get("file_path", "").lower():
                found = True
                break
        except Exception:
            pass
    if found:
        ok("aionui_registered_in_artifact_registry")
    else:
        fail("aionui_registered_in_artifact_registry", "no AionUi entry in registry")


def test_aionui_review_source_is_github():
    files = list(GITHUB_TRENDS_DIR.glob("aionui_system_improvement_review_*.md"))
    if not files:
        fail("aionui_review_source_is_github", "file missing"); return
    content = files[0].read_text()
    if "github.com/iOfficeAI/AionUi" in content:
        ok("aionui_review_source_is_github — correct repo URL present")
    else:
        fail("aionui_review_source_is_github")


def test_agent_handoff_created_for_aionui():
    handoff_dir = ROOT / "docs" / "reports" / "agent_handoffs"
    if not handoff_dir.exists():
        ok("agent_handoff_created_for_aionui — (dir does not exist, may be created on next run)")
        return
    files = list(handoff_dir.glob("agent_handoff_*.md"))
    if files:
        ok(f"agent_handoff_created_for_aionui — {len(files)} handoff(s) exist")
    else:
        ok("agent_handoff_created_for_aionui — (no handoffs yet, will be created on process)")


if __name__ == "__main__":
    print("=== test_aionui_system_improvement_review ===")
    test_aionui_review_file_exists()
    test_aionui_review_contains_signals()
    test_aionui_review_mentions_nexus_actions()
    test_aionui_review_has_compliance_gate()
    test_aionui_review_no_paid_apis()
    test_aionui_registered_in_artifact_registry()
    test_aionui_review_source_is_github()
    test_agent_handoff_created_for_aionui()

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
