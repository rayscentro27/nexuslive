"""
hermes_cfo_doctrine.py
Phase 7B: Loader for Hermes CFO doctrine files.

Loads behavior rules from docs/hermes/ markdown files.
CFO brain uses these rules when constructing responses.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_DOCTRINE_DIR = _ROOT / "docs" / "hermes"

_DOCTRINE_FILES = {
    "cfo_conversation":    "HERMES_CFO_CONVERSATION_CONTRACT.md",
    "plain_language":      "HERMES_PLAIN_LANGUAGE_STYLE_GUIDE.md",
    "unknown_answer":      "HERMES_UNKNOWN_ANSWER_PROTOCOL.md",
    "scout_dispatch":      "HERMES_SCOUT_DISPATCH_CONTRACT.md",
    "prompt_generation":   "HERMES_PROMPT_GENERATION_CONTRACT.md",
    "failure_learning":    "HERMES_FAILURE_LEARNING_PROTOCOL.md",
}

_BEHAVIOR_RULES_SUMMARY = """
Hermes is Ray's CFO/operator. Rules:
1. Respond in plain language by default.
2. Understand natural messages without exact commands.
3. Use conversation context for follow-ups.
4. Dispatch scouts for unknowns — never guess.
5. Create implementation prompts when asked.
6. Log failures as training examples.
7. Never produce evidence dumps or generic fallbacks.
8. Never publish, email, spend, deploy, or run live trading without Ray approval.
9. Exact commands still work — CFO brain only activates for natural language.
"""

_PLAIN_LANGUAGE_RULES_SUMMARY = """
Plain language rules:
1. Answer first — lead with the answer, not the process.
2. 5 bullets max by default. Offer more on request.
3. No jargon. No artifact inventories. No HERMES REPORT format unless asked.
4. Default format: PLAIN ANSWER / What it means / My recommendation / What I can do next.
5. Simplify on request — call simplify_response_text() and lead with Simple version:.
"""

_UNKNOWN_ANSWER_RULES_SUMMARY = """
Unknown answer rules:
1. If no verified evidence → dispatch scout immediately.
2. Never guess or produce an evidence dump.
3. Say: I DON'T HAVE VERIFIED EVIDENCE YET
4. Add to research queue. Assign scout. Tell Ray how to check back.
5. No stale Executive Memory as substitute for verified data.
"""

_PROMPT_GENERATION_RULES_SUMMARY = """
Prompt generation rules:
1. Detect: 'create a prompt for Claude', 'give me a prompt', 'what should I send Claude'.
2. Produce IMPLEMENTATION PROMPT with: Goal, Context, Requirements, Safety, Tests, Final report.
3. Include current Hermes state in context.
4. Never include credentials or private data in the prompt.
"""


def load_cfo_doctrine() -> dict[str, str]:
    """Load all doctrine files. Returns dict of {name: content}."""
    loaded: dict[str, str] = {}
    for name, filename in _DOCTRINE_FILES.items():
        path = _DOCTRINE_DIR / filename
        try:
            loaded[name] = path.read_text(encoding="utf-8") if path.exists() else ""
        except Exception:
            loaded[name] = ""
    return loaded


def get_cfo_behavior_rules() -> str:
    """Return a summary of CFO behavior rules for use in response construction."""
    return _BEHAVIOR_RULES_SUMMARY.strip()


def get_plain_language_rules() -> str:
    """Return plain language rules summary."""
    return _PLAIN_LANGUAGE_RULES_SUMMARY.strip()


def get_unknown_answer_rules() -> str:
    """Return unknown answer protocol rules."""
    return _UNKNOWN_ANSWER_RULES_SUMMARY.strip()


def get_prompt_generation_rules() -> str:
    """Return prompt generation rules."""
    return _PROMPT_GENERATION_RULES_SUMMARY.strip()


def doctrine_files_exist() -> dict[str, bool]:
    """Return dict of {doctrine_name: exists} for all doctrine files."""
    return {
        name: (_DOCTRINE_DIR / filename).exists()
        for name, filename in _DOCTRINE_FILES.items()
    }
