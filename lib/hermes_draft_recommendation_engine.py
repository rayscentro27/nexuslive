"""
hermes_draft_recommendation_engine.py
Evaluate a checklist draft and recommend the next best action.
No paid API. Deterministic signal-based evaluation only.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
_CONTENT_DIR = _ROOT / "docs" / "reports" / "content"
_CHECKLIST_SLUG = "credit_funding_readiness_checklist"

_REPLY_OPTIONS_BY_RECOMMENDATION: dict[str, list[str]] = {
    "lead_magnet": [
        "turn it into a lead magnet",
        "make it more professional",
        "create a short video script from this",
        "create a newsletter from this",
    ],
    "short_video_script": [
        "create a short video script from this",
        "create a newsletter from this",
        "turn it into a lead magnet",
    ],
    "approve": [
        "make it simpler",
        "make it more professional",
        "turn it into a lead magnet",
    ],
    "simplify": [
        "make it simpler",
        "clean it up",
        "make it more professional",
    ],
    "newsletter": [
        "create a newsletter from this",
        "create a short video script from this",
        "turn it into a lead magnet",
    ],
}


def evaluate_checklist_draft(path: Path) -> dict:
    """Read draft and return a structured evaluation dict."""
    try:
        text = path.read_text()
    except Exception as exc:
        return {"error": str(exc), "path": str(path)}

    is_simplified = "Simplified — Plain English Edition" in text
    is_professional = "Professional Edition" in text
    is_improved = "Improved Edition" in text
    is_cleaned = "Cleaned Edition" in text
    is_lead_magnet = "Lead Magnet Format" in text or ("Scorecard" in text and "Score Yourself" in text)
    is_video_script = "Video Script" in text or "Hook" in text
    is_newsletter = "Newsletter Format" in text
    is_email = "Email Format" in text or "Email Draft" in text

    has_start_here = bool(re.search(r"^## Start Here", text, re.MULTILINE))
    has_compliance = "educational purposes only" in text.lower() or "compliance" in text.lower()
    has_nexus_cta = "Nexus" in text
    has_scoring = bool(re.search(r"\bscore\b", text, re.IGNORECASE))

    section_count = len(re.findall(r"^## ", text, re.MULTILINE))
    item_count = len(re.findall(r"- \[[ x]\]", text, re.IGNORECASE))
    word_count = len(text.split())

    # What is good about the current draft
    what_is_good: list[str] = []
    if is_simplified or has_start_here:
        what_is_good.append("plain-English structure")
    if has_start_here:
        what_is_good.append("useful Start Here section for beginners")
    if item_count >= 10:
        what_is_good.append(f"comprehensive coverage ({item_count} checklist items)")
    if has_compliance:
        what_is_good.append("compliance note is preserved")
    if section_count >= 5:
        what_is_good.append(f"well-organized with {section_count} sections")
    if is_professional:
        what_is_good.append("professional executive-level language")
    if is_cleaned:
        what_is_good.append("cleaned up — no duplicate sections")
    if has_nexus_cta:
        what_is_good.append("Nexus next-step CTA present")
    if not what_is_good:
        what_is_good.append("solid first draft foundation")

    # What needs improvement
    what_to_improve: list[str] = []
    if not has_scoring and not is_lead_magnet:
        what_to_improve.append("add a quick scoring section to engage readers")
    if not has_nexus_cta or "next step with nexus" not in text.lower():
        what_to_improve.append("add a stronger Nexus next-step CTA")
    if word_count > 900:
        what_to_improve.append("shorten a few checklist items for faster scanning")
    if not (is_simplified or is_professional or is_cleaned) and not is_lead_magnet:
        what_to_improve.append("simplify the language for beginner business owners")
    if not what_to_improve:
        what_to_improve.append("no major gaps — this draft is close to ready for the next format")

    # Choose recommendation
    if is_lead_magnet:
        recommendation = "short_video_script"
        reason = (
            "The lead magnet is done. "
            "A short video script is the natural next format to drive traffic and awareness."
        )
        next_move = "Create a short video script from this"
    elif is_video_script:
        recommendation = "newsletter"
        reason = (
            "The video script is done. "
            "A newsletter version will let you reach your email audience with the same content."
        )
        next_move = "Create a newsletter from this"
    elif is_simplified or is_cleaned:
        recommendation = "lead_magnet"
        reason = (
            "It is now clear enough for a business owner to understand, "
            "and it supports the 30-day revenue goal by bringing leads into the Nexus funnel."
        )
        next_move = "Turn it into a lead magnet"
    elif is_professional:
        recommendation = "approve"
        reason = (
            "The professional edition is polished enough for Ray's review "
            "before the next publishing step."
        )
        next_move = "Prepare for Ray approval or turn it into a lead magnet"
    elif is_newsletter or is_email:
        recommendation = "approve"
        reason = (
            "This format is ready for Ray's review before any use with subscribers or clients."
        )
        next_move = "Prepare for Ray approval"
    else:
        recommendation = "simplify"
        reason = (
            "The draft needs plain-English simplification before it is ready for the public."
        )
        next_move = "Make it simpler"

    simple_answer_map = {
        "lead_magnet": "turning this cleaned checklist into a lead magnet next",
        "short_video_script": "creating a short video script from the lead magnet next",
        "approve": "preparing this version for Ray's review before the next step",
        "simplify": "simplifying this draft before converting it to other formats",
        "newsletter": "converting this into newsletter content next",
    }
    simple_answer = f"I recommend {simple_answer_map.get(recommendation, 'reviewing this draft')}."

    return {
        "recommendation": recommendation,
        "simple_answer": simple_answer,
        "reason": reason,
        "what_is_good": what_is_good,
        "what_to_improve": what_to_improve,
        "next_move": next_move,
        "path": str(path),
        "word_count": word_count,
        "item_count": item_count,
        "section_count": section_count,
        "is_simplified": is_simplified,
        "is_professional": is_professional,
        "is_cleaned": is_cleaned,
        "is_lead_magnet": is_lead_magnet,
        "has_compliance": has_compliance,
    }


def recommend_next_step_for_draft(path: Path) -> dict:
    """Evaluate a draft and return the recommendation. Entry point for Telegram."""
    if not path.exists():
        return {"error": f"Draft not found: {path}", "path": str(path)}
    return evaluate_checklist_draft(path)


def format_draft_recommendation_response(result: dict) -> str:
    """Format a draft recommendation for Telegram display."""
    if "error" in result:
        return (
            f"I could not evaluate the draft: {result['error']}\n\n"
            "Say 'create first draft' to start one."
        )

    recommendation = result.get("recommendation", "")
    simple_answer = result.get("simple_answer", "")
    reason = result.get("reason", "")
    what_is_good = result.get("what_is_good", [])
    what_to_improve = result.get("what_to_improve", [])
    next_move = result.get("next_move", "")
    path_str = result.get("path", "")

    try:
        rel_path = str(Path(path_str).relative_to(_ROOT))
    except (ValueError, TypeError):
        rel_path = path_str

    good_lines = "\n".join(f"- {g}" for g in what_is_good) if what_is_good else "- looks good overall"
    improve_lines = "\n".join(f"- {i}" for i in what_to_improve) if what_to_improve else "- no major gaps"

    reply_options = _REPLY_OPTIONS_BY_RECOMMENDATION.get(recommendation, [
        "make it simpler",
        "make it more professional",
        "turn it into a lead magnet",
    ])
    options_text = "\n".join(f"- {o}" for o in reply_options)

    return (
        f"RECOMMENDATION\n\n"
        f"Simple answer:\n{simple_answer}\n\n"
        f"Why:\n{reason}\n\n"
        f"What is good:\n{good_lines}\n\n"
        f"What I would improve before publishing:\n{improve_lines}\n\n"
        f"Next best move:\n{next_move}\n\n"
        f"Approval:\n"
        f"No approval needed for internal drafts.\n"
        f"Approval required before publishing, selling, emailing clients, or adding to the website.\n\n"
        f"Evidence:\n{rel_path}\n\n"
        f"Reply options:\n{options_text}"
    )


def format_action_recommendation_response(ctx: dict) -> str:
    """Format a recommendation response for an action context."""
    title = ctx.get("primary_object_title", "this action")
    status = ctx.get("primary_object_status", "unknown")
    path_str = ctx.get("primary_object_path", "")

    if status in ("pending", "queued"):
        rec = "continue"
        why = "It is pending and ready to move forward."
        next_step = "Assign it to a scout or mark it in progress."
    elif status in ("in_progress",):
        rec = "review progress"
        why = "It is in progress — check if there are blockers."
        next_step = "Ask 'what is its status?' for a detailed update."
    elif status in ("done", "complete", "completed"):
        rec = "archive or build on it"
        why = "It is complete. You can use the output as a foundation for the next step."
        next_step = "Say 'show it' to review the output."
    else:
        rec = "review"
        why = "The status is unclear."
        next_step = "Say 'what is its status?' to get details."

    evidence = f"- Action: {path_str}" if path_str else ""

    return (
        f"RECOMMENDATION\n\n"
        f"Simple answer:\nI recommend you {rec} — {title}.\n\n"
        f"Why:\n{why}\n\n"
        f"Next best move:\n{next_step}\n\n"
        f"Approval:\nNo approval needed to review or assign internal actions.\n\n"
        f"Evidence:\n{evidence or 'No path recorded.'}\n\n"
        f"Reply options:\n- what is its status?\n- show it\n- approve it\n- assign it"
    )


def format_opportunity_recommendation_response(ctx: dict) -> str:
    """Format a recommendation response for an opportunity context."""
    title = ctx.get("primary_object_title", "this opportunity")
    path_str = ctx.get("primary_object_path", "")
    evidence = f"- Opportunity: {path_str}" if path_str else ""

    return (
        f"RECOMMENDATION\n\n"
        f"Simple answer:\nI recommend researching this opportunity further before committing resources.\n\n"
        f"Why:\nOpportunities need validation before building. Confirm the revenue model and audience fit first.\n\n"
        f"Next best move:\nResearch the audience and revenue model for: {title}\n\n"
        f"Approval:\nApproval required before spending money or building toward this opportunity.\n\n"
        f"Evidence:\n{evidence or 'No path recorded.'}\n\n"
        f"Reply options:\n- research it\n- build it\n- reject it\n- ask Ray approval"
    )
