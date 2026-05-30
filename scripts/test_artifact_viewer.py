"""
test_artifact_viewer.py
Tests for hermes_artifact_viewer — format and compress functions.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_artifact_viewer as av


SAMPLE_MARKDOWN = """\
# Credit/Funding Readiness Checklist
*Internal Draft*

## Who This Checklist Is For

Business owners who want to apply for funding.

## 1. Business Setup Readiness

- [ ] Entity formed
- [ ] EIN obtained

## 2. Credit Profile Readiness

- [ ] Know your score

## 3. Business Banking Readiness

- [ ] Separate business account

## 4. Documentation Readiness

- [ ] Government-issued ID

## 5. Funding Red Flags

- ❌ Inconsistent business info

## Compliance Note

*This checklist is for educational purposes only.*
"""


def test_compress_stops_at_compliance():
    # With _TELEGRAM_SECTION_LIMIT=4 the section limit fires before compliance,
    # so verify the compliance body text is absent and a truncation marker is present.
    result = av._compress_markdown_for_telegram(SAMPLE_MARKDOWN)
    assert "educational purposes only" not in result, "Compliance body text leaked into preview"
    assert "[..." in result, "Expected a truncation/section-limit marker in preview"


def test_compress_limits_sections():
    result = av._compress_markdown_for_telegram(SAMPLE_MARKDOWN)
    section_count = result.count("\n## ")
    assert section_count <= av._TELEGRAM_SECTION_LIMIT


def test_compress_truncates_long_content():
    long_content = "## Section\n" + ("x " * 1000 + "\n") * 5
    result = av._compress_markdown_for_telegram(long_content, max_chars=500)
    assert "truncated" in result.lower() or len(result) <= 600


def test_format_artifact_preview_response():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "docs" / "reports" / "content" / "checklist_draft_20260530.md"
        p.parent.mkdir(parents=True)
        p.write_text(SAMPLE_MARKDOWN)
        with patch.object(av, "_ROOT", Path(tmp)):
            result = av.format_artifact_preview_response(p, SAMPLE_MARKDOWN)
            assert "CONTENT DRAFT PREVIEW" in result
            assert "Internal draft only" in result
            assert "Approval" in result
            assert "Reply options" in result


def test_find_latest_artifact_by_type_unknown():
    result = av.find_latest_artifact_by_type("unknown_type")
    assert result is None


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
