"""
test_telegram_source_intake.py
Test HermesTelegramSourceIntake — URL classification, registration, dedup, Telegram reply.
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


import lib.hermes_telegram_source_intake as _mod

_tmp = tempfile.mkdtemp()
_orig_log   = _mod.INTAKE_LOG
_orig_dir   = _mod.INTAKE_DIR
_mod.INTAKE_DIR = Path(_tmp) / "intake"
_mod.INTAKE_LOG = _mod.INTAKE_DIR / "telegram_source_intake.jsonl"
_mod.INTAKE_DIR.mkdir(parents=True, exist_ok=True)

_intake = _mod.HermesTelegramSourceIntake()


def test_youtube_video_classified():
    r = _intake.process("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    if r.source_type in ("youtube_video", "youtube_channel"):
        ok(f"youtube_video_classified — type={r.source_type}")
    else:
        fail("youtube_video_classified", r.source_type)


def test_youtube_channel_classified():
    r = _intake.process("https://www.youtube.com/@SomeChannel")
    if r.source_type == "youtube_channel":
        ok("youtube_channel_classified")
    else:
        fail("youtube_channel_classified", r.source_type)


def test_github_repo_classified():
    r = _intake.process("https://github.com/anthropics/anthropic-sdk-python")
    if r.source_type == "github_repo":
        ok("github_repo_classified")
    else:
        fail("github_repo_classified", r.source_type)


def test_unknown_url_classified():
    r = _intake.process("https://somerandomblog.com/article/2026/01/01/example")
    if r.source_type:
        ok(f"unknown_url_classified — type={r.source_type}")
    else:
        fail("unknown_url_classified")


def test_intake_id_generated():
    r = _intake.process("https://youtube.com/watch?v=test_id_gen")
    if r.intake_id and len(r.intake_id) > 4:
        ok("intake_id_generated")
    else:
        fail("intake_id_generated", repr(r.intake_id))


def test_url_extracted():
    r = _intake.process("Check out this video: https://youtube.com/watch?v=abc123 thoughts?")
    if r.url and "youtube.com" in r.url:
        ok("url_extracted — URL extracted from message text")
    else:
        fail("url_extracted", repr(r.url))


def test_telegram_reply_not_empty():
    r = _intake.process("https://youtube.com/watch?v=reply_test")
    reply = r.telegram_reply()
    if reply and len(reply) > 10:
        ok("telegram_reply_not_empty")
    else:
        fail("telegram_reply_not_empty", repr(reply))


def test_telegram_reply_contains_source_type():
    r = _intake.process("https://youtube.com/watch?v=reply_type")
    reply = r.telegram_reply()
    if r.source_type in reply or "youtube" in reply.lower():
        ok("telegram_reply_contains_source_type")
    else:
        fail("telegram_reply_contains_source_type", reply[:200])


def test_log_appended():
    log = _mod.INTAKE_LOG
    before = 0
    if log.exists():
        before = len([l for l in log.read_text().splitlines() if l.strip()])
    _intake.process("https://youtube.com/watch?v=log_test")
    after = len([l for l in log.read_text().splitlines() if l.strip()])
    if after > before:
        ok("log_appended — JSONL grows on process()")
    else:
        fail("log_appended", f"before={before}, after={after}")


def test_to_dict_has_required_keys():
    r = _intake.process("https://youtube.com/watch?v=dict_test")
    d = r.to_dict()
    required = {"intake_id", "source_type", "url", "status", "submitted_at"}
    missing = required - set(d.keys())
    if not missing:
        ok("to_dict_has_required_keys")
    else:
        fail("to_dict_has_required_keys", f"missing: {missing}")


def test_plain_text_no_url_handled():
    r = _intake.process("Hello Hermes, how are you today?")
    if r.source_type == "text_message" or r.url == "":
        ok("plain_text_no_url_handled — graceful for plain messages")
    else:
        fail("plain_text_no_url_handled", f"type={r.source_type}, url={r.url!r}")


def test_get_recent_intakes_returns_list():
    result = _mod.get_recent_intakes(limit=5)
    if isinstance(result, list):
        ok(f"get_recent_intakes_returns_list — len={len(result)}")
    else:
        fail("get_recent_intakes_returns_list")


def test_get_intake_summary_has_total():
    summary = _mod.get_intake_summary()
    summary_str = str(summary)
    if "total" in summary_str.lower() or "intake" in summary_str.lower():
        ok(f"get_intake_summary_has_total — summary contains count info")
    else:
        fail("get_intake_summary_has_total", repr(summary_str[:100]))


if __name__ == "__main__":
    print("=== test_telegram_source_intake ===")
    test_youtube_video_classified()
    test_youtube_channel_classified()
    test_github_repo_classified()
    test_unknown_url_classified()
    test_intake_id_generated()
    test_url_extracted()
    test_telegram_reply_not_empty()
    test_telegram_reply_contains_source_type()
    test_log_appended()
    test_to_dict_has_required_keys()
    test_plain_text_no_url_handled()
    test_get_recent_intakes_returns_list()
    test_get_intake_summary_has_total()

    shutil.rmtree(_tmp, ignore_errors=True)
    _mod.INTAKE_LOG = _orig_log
    _mod.INTAKE_DIR = _orig_dir

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
