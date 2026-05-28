"""
test_youtube_source_registry.py — Tests for lib/youtube_source_registry.py
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


print("\n=== test_youtube_source_registry ===\n")

# Use isolated tmp dir to avoid polluting real registry
with tempfile.TemporaryDirectory() as tmpdir:
    import lib.youtube_source_registry as _mod
    orig_registry_dir  = _mod.REGISTRY_DIR
    orig_registry_file = _mod.REGISTRY_FILE

    _mod.REGISTRY_DIR  = Path(tmpdir) / "youtube"
    _mod.REGISTRY_FILE = _mod.REGISTRY_DIR / "source_registry.json"

    from lib.youtube_source_registry import YouTubeSourceRegistry

    reg = YouTubeSourceRegistry()

    # 1. Register a channel
    src = reg.register(
        "https://www.youtube.com/@CreditSweep",
        "channel",
        channel_name="CreditSweep",
        submitted_by="raymond",
    )
    check("source registered",              src.source_id.startswith("yt_"))
    check("source_type is channel",         src.to_dict()["source_type"] == "channel")
    check("status is submitted",            src.status == "submitted")
    check("transcript_status not_started",  src.to_dict()["transcript_status"] == "not_started")
    check("quality_score is None",          src.to_dict()["quality_score"] is None)
    check("artifact_paths is empty list",   src.to_dict()["artifact_paths"] == [])

    # 2. Re-registering same URL returns same source_id
    src2 = reg.register(
        "https://www.youtube.com/@CreditSweep",
        "channel",
    )
    check("same URL → same source_id", src2.source_id == src.source_id)

    # 3. Register a video
    vid = reg.register(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video",
        video_title="Credit Repair 101",
    )
    check("video registered separately",    vid.source_id != src.source_id)
    check("video source_type",              vid.to_dict()["source_type"] == "video")

    # 4. Update a source
    updated = reg.update(src.source_id, status="active", quality_score=8.2)
    check("update returns record",          updated is not None)
    check("status updated to active",       updated.status == "active")
    check("quality_score updated",          updated.to_dict()["quality_score"] == 8.2)

    # 5. Add artifact
    added = reg.add_artifact(src.source_id, "/path/to/report.md")
    check("add_artifact returns True",      added)
    check("artifact in paths",
          "/path/to/report.md" in reg.get(src.source_id).to_dict()["artifact_paths"])

    # 6. find_by_url
    found = reg.find_by_url("https://www.youtube.com/@CreditSweep")
    check("find_by_url returns record",     found is not None)
    check("find_by_url correct source_id",  found.source_id == src.source_id)

    # 7. by_status
    active_sources = reg.by_status("active")
    check("by_status returns list",         isinstance(active_sources, list))
    check("active sources contain our src", any(s.source_id == src.source_id for s in active_sources))

    # 8. all() count
    all_srcs = reg.all()
    check("all() returns 2 sources",        len(all_srcs) == 2)

    # 9. needs_research includes non-rejected sources with not_started research
    needs = reg.needs_research()
    check("needs_research returns list",    isinstance(needs, list))

    # 10. pending_transcript includes sources with not_started transcript
    pending_t = reg.pending_transcript()
    check("pending_transcript returns list", isinstance(pending_t, list))

    # 11. summary_table
    table = reg.summary_table()
    check("summary_table contains header",  "| ID |" in table)
    check("summary_table contains source",  "CreditSweep" in table)

    # 12. count_by_status
    counts = reg.count_by_status()
    check("count_by_status is dict",        isinstance(counts, dict))
    check("active count is 1",              counts.get("active", 0) == 1)
    check("submitted count is 1",           counts.get("submitted", 0) == 1)

    # 13. Registry persists to JSON
    check("registry file created",          _mod.REGISTRY_FILE.exists())
    loaded = json.loads(_mod.REGISTRY_FILE.read_text())
    check("registry JSON has 2 entries",    len(loaded) == 2)

    # Restore
    _mod.REGISTRY_DIR  = orig_registry_dir
    _mod.REGISTRY_FILE = orig_registry_file

print(f"\nResults: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
