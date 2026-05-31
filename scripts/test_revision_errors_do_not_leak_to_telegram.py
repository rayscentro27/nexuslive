"""
test_revision_errors_do_not_leak_to_telegram.py
Revision command failures must never surface raw Python tracebacks to Telegram.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_bot():
    """Return a NexusTelegramBot instance with mocked Telegram."""
    import telegram_bot as tb
    bot = tb.NexusTelegramBot.__new__(tb.NexusTelegramBot)
    bot._token = "fake"
    bot._chat_id = "0"
    return bot


def test_no_import_error_reaches_telegram():
    """ImportError inside revision must produce a friendly message, not a traceback."""
    bot = _make_bot()
    with tempfile.TemporaryDirectory() as tmp:
        with patch("lib.hermes_artifact_version_compare._CONTENT_DIR",
                   Path(tmp) / "docs" / "reports" / "content"):
            result = bot._cmd_revise_draft("simplified")
    assert "cannot import name" not in result
    assert "Traceback" not in result
    assert "ImportError" not in result


def test_missing_draft_gives_friendly_message():
    """No draft on disk → friendly 'create first draft' prompt."""
    bot = _make_bot()
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        import lib.hermes_artifact_version_compare as avc
        import lib.hermes_content_revision_engine as engine
        import lib.hermes_conversation_context_resolver as ccr
        with patch.object(avc, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
            result = bot._cmd_revise_draft("simplified")
    assert "first draft" in result.lower() or "could not find" in result.lower()
    assert "Traceback" not in result
    assert "Error" not in result or "internal error" in result.lower()


def test_exception_in_revise_returns_safe_message():
    """If revise_content_draft raises unexpectedly, Telegram gets a safe message."""
    bot = _make_bot()
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000.md"
        prev.write_text("# Draft\n")
        import lib.hermes_artifact_version_compare as avc
        import lib.hermes_content_revision_engine as engine
        import lib.hermes_conversation_context_resolver as ccr
        with patch.object(avc, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "revise_content_draft", side_effect=RuntimeError("boom")), \
             patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
            result = bot._cmd_revise_draft("simplified")
    assert "Traceback" not in result
    assert "RuntimeError" not in result
    assert "internal error" in result.lower()


def test_no_raw_traceback_in_any_revision_type():
    """All revision types handle errors gracefully."""
    bot = _make_bot()
    import lib.hermes_artifact_version_compare as avc
    import lib.hermes_content_revision_engine as engine
    import lib.hermes_conversation_context_resolver as ccr
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        with patch.object(avc, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
            for rev_type in ["simplified", "professional", "lead_magnet",
                             "short_video_script", "newsletter", "email_draft"]:
                result = bot._cmd_revise_draft(rev_type)
                assert "Traceback" not in result, f"Traceback in {rev_type}: {result[:100]}"
                assert "cannot import name" not in result, f"ImportError in {rev_type}"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(failed)
