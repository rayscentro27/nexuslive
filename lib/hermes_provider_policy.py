"""
hermes_provider_policy.py
==========================
Provider selection for Hermes strategic reasoning and conversation.

Priority (highest to lowest):
  1. openai_api      — OpenAI REST API via OPENAI_API_KEY (standard paid API, not auth-login)
                       NOTE: this is an API-backed bridge, NOT a browser session or auth-login route.
                       A true auth-login route would use CHATGPT_ACCESS_TOKEN or browser cookies.
  2. codex_auth      — OpenAI Codex / Codex CLI auth
  3. openclaw_chatgpt_auth — OpenClaw ChatGPT auth wrapper
  4. local_ollama    — local Ollama (qwen3/llama) — safe for low-risk summarization
  5. openrouter      — DISABLED unless HERMES_ALLOW_OPENROUTER_FALLBACK=true

Environment variables:
  HERMES_PROVIDER_PRIORITY           — comma-separated override of default order
  HERMES_ALLOW_OPENROUTER_FALLBACK   — "true" to re-enable OpenRouter (default: false)
  HERMES_REQUIRE_APPROVAL_FOR_PAID_LLM — "true" to require Ray approval for paid providers
  HERMES_STRATEGIC_PROVIDER          — force a specific provider for strategic conversation
  HERMES_ROUTING_PROVIDER            — provider for routing/classification (default: rules)
  HERMES_SUMMARY_PROVIDER            — provider for summarization (default: openai_api)
  OPENAI_API_KEY                     — enables openai_api (standard REST API key, paid)
  CHATGPT_ACCESS_TOKEN               — enables openai_api via access token path
  OPENCLAW_CHATGPT_AUTH              — "true" enables openclaw_chatgpt_auth
  OLLAMA_HOST                        — Ollama host (default: http://localhost:11434)
  OPENROUTER_API_KEY                 — enables openrouter ONLY if fallback allowed

Rules:
  - OpenRouter is BLOCKED by default (HERMES_ALLOW_OPENROUTER_FALLBACK must be true)
  - Paid providers require HERMES_REQUIRE_APPROVAL_FOR_PAID_LLM=false or explicit config
  - When no LLM is available, evidence-only mode is used — no hallucination fallback
  - Provider disclosure: every response must label the provider used
"""
from __future__ import annotations

import json
import os
import socket
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ProviderType = Literal[
    "openai_api",
    "codex_auth",
    "openclaw_chatgpt_auth",
    "local_ollama",
    "openrouter",
    "evidence_only",   # no LLM — return evidence packet directly
    "none",
]

DEFAULT_PRIORITY: list[ProviderType] = [
    "openai_api",
    "codex_auth",
    "openclaw_chatgpt_auth",
    "local_ollama",
    # openrouter intentionally omitted from default
]

# Provider use cases
STRATEGIC_PROVIDERS: tuple[ProviderType, ...] = (
    "openai_api", "codex_auth", "openclaw_chatgpt_auth",
)
SUMMARY_PROVIDERS: tuple[ProviderType, ...] = (
    "openai_api", "codex_auth", "openclaw_chatgpt_auth", "local_ollama",
)
ROUTING_PROVIDERS: tuple[ProviderType, ...] = (
    "local_ollama", "openai_api",
)


@dataclass
class ProviderStatus:
    provider: ProviderType
    available: bool
    reason: str = ""
    model_hint: str = ""
    requires_approval: bool = False
    is_paid: bool = False

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "available": self.available,
            "reason": self.reason,
            "model_hint": self.model_hint,
            "requires_approval": self.requires_approval,
            "is_paid": self.is_paid,
        }


@dataclass
class ProviderPolicy:
    priority: list[ProviderType]
    openrouter_allowed: bool
    require_approval_for_paid: bool
    strategic_provider: ProviderType | None
    routing_provider: str
    summary_provider: str
    statuses: list[ProviderStatus] = field(default_factory=list)

    def best_for_strategic(self) -> ProviderType:
        if self.strategic_provider and self._is_available(self.strategic_provider):
            return self.strategic_provider
        for p in self.priority:
            if p in STRATEGIC_PROVIDERS and self._is_available(p):
                return p
        if self.openrouter_allowed and self._is_available("openrouter"):
            return "openrouter"
        return "evidence_only"

    def best_for_summary(self) -> ProviderType:
        override = os.getenv("HERMES_SUMMARY_PROVIDER", "").strip().lower()
        if override and self._is_available(override):
            return override  # type: ignore[return-value]
        for p in self.priority:
            if p in SUMMARY_PROVIDERS and self._is_available(p):
                return p
        return "evidence_only"

    def best_available(self) -> ProviderType:
        for p in self.priority:
            if self._is_available(p):
                return p
        return "evidence_only"

    def _is_available(self, name: str) -> bool:
        for s in self.statuses:
            if s.provider == name:
                return s.available
        return False

    def openrouter_status(self) -> ProviderStatus:
        for s in self.statuses:
            if s.provider == "openrouter":
                return s
        return ProviderStatus("openrouter", False, "not probed")

    def summary_dict(self) -> dict:
        return {
            "priority":               self.priority,
            "openrouter_allowed":     self.openrouter_allowed,
            "require_approval_paid":  self.require_approval_for_paid,
            "strategic_provider":     self.strategic_provider,
            "best_for_strategic":     self.best_for_strategic(),
            "best_for_summary":       self.best_for_summary(),
            "best_available":         self.best_available(),
            "providers":              [s.to_dict() for s in self.statuses],
            "generated_at":           datetime.now(timezone.utc).isoformat(),
        }

    def telegram_report(self) -> str:
        lines = [
            "🧠 *Hermes Provider Status*",
            f"Strategic: `{self.best_for_strategic()}`",
            f"Summary:   `{self.best_for_summary()}`",
            f"OpenRouter fallback: {'✅ enabled' if self.openrouter_allowed else '🚫 disabled'}",
            "",
            "*Provider availability:*",
        ]
        for s in self.statuses:
            icon = "✅" if s.available else "❌"
            note = f" — {s.reason}" if s.reason and not s.available else ""
            lines.append(f"  {icon} `{s.provider}`{note}")
        return "\n".join(lines)


# ── Detection functions ────────────────────────────────────────────────────────

def _detect_openai_api() -> ProviderStatus:
    """Detect OpenAI REST API availability (standard API key, not auth-login)."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    chatgpt_token = os.getenv("CHATGPT_ACCESS_TOKEN", "").strip()

    if openai_key and len(openai_key) > 20:
        return ProviderStatus(
            "openai_api", True,
            reason="OPENAI_API_KEY configured (REST API bridge — not auth-login)",
            model_hint=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            is_paid=True,
            requires_approval=_approval_required(),
        )
    if chatgpt_token and len(chatgpt_token) > 20:
        return ProviderStatus(
            "openai_api", True,
            reason="CHATGPT_ACCESS_TOKEN configured (access token path)",
            model_hint="gpt-4o",
            is_paid=True,
            requires_approval=_approval_required(),
        )
    # Check for ~/.openai/token file
    token_file = Path.home() / ".openai" / "token"
    if token_file.exists() and token_file.stat().st_size > 10:
        return ProviderStatus(
            "openai_api", True,
            reason=f"~/.openai/token file present (REST API bridge)",
            model_hint="gpt-4o",
            is_paid=True,
            requires_approval=_approval_required(),
        )
    return ProviderStatus("openai_api", False, reason="OPENAI_API_KEY not set")


def _detect_codex_auth() -> ProviderStatus:
    """Detect Codex CLI auth availability."""
    codex_token = os.getenv("CODEX_AUTH_TOKEN", "").strip()
    if codex_token:
        return ProviderStatus(
            "codex_auth", True,
            reason="CODEX_AUTH_TOKEN configured",
            model_hint="codex",
            is_paid=False,
        )
    # Check if codex CLI is installed and has auth
    import shutil
    codex_path = shutil.which("codex")
    if codex_path:
        # Presence of codex CLI with auth config
        codex_config = Path.home() / ".codex" / "auth.json"
        if codex_config.exists():
            return ProviderStatus(
                "codex_auth", True,
                reason=f"codex CLI auth at {codex_config}",
                model_hint="codex",
                is_paid=False,
            )
        return ProviderStatus(
            "codex_auth", False,
            reason=f"codex CLI at {codex_path} but no auth config found",
        )
    return ProviderStatus("codex_auth", False, reason="codex CLI not installed")


def _detect_openclaw_chatgpt_auth() -> ProviderStatus:
    """Detect OpenClaw ChatGPT auth availability."""
    if os.getenv("OPENCLAW_CHATGPT_AUTH", "").strip().lower() == "true":
        return ProviderStatus(
            "openclaw_chatgpt_auth", True,
            reason="OPENCLAW_CHATGPT_AUTH=true",
            model_hint="openclaw/chatgpt",
            is_paid=False,
        )
    # Check for openclaw config
    openclaw_cfg = Path.home() / ".openclaw" / "config.json"
    if openclaw_cfg.exists():
        try:
            cfg = json.loads(openclaw_cfg.read_text())
            if cfg.get("openai_api") or cfg.get("provider") == "chatgpt":
                return ProviderStatus(
                    "openclaw_chatgpt_auth", True,
                    reason=f"openclaw config at {openclaw_cfg}",
                    model_hint="openclaw/chatgpt",
                    is_paid=False,
                )
        except Exception:
            pass
    return ProviderStatus(
        "openclaw_chatgpt_auth", False,
        reason="OPENCLAW_CHATGPT_AUTH not set; no openclaw config",
    )


def _detect_local_ollama() -> ProviderStatus:
    """Detect Ollama availability by probing the health endpoint."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    try:
        req = urllib.request.Request(f"{host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                model = os.getenv("HERMES_OLLAMA_MODEL",
                                  os.getenv("HERMES_REASONING_MODEL", "qwen3:8b"))
                return ProviderStatus(
                    "local_ollama", True,
                    reason=f"Ollama running at {host}",
                    model_hint=model,
                    is_paid=False,
                )
    except Exception as e:
        return ProviderStatus("local_ollama", False, reason=f"Ollama not reachable: {e}")
    return ProviderStatus("local_ollama", False, reason="Ollama not reachable")


def _detect_openrouter() -> ProviderStatus:
    """Detect OpenRouter — available only when fallback is explicitly enabled."""
    allowed = os.getenv("HERMES_ALLOW_OPENROUTER_FALLBACK", "false").strip().lower() == "true"
    key = os.getenv("OPENROUTER_API_KEY", "").strip()

    if not allowed:
        return ProviderStatus(
            "openrouter", False,
            reason="HERMES_ALLOW_OPENROUTER_FALLBACK=false (disabled by policy)",
            is_paid=True,
        )
    if not key:
        return ProviderStatus(
            "openrouter", False,
            reason="HERMES_ALLOW_OPENROUTER_FALLBACK=true but OPENROUTER_API_KEY not set",
            is_paid=True,
        )
    model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    return ProviderStatus(
        "openrouter", True,
        reason=f"OpenRouter fallback enabled — model={model}",
        model_hint=model,
        is_paid=True,
        requires_approval=_approval_required(),
    )


def _approval_required() -> bool:
    return os.getenv("HERMES_REQUIRE_APPROVAL_FOR_PAID_LLM", "true").strip().lower() == "true"


def _parse_priority() -> list[ProviderType]:
    raw = os.getenv("HERMES_PROVIDER_PRIORITY", "").strip()
    if not raw:
        return list(DEFAULT_PRIORITY)
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    valid: list[ProviderType] = []
    allowed = {"openai_api", "codex_auth", "openclaw_chatgpt_auth",
               "local_ollama", "openrouter"}
    for p in parts:
        if p in allowed:
            valid.append(p)  # type: ignore[arg-type]
    return valid or list(DEFAULT_PRIORITY)


# ── Main builder ──────────────────────────────────────────────────────────────

def load_provider_policy() -> ProviderPolicy:
    """Build and return the current provider policy with live availability checks."""
    priority    = _parse_priority()
    or_allowed  = os.getenv("HERMES_ALLOW_OPENROUTER_FALLBACK", "false").lower() == "true"
    req_approval = _approval_required()
    strategic   = os.getenv("HERMES_STRATEGIC_PROVIDER", "").strip().lower() or None
    routing     = os.getenv("HERMES_ROUTING_PROVIDER", "local_or_rules").strip()
    summary     = os.getenv("HERMES_SUMMARY_PROVIDER", "openai_api").strip()

    statuses = [
        _detect_openai_api(),
        _detect_codex_auth(),
        _detect_openclaw_chatgpt_auth(),
        _detect_local_ollama(),
        _detect_openrouter(),
    ]

    return ProviderPolicy(
        priority=priority,
        openrouter_allowed=or_allowed,
        require_approval_for_paid=req_approval,
        strategic_provider=strategic,  # type: ignore[arg-type]
        routing_provider=routing,
        summary_provider=summary,
        statuses=statuses,
    )


def save_provider_status_report(policy: ProviderPolicy) -> str:
    """Save provider status to docs/reports/evidence/. Returns file path."""
    from pathlib import Path as _Path
    ROOT = _Path(__file__).resolve().parent.parent
    out_dir = ROOT / "docs" / "reports" / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path  = out_dir / f"hermes_provider_status_{ts}.md"
    json_path = out_dir / f"hermes_provider_status_{ts}.json"
    summary = policy.summary_dict()
    json_path.write_text(json.dumps(summary, indent=2))
    lines = [
        f"# Hermes Provider Status Report",
        f"*Generated: {summary['generated_at']}*",
        "",
        f"## Active Policy",
        f"- Priority: {', '.join(summary['priority'])}",
        f"- Strategic provider: `{summary['best_for_strategic']}`",
        f"- Summary provider: `{summary['best_for_summary']}`",
        f"- Best available: `{summary['best_available']}`",
        f"- OpenRouter fallback: {'ENABLED' if summary['openrouter_allowed'] else 'DISABLED'}",
        f"- Paid LLM requires Ray approval: {summary['require_approval_paid']}",
        "",
        "## Provider Availability",
    ]
    for p in summary["providers"]:
        icon = "✅" if p["available"] else "❌"
        lines.append(f"- {icon} `{p['provider']}` — {p['reason']}")
    md_path.write_text("\n".join(lines))
    return str(md_path)


# ── Singleton ─────────────────────────────────────────────────────────────────
_policy: ProviderPolicy | None = None


def get_policy(refresh: bool = False) -> ProviderPolicy:
    global _policy
    if _policy is None or refresh:
        _policy = load_provider_policy()
    return _policy


def get_provider_status(redact: bool = True) -> str:
    """
    Return a human-readable provider status string.
    With redact=True (default), no secrets or key values are printed.
    """
    policy = get_policy(refresh=True)
    lines = [
        "Hermes Provider Status",
        "======================",
        f"NOTE: openai_api = standard OpenAI REST API (API-backed bridge, NOT auth-login)",
        "",
        f"Strategic provider : {policy.best_for_strategic()}",
        f"Summary provider   : {policy.best_for_summary()}",
        f"Best available     : {policy.best_available()}",
        f"Priority order     : {', '.join(policy.priority)}",
        f"OpenRouter allowed : {policy.openrouter_allowed}",
        "",
        "Provider availability:",
    ]
    for s in policy.statuses:
        icon = "available  " if s.available else "unavailable"
        lines.append(f"  [{icon}] {s.provider}")
        if s.reason:
            lines.append(f"              reason: {s.reason}")
        if s.model_hint and s.available:
            lines.append(f"              model:  {s.model_hint}")
        if s.is_paid and s.available:
            lines.append(f"              paid:   yes — requires approval: {s.requires_approval}")
    return "\n".join(lines)
