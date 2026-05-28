"""
test_youtube_intelligence_extractor.py
=========================================
Tests for lib/youtube_intelligence_extractor.py
"""
import sys
import json
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def check(desc: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  ✅ {desc}")
        PASS += 1
    else:
        print(f"  ❌ FAIL: {desc}")
        FAIL += 1


print("\n=== test_youtube_intelligence_extractor ===\n")

import lib.youtube_intelligence_extractor as _mod

with tempfile.TemporaryDirectory() as tmpdir:
    orig_reports_dir = _mod.REPORTS_DIR
    _mod.REPORTS_DIR = Path(tmpdir)

    from lib.youtube_intelligence_extractor import YouTubeIntelligenceExtractor

    extractor = YouTubeIntelligenceExtractor()

    # 1. heuristic risk flags
    risky_text = "guaranteed credit score jump overnight 100% success instant credit loophole"
    flags = extractor._heuristic_risk_flags(risky_text)
    check("guarantee detected",       "guarantee" in flags)
    check("100% success detected",    "100% success" in flags)
    check("instant credit detected",  "instant credit" in flags)
    check("loophole detected",        "loophole" in flags)

    safe_text = "step by step credit repair guide for consumers"
    safe_flags = extractor._heuristic_risk_flags(safe_text)
    check("safe text has no flags",   len(safe_flags) == 0)

    # 2. heuristic hooks
    hooks = extractor._heuristic_hooks("credit score tips for beginners")
    check("hooks is a list",          isinstance(hooks, list))
    check("hooks has 3 items",        len(hooks) == 3)
    check("hooks contain title text", any("credit score" in h.lower() for h in hooks))

    # 3. Full extraction (no LLM — uses heuristic fallback)
    bundle = extractor.extract(
        source_id="yt_extract_test",
        url="https://youtube.com/@CreditAdviser",
        channel_name="Credit Adviser",
        video_title="How to remove late payments from your credit report",
        description=(
            "Learn how to write effective dispute letters. "
            "We show step-by-step how to challenge negative items with the bureaus. "
            "No guarantees, just proven processes."
        ),
    )
    check("bundle has source_id",          bundle.source_id == "yt_extract_test")
    check("bundle has content dict",       isinstance(bundle.content, dict))
    check("bundle has monetization dict",  isinstance(bundle.monetization, dict))
    check("bundle has nexus_improvement",  isinstance(bundle.nexus_improvement, dict))
    check("bundle has compliance dict",    isinstance(bundle.compliance, dict))
    check("bundle has artifact_paths",     isinstance(bundle.artifact_paths, list))
    check("4 artifacts saved",             len(bundle.artifact_paths) == 4)
    check("report_path is set",            bool(bundle.report_path))
    check("report file exists",            Path(bundle.report_path).exists())

    # Verify each artifact JSON is valid
    for ap in bundle.artifact_paths:
        path = Path(ap)
        try:
            data = json.loads(path.read_text())
            check(f"artifact {path.name} is valid JSON with source_id",
                  "source_id" in data)
        except Exception as e:
            check(f"artifact {path.name} JSON valid", False)

    # 4. Compliance flags check
    check("has_compliance_flags returns bool",
          isinstance(bundle.has_compliance_flags(), bool))

    # 5. Risky source → compliance flags detected
    risky_bundle = extractor.extract(
        source_id="yt_risky_test",
        url="https://youtube.com/watch?v=risky",
        video_title="Guaranteed 200 point credit score increase overnight",
        description="100% success with this secret loophole. Banks hate this trick.",
    )
    check("risky source has compliance flags",
          risky_bundle.has_compliance_flags() or len(risky_bundle.compliance.get("risk_flags", [])) > 0)

    # 6. Report markdown content
    report_text = Path(bundle.report_path).read_text()
    check("report contains source ID",     bundle.source_id in report_text)
    check("report contains URL",           bundle.url in report_text)
    check("report has Content Intelligence section",    "Content Intelligence" in report_text)
    check("report has Monetization Intelligence section", "Monetization Intelligence" in report_text)
    check("report has Nexus Improvement section",       "Nexus Improvement" in report_text)
    check("report has Compliance Intelligence section", "Compliance Intelligence" in report_text)

    _mod.REPORTS_DIR = orig_reports_dir

print(f"\nResults: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
