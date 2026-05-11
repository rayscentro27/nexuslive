"""
content_variant_generator_test.py — Unit tests for draft-only content variant generation.

Run:
    python3 /Users/raymonddavis/nexus-ai/lib/content_variant_generator_test.py

No external dependencies. No network calls. No database writes.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.content_variant_generator as mod

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    _results.append((name, condition, detail))


def _sample_topic() -> dict:
    return {
        "id": "topic-001",
        "campaign_id": "campaign-abc",
        "slug": "fundable-first",
        "topic": "Why founders should get fundable before applying",
        "theme": "fundability timing",
    }


def test_build_variant_schema():
    variant = mod.build_variant(_sample_topic(), "tiktok")
    required = {
        "topic_id", "campaign_id", "platform", "hook", "script", "caption",
        "hashtags", "cta", "compliance_notes", "status", "created_by",
    }
    check("build_variant includes required fields", required.issubset(variant.keys()), f"keys={sorted(variant.keys())}")
    check("build_variant uses pending_review status", variant["status"] == "pending_review", f"status={variant['status']}")
    check("build_variant uses generator created_by", variant["created_by"] == "content_variant_generator", f"created_by={variant['created_by']}")
    banned = ("guarantee", "guaranteed approval", "instant approval", "credit repair", "income")
    script_l = f"{variant['hook']} {variant['script']} {variant['caption']} {variant['cta']}".lower()
    check("build_variant avoids banned promises", not any(term in script_l for term in banned), script_l)


def test_dry_run_creates_no_records():
    calls: list[tuple[str, str]] = []
    mod._column_supported.cache_clear()

    def fake_rest_select(path: str, **_):
        calls.append(("select", path))
        if path.startswith("content_topics?"):
            return [_sample_topic()]
        if path.startswith("content_variants?"):
            return []
        return []

    def fake_supabase_request(path: str, **_):
        calls.append(("write", path))
        raise AssertionError("dry-run should not write to Supabase")

    old_rest_select = mod.rest_select
    old_supabase_request = mod.supabase_request
    mod.rest_select = fake_rest_select
    mod.supabase_request = fake_supabase_request
    try:
        report = mod.generate_content_variants(limit=1, dry_run=True)
    finally:
        mod.rest_select = old_rest_select
        mod.supabase_request = old_supabase_request

    check("dry-run reports zero created variants", report["variants_created"] == 0, f"created={report['variants_created']}")
    check("dry-run previews variants", len(report["preview_variants"]) == 3, f"preview_count={len(report['preview_variants'])}")
    check("dry-run performs no writes", not any(kind == "write" for kind, _ in calls), f"calls={calls}")


def test_duplicate_protection_skips_existing():
    writes: list[str] = []
    mod._column_supported.cache_clear()

    def fake_rest_select(path: str, **_):
        if path.startswith("content_topics?"):
            return [_sample_topic()]
        if "platform=eq.TikTok" in path:
            return [{"id": "variant-existing-1", "platform": "TikTok", "topic_id": "topic-001", "status": "pending_review"}]
        return []

    def fake_supabase_request(path: str, **_):
        writes.append(path)
        return ([{"id": "new-id"}], {})

    old_rest_select = mod.rest_select
    old_supabase_request = mod.supabase_request
    mod.rest_select = fake_rest_select
    mod.supabase_request = fake_supabase_request
    try:
        report = mod.generate_content_variants(limit=1, dry_run=False, platform="TikTok")
    finally:
        mod.rest_select = old_rest_select
        mod.supabase_request = old_supabase_request

    check("duplicate protection increments skipped count", report["duplicates_skipped"] == 1, f"skipped={report['duplicates_skipped']}")
    check("duplicate protection creates no duplicate row", report["variants_created"] == 0, f"created={report['variants_created']}")
    check("duplicate protection avoids writes", writes == [], f"writes={writes}")


def test_live_run_creates_draft_only_variant():
    writes: list[tuple[str, dict]] = []
    mod._column_supported.cache_clear()

    def fake_rest_select(path: str, **_):
        if path.startswith("content_topics?"):
            return [_sample_topic()]
        if path.startswith("content_variants?select=id,status,platform,topic_id"):
            return []
        if path.startswith("content_variants?select=campaign_id&limit=0"):
            return []
        if path.startswith("content_variants?select=hashtags&limit=0"):
            return []
        if path.startswith("content_variants?select=cta&limit=0"):
            return []
        if path.startswith("content_variants?select=created_by&limit=0"):
            return []
        if path.startswith("content_approvals?"):
            return []
        return []

    def fake_table_exists(table: str) -> bool:
        return table == "content_approvals"

    def fake_supabase_request(path: str, method: str = "GET", body=None, **_):
        writes.append((path, body or {}))
        if path == "content_variants":
            return ([{"id": "variant-123", "status": "pending_review"}], {})
        if path == "content_approvals":
            return ([{"id": "approval-123"}], {})
        raise AssertionError(f"unexpected write path: {path}")

    old_rest_select = mod.rest_select
    old_supabase_request = mod.supabase_request
    old_table_exists = mod.table_exists
    mod.rest_select = fake_rest_select
    mod.supabase_request = fake_supabase_request
    mod.table_exists = fake_table_exists
    try:
        report = mod.generate_content_variants(limit=1, dry_run=False, platform="YouTube Shorts")
    finally:
        mod.rest_select = old_rest_select
        mod.supabase_request = old_supabase_request
        mod.table_exists = old_table_exists

    check("live run creates one variant", report["variants_created"] == 1, f"created={report['variants_created']}")
    check("live run posts no messages", report["messages_sent_count"] == 0, f"messages={report['messages_sent_count']}")
    check("live run schedules nothing", report["scheduled_count"] == 0, f"scheduled={report['scheduled_count']}")
    check("live run writes content variant row", any(path == "content_variants" for path, _ in writes), f"writes={writes}")
    check("live run writes approval row", any(path == "content_approvals" for path, _ in writes), f"writes={writes}")
    check(
        "live run never writes content_calendar or message tables",
        not any(path in {"content_calendar", "dm_messages", "message_logs"} for path, _ in writes),
        f"writes={writes}",
    )


def main() -> int:
    test_build_variant_schema()
    test_dry_run_creates_no_records()
    test_duplicate_protection_skips_existing()
    test_live_run_creates_draft_only_variant()

    failed = [name for name, ok, _ in _results if not ok]
    print()
    if failed:
        print(f"{len(failed)} test(s) failed")
        for name in failed:
            print(f" - {name}")
        return 1
    print(f"All {len(_results)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
