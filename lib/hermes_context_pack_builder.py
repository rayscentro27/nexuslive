"""
hermes_context_pack_builder.py
================================
Build compact evidence context packs for Hermes provider calls.

Purpose: local Ollama and other weak models must receive compact context (≤3000
tokens), not the full Nexus memory. This module classifies the user's question,
retrieves only the relevant evidence files, and returns a compact pack.

TOKEN BUDGET:
  local_ollama     → max 2500 tokens
  hermes_gateway   → max 8000 tokens
  openai_api       → max 12000 tokens
  evidence_only    → no LLM needed

INTENT MAP:
  greeting, today_recommendation, claude_code_work, youtube_status,
  source_intake_status, thirty_day_goals, trading_recommendation,
  nexus_project, information_sources, provider_status, monetization,
  blocker, general_strategy, source_review, scout_dispatch
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent

# Rough estimate: 1 token ≈ 4 characters
_CHARS_PER_TOKEN = 4

TOKEN_BUDGET: dict[str, int] = {
    "local_ollama":   2500,
    "hermes_gateway": 8000,
    "openai_api":     12000,
    "evidence_only":  0,
}


# ── Intent classifier ─────────────────────────────────────────────────────────

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "greeting":            ["good morning", "hello", "morning", "hi hermes", "hey hermes", "gm", "greetings"],
    "today_recommendation":["what should i work on", "what should we work on", "today", "focus today",
                            "priorities today", "next best move", "recommend we work on", "top priorities"],
    "claude_code_work":    ["claude code", "what did claude", "handoff", "what was built", "yesterday's progress",
                            "show handoffs", "recent handoffs", "latest handoff"],
    "youtube_status":      ["youtube status", "youtube intake", "youtube source", "last youtube channel",
                            "processed youtube", "youtube channel", "youtube registry", "show youtube"],
    "source_intake_status":["source intake", "intake status", "last link", "what happened to the link",
                            "what did i send", "batch review", "registered source"],
    "thirty_day_goals":    ["30 day", "30-day", "monthly goals", "revenue plan", "monthly target",
                            "this month", "monthly revenue"],
    "trading_recommendation":["trading strategy", "forex strategy", "paper trade", "oanda demo",
                              "vibe-trading", "vibe trading", "backtest", "best strategy"],
    "nexus_project":       ["what is nexus", "nexus project", "nexus overview", "nexus mission",
                            "tell me about nexus"],
    "information_sources": ["where do you get", "information sources", "what are your sources",
                            "how do you know", "where does this data"],
    "provider_status":     ["provider mode", "what brain", "provider status", "what ai", "which model",
                            "hermes gateway", "show provider", "use reliable", "use gateway",
                            "disable gateway", "enable gateway", "use local", "use evidence"],
    "monetization":        ["monetization", "make money", "revenue", "affiliate", "income strategy",
                            "what can make money", "business goals"],
    "blocker":             ["blocked", "stuck", "blocker", "can't proceed", "problem with"],
    "general_strategy":    ["what should nexus do", "what next", "what should we do",
                            "strategic recommendation", "nexus strategy"],
    "source_review":       ["review", "analyze this", "check this link", "what do you think about this"],
    "scout_dispatch":      ["scout", "dispatch", "run scout", "intelligence scout"],
}


def classify_question(message: str) -> str:
    """Return the intent string that best matches the message."""
    text = (message or "").lower().strip()
    scores: dict[str, int] = {}
    for intent, keywords in _INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score:
            scores[intent] = score
    if not scores:
        return "general_strategy"
    return max(scores, key=lambda k: scores[k])


# ── Token utilities ───────────────────────────────────────────────────────────

def estimate_text_tokens(text: str) -> int:
    return max(1, len(text or "") // _CHARS_PER_TOKEN)


def truncate_safely(text: str, max_tokens: int) -> str:
    max_chars = max_tokens * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_newline = truncated.rfind("\n")
    if last_newline > max_chars // 2:
        truncated = truncated[:last_newline]
    return truncated + "\n[...truncated for context limit]"


# ── Evidence retrievers ───────────────────────────────────────────────────────

def _read_file_safe(path: Path, max_chars: int = 2000) -> str:
    try:
        text = path.read_text(errors="replace")
        return text[:max_chars] if len(text) > max_chars else text
    except Exception:
        return ""


def _handoffs_summary(max_files: int = 5, max_chars_each: int = 300) -> list[dict]:
    handoff_dir = _ROOT / "docs" / "reports" / "handoffs"
    if not handoff_dir.exists():
        return []
    files = sorted(handoff_dir.glob("claude_code_handoff_*.md"), reverse=True)[:max_files]
    items = []
    for f in files:
        content = _read_file_safe(f, max_chars_each)
        first_line = next((l.strip() for l in content.splitlines()
                           if l.strip() and not l.startswith("#") and "intake id" not in l.lower()), f.stem)
        items.append({
            "path": str(f.relative_to(_ROOT)),
            "title": first_line[:80],
            "snippet": content[:200],
        })
    return items


def _intake_summary(max_records: int = 8) -> list[dict]:
    log = _ROOT / "docs" / "reports" / "intake" / "telegram_source_intake.jsonl"
    if not log.exists():
        return []
    try:
        lines = log.read_text().splitlines()[-max_records:]
        return [json.loads(l) for l in lines if l.strip()]
    except Exception:
        return []


def _revenue_plan_snippet(max_chars: int = 800) -> dict:
    mono_dir = _ROOT / "docs" / "reports" / "monetization"
    if not mono_dir.exists():
        return {"found": False, "content": ""}
    plans = sorted(mono_dir.glob("30_day_revenue_plan_*.md"), reverse=True)
    if not plans:
        return {"found": False, "content": ""}
    return {"found": True, "path": str(plans[0].relative_to(_ROOT)),
            "content": _read_file_safe(plans[0], max_chars)}


def _nexus_brief_snippet(max_chars: int = 1000) -> dict:
    brief = _ROOT / "docs" / "reports" / "core" / "nexus_project_brief.md"
    if not brief.exists():
        return {"found": False, "content": ""}
    return {"found": True, "path": str(brief.relative_to(_ROOT)),
            "content": _read_file_safe(brief, max_chars)}


def _trading_evidence() -> dict:
    vibe_dir = _ROOT / "integrations" / "vibe_trading" / "reports"
    oanda_dir = _ROOT / "integrations" / "oanda_demo" / "reports"
    result: dict[str, Any] = {}
    if vibe_dir.exists():
        files = sorted(vibe_dir.glob("backtest_*.json"), reverse=True)
        if files:
            result["backtest_path"] = str(files[0].relative_to(_ROOT))
            try:
                d = json.loads(files[0].read_text())
                result["backtest_timestamp"] = d.get("timestamp", "")[:10]
                result["backtest_safety"] = d.get("safety_mode", "")
            except Exception:
                pass
    if oanda_dir.exists():
        files = sorted(oanda_dir.glob("demo_execution_packet_*.json"), reverse=True)
        if files:
            result["oanda_path"] = str(files[0].relative_to(_ROOT))
            try:
                d = json.loads(files[0].read_text())
                result["oanda_strategy"] = d.get("strategy", {})
                result["oanda_order_blocked"] = not d.get("order_result", {}).get("ok", False)
            except Exception:
                pass
    return result


def _directory_inventory() -> dict[str, int]:
    dirs = [
        "docs/reports/evidence",
        "docs/reports/handoffs",
        "docs/reports/intake",
        "docs/reports/monetization",
        "docs/reports/core",
        "artifacts",
        "reports/knowledge_intake",
    ]
    out: dict[str, int] = {}
    for rel in dirs:
        p = _ROOT / rel
        if p.exists():
            try:
                out[rel] = len(list(p.iterdir()))
            except Exception:
                out[rel] = 0
    return out


# ── Context pack builder ──────────────────────────────────────────────────────

@dataclass
class ContextPack:
    question: str
    intent: str
    evidence_items: list[dict] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    safe_next_actions: list[str] = field(default_factory=list)
    approval_boundaries: list[str] = field(default_factory=list)
    token_estimate: int = 0
    provider_instructions: str = ""

    def as_prompt_text(self) -> str:
        """Render as compact text for LLM system prompt."""
        lines = [
            f"CONTEXT PACK — intent: {self.intent}",
            f"Question: {self.question}",
            "",
        ]
        if self.evidence_items:
            lines.append("Evidence:")
            for item in self.evidence_items[:8]:
                label = item.get("label", "")
                content = item.get("content", "")
                if label:
                    lines.append(f"[{label}] {content}")
        if self.artifact_paths:
            lines.append("")
            lines.append("Source paths: " + " | ".join(self.artifact_paths[:5]))
        if self.missing_evidence:
            lines.append("Missing: " + "; ".join(self.missing_evidence))
        if self.approval_boundaries:
            lines.append("Approval required for: " + "; ".join(self.approval_boundaries))
        return "\n".join(lines)


def retrieve_relevant_evidence(message: str, intent: str) -> dict[str, Any]:
    """Retrieve evidence relevant to the detected intent."""
    ev: dict[str, Any] = {"intent": intent}

    if intent == "greeting":
        ev["inventory"] = _directory_inventory()

    elif intent in ("today_recommendation", "general_strategy"):
        ev["handoffs"] = _handoffs_summary(max_files=3, max_chars_each=200)
        ev["revenue_plan"] = _revenue_plan_snippet(max_chars=400)
        ev["inventory"] = _directory_inventory()

    elif intent == "claude_code_work":
        ev["handoffs"] = _handoffs_summary(max_files=5, max_chars_each=400)

    elif intent == "youtube_status":
        ev["intake"] = _intake_summary(max_records=8)

    elif intent == "source_intake_status":
        ev["intake"] = _intake_summary(max_records=10)

    elif intent == "thirty_day_goals":
        ev["revenue_plan"] = _revenue_plan_snippet(max_chars=1200)

    elif intent == "trading_recommendation":
        ev["trading"] = _trading_evidence()

    elif intent == "nexus_project":
        ev["nexus_brief"] = _nexus_brief_snippet(max_chars=1200)

    elif intent == "information_sources":
        ev["inventory"] = _directory_inventory()

    elif intent == "monetization":
        ev["revenue_plan"] = _revenue_plan_snippet(max_chars=600)
        ev["inventory"] = _directory_inventory()

    elif intent == "blocker":
        ev["handoffs"] = _handoffs_summary(max_files=2, max_chars_each=200)

    elif intent in ("source_review", "scout_dispatch"):
        ev["intake"] = _intake_summary(max_records=5)

    else:
        ev["inventory"] = _directory_inventory()

    return ev


def build_context_pack(
    message: str,
    intent: str | None = None,
    max_tokens: int = 2500,
) -> ContextPack:
    """
    Build a compact context pack for the given message.

    max_tokens controls total size of prompt text for the provider.
    For local_ollama use max_tokens=2500. For gateway use max_tokens=8000.
    """
    if not intent:
        intent = classify_question(message)

    ev = retrieve_relevant_evidence(message, intent)
    pack = ContextPack(question=message, intent=intent)

    # Translate evidence dict into evidence_items list
    items: list[dict] = []
    paths: list[str] = []
    missing: list[str] = []
    next_actions: list[str] = []
    approval: list[str] = []

    if "inventory" in ev:
        inv = ev["inventory"]
        found = [f"{k} ({v} items)" for k, v in inv.items() if v > 0]
        if found:
            items.append({"label": "artifact_inventory", "content": ", ".join(found)})
            paths.extend(k for k, v in inv.items() if v > 0)
        else:
            missing.append("no artifact directories populated yet")

    if "handoffs" in ev:
        handoffs = ev["handoffs"]
        if handoffs:
            for h in handoffs[:5]:
                items.append({"label": "handoff", "content": f"{h['path']}: {h['title']}"})
                paths.append(h["path"])
        else:
            missing.append("no claude_code handoff files found")
            next_actions.append("create a handoff after next Claude Code session")

    if "intake" in ev:
        intake = ev["intake"]
        if intake:
            for r in intake[:5]:
                uid = str(r.get("intake_id", "?"))[:12]
                url = str(r.get("url", "?"))[:60]
                status = r.get("status", "?")
                items.append({"label": "intake", "content": f"{uid} | {status} | {url}"})
            paths.append("docs/reports/intake/telegram_source_intake.jsonl")
        else:
            missing.append("source intake log empty")

    if "revenue_plan" in ev:
        rp = ev["revenue_plan"]
        if rp.get("found"):
            items.append({"label": "revenue_plan", "content": rp["content"][:600]})
            paths.append(rp["path"])
        else:
            missing.append("30-day revenue plan not found")
            next_actions.append("run `nexus monetization plan` to generate")

    if "nexus_brief" in ev:
        nb = ev["nexus_brief"]
        if nb.get("found"):
            items.append({"label": "nexus_brief", "content": nb["content"][:800]})
            paths.append(nb["path"])
        else:
            missing.append("nexus_project_brief.md not found")

    if "trading" in ev:
        td = ev["trading"]
        if td.get("backtest_path"):
            items.append({"label": "backtest", "content": f"path={td['backtest_path']} safety={td.get('backtest_safety','')}"})
            paths.append(td["backtest_path"])
        if td.get("oanda_path"):
            strat = td.get("oanda_strategy", {})
            blocked = td.get("oanda_order_blocked", True)
            items.append({"label": "oanda_demo", "content": f"path={td['oanda_path']} instrument={strat.get('instrument','')} win_rate={strat.get('win_rate','')} order_blocked={blocked}"})
            paths.append(td["oanda_path"])
        if not td:
            missing.append("vibe_trading and oanda_demo reports not found")
            next_actions.append("run `nexus trading backtest` to generate")
        approval.append("live trading requires Ray approval")

    pack.evidence_items = items
    pack.artifact_paths = list(dict.fromkeys(paths))  # dedupe, preserve order
    pack.missing_evidence = missing
    pack.safe_next_actions = next_actions
    pack.approval_boundaries = approval

    # Enforce token budget
    prompt_text = pack.as_prompt_text()
    token_est = estimate_text_tokens(prompt_text)
    if token_est > max_tokens:
        # Trim evidence items until under budget
        while pack.evidence_items and estimate_text_tokens(pack.as_prompt_text()) > max_tokens:
            pack.evidence_items.pop()
        pack.evidence_items.append({"label": "note", "content": "...evidence trimmed to fit token budget"})

    pack.token_estimate = estimate_text_tokens(pack.as_prompt_text())
    pack.provider_instructions = (
        f"Answer from the context pack above. "
        f"State which artifact paths you used. "
        f"Say 'Missing evidence' for anything not in the pack. "
        f"Do not invent data not present."
    )
    return pack


def build_evidence_only_response(message: str, context_pack: ContextPack | None = None) -> str:
    """Build a clean evidence-only response without calling any LLM."""
    if context_pack is None:
        intent = classify_question(message)
        context_pack = build_context_pack(message, intent)

    lines = ["I can answer from verified artifacts.", ""]

    if context_pack.artifact_paths:
        lines.append("Evidence used:")
        for p in context_pack.artifact_paths[:5]:
            lines.append(f"  • {p}")
        lines.append("")

    if context_pack.evidence_items:
        lines.append("Summary:")
        for item in context_pack.evidence_items[:6]:
            label = item.get("label", "")
            content = item.get("content", "")
            if label and content:
                lines.append(f"  [{label}] {content[:120]}")
        lines.append("")

    if context_pack.missing_evidence:
        lines.append("Missing evidence:")
        for m in context_pack.missing_evidence:
            lines.append(f"  • {m}")
        lines.append("")

    if context_pack.safe_next_actions:
        lines.append("Next action:")
        for a in context_pack.safe_next_actions:
            lines.append(f"  • {a}")

    return "\n".join(lines)


def build_provider_prompt(message: str, context_pack: ContextPack) -> str:
    """Build the full system+user prompt to send to a provider."""
    system = (
        "You are Hermes, Nexus AI chief of staff. "
        "Answer only from the provided context pack. "
        "If the evidence is missing, say so clearly. "
        "Do not invent data. Do not hallucinate. "
        "State which artifact paths you used in your answer."
    )
    context = context_pack.as_prompt_text()
    return f"{system}\n\n{context}\n\nQuestion: {message}"


def summarize_artifacts_for_context(artifacts: list[dict], max_items: int = 8) -> str:
    """Format a list of artifact dicts into a compact context string."""
    if not artifacts:
        return "No artifacts found."
    lines = []
    for a in artifacts[:max_items]:
        label = a.get("label") or a.get("type") or "artifact"
        path = a.get("path") or a.get("file") or ""
        content = a.get("content") or a.get("summary") or ""
        line = f"[{label}]"
        if path:
            line += f" {path}"
        if content:
            line += f": {str(content)[:80]}"
        lines.append(line)
    return "\n".join(lines)


def prioritize_evidence(items: list[dict], intent: str) -> list[dict]:
    """Sort evidence items by relevance to the given intent."""
    intent_labels: dict[str, list[str]] = {
        "trading_recommendation": ["backtest", "oanda_demo", "trading"],
        "claude_code_work":       ["handoff"],
        "thirty_day_goals":       ["revenue_plan"],
        "nexus_project":          ["nexus_brief"],
        "youtube_status":         ["intake"],
        "source_intake_status":   ["intake"],
        "information_sources":    ["artifact_inventory"],
    }
    preferred = intent_labels.get(intent, [])
    if not preferred:
        return items

    def rank(item: dict) -> int:
        label = item.get("label", "")
        for i, pref in enumerate(preferred):
            if pref in label:
                return i
        return len(preferred) + 1

    return sorted(items, key=rank)
