"""
TheChoseone — live command delegation gate.

Thin, strictly-gated adapter between TheChoseone's live Telegram command handler
and the delegation router. It fires ONLY for explicit delegation commands or
explicit unsafe imperatives, so ordinary chat/read-only commands fall through
untouched (returns None).

When it fires, it calls `thechosenone_delegation_router.delegate()` which
classifies, writes an execution-truth receipt, and returns a mobile-readable
reply. It NEVER executes a backend action itself.
"""
from __future__ import annotations

import re

# Explicit delegation command triggers (Task-2 set). Order: most specific first.
_DELEGATION_PREFIXES = (
    "run web research:",
    "create monetization task from package",
    "turn package ",
    "review package ",
    "send this to codex:",
    "send this to claude:",
    "send this to opencode:",
    "route to codex:",
    "route to claude:",
    "route to opencode:",
    "ask codex to ",
    "ask claude to ",
    "ask opencode to ",
    "create offer from package ",
    "create showroom package from ",
    "backtest strategy idea:",
    "analyze trading strategy:",
)

# Explicit unsafe imperatives (Task-5 set) — narrow on purpose so normal
# questions like "how do we publish content?" are NOT blocked.
_UNSAFE_RE = re.compile(
    r"(?i)^(please\s+)?("
    r"send (an? )?emails?( to | to leads| to prospects)|email (the )?leads|"
    r"dm (the )?(prospects|leads)|"
    r"publish (this|the)? ?post|publish (it|now)|post to (twitter|x|linkedin|instagram|facebook)|"
    r"charge (the )?customers?|charge (them|the card)|"
    r"deploy to (production|prod)|"
    r"place (a )?live trade|go live with (a )?trade|"
    r"approve all packages( automatically)?|auto[- ]approve all|"
    r"use (a )?paid api"
    r")\b")


def is_delegation_command(normalized: str) -> bool:
    low = (normalized or "").strip()
    if low.startswith("research ") and not low.startswith("research queue") \
            and not low.startswith("research status"):
        return True
    if low == "run proof automation dry run":
        return True
    if low.startswith(_DELEGATION_PREFIXES):
        return True
    # Package-less monetization phrasings (Task-4):
    #   "turn proof_credit into a paid offer", "create monetization task from proof_credit"
    if "proof_credit" in low and ("offer" in low or "monetiz" in low):
        return True
    if low.startswith("create monetization task from "):
        return True
    return False


def is_unsafe_imperative(normalized: str) -> bool:
    return bool(_UNSAFE_RE.search((normalized or "").strip()))


def maybe_handle(text: str) -> str | None:
    """Return a mobile-readable delegation/blocked reply, or None to fall through.

    None means: not a delegation command and not an unsafe imperative — let the
    existing TheChoseone handlers run unchanged."""
    normalized = (text or "").strip().lower()
    if not normalized:
        return None
    if not (is_delegation_command(normalized) or is_unsafe_imperative(normalized)):
        return None
    # Lazy import so TheChoseone startup stays light and import-safe.
    from lib import thechosenone_delegation_router as DR
    return DR.delegate(text, source="telegram", user="ray")["response"]
