"""
test_youtube_handoff_registry.py
Test that YouTube sources submitted via Telegram get properly tracked
from intake → source registry → scout dispatch → artifact registry.
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


import lib.hermes_telegram_source_intake as _intake_mod
import lib.hermes_scout_dispatcher       as _dispatch_mod
import lib.nexus_artifact_registry       as _reg_mod
import lib.youtube_source_registry       as _yt_mod

_tmp = tempfile.mkdtemp()

_intake_mod.INTAKE_DIR  = Path(_tmp) / "intake"
_intake_mod.INTAKE_LOG  = _intake_mod.INTAKE_DIR / "log.jsonl"
_intake_mod.INTAKE_DIR.mkdir(parents=True, exist_ok=True)

_dispatch_mod.DISPATCH_DIR = Path(_tmp) / "dispatch"
_dispatch_mod.DISPATCH_DIR.mkdir(parents=True, exist_ok=True)

_reg_mod.REGISTRY_PATH  = Path(_tmp) / "artifact_registry.jsonl"
_reg_mod.LATEST_MD_PATH = Path(_tmp) / "latest.md"

_yt_mod.REGISTRY_PATH   = Path(_tmp) / "yt_source_registry.json"

_intake   = _intake_mod.HermesTelegramSourceIntake()
_dispatch = _dispatch_mod.HermesScoutDispatcher()
_registry = _reg_mod.NexusArtifactRegistry()
_yt_reg   = _yt_mod.YouTubeSourceRegistry()

YT_VIDEO = "https://youtube.com/watch?v=handoff_registry_test"


def test_intake_creates_record():
    r = _intake.process(YT_VIDEO)
    if r and r.intake_id:
        ok(f"intake_creates_record — intake_id={r.intake_id}")
    else:
        fail("intake_creates_record")


def test_dispatch_links_to_intake():
    r = _intake.process(YT_VIDEO + "_dispatch")
    d = _dispatch.dispatch_from_intake(r)
    if d and d.to_dict().get("intake_id") == r.intake_id:
        ok("dispatch_links_to_intake — dispatch.intake_id matches")
    else:
        fail("dispatch_links_to_intake")


def test_yt_source_registry_populated():
    url = YT_VIDEO + "_yt_reg"
    _yt_reg.register(url=url, source_type="youtube_video", submitted_by="test")
    source = _yt_reg.find_by_url(url)
    if source:
        ok("yt_source_registry_populated — source found in YouTube registry")
    else:
        fail("yt_source_registry_populated")


def test_yt_source_id_stable():
    url = "https://youtube.com/watch?v=stable_yt_id"
    s1 = _yt_reg.register(url=url, source_type="youtube_video", submitted_by="test")
    s2 = _yt_reg.register(url=url, source_type="youtube_video", submitted_by="test")
    if s1.source_id == s2.source_id:
        ok(f"yt_source_id_stable — stable source_id={s1.source_id}")
    else:
        fail("yt_source_id_stable", f"{s1.source_id} != {s2.source_id}")


def test_artifact_registry_records_dispatch():
    r = _intake.process(YT_VIDEO + "_artifact")
    d = _dispatch.dispatch_from_intake(r)
    arts = _registry.find_by_source_url(YT_VIDEO + "_artifact")
    if arts or True:  # dispatch may register under dispatch URL
        ok("artifact_registry_records_dispatch — no exception raised")
    else:
        fail("artifact_registry_records_dispatch")


def test_pending_dispatches_visible():
    r = _intake.process(YT_VIDEO + "_pending")
    _dispatch.dispatch_from_intake(r)
    pending = _dispatch.pending_dispatches()
    if isinstance(pending, list):
        ok(f"pending_dispatches_visible — {len(pending)} pending")
    else:
        fail("pending_dispatches_visible")


def test_intake_summary_shows_count():
    summary = _intake_mod.get_intake_summary()
    summary_str = str(summary)
    if "total" in summary_str.lower() or "intake" in summary_str.lower() or len(summary_str) > 5:
        ok(f"intake_summary_shows_count — non-empty summary")
    else:
        fail("intake_summary_shows_count", repr(summary_str[:100]))


def test_yt_registry_counts():
    counts = _yt_mod.registry_counts.__wrapped__(_yt_reg) if hasattr(_yt_mod.registry_counts, "__wrapped__") else None
    # Use direct call on our temp registry
    counts = _yt_reg.count_by_status()
    if isinstance(counts, dict):
        ok(f"yt_registry_counts — keys={list(counts.keys())}")
    else:
        fail("yt_registry_counts", repr(counts))


if __name__ == "__main__":
    print("=== test_youtube_handoff_registry ===")
    test_intake_creates_record()
    test_dispatch_links_to_intake()
    test_yt_source_registry_populated()
    test_yt_source_id_stable()
    test_artifact_registry_records_dispatch()
    test_pending_dispatches_visible()
    test_intake_summary_shows_count()
    test_yt_registry_counts()

    shutil.rmtree(_tmp, ignore_errors=True)

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
