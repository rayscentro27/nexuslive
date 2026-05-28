"""
test_youtube_evidence_gating.py
=================================
Verify that YouTube/research queries cite real source registry entries
and do not fabricate channel names, counts, or transcript statuses.
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


print("\n=== test_youtube_evidence_gating ===\n")

import hermes_command_router.router as _router

# 1. No registry file → reports artifact_missing
with tempfile.TemporaryDirectory() as tmpdir:
    orig_root = _router._nexus_ai_root
    _router._nexus_ai_root = lambda: tmpdir

    status, evidence, rec = _router._run_youtube_source_status()
    check("no registry → unknown status",     status == "unknown")
    check("no registry → artifact_missing",   any("artifact_missing" in e or "no youtube" in e.lower() for e in evidence))
    check("no registry → suggests run command", "run_youtube_source_reconciliation" in rec.lower() or "reconciliation" in rec.lower())

    _router._nexus_ai_root = orig_root

# 2. Empty registry → reports no sources
with tempfile.TemporaryDirectory() as tmpdir:
    registry_dir = Path(tmpdir) / "docs" / "reports" / "youtube"
    registry_dir.mkdir(parents=True)
    (registry_dir / "source_registry.json").write_text("{}")

    orig_root = _router._nexus_ai_root
    _router._nexus_ai_root = lambda: tmpdir

    status2, evidence2, _ = _router._run_youtube_source_status()
    check("empty registry → unknown status",  status2 == "unknown")
    check("empty registry → no sources msg",  any("no sources" in e.lower() for e in evidence2))

    _router._nexus_ai_root = orig_root

# 3. Registry with 2 sources → reports counts from real file
with tempfile.TemporaryDirectory() as tmpdir:
    registry_dir = Path(tmpdir) / "docs" / "reports" / "youtube"
    registry_dir.mkdir(parents=True)
    sources = {
        "yt_abc123": {
            "source_id": "yt_abc123",
            "url": "https://youtube.com/@CreditPro",
            "channel_name": "CreditPro",
            "source_type": "channel",
            "status": "active",
            "transcript_status": "downloaded",
            "quality_score": 8.5,
            "research_status": "complete",
            "artifact_paths": ["/path/report.md"],
        },
        "yt_def456": {
            "source_id": "yt_def456",
            "url": "https://youtube.com/watch?v=xyz",
            "channel_name": "",
            "video_title": "Dispute Letters That Work",
            "source_type": "video",
            "status": "submitted",
            "transcript_status": "not_started",
            "quality_score": None,
            "research_status": "not_started",
            "artifact_paths": [],
        },
    }
    (registry_dir / "source_registry.json").write_text(json.dumps(sources))

    orig_root = _router._nexus_ai_root
    _router._nexus_ai_root = lambda: tmpdir

    status3, evidence3, rec3 = _router._run_youtube_source_status()
    check("populated registry → healthy status",  status3 == "healthy")
    check("evidence contains status counts",       any("active" in e or "submitted" in e for e in evidence3))
    check("evidence lists active source ID",       any("yt_abc123"[:8] in e or "CreditPro" in e for e in evidence3))
    check("total count mentioned in recommendation", "2" in rec3)
    check("next step mentioned",                   "intelligence" in rec3.lower() or "run" in rec3.lower())

    _router._nexus_ai_root = orig_root

# 4. Evidence mode CLAIM_EVIDENCE_MAP has youtube entry
from lib.hermes_evidence_mode import CLAIM_EVIDENCE_MAP
check("youtube_processed in CLAIM_EVIDENCE_MAP", "youtube_processed" in CLAIM_EVIDENCE_MAP)
check("youtube source_registry.json in patterns",
      any("source_registry.json" in p for p in CLAIM_EVIDENCE_MAP["youtube_processed"]))

print(f"\nResults: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
