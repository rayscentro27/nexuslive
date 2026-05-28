"""
hermes_reasoning_layer.py
==========================
Accept Ray's question + truth evidence packet, select a provider via
hermes_provider_policy, and reason over evidence.

Rules:
  - Never creates operational facts without evidence
  - Always labels the provider used in the response
  - Labels unsupported assumptions
  - OpenRouter requires HERMES_ALLOW_OPENROUTER_FALLBACK=true
  - If no LLM available, returns evidence-only summary (no hallucination fallback)
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

from lib.hermes_provider_policy import ProviderType, get_policy


EVIDENCE_RULES = (
    "EVIDENCE RULES — MANDATORY: "
    "(E1) NEVER fabricate task names, approval counts, pending items, GitHub commit hashes, "
    "     slide numbers, trading system names, SBA deadlines, YouTube video counts, or any operational detail. "
    "(E2) If you do not have a real artifact path, Supabase ID, or workflow_output_id to back a claim — "
    "     DO NOT make the claim. Instead say: "
    "     'I don't have a verified artifact for that. Ask me to run a status check.' "
    "(E3) NEVER invent names like 'NitroTrades', 'Slide 12', or fake pending-approval counts. "
    "(E4) NEVER say '6 pending approvals' or any specific number unless the evidence packet below "
    "     contains that exact count from a verified source. "
    "(E5) For any question about approvals, YouTube sources, evidence, or task completions — "
    "     respond ONLY from the evidence packet below. "
    "     If the evidence packet does not contain the answer, say: "
    "     'No verified data for that yet. Run: show source intake' "
)

IDENTITY_RULES = (
    "You are Hermes, the AI Chief of Staff for Nexus — Raymond's private business intelligence "
    "and credit platform. You are NOT a generic assistant. You ONLY answer in the context of "
    "Nexus operations. Personality: calm, sharp, strategic. "
    "CONVERSATION RULES: "
    "(1) Short — 2-4 sentences max unless the user asks for detail. "
    "    No markdown headers in conversational mode. "
    "(2) Operational first — reference only what is in the evidence packet. "
    "    Do not invent operational state. "
    "(3) AI providers are Nexus-internal only. Never name external AI products not in evidence. "
    "(4) For 'what to focus on today' — give priorities ONLY from evidence packet. "
    "    Never invent priorities. "
    "(5) Conversational tone — chief of staff, not a report generator. "
    "    Avoid 'Summary:', 'Here is a list:'. "
    "(6) Trading topics: reference only real verified data from evidence packet. "
    "    Do NOT reference 'NitroTrades' or any external trading system unless it appears in evidence. "
    "(7) Grant/funding topics: reference only grants from evidence packet. "
    "    Do NOT invent SBA deadlines, Hello Alice statuses, or funding amounts. "
)


@dataclass
class ReasoningResult:
    reply: str
    provider_used: ProviderType
    model_used: str = ""
    evidence_refs: int = 0
    is_evidence_only: bool = False
    provider_disclosed: bool = False


def _build_system_prompt(evidence_text: str, ops_context: str = "") -> str:
    parts = [IDENTITY_RULES, EVIDENCE_RULES]
    if evidence_text:
        parts.append(f"\nVERIFIED EVIDENCE PACKET:\n{evidence_text}\n")
    if ops_context:
        parts.append(f"\nOPS CONTEXT (reference counts only, NOT evidence for specific claims):\n{ops_context}\n")
    return "".join(parts)


# ── Provider-specific callers ─────────────────────────────────────────────────

def _call_openai(
    messages: list[dict],
    model: str,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    timeout: int = 45,
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": 350,
        "temperature": 0.4,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()


def _call_ollama(
    messages: list[dict],
    model: str,
    host: str,
    timeout: int = 60,
) -> str:
    url = f"{host.rstrip('/')}/api/chat"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.4, "num_predict": 350},
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return str((data.get("message") or {}).get("content") or "").strip()


def _call_openrouter(
    messages: list[dict],
    model: str,
    api_key: str,
    base_url: str = "https://openrouter.ai/api/v1",
    timeout: int = 45,
) -> str:
    return _call_openai(messages, model, api_key, base_url=base_url, timeout=timeout)


# ── Reasoning entry point ─────────────────────────────────────────────────────

def reason(
    question: str,
    evidence_text: str = "",
    ops_context: str = "",
    history: list[dict] | None = None,
    is_followup: bool = False,
) -> ReasoningResult:
    """
    Reason over evidence using the best available provider.

    Args:
        question:       Ray's raw question
        evidence_text:  Pre-formatted evidence summary from TruthPacket
        ops_context:    Ops memory snippet (NOT evidence — counts only)
        history:        Prior conversation turns [{"role": ..., "content": ...}]
        is_followup:    Whether this is a follow-up to a prior turn

    Returns:
        ReasoningResult with reply, provider_used, model_used
    """
    policy = get_policy()
    provider = policy.best_for_strategic()

    system_prompt = _build_system_prompt(evidence_text, ops_context)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if history:
        turns = history[-6:] if is_followup else history[-3:]
        messages.extend(turns)
    messages.append({"role": "user", "content": question})

    evidence_count = len([ln for ln in evidence_text.splitlines() if ln.strip().startswith("[verified")])

    # ── chatgpt_auth ──────────────────────────────────────────────────────────
    if provider == "chatgpt_auth":
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not openai_key:
            from pathlib import Path as _P
            token_file = _P.home() / ".openai" / "token"
            if token_file.exists():
                openai_key = token_file.read_text().strip()
        if openai_key:
            try:
                reply = _call_openai(messages, model, openai_key)
                return ReasoningResult(
                    reply=reply,
                    provider_used="chatgpt_auth",
                    model_used=model,
                    evidence_refs=evidence_count,
                    provider_disclosed=True,
                )
            except Exception as e:
                pass  # fall through to next provider
        provider = policy.best_available()  # re-select excluding chatgpt_auth

    # ── codex_auth ────────────────────────────────────────────────────────────
    if provider == "codex_auth":
        codex_token = os.getenv("CODEX_AUTH_TOKEN", "").strip()
        if not codex_token:
            from pathlib import Path as _P
            codex_cfg = _P.home() / ".codex" / "auth.json"
            if codex_cfg.exists():
                try:
                    cfg = json.loads(codex_cfg.read_text())
                    codex_token = cfg.get("token") or cfg.get("api_key") or ""
                except Exception:
                    pass
        if codex_token:
            model = os.getenv("CODEX_MODEL", "gpt-4o-mini")
            try:
                reply = _call_openai(messages, model, codex_token)
                return ReasoningResult(
                    reply=reply,
                    provider_used="codex_auth",
                    model_used=model,
                    evidence_refs=evidence_count,
                    provider_disclosed=True,
                )
            except Exception:
                pass

    # ── openclaw_chatgpt_auth ─────────────────────────────────────────────────
    if provider == "openclaw_chatgpt_auth":
        from pathlib import Path as _P
        openclaw_cfg = _P.home() / ".openclaw" / "config.json"
        try:
            cfg = json.loads(openclaw_cfg.read_text()) if openclaw_cfg.exists() else {}
            oc_key = cfg.get("api_key") or cfg.get("openai_key") or os.getenv("OPENCLAW_API_KEY", "")
            oc_base = cfg.get("base_url") or "https://api.openai.com/v1"
            oc_model = cfg.get("model") or "gpt-4o-mini"
            if oc_key:
                reply = _call_openai(messages, oc_model, oc_key, base_url=oc_base)
                return ReasoningResult(
                    reply=reply,
                    provider_used="openclaw_chatgpt_auth",
                    model_used=oc_model,
                    evidence_refs=evidence_count,
                    provider_disclosed=True,
                )
        except Exception:
            pass

    # ── local_ollama ──────────────────────────────────────────────────────────
    if provider == "local_ollama":
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("HERMES_OLLAMA_MODEL",
                          os.getenv("HERMES_REASONING_MODEL", "qwen3:8b"))
        try:
            reply = _call_ollama(messages, model, host)
            return ReasoningResult(
                reply=reply,
                provider_used="local_ollama",
                model_used=model,
                evidence_refs=evidence_count,
                provider_disclosed=True,
            )
        except Exception:
            pass

    # ── openrouter ── only if explicitly allowed ──────────────────────────────
    if provider == "openrouter" and policy.openrouter_allowed:
        or_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        or_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        or_model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
        if or_key:
            try:
                reply = _call_openrouter(messages, or_model, or_key, base_url=or_base)
                return ReasoningResult(
                    reply=reply,
                    provider_used="openrouter",
                    model_used=or_model,
                    evidence_refs=evidence_count,
                    provider_disclosed=True,
                )
            except Exception:
                pass

    # ── evidence_only fallback ─────────────────────────────────────────────────
    if evidence_text:
        reply = (
            "No conversational LLM is available right now. "
            "Here is what I have verified:\n" + evidence_text[:800]
        )
    else:
        reply = (
            "No conversational LLM is available and no verified evidence was found. "
            "Run a status check: /status or 'show source intake'."
        )
    return ReasoningResult(
        reply=reply,
        provider_used="evidence_only",
        evidence_refs=evidence_count,
        is_evidence_only=True,
        provider_disclosed=True,
    )
