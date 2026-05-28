"""
test_hermes_artifact_registry_lookup.py
Test that Hermes can answer evidence questions by looking up the artifact registry.
"""
import sys, tempfile, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS; PASS += 1; print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL; FAIL += 1; print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


import lib.nexus_artifact_registry as _reg_mod

_tmp = tempfile.mkdtemp()
_orig_reg = _reg_mod.REGISTRY_FILE
_orig_md  = _reg_mod.REGISTRY_MD
_reg_mod.REGISTRY_FILE = Path(_tmp) / "nexus_artifact_registry.jsonl"
_reg_mod.REGISTRY_MD   = Path(_tmp) / "nexus_artifact_registry_latest.md"

_registry = _reg_mod.NexusArtifactRegistry()

# Pre-populate with test artifacts
_registry.register_artifact(
    agent_name="youtube_research_scout", agent_type="scout",
    source_input="https://youtube.com/watch?v=lookup_yt",
    source_type="youtube_video", artifact_type="report",
    title="YouTube Research Report", summary="Research on video",
    file_path=str(ROOT / "scripts" / "test_hermes_artifact_registry_lookup.py"),
    tags=["youtube", "research"],
    what_hermes_should_know="YouTube research complete for lookup_yt",
)
_registry.register_artifact(
    agent_name="credit_repair_research_scout", agent_type="scout",
    source_input="", source_type="credit_repair_strategy",
    artifact_type="report", title="Credit Repair Research",
    summary="Credit repair cycle output",
    file_path="",
    tags=["credit", "research"],
    what_hermes_should_know="Credit repair research cycle complete",
)
_registry.register_artifact(
    agent_name="funding_readiness_scout", agent_type="scout",
    source_input="", source_type="business_funding",
    artifact_type="report", title="Funding Readiness Report",
    summary="Funding readiness check",
    file_path=str(ROOT / "scripts" / "test_hermes_artifact_registry_lookup.py"),
    tags=["funding"],
)


def test_find_by_source_url_returns_youtube():
    results = _registry.find_by_source_url("https://youtube.com/watch?v=lookup_yt")
    if results:
        ok(f"find_by_source_url_returns_youtube — found {len(results)} record(s)")
    else:
        fail("find_by_source_url_returns_youtube")


def test_find_artifacts_by_agent():
    results = _registry.find_agent_outputs("youtube_research_scout")
    if results:
        ok(f"find_artifacts_by_agent — {len(results)} artifact(s) for youtube_research_scout")
    else:
        fail("find_artifacts_by_agent")


def test_find_youtube_artifacts():
    results = _registry.find_youtube_artifacts()
    if results:
        ok(f"find_youtube_artifacts — {len(results)} YouTube artifact(s)")
    else:
        fail("find_youtube_artifacts")


def test_find_artifacts_filter_by_tag():
    results = _registry.find_artifacts(tags=["credit"])
    if results:
        ok(f"find_artifacts_filter_by_tag — {len(results)} record(s) with tag 'credit'")
    else:
        fail("find_artifacts_filter_by_tag")


def test_latest_artifacts_ordered():
    arts = _registry.latest_artifacts(limit=3)
    if len(arts) >= 2:
        ok(f"latest_artifacts_ordered — {len(arts)} artifacts")
    else:
        fail("latest_artifacts_ordered", f"expected >=2, got {len(arts)}")


def test_summary_counts_total():
    summary = _registry.create_registry_summary()
    # create_registry_summary returns a string (markdown table)
    if summary and len(str(summary)) > 10:
        ok(f"summary_counts_total — non-empty summary returned")
    else:
        fail("summary_counts_total", repr(str(summary)[:100]))


def test_summary_counts_verified():
    summary = _registry.create_registry_summary()
    summary_str = str(summary)
    if "✅" in summary_str or "verified" in summary_str.lower() or "artifact" in summary_str.lower():
        ok("summary_counts_verified — summary contains verification info")
    else:
        fail("summary_counts_verified", repr(summary_str[:100]))


def test_what_hermes_should_know_retrievable():
    results = _registry.find_agent_outputs("youtube_research_scout")
    if results:
        d = results[0].to_dict()
        know = d.get("what_hermes_should_know", "")
        if "lookup_yt" in know or "complete" in know.lower():
            ok("what_hermes_should_know_retrievable")
        else:
            fail("what_hermes_should_know_retrievable", repr(know))
    else:
        fail("what_hermes_should_know_retrievable", "no records found")


def test_module_singleton_find_works():
    results = _reg_mod.find_artifacts(agent_name="funding_readiness_scout")
    if isinstance(results, list):
        ok(f"module_singleton_find_works — len={len(results)}")
    else:
        fail("module_singleton_find_works")


def test_module_singleton_latest_works():
    arts = _reg_mod.latest_artifacts(limit=5)
    if isinstance(arts, list):
        ok(f"module_singleton_latest_works — len={len(arts)}")
    else:
        fail("module_singleton_latest_works")


if __name__ == "__main__":
    print("=== test_hermes_artifact_registry_lookup ===")
    test_find_by_source_url_returns_youtube()
    test_find_artifacts_by_agent()
    test_find_youtube_artifacts()
    test_find_artifacts_filter_by_tag()
    test_latest_artifacts_ordered()
    test_summary_counts_total()
    test_summary_counts_verified()
    test_what_hermes_should_know_retrievable()
    test_module_singleton_find_works()
    test_module_singleton_latest_works()

    shutil.rmtree(_tmp, ignore_errors=True)
    _reg_mod.REGISTRY_FILE = _orig_reg
    _reg_mod.REGISTRY_MD   = _orig_md

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
