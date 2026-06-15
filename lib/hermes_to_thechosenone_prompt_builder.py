"""
Hermes → TheChoseone prompt builder.

Hermes Mobile Advisor never executes. When a request needs a backend action or
research, Hermes turns it into an EXACT, copy/paste task prompt for TheChoseone
using one fixed standard (docs/hermes_mobile/thechosenone_task_prompt_standard.md).

Pure functions, no side effects, no network, no secrets.
"""
from __future__ import annotations

import re

# The only routes Hermes is allowed to suggest.
ROUTES = [
    "research", "showroom", "proof_automation", "codex", "claude",
    "opencode", "internal_script", "manual_review",
]

# Standing safety block — always attached to every task prompt.
SAFETY_BLOCK = [
    "Do not expose secrets.",
    "Do not send emails/DMs.",
    "Do not publish.",
    "Do not approve.",
    "Do not trade live.",
    "Do not charge.",
    "Do not deploy.",
    "Do not use paid APIs unless explicitly approved.",
]

# Light secret scrub so private identifiers never end up in a task prompt.
_SENSITIVE = re.compile(
    r"(?i)\b(token|api[_-]?key|secret|password|bearer|chat[_-]?id|"
    r"goclearonline|rayscentro|supabase|oanda\s*account)\b\S*"
)
# Bare long numbers (ids / chat ids / account numbers). 8+ digits so 2-3 digit
# prices like "$97–$297" are never touched.
_LONGNUM = re.compile(r"\b\d{8,}\b")


def _scrub(text: str) -> str:
    t = _SENSITIVE.sub("[redacted]", (text or "").strip())
    return _LONGNUM.sub("[redacted]", t)


def suggest_route(text: str) -> str:
    """Best-guess route from free text. Conservative defaults; never returns a
    route outside ROUTES."""
    low = (text or "").lower()
    if re.search(r"\b(web research|research|find|look up|sources?|affiliate|"
                 r"requirements|payout|competitor)\b", low):
        return "research"
    if re.search(r"\b(package|offer|showroom|monetiz|pack|landing|asset)\b", low):
        return "showroom"
    if re.search(r"\b(proof|automation|dry[- ]?run|receipt|truth)\b", low):
        return "proof_automation"
    if re.search(r"\b(codex)\b", low):
        return "codex"
    if re.search(r"\b(claude)\b", low):
        return "claude"
    if re.search(r"\b(opencode)\b", low):
        return "opencode"
    if re.search(r"\b(backtest|strategy|trading)\b", low):
        return "manual_review"
    if re.search(r"\b(script|generate|build|render|compute)\b", low):
        return "internal_script"
    return "manual_review"


def build_task_prompt(task: str,
                      goal: str,
                      context: str = "",
                      inputs: list[str] | None = None,
                      required_output: list[str] | None = None,
                      success_criteria: str = "",
                      route: str | None = None) -> str:
    """Render a TheChoseone task prompt in the fixed standard format.

    `task` should be one sentence. Everything is scrubbed of obvious secrets.
    `route` is validated against ROUTES; an unknown route falls back to suggest_route.
    """
    task = _scrub(task)
    goal = _scrub(goal)
    context = _scrub(context)
    inputs = [_scrub(x) for x in (inputs or [])] or ["(none provided)"]
    required_output = [_scrub(x) for x in (required_output or [])] or [
        "A written report with findings.",
        "A clear recommended decision.",
    ]
    success_criteria = _scrub(success_criteria) or "Ray can act on the result without rework."
    if route not in ROUTES:
        route = suggest_route(f"{task} {goal} {context}")

    lines: list[str] = []
    lines.append(f"Task: {task}")
    lines.append("")
    lines.append(f"Goal: {goal}")
    lines.append("")
    lines.append(f"Context: {context or '(no extra context)'}")
    lines.append("")
    lines.append("Inputs:")
    for i in inputs:
        lines.append(f"* {i}")
    lines.append("")
    lines.append("Required output:")
    for o in required_output:
        lines.append(f"* {o}")
    lines.append("")
    lines.append("Safety:")
    for s in SAFETY_BLOCK:
        lines.append(f"* {s}")
    lines.append("")
    lines.append(f"Success criteria: {success_criteria}")
    lines.append("")
    lines.append("Suggested route:")
    lines.append(route)
    return "\n".join(lines)


def build_research_prompt(topic: str) -> str:
    """Convenience: a research task prompt for a public-info question."""
    return build_task_prompt(
        task=f"Research: {topic}.",
        goal="Give Ray verified public facts and a clear recommendation.",
        context="Hermes cannot browse from the mobile bot; this is delegated research.",
        inputs=[f"Topic: {topic}"],
        required_output=[
            "Source links (with titles/dates).",
            "Short summary + key facts.",
            "Payout/cost and approval requirements if relevant.",
            "Compliance/audience-fit risk.",
            "Recommended top 3 + next step.",
        ],
        success_criteria="Ray can pick a direction from cited sources, nothing applied/activated.",
        route="research",
    )
