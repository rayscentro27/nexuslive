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
    "request revision", "scouts status",
)


# Unambiguous conversation openers — these are never TheChoseone commands, so they
# route to the advisor even if a command-ish word appears later in the sentence.
ADVISOR_LEADS = ("hermes", "explain", "should we", "should i", "what do you think",
                 "help me decide", "how do i", "how should", "why ", "research ",
                 "find the best", "can thechoseone", "what can thechoseone", "what command")


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
