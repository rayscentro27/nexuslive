"""
test_hermes_scout_dispatcher.py
Test HermesScoutDispatcher — routing, handoff creation, approval gates.
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


import lib.hermes_scout_dispatcher as _mod

_tmp = tempfile.mkdtemp()
_orig_dir = _mod.DISPATCH_DIR
_mod.DISPATCH_DIR = Path(_tmp) / "scout_dispatch"
_mod.DISPATCH_DIR.mkdir(parents=True, exist_ok=True)

_dispatcher = _mod.HermesScoutDispatcher()


def test_youtube_video_routes_to_youtube_scout():
    r = _dispatcher.dispatch(
        intake_id="intake_yt_001",
        source_type="youtube_video",
        url="https://youtube.com/watch?v=abc123",
    )
    if r.primary_scout == "youtube_research_scout":
        ok("youtube_video_routes_to_youtube_scout")
    else:
        fail("youtube_video_routes_to_youtube_scout", r.primary_scout)


def test_github_repo_routes_to_github_scout():
    r = _dispatcher.dispatch(
        intake_id="intake_gh_001",
        source_type="github_repo",
        url="https://github.com/example/repo",
    )
    if r.primary_scout == "github_trend_researcher":
        ok("github_repo_routes_to_github_scout")
    else:
        fail("github_repo_routes_to_github_scout", r.primary_scout)


def test_trading_strategy_requires_approval():
    r = _dispatcher.dispatch(
        intake_id="intake_trade_001",
        source_type="trading_strategy",
        url="",
        raw_message="my trading strategy",
    )
    d = r.to_dict()
    if d.get("requires_approval") is True:
        ok("trading_strategy_requires_approval")
    else:
        fail("trading_strategy_requires_approval", repr(d.get("requires_approval")))


def test_trading_strategy_status_needs_review():
    r = _dispatcher.dispatch(
        intake_id="intake_trade_002",
        source_type="trading_strategy",
        url="",
    )
    if r.status == "needs_ray_review":
        ok("trading_strategy_status_needs_review")
    else:
        fail("trading_strategy_status_needs_review", r.status)


def test_youtube_video_status_queued():
    r = _dispatcher.dispatch(
        intake_id="intake_yt_002",
        source_type="youtube_video",
        url="https://youtube.com/watch?v=queued_test",
    )
    if r.status == "queued":
        ok("youtube_video_status_queued")
    else:
        fail("youtube_video_status_queued", r.status)


def test_dispatch_id_generated():
    r = _dispatcher.dispatch(
        intake_id="intake_id_001",
        source_type="youtube_video",
        url="https://youtube.com/watch?v=id_test",
    )
    if r.dispatch_id.startswith("dsp_"):
        ok("dispatch_id_generated — starts with dsp_")
    else:
        fail("dispatch_id_generated", r.dispatch_id)


def test_handoff_file_created():
    r = _dispatcher.dispatch(
        intake_id="intake_hf_001",
        source_type="youtube_channel",
        url="https://youtube.com/@TestChannel",
    )
    if r.handoff_path and Path(r.handoff_path).exists():
        ok("handoff_file_created — MD file exists on disk")
    else:
        fail("handoff_file_created", r.handoff_path)


def test_handoff_file_contains_scout_name():
    r = _dispatcher.dispatch(
        intake_id="intake_hf_002",
        source_type="youtube_video",
        url="https://youtube.com/watch?v=scout_name",
    )
    content = Path(r.handoff_path).read_text()
    if "youtube_research_scout" in content:
        ok("handoff_file_contains_scout_name")
    else:
        fail("handoff_file_contains_scout_name", content[:200])


def test_handoff_file_contains_completion_contract():
    r = _dispatcher.dispatch(
        intake_id="intake_cc_001",
        source_type="github_repo",
        url="https://github.com/example/test",
    )
    content = Path(r.handoff_path).read_text()
    if "Completion Contract" in content or "artifact" in content.lower():
        ok("handoff_file_contains_completion_contract")
    else:
        fail("handoff_file_contains_completion_contract")


def test_unknown_source_type_routes_to_triage():
    r = _dispatcher.dispatch(
        intake_id="intake_unk_001",
        source_type="unknown_xyz",
        url="https://example.com/unknown",
    )
    if r.primary_scout == "triage_scout":
        ok("unknown_source_type_routes_to_triage")
    else:
        fail("unknown_source_type_routes_to_triage", r.primary_scout)


def test_log_appended():
    log = _mod.DISPATCH_DIR / "scout_dispatch_log.jsonl"
    before = 0
    if log.exists():
        before = len([l for l in log.read_text().splitlines() if l.strip()])
    _dispatcher.dispatch(intake_id="intake_log_001", source_type="grant", url="")
    after = len([l for l in log.read_text().splitlines() if l.strip()])
    if after > before:
        ok("log_appended — JSONL grows on dispatch()")
    else:
        fail("log_appended", f"before={before}, after={after}")


def test_pending_dispatches_returns_list():
    result = _dispatcher.pending_dispatches()
    if isinstance(result, list):
        ok(f"pending_dispatches_returns_list — len={len(result)}")
    else:
        fail("pending_dispatches_returns_list")


def test_get_dispatch_for_intake():
    intake_id = "intake_find_me_001"
    r = _dispatcher.dispatch(
        intake_id=intake_id,
        source_type="article",
        url="https://example.com/article",
    )
    found = _dispatcher.get_dispatch_for_intake(intake_id)
    if found and found.dispatch_id == r.dispatch_id:
        ok("get_dispatch_for_intake — found by intake_id")
    else:
        fail("get_dispatch_for_intake", f"expected {r.dispatch_id}, got {getattr(found, 'dispatch_id', None)}")


def test_to_dict_has_required_keys():
    r = _dispatcher.dispatch(
        intake_id="intake_dict_001",
        source_type="youtube_video",
        url="https://youtube.com/watch?v=dict_test",
    )
    d = r.to_dict()
    required = {"dispatch_id", "intake_id", "source_type", "primary_scout", "status"}
    missing = required - set(d.keys())
    if not missing:
        ok("to_dict_has_required_keys")
    else:
        fail("to_dict_has_required_keys", f"missing: {missing}")


if __name__ == "__main__":
    print("=== test_hermes_scout_dispatcher ===")
    test_youtube_video_routes_to_youtube_scout()
    test_github_repo_routes_to_github_scout()
    test_trading_strategy_requires_approval()
    test_trading_strategy_status_needs_review()
    test_youtube_video_status_queued()
    test_dispatch_id_generated()
    test_handoff_file_created()
    test_handoff_file_contains_scout_name()
    test_handoff_file_contains_completion_contract()
    test_unknown_source_type_routes_to_triage()
    test_log_appended()
    test_pending_dispatches_returns_list()
    test_get_dispatch_for_intake()
    test_to_dict_has_required_keys()

    shutil.rmtree(_tmp, ignore_errors=True)
    _mod.DISPATCH_DIR = _orig_dir

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
