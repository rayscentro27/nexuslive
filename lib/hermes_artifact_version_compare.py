"""
hermes_artifact_version_compare.py
Compare two checklist draft versions and format a concise Telegram summary.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
_CONTENT_DIR = _ROOT / "docs" / "reports" / "content"
_CHECKLIST_SLUG = "credit_funding_readiness_checklist"


def find_prior_artifact_version(current_path: Path, artifact_type: str = "content_draft") -> Optional[Path]:
    """Return the second-newest draft file, or None if no prior version exists."""
    if artifact_type != "content_draft":
        return None
    if not _CONTENT_DIR.exists():
        return None
    drafts = sorted(_CONTENT_DIR.glob(f"{_CHECKLIST_SLUG}_draft_*.md"), reverse=True)
    for d in drafts:
        if d.resolve() != current_path.resolve():
            return d
    return None


def find_two_latest_drafts() -> tuple[Optional[Path], Optional[Path]]:
    """Return (latest, previous) paths. Either may be None."""
    if not _CONTENT_DIR.exists():
        return None, None
    drafts = sorted(_CONTENT_DIR.glob(f"{_CHECKLIST_SLUG}_draft_*.md"), reverse=True)
    latest = drafts[0] if len(drafts) >= 1 else None
    previous = drafts[1] if len(drafts) >= 2 else None
    return latest, previous


def find_latest_checklist_draft() -> Optional[Path]:
    """Return the single newest checklist draft path, or None."""
    latest, _ = find_two_latest_drafts()
    return latest


def find_latest_checklist_draft_pair() -> tuple[Optional[Path], Optional[Path]]:
    """Return (previous, latest) for comparison. Either may be None."""
    latest, previous = find_two_latest_drafts()
    return previous, latest


def _extract_sections(text: str) -> dict[str, str]:
    """Return {section_title: section_body} for all ## sections."""
    sections: dict[str, str] = {}
    current_title: Optional[str] = None
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_title is not None:
                sections[current_title] = "\n".join(current_lines).strip()
            current_title = line[3:].strip()
            current_lines = []
        else:
            if current_title is not None:
                current_lines.append(line)
    if current_title is not None:
        sections[current_title] = "\n".join(current_lines).strip()
    return sections


def summarize_markdown_changes(previous_text: str, current_text: str) -> dict:
    """Return a structured summary of section-level changes between two markdown docs."""
    prev_sections = _extract_sections(previous_text)
    curr_sections = _extract_sections(current_text)

    added = [t for t in curr_sections if t not in prev_sections]
    removed = [t for t in prev_sections if t not in curr_sections]
    changed = [
        t for t in curr_sections
        if t in prev_sections and curr_sections[t] != prev_sections[t]
    ]
    unchanged = [
        t for t in curr_sections
        if t in prev_sections and curr_sections[t] == prev_sections[t]
    ]

    compliance_changed = any("compliance" in t.lower() for t in changed)
    compliance_unchanged = any("compliance" in t.lower() for t in unchanged)

    prev_items = len(re.findall(r"- \[[ x]\]", previous_text, re.IGNORECASE))
    curr_items = len(re.findall(r"- \[[ x]\]", current_text, re.IGNORECASE))

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "compliance_changed": compliance_changed,
        "compliance_unchanged": compliance_unchanged,
        "prev_item_count": prev_items,
        "curr_item_count": curr_items,
        "total_sections_prev": len(prev_sections),
        "total_sections_curr": len(curr_sections),
    }


def compare_text_artifacts(previous_path: Path, current_path: Path) -> dict:
    """Read both files and return a changes summary dict."""
    try:
        prev_text = previous_path.read_text()
    except Exception as exc:
        return {"error": f"Could not read previous draft: {exc}"}
    try:
        curr_text = current_path.read_text()
    except Exception as exc:
        return {"error": f"Could not read current draft: {exc}"}

    changes = summarize_markdown_changes(prev_text, curr_text)
    changes["previous_path"] = str(previous_path)
    changes["current_path"] = str(current_path)
    return changes


def format_version_comparison_response(
    previous_path: Optional[Path],
    current_path: Optional[Path],
    changes: Optional[dict] = None,
) -> str:
    """Format a draft version comparison for Telegram display."""
    if previous_path is None:
        return (
            "I only found one draft version, so there is nothing to compare yet.\n\n"
            "Say 'create a new version' and then 'what changed?' to see a comparison."
        )
    if current_path is None:
        return "Could not find the latest draft to compare."

    if changes is None:
        changes = compare_text_artifacts(previous_path, current_path)

    if "error" in changes:
        return f"Could not compare drafts: {changes['error']}"

    try:
        prev_rel = str(previous_path.relative_to(_ROOT))
    except ValueError:
        prev_rel = str(previous_path)
    try:
        curr_rel = str(current_path.relative_to(_ROOT))
    except ValueError:
        curr_rel = str(current_path)

    lines = [
        "DRAFT VERSION CHANGES",
        "",
        "I compared the latest checklist draft with the previous version.",
        "",
        "Main changes:",
        "",
    ]

    change_items: list[str] = []
    for t in changes.get("added", []):
        change_items.append(f"Added: {t}")
    for t in changes.get("changed", []):
        change_items.append(f"Updated: {t}")
    for t in changes.get("removed", []):
        change_items.append(f"Removed: {t}")

    prev_items = changes.get("prev_item_count", 0)
    curr_items = changes.get("curr_item_count", 0)
    if curr_items != prev_items:
        delta = abs(curr_items - prev_items)
        direction = "added" if curr_items > prev_items else "reduced"
        change_items.append(f"Checklist items: {prev_items} → {curr_items} ({direction} {delta})")

    if changes.get("compliance_changed"):
        change_items.append("Compliance note: updated")
    elif changes.get("compliance_unchanged"):
        change_items.append("Compliance note: unchanged")

    if not change_items:
        change_items.append("No structural changes detected between versions.")

    for i, item in enumerate(change_items, 1):
        lines.append(f"{i}. {item}")

    lines += [
        "",
        "My read:",
        "This version preserves the same structure. "
        "Say 'make it simpler' or 'make it more professional' to push it further.",
        "",
        "Evidence:",
        f"- Previous: {prev_rel}",
        f"- Latest: {curr_rel}",
        "",
        "Next:",
        "You can say:",
        "  show it",
        "  make it simpler",
        "  make it more professional",
        "  turn it into a lead magnet",
        "  create a short video script from this",
    ]

    return "\n".join(lines)
