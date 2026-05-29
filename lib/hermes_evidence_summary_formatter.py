"""
hermes_evidence_summary_formatter.py
======================================
Format evidence-only responses cleanly without raw dumping.

Bad: "No conversational LLM is available right now. Here is what I have verified: [verified_file]..."
Good: "I can answer from verified artifacts.\n\nEvidence used:\n  • handoffs/: 54 files\n..."
"""
from __future__ import annotations

from lib.hermes_context_pack_builder import ContextPack


_INTENT_HEADERS: dict[str, str] = {
    "greeting":               "Good morning.",
    "today_recommendation":   "Today's recommendation from verified evidence:",
    "claude_code_work":       "Recent Claude Code activity:",
    "youtube_status":         "YouTube / source intake status:",
    "source_intake_status":   "Source intake status:",
    "thirty_day_goals":       "30-day plan summary:",
    "trading_recommendation": "Trading evidence summary:",
    "nexus_project":          "Nexus project overview:",
    "information_sources":    "Hermes information sources:",
    "provider_status":        "Hermes provider status:",
    "monetization":           "Monetization evidence:",
    "blocker":                "Blockers from evidence:",
    "general_strategy":       "Strategic context from evidence:",
    "source_review":          "Source review:",
    "scout_dispatch":         "Scout status from evidence:",
}


def format_evidence_response(intent: str, context_pack: ContextPack) -> str:
    """
    Format a clean evidence response without raw dumping.
    Does not say "No LLM available" — just presents what is known.
    """
    lines = ["I can answer from verified artifacts.", ""]

    header = _INTENT_HEADERS.get(intent, "Evidence from verified artifacts:")
    lines.append(header)
    lines.append("")

    if context_pack.artifact_paths:
        lines.append("Evidence used:")
        for p in context_pack.artifact_paths[:6]:
            lines.append(f"  • {p}")
        lines.append("")

    if context_pack.evidence_items:
        for item in context_pack.evidence_items[:6]:
            label = item.get("label", "")
            content = item.get("content", "")
            if label and content and label != "note":
                lines.append(f"[{label}] {content[:120]}")
        lines.append("")

    if context_pack.missing_evidence:
        lines.append("Missing evidence:")
        for m in context_pack.missing_evidence[:3]:
            lines.append(f"  • {m}")
        lines.append("")

    if context_pack.safe_next_actions:
        lines.append("Next action:")
        for a in context_pack.safe_next_actions[:2]:
            lines.append(f"  • {a}")
        lines.append("")

    if context_pack.approval_boundaries:
        lines.append("Requires approval:")
        for a in context_pack.approval_boundaries[:2]:
            lines.append(f"  • {a}")

    return "\n".join(lines).rstrip()


def format_no_evidence_response(intent: str) -> str:
    """Response when no evidence exists at all."""
    header = _INTENT_HEADERS.get(intent, "")
    lines: list[str] = []
    if header:
        lines += [header, ""]
    lines += [
        "No verified evidence found for this question.",
        "",
        "Hermes only responds from real artifacts — no data has been generated yet.",
        "",
        "Next action:",
        "  • Run a relevant Nexus command to generate evidence",
        "  • Or send source URLs to begin intake",
    ]
    return "\n".join(lines)


def format_provider_fallback_response(question: str, active_provider: str, context_pack: ContextPack | None = None) -> str:
    """
    Returned when all LLMs are unavailable — clean evidence summary,
    never "Command timed out" or "No conversational LLM available right now."
    """
    if context_pack and (context_pack.evidence_items or context_pack.artifact_paths):
        return format_evidence_response(context_pack.intent, context_pack)

    return (
        "Evidence-only mode active — no LLM provider available.\n"
        "\n"
        "What I know from artifacts:\n"
        "  • Ask 'show source intake' to see registered sources\n"
        "  • Ask 'what did claude code work on' to see recent handoffs\n"
        "  • Ask 'show provider status' to check which providers are available\n"
        "\n"
        "Run 'show provider status' to diagnose provider availability."
    )
