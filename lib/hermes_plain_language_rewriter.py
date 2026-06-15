"""
hermes_plain_language_rewriter.py
Phase 7B: Plain-language response rewriter.

Ensures CFO responses are short, plain, and useful.
No raw evidence. No artifact inventories. No HERMES REPORT unless asked.
"""
from __future__ import annotations

import re
from typing import Optional

_SAFETY_BOUNDARY = (
    "I will not publish, email subscribers, sell, deploy, spend money, "
    "apply to affiliate programs, activate Stripe, run live trading, or "
    "use client-facing content without explicit Ray approval."
)

# ── Jargon / technical terms → plain equivalents ─────────────────────────────
_JARGON_MAP = {
    r"\bintent classifier\b": "message routing system",
    r"\bdeterministic handler\b": "exact command handler",
    r"\bAI synthesis\b": "AI thinking",
    r"\bevidence dump\b": "information dump",
    r"\bvector\b": "match",
    r"\bembedding\b": "AI comparison",
    r"\bsemantic\b": "meaning-based",
    r"\binference\b": "AI decision",
    r"\bconfidence score\b": "certainty level",
    r"\bsupabase\b": "internal database",
    r"\bjsonl\b": "log file",
    r"\bpayload\b": "message data",
    r"\bfallback\b": "backup option",
    r"\bhandler\b": "command processor",
}

# ── Long response markers that suggest over-engineering ──────────────────────
_TECHNICAL_MARKERS = [
    "artifact_inventory", "handoff", "HERMES REPORT", "Evidence:", "Source:",
    "Confidence:", "intelligence_division", "scout_status", "────", "════",
    "What happened:", "Action needed:", "Recommendation:",
]


def simplify_response_text(text: str, max_bullets: int = 5) -> str:
    """Return a simplified version of a long Hermes response.

    Extracts the key lines and formats as a short plain answer.
    """
    if not text or len(text.strip()) < 50:
        return text or ""

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Find the header (first non-separator line)
    header = ""
    content_lines = []
    for line in lines:
        if re.match(r'^[═─]+$', line):
            continue
        if not header:
            header = line
            continue
        # Skip separator lines
        if re.match(r'^[═─\-=]+$', line):
            continue
        content_lines.append(line)

    # Extract bullets/numbered items (most useful content)
    bullets = [l for l in content_lines if re.match(r'^\s*[-•*]\s|^\s*\d+[.:)]\s', l)]
    prose = [l for l in content_lines if l and not re.match(r'^\s*[-•*]\s|^\s*\d+[.:)]\s', l)]

    # Build simplified response
    parts = ["PLAIN ANSWER", "", f"Simple version of: {header[:60]}"]

    if bullets[:max_bullets]:
        parts.append("")
        for b in bullets[:max_bullets]:
            parts.append(f"  {b.lstrip('  -•*').strip()[:100]}")
    elif prose[:3]:
        parts.append("")
        for p in prose[:3]:
            parts.append(f"  {p[:120]}")

    if len(bullets) > max_bullets:
        parts.append(f"  ... and {len(bullets) - max_bullets} more items.")

    parts += [
        "",
        f"Approval boundary:",
        f"  {_SAFETY_BOUNDARY}",
    ]
    return "\n".join(parts)


def explain_response_plainly(text: str, context: Optional[dict] = None) -> str:
    """Return a plain-language explanation of what the response means."""
    if not text:
        return "I don't have a previous response to explain."

    # Extract the recommendation from the text
    rec = _extract_recommendation_from_text(text)
    summary = _extract_first_meaningful_lines(text, n=3)

    parts = [
        "PLAIN ANSWER",
        "",
        "Here is what that means in plain language:",
        "",
    ]

    if rec:
        parts += [f"The recommendation was:", f"  {rec}", ""]

    if summary:
        parts += ["In simple terms:", f"  {summary}", ""]

    if context and context.get("current_topic"):
        topic = context["current_topic"].replace("_", " ")
        parts += [f"We were discussing: {topic}", ""]

    parts += [
        "What I can do next:",
        "  - Break this down further if you need",
        "  - Choose an option (say 'let's do 1')",
        "  - Create an implementation prompt",
        "",
        f"Approval boundary:",
        f"  {_SAFETY_BOUNDARY}",
    ]
    return "\n".join(parts)


def remove_jargon(text: str) -> str:
    """Replace technical jargon with plain-language equivalents."""
    result = text
    for pattern, replacement in _JARGON_MAP.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def compress_technical_output(text: str) -> str:
    """Remove artifact inventories, evidence sections, HERMES REPORT scaffolding."""
    if not text:
        return ""
    lines = text.splitlines()
    filtered = []
    skip_section = False
    for line in lines:
        # Skip sections that are clearly technical/internal
        if any(marker in line for marker in [
            "artifact_inventory", "handoff_state", "What happened:",
            "Action needed:", "Evidence:", "Source:", "Confidence:",
            "────────────", "════════════",
        ]):
            skip_section = True
        elif line.strip() and skip_section:
            # Resume after a blank line or new header
            if not line.strip().startswith(("  ", "\t", "-", "•", "*")):
                skip_section = False
        if not skip_section:
            filtered.append(line)
    return "\n".join(filtered)


def format_plain_answer(
    answer: str,
    why: Optional[str] = None,
    recommendation: Optional[str] = None,
    next_step: Optional[str] = None,
    approval_boundary: bool = True,
) -> str:
    """Format a plain-language answer using the standard CFO format."""
    parts = ["PLAIN ANSWER", ""]
    parts.append(answer[:400])

    if why:
        parts += ["", f"What it means:", f"  {why[:200]}"]

    if recommendation:
        parts += ["", f"My recommendation:", f"  {recommendation[:200]}"]

    actions = []
    if next_step:
        actions.append(next_step[:150])
    actions += ["Assign a scout if more research is needed", "Create an implementation prompt on request"]
    if actions:
        parts += ["", "What I can do next:"]
        for act in actions[:3]:
            parts.append(f"  - {act}")

    if approval_boundary:
        parts += ["", "Approval boundary:", f"  {_SAFETY_BOUNDARY}"]

    return "\n".join(parts)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_recommendation_from_text(text: str) -> Optional[str]:
    """Extract the recommendation line from a response."""
    for pattern in [
        re.compile(r'(?:my recommendation|recommendation)[:\s]+(.+)', re.IGNORECASE | re.DOTALL),
        re.compile(r'i recommend[:\s]+(.+)', re.IGNORECASE | re.DOTALL),
    ]:
        m = pattern.search(text)
        if m:
            lines = [l.strip() for l in m.group(1).splitlines() if l.strip()]
            return " ".join(lines[:2])[:300]
    return None


def _extract_first_meaningful_lines(text: str, n: int = 3) -> str:
    """Return first N meaningful non-header lines as a string."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    meaningful = []
    for line in lines:
        if re.match(r'^[═─A-Z ]{5,50}$', line):
            continue
        if re.match(r'^\d{4}-\d{2}-\d{2}', line):
            continue
        meaningful.append(line[:120])
        if len(meaningful) >= n:
            break
    return " ".join(meaningful)[:400]
