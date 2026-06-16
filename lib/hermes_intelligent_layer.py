"""
Hermes Intelligent Layer — flag-gated advisor brain for the live Telegram bot.

When HERMES_INTELLIGENT_LAYER_ENABLED=true, advisor-style messages (opinion,
research, prompt-building) are answered by the opinion engine / web-research
handoff / prompt builder instead of the generic conversation pipeline.

Hard guarantees:
  * Default OFF (HERMES_INTELLIGENT_LAYER_ENABLED=false) — existing behavior intact.
  * Hermes only ADVISES and DRAFTS. It never executes, never calls the delegation
    router, never writes a TheChoseone receipt, never sends/approves/trades/spends.
  * Operational commands (status / approvals / show package / *status) are NEVER
    handled here — they stay with the war-room router → TheChoseone.
  * Research is handoff-only (no safe live web provider wired).

This module returns text only. The Telegram wiring decides whether to use it.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from lib import hermes_advisor_opinion_engine as OE
from lib import hermes_advisor_web_research as WR
from lib import hermes_to_thechosenone_prompt_builder as PB

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"

ENABLED_ENV = "HERMES_INTELLIGENT_LAYER_ENABLED"
DRY_RUN_ENV = "HERMES_INTELLIGENT_LAYER_DRY_RUN"

# Exact safety boundary appended to every research handoff.
RESEARCH_FOOTER = ("Do not apply, email, publish, pay, activate links, use paid APIs, "
                   "or expose secrets.")


def _env(name: str) -> str | None:
    v = os.environ.get(name)
    if v is not None:
        return v
    try:
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def enabled() -> bool:
    """Default FALSE. Only true when Ray explicitly enables the flag."""
    return (_env(ENABLED_ENV) or "false").strip().lower() == "true"


def dry_run() -> bool:
    """Default TRUE. Hermes never mutates backend state regardless, but this makes
    the intent explicit for the test/rollout."""
    return (_env(DRY_RUN_ENV) or "true").strip().lower() == "true"


# ── intent matchers ───────────────────────────────────────────────────────────
# Prompt-building wins over research/opinion when explicit.
_PROMPT_INTENT = re.compile(
    r"(?i)(create a prompt for thechose?one|build (me )?a prompt|give me a prompt|"
    r"turn .*(credit pack|proof_credit|package).* into (an? )?offer|"
    r"turn the credit pack into an offer|create monetization task)")
_RESEARCH_INTENT = re.compile(
    r"(?i)(run web research|^research\b|research the|find the best|affiliate offers|"
    r"look up|search the web)")
_OPINION_INTENT = re.compile(
    r"(?i)(what do you think|what'?s your take|your take|what should i do next|"
    r"how do we make money|how do we make|how can we make money|"
    r"explain (this|the)\b.*report|explain this|"
    r"review this thechose?one result|review .* result)")


def classify_advisor_intent(text: str) -> str | None:
    """Return 'prompt' | 'research' | 'opinion' | None."""
    t = text or ""
    if _PROMPT_INTENT.search(t):
        return "prompt"
    if _RESEARCH_INTENT.search(t):
        return "research"
    if _OPINION_INTENT.search(t):
        return "opinion"
    return None


def _extract_package(text: str) -> str:
    low = (text or "").lower()
    m = re.search(r"package\s+([a-z0-9_\-]+)", low)
    if m:
        return m.group(1)
    if "proof_credit" in low:
        return "proof_credit"
    if "credit pack" in low or "credit" in low:
        return "proof_credit"
    return "proof_credit"


def _strip_research_prefix(text: str) -> str:
    t = re.sub(r"(?i)^\s*(run web research:?|research(\s+the)?:?|find the best|look up|search the web)\s*",
               "", text or "").strip()
    return t or (text or "").strip()


def _research_reply(text: str) -> tuple[str, str]:
    topic = _strip_research_prefix(text)
    # Mode A only if a safe live provider is actually wired (none today).
    draft = WR.draft_research_task(topic)
    reply = ("I can't browse directly from this bot yet — research is **handoff-only**. "
             "Here's the task for TheChoseone:\n\n"
             f"{draft}\n\n{RESEARCH_FOOTER}")
    return reply, draft


def _prompt_reply(text: str) -> tuple[str, str]:
    pkg = _extract_package(text)
    # goal: anything after a colon, else a sensible default.
    goal = ""
    if ":" in text:
        goal = text.split(":", 1)[1].strip()
    goal = goal or "Turn this into a reviewable paid offer (Credit/Funding readiness review)."
    task = PB.build_task_prompt(
        task=f"Turn package {pkg} into a reviewable paid offer.",
        goal=goal,
        context="Default monetization priority: Credit/Funding readiness first. Compliance-safe; nothing published.",
        inputs=[f"Package: {pkg}", "Price band: $97-$297", "Channel: manual review only"],
        required_output=[
            "Offer name + compliance-safe promise (no guaranteed-funding claims).",
            "Deliverables list + price options.",
            "Draft showroom entry (not published).",
            "A clear go/no-go decision for Ray.",
        ],
        success_criteria="Ray can approve/reject a concrete offer; nothing published, charged, or emailed.",
        route="showroom")
    command = f"create monetization task from package {pkg}: {goal}"
    reply = f"{task}\n\nCommand for TheChoseone:\n{command}"
    return reply, command


def handle(text: str) -> dict | None:
    """If `text` is advisor-style, return an intelligent reply dict; else None.

    Returns: {reply_text, intent, command_draft, used_intelligent_layer, dry_run}.
    NEVER executes, delegates, or writes a receipt.
    """
    intent = classify_advisor_intent(text or "")
    if not intent:
        return None
    if intent == "opinion":
        reply = OE.render(text)
        # OE may embed a 'Command for TheChoseone:' block; surface it as the draft.
        draft = None
        if "Command for TheChoseone:" in reply:
            draft = reply.split("Command for TheChoseone:", 1)[1].strip()
    elif intent == "research":
        reply, draft = _research_reply(text)
    else:  # prompt
        reply, draft = _prompt_reply(text)
    return {
        "reply_text": reply,
        "intent": intent,
        "command_draft": draft,
        "used_intelligent_layer": True,
        "dry_run": dry_run(),
        "executed": False,
    }
