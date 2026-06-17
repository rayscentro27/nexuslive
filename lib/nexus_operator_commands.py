"""
Nexus Operator command handler — answers War Room/TheChosenOne operator commands
from the canonical operator status file (reports/operator/nexus_operator_status.json).

Read-only. Never answers from memory. Safe to import from the Telegram bot/router:

    from lib.nexus_operator_commands import is_operator_command, answer_operator_command
    if is_operator_command(text):
        reply = answer_operator_command(text)
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS_JSON = ROOT / "reports" / "operator" / "nexus_operator_status.json"

# Recognized operator intents (substring match, case-insensitive).
OPERATOR_INTENTS = (
    "how do we make money today", "make money today", "money today",
    "what needs approval", "needs approval",
    "show money pipeline", "money pipeline",
    "show oanda status", "oanda status",
    "show showroom", "showroom status",
    "show automation status", "automation status",
    "what is blocked", "what's blocked", "blockers",
    "run daily operator",
)


def is_operator_command(text: str) -> bool:
    low = (text or "").strip().lower()
    return any(k in low for k in OPERATOR_INTENTS)


def _status() -> dict | None:
    try:
        return json.loads(STATUS_JSON.read_text())
    except Exception:
        return None


def answer_operator_command(text: str) -> str:
    """Format an answer for the given operator command from the status file."""
    st = _status()
    if not st:
        return ("Operator status not yet generated. Run: "
                "python3 scripts/run_nexus_operator_core.py")
    # Delegate to the core's formatter so logic stays in one place.
    try:
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_nexus_operator_core import answer as core_answer  # type: ignore
        return core_answer(text, st)
    except Exception:
        # Minimal inline fallback if the core module can't be imported.
        m = st.get("monetization", {})
        return (f"Offer: {m.get('primary_offer')} ({' / '.join(m.get('prices', []))}). "
                f"Approval queue: {st.get('automation', {}).get('approval_queue_count')}. "
                f"Blockers: {len(st.get('blockers', []))}. "
                "See reports/operator/nexus_operator_brief.md")
