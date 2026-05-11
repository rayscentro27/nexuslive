"""
hermes_model_router.py — Maps Hermes intents to models and provides AI synthesis.

Architecture:
  - Simple status checks  → deterministic only (no AI)
  - Reasoning/summary     → qwen3:8b via Ollama (fallback: llama3.2:3b)
  - Code tasks            → Codex CLI task brief (no AI writing code)

Hermes never asks a model to write or review code directly.
Code tasks produce a structured brief that the operator gives to Codex CLI.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("HermesModelRouter")

# ── Intent classification ──────────────────────────────────────────────────────

# Intents that benefit from AI synthesis (qwen3:8b)
REASONING_INTENTS: frozenset[str] = frozenset({
    "summarize_recent_activity",
    "next_best_move",
    "pilot_readiness",
    "task_brief_generation",
    "complex_reasoning",
    "recommendation",
})

# Intents handled by Codex CLI — Hermes generates a task brief only
CODEX_INTENTS: frozenset[str] = frozenset({
    "code_task",
    "code_review",
})

# Intents handled deterministically — no AI call
DETERMINISTIC_INTENTS: frozenset[str] = frozenset({
    "health_check",
    "worker_status",
    "queue_status",
    "trading_lab_status",
    "communication_health",
    "funding_status",
    "credit_workflow_status",
    "grant_research_status",
    "research_task",
    "run_tests",
})


def model_class_for(intent: str) -> str:
    """Return 'reasoning', 'codex_cli', or 'deterministic'."""
    if intent in CODEX_INTENTS:
        return "codex_cli"
    if intent in REASONING_INTENTS:
        return "reasoning"
    return "deterministic"


def model_name_for(intent: str) -> str:
    """Return the Ollama model name to use for a given intent."""
    mc = model_class_for(intent)
    if mc == "reasoning":
        return os.getenv("HERMES_REASONING_MODEL", "qwen3:8b")
    if mc == "deterministic":
        return os.getenv("HERMES_DEFAULT_MODEL", "llama3.2:3b")
    return "codex_cli"


# ── System prompts ─────────────────────────────────────────────────────────────

_SYSTEM_BASE = (
    "You are Hermes, the AI Chief of Staff for a business intelligence system. "
    "You provide structured, concise executive-level analysis. "
    "Never write code. Never speculate beyond the data provided. "
    "Respond in 3-5 sentences maximum unless a structured format is requested."
)

_SYSTEM_REASONING = _SYSTEM_BASE + (
    " Your role is to synthesize operational data into a clear recommendation. "
    "Lead with the most important finding. End with one specific action."
)

_SYSTEM_SUMMARY = _SYSTEM_BASE + (
    " Summarize what is happening, what matters most, and what the operator should focus on next."
)


def _build_synthesis_prompt(intent: str, evidence: list[str], context: str = "") -> str:
    evidence_text = "\n".join(f"- {e}" for e in evidence)
    if intent == "next_best_move":
        return (
            f"Operational snapshot:\n{evidence_text}\n\n"
            f"Based on this data, what is the single best next move for the operator? "
            f"State it clearly. Include the reason and any risk."
        )
    if intent == "summarize_recent_activity":
        return (
            f"Recent system activity:\n{evidence_text}\n\n"
            f"{context}\n\n"
            f"Write an executive summary: what happened, what stands out, and one recommendation."
        )
    if intent == "pilot_readiness":
        return (
            f"Pilot readiness check results:\n{evidence_text}\n\n"
            f"Assess whether this system is ready for a 10-user pilot. "
            f"State: ready / not ready / ready with caveats. Give one action if not fully ready."
        )
    # Generic reasoning fallback
    return (
        f"System data:\n{evidence_text}\n\n"
        f"{context}\n\n"
        f"Provide a concise analysis and one recommended action."
    )


# ── AI synthesis ───────────────────────────────────────────────────────────────

def synthesize(
    intent:   str,
    evidence: list[str],
    context:  str = "",
    timeout:  int = 90,
) -> dict:
    """
    Generate an AI-synthesized recommendation for reasoning intents.

    Returns:
        {
            "success":       bool,
            "recommendation": str,
            "model":         str,
            "duration_s":    float,
            "fallback_used": bool,
            "fallback_reason": str,
            "error":         str | None,
        }
    """
    mc = model_class_for(intent)

    if mc == "deterministic":
        return {
            "success":        True,
            "recommendation": "",  # caller uses its own deterministic rec
            "model":          "deterministic",
            "duration_s":     0.0,
            "fallback_used":  False,
            "fallback_reason": "",
            "error":          None,
        }

    if mc == "codex_cli":
        brief = generate_codex_brief(intent, evidence, context)
        return {
            "success":        True,
            "recommendation": brief,
            "model":          "codex_cli",
            "duration_s":     0.0,
            "fallback_used":  False,
            "fallback_reason": "",
            "error":          None,
        }

    # Reasoning path — try qwen3:8b, fall back to llama3.2:3b
    from lib.hermes_ollama_client import call_with_fallback, HERMES_REASONING_MODEL, HERMES_DEFAULT_MODEL

    prompt = _build_synthesis_prompt(intent, evidence, context)
    system = _SYSTEM_REASONING if intent in {"next_best_move", "pilot_readiness"} else _SYSTEM_SUMMARY

    result = call_with_fallback(
        prompt=prompt,
        primary_model=HERMES_REASONING_MODEL,
        fallback_model=HERMES_DEFAULT_MODEL,
        timeout=timeout,
        system=system,
    )

    recommendation = result.get("response") or ""
    if not result["success"]:
        logger.warning("AI synthesis failed for intent=%s: %s", intent, result.get("error"))
        recommendation = (
            f"[AI synthesis unavailable — {result.get('error', 'unknown error')}. "
            f"Deterministic data shown above.]"
        )

    return {
        "success":        result["success"],
        "recommendation": recommendation,
        "model":          result.get("model", "unknown"),
        "duration_s":     result.get("duration_s", 0.0),
        "fallback_used":  result.get("fallback_used", False),
        "fallback_reason": result.get("fallback_reason", ""),
        "error":          result.get("error"),
    }


# ── Codex CLI brief generator ──────────────────────────────────────────────────

def generate_codex_brief(intent: str, evidence: list[str], context: str = "") -> str:
    """
    Generate a Codex CLI task brief for code tasks.
    Hermes never asks a model to write code — it produces a brief for the operator to run.
    """
    evidence_text = "\n".join(f"- {e}" for e in evidence) if evidence else "(no additional context)"
    lines = [
        "=== CODEX CLI TASK BRIEF ===",
        "",
        f"Task type  : {intent.replace('_', ' ').upper()}",
        "",
        "Context:",
        evidence_text,
    ]
    if context:
        lines += ["", "Additional context:", context]

    lines += [
        "",
        "To execute with Codex CLI, run:",
        "  codex \"<paste your specific instruction here>\"",
        "",
        "Or with Claude Code:",
        "  claude \"<paste your specific instruction here>\"",
        "",
        "IMPORTANT: Hermes does not write or review code.",
        "This brief is for Codex CLI or Claude Code to action.",
        "==========================="
    ]
    return "\n".join(lines)
