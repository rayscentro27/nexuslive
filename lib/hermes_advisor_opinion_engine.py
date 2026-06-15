"""
Hermes Advisor — opinion engine.

Turns Hermes Mobile from a command helper into a real business advisor that can
state a plain-English opinion, explain why, name the risk, give the next move,
and (when a backend action or research is needed) hand an EXACT task to
TheChoseone. Hermes never executes — it forms opinions and delegates.

Hard rules (see docs/hermes_mobile/opinion_policy.md):
  * Direct, plain language — not a generic chatbot.
  * Never invent live operational facts (revenue, approvals, balances, counts).
  * Separate opinion from verified facts. If live Nexus data is needed → hand off
    to TheChoseone. If current public info is needed → research handoff.
  * Default monetization priority:
        1) Credit/Funding Readiness   2) Funding upsell
        3) Opportunity pack           4) Trading/demo (later)

Pure/deterministic: no network, no LLM call, no secrets. (An optional model
polish hook exists but is OFF by default so tests stay deterministic.)
"""
from __future__ import annotations

import re

from lib import hermes_to_thechosenone_prompt_builder as PB

# Canonical monetization priority — used verbatim so doctrine never drifts.
MONETIZATION_PRIORITY = [
    "Credit/Funding Readiness (fastest cash, existing proof assets)",
    "Funding upsell (for those who pass readiness)",
    "Opportunity / Content pack (the 30-Day AI Content Growth Pack)",
    "Trading/demo education (later — never live money first)",
]

# Phrases that mean the user wants live Nexus state we must NOT fabricate.
_LIVE_DATA = re.compile(
    r"(?i)\b(how much|revenue|made|earned|balance|profit|today|right now|"
    r"current|status|how many|approved|pending|queue|did we|are we on track|"
    r"what did (we|nexus) (make|produce|do))\b"
)
# Phrases that mean current public/external info is needed.
_PUBLIC_INFO = re.compile(
    r"(?i)\b(best|compare|competitor|market|pricing|affiliate|requirements|"
    r"trend|latest|news|who offers|payout|reviews?)\b"
)
_MONETIZATION = re.compile(
    r"(?i)\b(make money|monetiz|revenue|income|\$\d|earn|sell|offer|pricing|"
    r"30[- ]?day|first dollar|first sale|cash)\b"
)


def needs_live_data(question: str) -> bool:
    return bool(_LIVE_DATA.search(question or ""))


def needs_public_info(question: str) -> bool:
    return bool(_PUBLIC_INFO.search(question or ""))


def is_monetization(question: str) -> bool:
    return bool(_MONETIZATION.search(question or ""))


def _monetization_opinion(question: str) -> dict:
    take = ("Go Credit/Funding Readiness first. It's the fastest money because the proof "
            "assets already exist — we package and sell a manual readiness review, then "
            "upsell funding. Content pack second, trading/demo last.")
    why = [
        "Credit/Funding readiness uses assets Nexus already produced — least new work, fastest first dollar.",
        "It targets people who already pay for this outcome (funding/credit pros, small businesses).",
        "Funding upsell and the 30-Day Content Pack stack on top without changing the core motion.",
    ]
    risk = ("The real risk is compliance language — never promise guaranteed funding/credit "
            "or specific approval amounts. Sell the readiness review, not an outcome.")
    next_move = ("Stand up ONE paid offer: a $97–$297 manual Funding Readiness Review built "
                 "from the existing proof_credit package — no auto-publish, no charging yet.")
    cmd = PB.build_task_prompt(
        task="Turn the proof_credit package into a paid Funding Readiness Review offer.",
        goal="A reviewable $97–$297 manual offer Ray can approve before anything goes live.",
        context="Default monetization priority: Credit/Funding first, then funding upsell, then content pack.",
        inputs=["Package: proof_credit", "Price band: $97–$297", "Channel: manual review only"],
        required_output=[
            "Offer name + one-paragraph promise (compliance-safe, no guaranteed-funding claims).",
            "What the buyer receives (deliverables list).",
            "Draft sales blurb + price options.",
            "Showroom entry (draft only — not published).",
        ],
        success_criteria="Ray can approve/reject a concrete offer; nothing published, charged, or emailed.",
        route="showroom",
    )
    return {"my_take": take, "why": why, "risk": risk,
            "best_next_move": next_move, "command_for_thechosenone": cmd}


def _generic_opinion(question: str, facts: list[str] | None) -> dict:
    q = (question or "").strip()
    take = ("Here's my honest read — but treat it as opinion, not verified status. "
            "I won't make up live numbers; if you need those, I'll hand it to TheChoseone.")
    why = [
        "I'm reasoning from doctrine and what's durable, not from live operational data.",
        "Where the answer depends on current facts, the honest move is to verify, not guess.",
        "Keeping opinion and verified facts separate is what makes the advice trustworthy.",
    ]
    if facts:
        why[0] = "Based on the facts you gave me: " + "; ".join(facts[:3]) + "."
    risk = "Main risk: acting on an opinion as if it were confirmed status. Verify before you commit money or sends."
    next_move = "Tell me the decision you're actually trying to make — I'll give a sharper call or a research/verify task."
    cmd = None
    if needs_live_data(q):
        cmd = PB.build_task_prompt(
            task=f"Pull the live Nexus facts needed to answer: {q}",
            goal="Give Ray verified current state instead of an opinion.",
            context="Hermes must not fabricate live operational data.",
            inputs=[f"Question: {q}"],
            required_output=["The relevant live numbers/status from Nexus systems.",
                             "A one-line plain-English read on what it means."],
            success_criteria="Ray sees verified facts, clearly separated from opinion.",
            route="internal_script",
        )
        next_move = "I can't see live numbers from this bot — I've drafted a task for TheChoseone to fetch them."
    elif needs_public_info(q):
        cmd = PB.build_research_prompt(q)
        next_move = "This needs current public info — I've drafted a research task for TheChoseone."
    return {"my_take": take, "why": why, "risk": risk,
            "best_next_move": next_move, "command_for_thechosenone": cmd}


def _nexus_opinion(question: str) -> dict:
    take = ("Nexus is strongest as a money-making operator, not a science project. The win "
            "is turning the proof assets it already builds into one paid offer and selling it "
            "— Credit/Funding readiness first.")
    why = [
        "It already produces real artifacts (proof packs, showroom packages) — that's sellable now.",
        "The bottleneck isn't capability, it's picking ONE offer and charging for it.",
        "Lean infra (the Mac Mini stays Nexus-only) keeps focus on revenue, not maintenance.",
    ]
    risk = ("Risk is breadth over depth — too many lanes, no single paid offer shipped. And on "
            "live status I won't guess; numbers come from TheChoseone.")
    next_move = "Ship the Funding Readiness Review offer from proof_credit and put a price on it."
    cmd = PB.build_task_prompt(
        task="Report verified current Nexus status to back up this opinion with facts.",
        goal="Separate my opinion from real numbers Ray can trust.",
        context="Hermes opinion is doctrine-based; live status must be verified.",
        inputs=["Question: what do you think about Nexus / how are we doing"],
        required_output=["Latest produced artifacts + counts.", "Open approvals.",
                         "Any revenue/readiness signals on record."],
        success_criteria="Ray sees opinion and verified status side by side.",
        route="internal_script",
    )
    return {"my_take": take, "why": why, "risk": risk,
            "best_next_move": next_move, "command_for_thechosenone": cmd}


def form_opinion(question: str, facts: list[str] | None = None) -> dict:
    """Return a structured opinion dict:
      { my_take, why:[..], risk, best_next_move, command_for_thechosenone|None }
    """
    q = (question or "").strip()
    if re.search(r"(?i)\bnexus\b", q) and not is_monetization(q) and not needs_public_info(q):
        return _nexus_opinion(q)
    if is_monetization(q):
        return _monetization_opinion(q)
    return _generic_opinion(q, facts)


def render(question: str, facts: list[str] | None = None) -> str:
    """Render the fixed Hermes opinion format as plain text."""
    op = form_opinion(question, facts)
    lines = [f"My take: {op['my_take']}", "", "Why:"]
    for i, r in enumerate(op["why"], 1):
        lines.append(f"{i}. {r}")
    lines += ["", "Risk:", op["risk"], "", f"Best next move: {op['best_next_move']}"]
    if op.get("command_for_thechosenone"):
        lines += ["", "Command for TheChoseone:", op["command_for_thechosenone"]]
    return "\n".join(lines)
