"""
Nexus War Room Router — decides which bot answers a message so the two bots
never double-reply.

  - Command verbs / prefixes  -> TheChoseone (command bot, gated execution)
  - Natural conversation      -> Hermes Mobile (read-only advisor)

This module only ROUTES (classification). It does not execute commands and does
not send messages. No live group router is enabled here.
"""
from __future__ import annotations

import re

# Leading command prefixes and verbs that belong to TheChoseone.
COMMAND_PREFIXES = ("!", "/run", "/cmd")
COMMAND_VERBS = (
    "status", "approve", "pause", "resume", "stop", "run",
    "what needs approval", "needs approval", "daily report",
    "request revision",
    # approval-queue phrasings — these belong to TheChoseone (it has live data)
    "what needs to be approved", "what do i need to approve", "what needs my approval",
    "approvals", "approval queue", "show approvals", "pending approvals",
    "what assets need review", "what packages need review", "review queue", "showroom queue",
    # scout-status phrasings (singular + plural)
    "scouts status", "scout status", "scout statuses", "scouts", "scout report",
    "scout reports", "status scouts", "status scout",
)


# Unambiguous conversation openers — these are never TheChoseone commands, so they
# route to the advisor even if a command-ish word appears later in the sentence.
ADVISOR_LEADS = ("hermes", "explain", "should we", "should i", "what do you think",
                 "help me decide", "how do i", "how should", "why ", "research ",
                 "find the best", "can thechoseone", "what can thechoseone", "what command")


# Operational TheChoseone commands -> their canonical form (typo handling below).
OPERATIONAL_CANONICAL = {
    "status": "status", "system status": "status", "what is running": "status",
    "raw status": "raw status", "details status": "raw status", "full status": "raw status",
    "scout status": "scouts status", "scouts status": "scouts status", "scout statuses": "scouts status",
    "scouts": "scouts status", "scout report": "scouts status", "scout reports": "scouts status",
    "status scouts": "scouts status", "status scout": "scouts status",
    "what did nexus produce": "what did nexus produce", "what did you produce": "what did nexus produce",
    "daily report": "daily report", "safety status": "status", "trading status": "status",
    "worker bridge status": "status", "command routing audit": "status",
    "war room version": "war room version", "warroom version": "war room version",
}


def _dedupe(s: str) -> str:
    """Collapse consecutive duplicate letters so 'approvals'/'aprrovals'/'apprrovals'
    all normalize to the same string ('aprovals')."""
    return re.sub(r"(.)\1+", r"\1", s or "")


def is_approval_phrase(text: str) -> bool:
    """Typo-tolerant detection of approval-QUEUE phrasings (not batch-approve actions)."""
    low = (text or "").strip().lower().rstrip("?!. ")
    # batch-approve / revision commands are separate actions, not the queue view
    if low.startswith(("approve all", "approve package", "request revision")):
        return False
    d = _dedupe(low)
    if "aprov" in d:          # approve, approval(s), aprovals, aprrovals, pending approvals…
        return True
    return any(k in d for k in ("review que", "review queue", "review cue", "showroom queue"))


# Package name aliases -> canonical package id (multiword first).
PKG_ALIASES = [
    ("credit readiness", "proof_credit"), ("ai improvement", "proof_ai_improvement"),
    ("credit", "proof_credit"), ("funding", "proof_funding"),
    ("opportunity", "proof_opportunity"), ("trading", "proof_trading"),
    ("ai", "proof_ai_improvement"),
]


def resolve_package_id(text: str) -> str | None:
    """Resolve a 'show package' style phrase to a canonical package id, else None."""
    low = (text or "").strip().lower().rstrip("?!. ")
    if not ("package" in low or low.startswith(("show ", "view ", "details "))):
        return None
    m = re.search(r"\b(proof_[a-z_]+)\b", low)
    if m:
        return m.group(1)
    for alias, pid in PKG_ALIASES:
        if alias in low:
            return pid
    return None


def canonical_command(text: str) -> str | None:
    """The exact TheChoseone command for an operational/approval/package phrase, else None."""
    low = (text or "").strip().lower().rstrip("?!. ")
    if is_approval_phrase(low):
        return "what needs approval"
    if low in OPERATIONAL_CANONICAL:
        return OPERATIONAL_CANONICAL[low]
    pid = resolve_package_id(low)
    if pid:
        return f"show package {pid}"
    return None


def looks_like_command(text: str) -> bool:
    """True if the message is a TheChoseone command (verb, prefix, or operational/
    approval alias incl. typos). Used to keep Hermes out of TheChoseone's lane."""
    if canonical_command(text):
        return True
    return route(text).get("is_command", False)


def route(message: str) -> dict:
    """Return {target, reason, is_command, command_text?}. target in
    {'thechoseone','hermes_mobile'}. Command always wins the tie-break, except
    explicit advisor-address openers (e.g. 'Hermes, ...', 'how do I approve ...')."""
    t = (message or "").strip()
    low = t.lower()

    # explicit advisor address -> conversation (e.g. "how do I approve this?")
    for lead in ADVISOR_LEADS:
        if low.startswith(lead):
            return {"target": "hermes_mobile", "is_command": False,
                    "reason": f"advisor lead '{lead.strip()}'"}

    # operational/approval alias (typo-tolerant) -> TheChoseone
    canon = canonical_command(low)
    if canon:
        return {"target": "thechoseone", "is_command": True,
                "command_text": canon, "reason": "operational/approval alias"}

    # explicit prefix -> command bot, strip the prefix for execution
    for p in COMMAND_PREFIXES:
        if low.startswith(p):
            cmd = t[len(p):].strip()
            return {"target": "thechoseone", "is_command": True,
                    "command_text": cmd, "reason": f"prefix '{p}'"}

    # leading command verb -> command bot
    for v in COMMAND_VERBS:
        if low == v or low.startswith(v + " ") or low.startswith(v + ":"):
            return {"target": "thechoseone", "is_command": True,
                    "command_text": t, "reason": f"verb '{v}'"}

    # batch approval / revision phrasing anywhere at start
    if re.match(r"^\s*(approve all assets in package|request revision for package|approve package)\b", low):
        return {"target": "thechoseone", "is_command": True, "command_text": t,
                "reason": "batch command"}

    # everything else is conversation -> Hermes Mobile (read-only)
    return {"target": "hermes_mobile", "is_command": False, "reason": "natural conversation"}


def should_reply(bot: str, message: str) -> bool:
    """A bot replies only if the router routed the message to it (prevents dupes)."""
    r = route(message)
    return r["target"] == bot
