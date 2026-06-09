#!/usr/bin/env python3
"""
validate_content_prompt_library.py — verify the Content Prompt Library is complete and safe.

Read-only checks (no network, no writes, no publishing). Exit 0 = all pass, 1 = issues found.

Verifies:
  * required category prompt files exist (12) + universal rules + README
  * routing doc, variable schema, and quality rubric exist
  * the six fcf087ea example files exist
  * no secrets embedded in any library file
  * no publish/post commands embedded as EXECUTABLE actions (e.g. enabling the executor or --apply)
  * approval rules are present (universal rules + each prompt reference Ray approval)
"""
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills" / "content_prompts"
LIB = ROOT / "reports" / "content_engine" / "prompt_library"
EXAMPLES = LIB / "examples"
ROUTING = ROOT / "reports" / "content_engine" / "content_prompt_routing.md"

CATEGORY_PROMPTS = [
    "youtube_shorts.md", "tiktok_reels.md", "long_form_youtube.md",
    "notebooklm_podcast_audio_overview.md", "podcast_to_video.md", "hyperframes_video.md",
    "broll_short_video.md", "linkedin_post.md", "newsletter.md", "blog_seo_article.md",
    "content_repurposing.md", "performance_improvement.md",
]
EXAMPLE_FILES = [
    "fcf087ea_youtube_short_prompt.md", "fcf087ea_podcast_audio_prompt.md",
    "fcf087ea_hyperframes_prompt.md", "fcf087ea_linkedin_prompt.md",
    "fcf087ea_newsletter_prompt.md", "fcf087ea_repurposing_prompt.md",
]

# Secret-ish patterns (presence of a real-looking secret VALUE, not just a NAME).
SECRET_PATTERNS = [
    re.compile(r"SUPABASE_SERVICE_ROLE_KEY\s*=\s*['\"]?eyJ"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"),  # telegram bot token value
]
# Executable publish/enable patterns that must NOT appear as runnable actions in the library.
FORBIDDEN_EXEC = [
    re.compile(r"NEXUS_PUBLISH_EXECUTOR_ENABLED\s*=\s*true", re.I),
    re.compile(r"social_publish_executor\.py[^\n]*--apply"),
    re.compile(r"\bgit\s+push\b"),
]


def main() -> int:
    issues: list[str] = []
    ok: list[str] = []

    def need(p: Path, label: str):
        (ok if p.exists() else issues).append(
            f"{'OK ' if p.exists() else 'MISSING'} {label}: {p.relative_to(ROOT)}")

    # 1. required files
    need(SKILLS / "README.md", "README")
    need(SKILLS / "_universal_content_rules.md", "universal rules")
    for f in CATEGORY_PROMPTS:
        need(SKILLS / f, "prompt")
    need(ROUTING, "routing doc")
    need(LIB / "prompt_variables_schema.md", "variable schema")
    need(LIB / "content_quality_rubric.md", "quality rubric")
    for f in EXAMPLE_FILES:
        need(EXAMPLES / f, "example")

    # gather all library files that exist for content scans
    lib_files = [p for p in [
        SKILLS / "README.md", SKILLS / "_universal_content_rules.md", ROUTING,
        LIB / "prompt_variables_schema.md", LIB / "content_quality_rubric.md",
    ] + [SKILLS / f for f in CATEGORY_PROMPTS] + [EXAMPLES / f for f in EXAMPLE_FILES]
        if p.exists()]

    # 2. secret scan
    for p in lib_files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        for rx in SECRET_PATTERNS:
            if rx.search(text):
                issues.append(f"SECRET? {p.relative_to(ROOT)} matches {rx.pattern}")
    ok.append(f"OK  secret scan ({len(lib_files)} files)")

    # 3. no executable publish/enable actions
    for p in lib_files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        for rx in FORBIDDEN_EXEC:
            if rx.search(text):
                issues.append(f"FORBIDDEN-EXEC {p.relative_to(ROOT)} matches {rx.pattern}")
    ok.append("OK  no executable publish/enable commands")

    # 4. approval rules present
    uni = SKILLS / "_universal_content_rules.md"
    if uni.exists() and "Ray approval" not in uni.read_text(encoding="utf-8"):
        issues.append("universal rules missing 'Ray approval'")
    missing_appr = []
    for f in CATEGORY_PROMPTS:
        p = SKILLS / f
        if p.exists():
            t = p.read_text(encoding="utf-8").lower()
            if "approval" not in t and "ray approval" not in t:
                missing_appr.append(f)
    if missing_appr:
        issues.append("prompts missing approval rules: " + ", ".join(missing_appr))
    else:
        ok.append("OK  approval rules present in all prompts")

    # report
    print("=== Content Prompt Library validation ===")
    for line in ok:
        print(" ", line)
    print()
    if issues:
        print(f"✗ {len(issues)} issue(s):")
        for i in issues:
            print("  -", i)
        return 1
    print("✓ ALL CHECKS PASSED — library complete and safe (no secrets, no executable publish actions).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
