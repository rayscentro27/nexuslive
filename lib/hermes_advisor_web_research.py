"""
Hermes Advisor — safe web research adapter (read-only, citation-first).

Behavior:
  - If a safe local web-search path is available AND enabled, run read-only research.
  - Otherwise, draft a TheChoseone research task (no live browsing claimed).
  - Never mix private Nexus context into external prompts (queries are sanitized).
  - Always cite source URL/title; distinguish verified facts from recommendations.
  - No affiliate signups, applications, emails, payments, or publishing.

Live web access is OFF by default (HERMES_ADVISOR_WEB_ENABLED=false) and there is
no paid-API usage. When unavailable, the adapter returns a drafted research
command for TheChoseone instead of guessing.
"""
from __future__ import annotations

import os
import re

SUPPORTED_TOPICS = [
    "affiliate programs", "monetization offers", "ai tools", "repos",
    "competitor offers", "credit content", "funding content",
    "trading education", "youtube research", "platform recommendations",
]

# Never let private identifiers leak into an external query. Redact the key word
# AND any value that immediately follows it (token=ABC, api_key: xyz, bearer ZZZ).
_SENSITIVE_KV = re.compile(r"(?i)\b(token|api[_-]?key|secret|password|bearer|"
                           r"chat[_-]?id)\b[\s:=]*\S*")
_SENSITIVE_WORD = re.compile(r"(?i)\b(goclearonline|rayscentro|supabase|"
                             r"oanda\s*account|\d{8,})\b")


def web_enabled() -> bool:
    return os.environ.get("HERMES_ADVISOR_WEB_ENABLED", "false").lower() == "true"


def sanitize_query(topic: str) -> str:
    """Strip anything private before any external call. Public topic words only."""
    t = _SENSITIVE_KV.sub("[redacted]", (topic or "").strip())
    t = _SENSITIVE_WORD.sub("[redacted]", t)
    return t[:160]


def draft_research_task(topic: str) -> str:
    """The safe default: a copy/paste research command for TheChoseone."""
    t = sanitize_query(topic)
    return ("run web research: " + t + " and return source links, summary, payout/cost, "
            "approval requirements, risk, and recommended next step.")


def research(topic: str) -> dict:
    """Return a structured result. When live web is unavailable, returns a drafted
    TheChoseone task instead of fabricating facts."""
    t = sanitize_query(topic)
    if not web_enabled():
        return {
            "mode": "handoff",
            "message": ("I can't browse directly from this bot yet. I can draft a research "
                        "task for TheChoseone."),
            "command_draft": draft_research_task(t),
            "results": [],
            "note": "No live web access; no facts fabricated.",
        }
    # Live path is intentionally not wired to any provider here. If a safe local
    # search tool is added later, call it and map each hit into result_template().
    return {
        "mode": "handoff",
        "message": "Live web search is enabled by flag but no safe local search tool is wired yet.",
        "command_draft": draft_research_task(t),
        "results": [],
        "note": "Flag on, tool absent — still no fabricated facts.",
    }


def result_template() -> dict:
    """Shape every web result must follow when a live tool is added."""
    return {
        "title": "", "url": "", "summary": "", "relevance_to_nexus": "",
        "estimated_cost": "", "benefit": "", "risk": "", "recommendation": "",
        "source_date": "", "confidence": "low",
        "fact_vs_recommendation": "recommendation",
    }


# ── Mobile-facing responder (Mode A live / Mode B handoff) ───────────────────
def respond(topic: str) -> str:
    """Plain-text answer for the mobile bot.

    Mode A (safe live web available + wired): source links, summary, key facts,
        payout/cost, requirements, risk, Hermes opinion, next step, optional
        TheChoseone command.
    Mode B (no live web): clearly say browsing isn't available and hand a ready
        research task to TheChoseone. Never fabricate facts.
    """
    res = research(topic)
    t = sanitize_query(topic)
    if res.get("mode") == "live" and res.get("results"):
        lines = [f"Research: {t}", "", "Sources:"]
        for r in res["results"][:5]:
            lines.append(f"- {r.get('title','(untitled)')} — {r.get('url','')}"
                         f"  [{r.get('fact_vs_recommendation','recommendation')}]")
        lines += ["", "Summary:", res.get("summary", "(none)")]
        facts = res.get("key_facts") or []
        if facts:
            lines += ["", "Key facts:"] + [f"- {f}" for f in facts]
        lines += ["", f"Payout/cost: {res.get('payout_cost','n/a')}",
                  f"Requirements: {res.get('requirements','n/a')}",
                  f"Risk: {res.get('risk','n/a')}", "",
                  f"My opinion: {res.get('opinion','(form via opinion engine)')}",
                  f"Recommended next step: {res.get('next_step','review the cited sources')}"]
        if res.get("command_draft"):
            lines += ["", "Command for TheChoseone:", res["command_draft"]]
        return "\n".join(lines)

    # Mode B — handoff (the safe default today)
    return ("I can't browse directly from this bot yet. Here is the task for TheChoseone:\n\n"
            + res.get("command_draft", draft_research_task(t))
            + "\n\nDo not apply, do not email, do not publish, do not activate links, "
              "and do not use paid APIs.")
