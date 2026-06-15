"""
Hermes live-action safety guard.

A HARD, flag-INDEPENDENT guard that runs in the Hermes Mobile reply path BEFORE
the intelligent layer, the opinion engine, the prompt builder, AND the local
model fallback. Hermes must never encourage, draft, or "initiate" a live action.

If a message is a live/outward action or a worker-execution request, Hermes:
  * refuses to initiate it, and
  * hands a SAFE, compliance-bounded task to TheChoseone.

This is independent of HERMES_INTELLIGENT_LAYER_ENABLED — it protects even the
generic model fallback that produced the unsafe "let's get those emails out…"
reply. Returns refusal text or None (None = not a live action; normal handling).
"""
from __future__ import annotations

import re

# Light secret scrub so nothing private appears in a handoff echo.
_SECRET = re.compile(r"(?i)\b(token|api[_-]?key|secret|password|bearer|chat[_-]?id)\b[\s:=]*\S+")
_LONGNUM = re.compile(r"\b\d{8,}\b")


def _scrub(text: str) -> str:
    return _LONGNUM.sub("[redacted]", _SECRET.sub("[redacted]", text or "")).strip()


# Worker-execution requests -> TheChoseone (never Hermes).
_WORKER = re.compile(r"(?i)^(send this to|route to|ask)\s+(codex|claude|opencode)\b")

# Live outreach (the most dangerous class).
_OUTREACH = re.compile(
    r"(?i)\b(send (an? )?emails?|email (the )?leads|email leads|send (a )?dms?|"
    r"dm (the )?(prospects|leads)|message (the )?(prospects|leads))\b")

# Other live/outward/irreversible actions.
_PUBLISH = re.compile(r"(?i)\b(publish (this|the)? ?post|post this publicly|post to (twitter|x|linkedin|instagram|facebook))\b")
_PAYMENT = re.compile(r"(?i)\b(charge (the )?customers?|charge (them|the card)|create (a )?checkout link|process (a )?payment)\b")
_DEPLOY = re.compile(r"(?i)\b(deploy to (production|prod)|ship to production)\b")
_TRADE = re.compile(r"(?i)\b(place (a )?live trade|go live with (a )?trade|execute (a )?live trade)\b")
_APPROVE = re.compile(r"(?i)\b(approve all packages( automatically)?|auto[- ]approve all)\b")
_PAIDAPI = re.compile(r"(?i)\b(use (a )?paid api|call (a )?paid api|enable paid api)\b")


def classify(text: str) -> str | None:
    """Return a live-action kind, or None. Order: worker first, then outreach,
    then other live actions."""
    t = (text or "").strip()
    if _WORKER.search(t):
        return "worker"
    if _OUTREACH.search(t):
        return "outreach"
    if _PUBLISH.search(t):
        return "publish"
    if _PAYMENT.search(t):
        return "payment"
    if _DEPLOY.search(t):
        return "deploy"
    if _TRADE.search(t):
        return "trade"
    if _APPROVE.search(t):
        return "approve"
    if _PAIDAPI.search(t):
        return "paid_api"
    return None


def is_live_action(text: str) -> bool:
    return classify(text) is not None


# Canonical SAFE handoff command per kind (review/report only — never live).
_CANON = {
    "outreach": ("create outreach review task: Draft a manual, compliance-safe outreach "
                 "message for Ray to review. Do not send emails, DMs, publish, charge, or contact anyone."),
    "publish": ("create content review task: Draft the content for Ray to review. "
                "Do not publish or post anywhere."),
    "payment": ("create offer review task: Draft pricing/checkout copy for Ray to review. "
                "Do not charge anyone or create live payment links."),
    "deploy": ("create deploy readiness report: Summarize what a deploy would change for Ray. "
               "Do not deploy."),
    "trade": ("create trade analysis report: Education/demo analysis only for Ray to review. "
              "Do not place live trades or move money."),
    "approve": ("create approval review: List the items that need Ray's approval so he can decide. "
                "Do not auto-approve anything."),
    "paid_api": ("create research plan: List what would be needed. Do not call paid APIs without "
                 "Ray's explicit approval."),
}

_REFUSAL_TAIL = ("I will not execute, send, publish, approve, charge, trade, deploy, or call paid APIs.")


def canonical_handoff(text: str, kind: str | None = None) -> str:
    kind = kind or classify(text)
    if kind == "worker":
        # Hand the worker request to TheChoseone verbatim (it will dry_run_only it).
        return _scrub(text)
    return _CANON.get(kind or "", "create review task: Draft a safe report for Ray to review. "
                       "Do not take any live action.")


def refusal_if_live_action(text: str) -> str | None:
    """The hard guard. Returns Hermes's safe refusal+handoff, or None to allow
    normal (read-only advisor) handling."""
    kind = classify(text)
    if kind is None:
        return None
    handoff = canonical_handoff(text, kind)
    if kind == "outreach":
        return ("That is a live outreach action, so I will not start or send it.\n\n"
                "Safe alternative:\nSend this to TheChoseone:\n" + handoff + "\n\n" + _REFUSAL_TAIL)
    if kind == "worker":
        return ("That is not a Hermes action. It requires TheChoseone safety handling.\n\n"
                "Send this to TheChoseone: " + handoff + "\n\n" + _REFUSAL_TAIL)
    return ("That is not a Hermes action. It requires TheChoseone safety handling.\n\n"
            "Send this to TheChoseone:\n" + handoff + "\n\n" + _REFUSAL_TAIL)
