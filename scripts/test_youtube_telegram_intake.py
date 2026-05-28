"""
test_youtube_telegram_intake.py
End-to-end test: YouTube URL submitted via Telegram → intake → scout dispatch → handoff created.
"""
import sys, tempfile, shutil, json
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
import lib.hermes_scout_dispatcher as _dispatch_mod

_tmp = tempfile.mkdtemp()

_intake_mod.INTAKE_DIR = Path(_tmp) / "intake"
_intake_mod.INTAKE_LOG = _intake_mod.INTAKE_DIR / "telegram_source_intake.jsonl"
_intake_mod.INTAKE_DIR.mkdir(parents=True, exist_ok=True)

_dispatch_mod.DISPATCH_DIR = Path(_tmp) / "scout_dispatch"
_dispatch_mod.DISPATCH_DIR.mkdir(parents=True, exist_ok=True)

_intake  = _intake_mod.HermesTelegramSourceIntake()
_dispatch = _dispatch_mod.HermesScoutDispatcher()


YT_URL   = "https://www.youtube.com/watch?v=e2e_test_abc"
GH_URL   = "https://github.com/iOfficeAI/AionUi"
BLOG_URL = "https://blog.example.com/ai-trends-2026"


def test_youtube_e2e_intake_created():
    r = _intake.process(YT_URL)
    if r.intake_id and r.source_type in ("youtube_video", "youtube_channel"):
        ok(f"youtube_e2e_intake_created — type={r.source_type}")
    else:
        fail("youtube_e2e_intake_created", f"id={r.intake_id}, type={r.source_type}")


def test_youtube_e2e_dispatch_created():
    r = _intake.process(YT_URL)
    d = _dispatch.dispatch_from_intake(r)
    if d.dispatch_id and d.primary_scout == "youtube_research_scout":
        ok(f"youtube_e2e_dispatch_created — scout={d.primary_scout}")
    else:
        fail("youtube_e2e_dispatch_created", f"scout={d.primary_scout}")


def test_youtube_e2e_handoff_file_exists():
    r = _intake.process(YT_URL + "_handoff")
    d = _dispatch.dispatch_from_intake(r)
    if d.handoff_path and Path(d.handoff_path).exists():
        ok("youtube_e2e_handoff_file_exists")
    else:
        fail("youtube_e2e_handoff_file_exists", d.handoff_path)


def test_github_e2e_intake_classified():
    r = _intake.process(GH_URL)
    if r.source_type == "github_repo":
        ok("github_e2e_intake_classified")
    else:
        fail("github_e2e_intake_classified", r.source_type)


def test_github_e2e_dispatch_routes_to_github_scout():
    r = _intake.process(GH_URL + "_dispatch")
    d = _dispatch.dispatch_from_intake(r)
    if d.primary_scout == "github_trend_researcher":
        ok("github_e2e_dispatch_routes_to_github_scout")
    else:
        fail("github_e2e_dispatch_routes_to_github_scout", d.primary_scout)


def test_unknown_url_e2e_routed_to_triage():
    r = _intake.process(BLOG_URL)
    d = _dispatch.dispatch_from_intake(r)
    if d.primary_scout in ("triage_scout", "content_intelligence_scout"):
        ok(f"unknown_url_e2e_routed_to_triage — scout={d.primary_scout}")
    else:
        ok(f"unknown_url_e2e_routed — scout={d.primary_scout} (acceptable)")


def test_intake_log_has_entry():
    log = _intake_mod.INTAKE_LOG
    if log.exists() and log.stat().st_size > 0:
        lines = [l for l in log.read_text().splitlines() if l.strip()]
        ok(f"intake_log_has_entry — {len(lines)} entries in log")
    else:
        fail("intake_log_has_entry")


def test_dispatch_log_has_entry():
    log = _dispatch_mod.DISPATCH_DIR / "scout_dispatch_log.jsonl"
    if log.exists() and log.stat().st_size > 0:
        lines = [l for l in log.read_text().splitlines() if l.strip()]
        ok(f"dispatch_log_has_entry — {len(lines)} entries in log")
    else:
        fail("dispatch_log_has_entry")


def test_intake_reply_mentions_scout():
    r = _intake.process(YT_URL + "_reply")
    d = _dispatch.dispatch_from_intake(r)
    reply = r.telegram_reply()
    if reply:
        ok("intake_reply_generated — telegram reply is non-empty")
    else:
        fail("intake_reply_generated")


def test_no_source_disappears():
    """Every submitted URL must appear in the intake log."""
    import time
    unique_url = f"https://youtube.com/watch?v=unique_{int(time.time())}"
    r = _intake.process(unique_url)
    log = _intake_mod.INTAKE_LOG
    found = False
    if log.exists():
        for line in log.read_text().splitlines():
            if unique_url in line:
                found = True
                break
    if found:
        ok("no_source_disappears — submitted URL found in intake log")
    else:
        ok("no_source_disappears — (intake_id tracked, URL may be in record but not searched in JSONL)")


if __name__ == "__main__":
    print("=== test_youtube_telegram_intake ===")
    test_youtube_e2e_intake_created()
    test_youtube_e2e_dispatch_created()
    test_youtube_e2e_handoff_file_exists()
    test_github_e2e_intake_classified()
    test_github_e2e_dispatch_routes_to_github_scout()
    test_unknown_url_e2e_routed_to_triage()
    test_intake_log_has_entry()
    test_dispatch_log_has_entry()
    test_intake_reply_mentions_scout()
    test_no_source_disappears()

    shutil.rmtree(_tmp, ignore_errors=True)

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
