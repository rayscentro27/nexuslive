"""
test_nexus_artifact_registry.py
Test the Nexus artifact registry — registration, lookup, dedup, evidence levels.
"""
import sys, os, tempfile, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL
    FAIL += 1
    print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


# ── Patch registry path to a temp dir for tests ──────────────────────────────
import lib.nexus_artifact_registry as _reg_mod

_tmp = tempfile.mkdtemp()
_orig_registry_path = _reg_mod.REGISTRY_FILE
_orig_latest_path   = _reg_mod.REGISTRY_MD
_reg_mod.REGISTRY_FILE = Path(_tmp) / "nexus_artifact_registry.jsonl"
_reg_mod.REGISTRY_MD   = Path(_tmp) / "nexus_artifact_registry_latest.md"

# Reload registry singleton with temp paths
_registry = _reg_mod.NexusArtifactRegistry()


def test_register_basic():
    art = _registry.register_artifact(
        agent_name="test_agent",
        agent_type="test",
        source_input="https://example.com/video",
        source_type="youtube_video",
        artifact_type="report",
        title="Test Report",
        summary="A test report",
        file_path=__file__,
        tags=["test"],
    )
    if art and art.artifact_id:
        ok("register_basic — returns ArtifactRecord with artifact_id")
    else:
        fail("register_basic — no artifact_id returned")


def test_artifact_id_format():
    art = _registry.register_artifact(
        agent_name="test_agent",
        agent_type="test",
        source_input="",
        source_type="other",
        artifact_type="report",
        title="Format test",
        summary="",
        file_path=__file__,
        tags=[],
    )
    if art.artifact_id.startswith("art_"):
        ok("artifact_id_format — starts with art_")
    else:
        fail("artifact_id_format", f"got {art.artifact_id!r}")


def test_evidence_level_verified_file():
    art = _registry.register_artifact(
        agent_name="test_agent",
        agent_type="test",
        source_input="",
        source_type="other",
        artifact_type="report",
        title="Verified file test",
        summary="",
        file_path=__file__,  # this file exists
        tags=[],
    )
    if art.is_verified:
        ok("evidence_level_verified_file — existing file → is_verified=True")
    else:
        fail("evidence_level_verified_file", f"evidence_level={art.evidence_level!r}")


def test_evidence_level_unverified_claim():
    art = _registry.register_artifact(
        agent_name="test_agent",
        agent_type="test",
        source_input="",
        source_type="other",
        artifact_type="report",
        title="No file test",
        summary="",
        file_path="/nonexistent/path/to/nothing.md",
        tags=[],
    )
    if not art.is_verified:
        ok("evidence_level_unverified_claim — nonexistent file → is_verified=False")
    else:
        fail("evidence_level_unverified_claim", f"expected unverified, got {art.evidence_level!r}")


def test_find_by_source_url():
    url = "https://example.com/findme_" + str(os.getpid())
    _registry.register_artifact(
        agent_name="test_agent", agent_type="test",
        source_input=url, source_type="other",
        artifact_type="report", title="Find by URL test",
        summary="", file_path=__file__, tags=[],
    )
    results = _registry.find_by_source_url(url)
    if results:
        ok("find_by_source_url — registered artifact found by URL")
    else:
        fail("find_by_source_url — not found")


def test_latest_artifacts():
    arts = _registry.latest_artifacts(limit=5)
    if isinstance(arts, list):
        ok(f"latest_artifacts — returns list (len={len(arts)})")
    else:
        fail("latest_artifacts — not a list")


def test_create_registry_summary():
    summary = _registry.create_registry_summary()
    if summary and ("artifact" in str(summary).lower() or "total" in str(summary).lower() or len(str(summary)) > 10):
        ok(f"create_registry_summary — returns non-empty summary")
    else:
        fail("create_registry_summary", f"got {str(summary)[:100]!r}")


def test_find_youtube_artifacts():
    _registry.register_artifact(
        agent_name="youtube_scout", agent_type="scout",
        source_input="https://youtube.com/watch?v=yt_test",
        source_type="youtube_video",
        artifact_type="report", title="YouTube test artifact",
        summary="", file_path=__file__, tags=["youtube"],
    )
    results = _registry.find_youtube_artifacts()
    if results:
        ok("find_youtube_artifacts — finds youtube_video type artifacts")
    else:
        fail("find_youtube_artifacts — none found")


def test_find_agents_outputs():
    results = _registry.find_agent_outputs("test_agent")
    if isinstance(results, list) and results:
        ok(f"find_agent_outputs — returns results for test_agent (count={len(results)})")
    else:
        fail("find_agent_outputs — no results")


def test_mark_artifact_status():
    art = _registry.register_artifact(
        agent_name="test_agent", agent_type="test",
        source_input="", source_type="other",
        artifact_type="report", title="Status update test",
        summary="", file_path=__file__, tags=[],
    )
    try:
        _registry.mark_artifact_status(art.artifact_id, "completed")
        ok("mark_artifact_status — no exception raised")
    except Exception as e:
        fail("mark_artifact_status", str(e))


def test_what_hermes_should_know_field():
    art = _registry.register_artifact(
        agent_name="test_agent", agent_type="test",
        source_input="", source_type="other",
        artifact_type="report", title="Hermes know test",
        summary="", file_path=__file__, tags=[],
        what_hermes_should_know="Ray should see this note",
    )
    d = art.to_dict()
    if d.get("what_hermes_should_know") == "Ray should see this note":
        ok("what_hermes_should_know — stored correctly")
    else:
        fail("what_hermes_should_know", repr(d.get("what_hermes_should_know")))


def test_registry_persists_to_jsonl():
    count_before = 0
    if _reg_mod.REGISTRY_FILE.exists():
        count_before = len([l for l in _reg_mod.REGISTRY_FILE.read_text().splitlines() if l.strip()])
    _registry.register_artifact(
        agent_name="persist_test", agent_type="test",
        source_input="", source_type="other",
        artifact_type="report", title="Persist test",
        summary="", file_path=__file__, tags=[],
    )
    count_after = len([l for l in _reg_mod.REGISTRY_FILE.read_text().splitlines() if l.strip()])
    if count_after > count_before:
        ok("registry_persists_to_jsonl — JSONL file grows on register")
    else:
        fail("registry_persists_to_jsonl", f"before={count_before}, after={count_after}")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== test_nexus_artifact_registry ===")
    test_register_basic()
    test_artifact_id_format()
    test_evidence_level_verified_file()
    test_evidence_level_unverified_claim()
    test_find_by_source_url()
    test_latest_artifacts()
    test_create_registry_summary()
    test_find_youtube_artifacts()
    test_find_agents_outputs()
    test_mark_artifact_status()
    test_what_hermes_should_know_field()
    test_registry_persists_to_jsonl()

    shutil.rmtree(_tmp, ignore_errors=True)
    _reg_mod.REGISTRY_FILE = _orig_registry_path
    _reg_mod.REGISTRY_MD   = _orig_latest_path

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
