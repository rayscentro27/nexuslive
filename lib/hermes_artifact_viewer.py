"""
hermes_artifact_viewer.py
===========================
Preview content drafts, actions, and opportunities for Telegram.
Keeps responses short enough for mobile — no raw evidence dumps.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Any

_ROOT = Path(__file__).resolve().parent.parent
_CONTENT_DIR = _ROOT / "docs" / "reports" / "content"
_CHECKLIST_SLUG = "credit_funding_readiness_checklist"

MAX_PREVIEW_CHARS = 2500
_TELEGRAM_SECTION_LIMIT = 4


def find_latest_content_draft() -> Optional[Path]:
    """Return path to the most recent checklist draft, or None."""
    if not _CONTENT_DIR.exists():
        return None
    drafts = sorted(_CONTENT_DIR.glob(f"{_CHECKLIST_SLUG}_draft_*.md"), reverse=True)
    return drafts[0] if drafts else None


def find_latest_artifact_by_type(type_name: str) -> Optional[Path]:
    if type_name == "content_draft":
        return find_latest_content_draft()
    return None


def read_artifact_preview(path: Path, max_chars: int = MAX_PREVIEW_CHARS) -> str:
    try:
        return path.read_text()
    except Exception as exc:
        return f"Could not read artifact: {exc}"


def _compress_markdown_for_telegram(content: str, max_chars: int = 1800) -> str:
    """Return a condensed Markdown preview — first 4 sections, no compliance block."""
    lines = content.splitlines()
    preview_lines: list[str] = []
    char_count = 0
    section_count = 0
    in_preamble = True  # include internal-only banner and intro

    for line in lines:
        # Stop at compliance note (always the last section we want to skip)
        if line.startswith("## ") and "compliance" in line.lower():
            preview_lines.append("\n[...compliance note and full text in file]")
            break
        # Count H2 sections
        if line.startswith("## "):
            section_count += 1
            in_preamble = False
            if section_count > _TELEGRAM_SECTION_LIMIT:
                preview_lines.append(f"\n[...{section_count - 1}+ more sections in full file]")
                break

        preview_lines.append(line)
        char_count += len(line) + 1
        if char_count >= max_chars:
            preview_lines.append("\n[...truncated — see full file for complete draft]")
            break

    return "\n".join(preview_lines)


def format_artifact_preview_response(path: Path, content: str) -> str:
    """Format a Markdown draft for display in Telegram."""
    try:
        rel_path = str(path.relative_to(_ROOT))
    except ValueError:
        rel_path = str(path)

    preview = _compress_markdown_for_telegram(content, max_chars=1800)

    return (
        "CONTENT DRAFT PREVIEW\n\n"
        + preview.strip()
        + "\n\n---\n\n"
        "Status: Internal draft only.\n\n"
        "Approval: Required before publishing, selling, or sharing with clients.\n\n"
        f"Evidence:\n{rel_path}\n\n"
        "Reply options:\n"
        "  create a new version\n"
        "  make it simpler\n"
        "  build a short video script from this"
    )


def format_action_preview_response(action: Any) -> str:
    """Format an action for display in Telegram."""
    title = (getattr(action, "title", "") or str(action))[:80]
    status = getattr(action, "status", "unknown")
    scout = (getattr(action, "assigned_scout", "") or getattr(action, "assigned_to", "") or "").strip()
    next_step = (getattr(action, "next_step", "") or "").strip()
    action_id = (getattr(action, "action_id", "") or "").strip()

    lines = [f"ACTION: {title}", "", f"Status: {status}"]
    if scout:
        lines.append(f"Scout: {scout}")
    if next_step:
        lines.append(f"Next: {next_step}")
    if action_id:
        lines.append(f"ID: {action_id}")
    lines += ["", "Evidence:", "docs/reports/actions/hermes_action_queue.jsonl"]
    return "\n".join(lines)


def format_opportunity_preview_response(opportunity: dict) -> str:
    """Format an opportunity dict for display in Telegram."""
    title = str(
        opportunity.get("title") or opportunity.get("recommended_action") or ""
    )[:80]
    why = str(opportunity.get("why_it_matters") or opportunity.get("rationale") or "")[:200]
    status = str(opportunity.get("status") or "")

    lines = [f"OPPORTUNITY: {title}"]
    if why:
        lines += ["", f"Why: {why}"]
    if status:
        lines += ["", f"Status: {status}"]
    return "\n".join(lines)
