"""
Hermes Strategic Conversation Service
Provides ChatGPT-style strategic discussion for Ray when away from the office.
Loads Nexus context (latest artifacts, mistake memory, CEO packet) before answering.
All conversations saved to docs/reports/hermes_conversations/.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CONV_DIR = Path("docs/reports/hermes_conversations")
CONV_DIR.mkdir(parents=True, exist_ok=True)

# Artifact lookup helpers
ARTIFACT_HINTS: dict[str, str] = {
    "ceo_packet":       "docs/reports/ceo_review",
    "credit_repair":    "docs/reports/learn_by_doing/credit_repair",
    "risk_analysis":    "docs/reports/risky_opportunities",
    "github_trends":    "docs/reports/github_trends",
    "compliance":       "docs/reports/learn_by_doing/credit_repair",
    "monetization":     "docs/reports/monetization",
    "content":          "docs/content/approval_packets",
    "mistake_memory":   "docs/reports/hermes_mistake_memory.json",
    "demo_exec":        "integrations/oanda_demo/reports",
    "premium_blockers": "docs/reports/premium_blockers",
    "ray_feedback":     "docs/reports/ray_feedback",
}

SYSTEM_CONTEXT = """You are Hermes, the strategic operating partner for Ray's Nexus AI system.
Ray is asking you for strategic advice or operational guidance while away from the office.

Rules:
- Only answer based on real Nexus artifacts. If you don't have an artifact to cite, say so.
- Never guarantee outcomes (credit scores, income, trading results).
- Never label strategies client_safe unless compliance review is complete.
- If a question requires action beyond analysis, create an action handoff item.
- Use educational framing for credit/funding topics.
- Be direct. Ray wants decisions, not summaries.

Available context will be injected below.
"""


def _latest_file(directory: str, pattern: str = "*.md") -> str | None:
    d = Path(directory)
    if not d.exists():
        return None
    files = sorted(d.glob(pattern))
    return str(files[-1]) if files else None


def _load_artifact_context(topic_hints: list[str]) -> str:
    snippets = []
    for hint in topic_hints:
        folder = ARTIFACT_HINTS.get(hint)
        if not folder:
            continue
        if folder.endswith(".json"):
            p = Path(folder)
            if p.exists():
                try:
                    data = json.loads(p.read_text())
                    snippets.append(f"[{hint}]\n{json.dumps(data, indent=2)[:1200]}")
                except Exception:
                    pass
        else:
            path = _latest_file(folder, "*.md") or _latest_file(folder, "*.json")
            if path:
                try:
                    text = Path(path).read_text()[:1500]
                    snippets.append(f"[{hint} — {Path(path).name}]\n{text}")
                except Exception:
                    pass
    return "\n\n---\n".join(snippets) if snippets else "(no context loaded)"


def _detect_topics(message: str) -> list[str]:
    msg = message.lower()
    found = []
    mapping = {
        "ceo_packet":       ["ceo", "packet", "review", "briefing"],
        "credit_repair":    ["credit", "repair", "funding", "readiness"],
        "risk_analysis":    ["risk", "risky", "opportunity"],
        "github_trends":    ["github", "trend", "repo"],
        "compliance":       ["compliance", "croa", "legal", "strategy status"],
        "monetization":     ["monetiz", "revenue", "30 day", "plan"],
        "content":          ["content", "youtube", "newsletter", "hook", "script"],
        "mistake_memory":   ["mistake", "error", "pattern", "hermes fail"],
        "demo_exec":        ["oanda", "demo", "trade", "broker"],
        "premium_blockers": ["blocker", "beehiiv", "paid tool", "alternative"],
        "ray_feedback":     ["feedback", "lesson", "remember"],
    }
    for key, keywords in mapping.items():
        if any(k in msg for k in keywords):
            found.append(key)
    return found or ["ceo_packet"]


class HermesConversationService:
    """
    Main entry point for strategic Ray ↔ Hermes conversations.
    """

    def __init__(self) -> None:
        self._history: list[dict] = []

    def chat(self, message: str, save: bool = True) -> dict[str, Any]:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        topics = _detect_topics(message)
        context = _load_artifact_context(topics)

        prompt = (
            SYSTEM_CONTEXT
            + "\n\n=== NEXUS CONTEXT ===\n"
            + context
            + "\n\n=== RAY'S MESSAGE ===\n"
            + message
        )

        reply_text = self._llm(prompt)
        self._history.append({"role": "ray", "content": message, "ts": ts})
        self._history.append({"role": "hermes", "content": reply_text, "ts": ts})

        result: dict[str, Any] = {
            "ts": ts,
            "message": message,
            "topics_loaded": topics,
            "reply": reply_text,
            "context_sources": topics,
        }

        if save:
            path = self._save_conversation(result, ts)
            result["saved_to"] = str(path)

        return result

    def get_history(self) -> list[dict]:
        return list(self._history)

    # ── LLM call ──────────────────────────────────────────────────────────────

    def _llm(self, prompt: str) -> str:
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parents[1]))
            from lib.llm_router import llm_call
            return llm_call(prompt, tier="standard", timeout=60)
        except Exception:
            pass
        # Fallback: try direct openrouter import
        try:
            from lib.nexus_llm_client import query as _q
            return _q(prompt)
        except Exception as e:
            return f"[LLM_ERROR: {e}] — Hermes could not generate a response. Check LLM provider config."

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save_conversation(self, result: dict, ts: str) -> Path:
        path = CONV_DIR / f"hermes_conversation_{ts}.json"
        path.write_text(json.dumps(result, indent=2, default=str))
        return path
