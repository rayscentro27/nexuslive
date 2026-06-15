"""
Hermes Mobile — read-only context builder.

Loads ONLY approved local sources, redacts anything sensitive, and summarizes
into a compact prompt context for the local model. No writes, no secrets, no
network. If a source is missing it is skipped (never fails the build).

Allowed sources:
  - docs/hermes_mobile/*.md            (Ray-approved profile/persona)
  - reports/showroom/*.md              (Nexus reports)
  - logs/proof_automation/continuous_ops_latest.json
  - logs/proof_automation/continuous_operations_history.jsonl
  - Showroom asset registry (status counts only, via showroom_assets)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "hermes_mobile"
REPORTS = ROOT / "reports" / "showroom"
LOGS = ROOT / "logs" / "proof_automation"

# Redaction patterns — never let a secret reach the model or a log.
_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|bearer|authorization)\s*[:=]\s*\S+"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"(?i)(ghp|github_pat)_[A-Za-z0-9_]{20,}"),
    re.compile(r"\d{4,}:[A-Za-z0-9_-]{30,}"),  # telegram bot token shape
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT
]


def redact_sensitive_values(text: str) -> str:
    if not text:
        return text
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def _read(path: Path, limit: int = 2500) -> str:
    try:
        return redact_sensitive_values(path.read_text()[:limit])
    except Exception:
        return ""


def load_latest_nexus_status() -> dict:
    p = LOGS / "continuous_ops_latest.json"
    try:
        d = json.loads(p.read_text())
    except Exception:
        return {}
    # surface only non-sensitive fields
    return {
        "mode": d.get("mode"), "at": d.get("at"),
        "telegram_status": redact_sensitive_values(d.get("telegram_status", "")),
        "email_negative_test_blocked": d.get("email", {}).get("negative_test_blocked"),
        "instagram_status": d.get("instagram", {}).get("status"),
        "oanda_mode": d.get("oanda", {}).get("broker_mode"),
    }


def load_pending_approvals_summary() -> dict:
    try:
        from lib import showroom_assets as SA
        assets = [a for a in SA.load().get("assets", {}).values()
                  if a.get("asset_type", "").startswith("proof_")]
    except Exception:
        return {"needs_review": 0, "top_packages": []}
    needs = [a for a in assets if a.get("status") == "needs_review"]
    by = Counter(a["asset_type"] for a in needs)
    return {"needs_review": len(needs), "total": len(assets),
            "top_packages": by.most_common(5)}


def load_latest_scout_summary() -> dict:
    p = LOGS / "continuous_ops_latest.json"
    try:
        scouts = json.loads(p.read_text()).get("scouts", {})
    except Exception:
        scouts = {}
    # trim each scout line; redact defensively
    return {k: redact_sensitive_values((v or "")[:160]) for k, v in scouts.items()}


def load_daily_report_summary(limit: int = 1200) -> str:
    return _read(REPORTS / "nexus_continuous_operations_status.md", limit)


def _load_persona() -> str:
    parts = []
    for name in ("ray_profile.md", "nexus_mission.md", "conversation_style.md",
                 "business_tracks.md", "command_boundaries.md"):
        t = _read(DOCS / name, 1400)
        if t:
            parts.append(f"## {name}\n{t}")
    return "\n\n".join(parts)


def build_mobile_context(user_message: str) -> dict:
    """Assemble all approved, redacted context for a given message."""
    return {
        "persona": _load_persona(),
        "status": load_latest_nexus_status(),
        "approvals": load_pending_approvals_summary(),
        "scouts": load_latest_scout_summary(),
        "daily_report": load_daily_report_summary(),
        "user_message": redact_sensitive_values(user_message or ""),
    }


def summarize_context_for_prompt(ctx: dict | None = None, user_message: str = "") -> str:
    """Compact system+context string for the local model. Redacted, no secrets."""
    ctx = ctx or build_mobile_context(user_message)
    appr = ctx["approvals"]
    top = ", ".join(f"{k.replace('proof_','')}({v})" for k, v in appr.get("top_packages", [])) or "none"
    st = ctx["status"]
    # Keep this lean: CPU-only local inference cost scales with prompt tokens.
    sys_lines = [
        "You are Hermes Mobile, Ray's read-only conversational advisor for Nexus.",
        "Reply conversationally, plain, phone-friendly, short. No raw logs.",
        "You NEVER execute actions; you may DRAFT a command for the command bot 'TheChoseone'.",
        "No guaranteed claims (credit/funding/profit). Be honest about weaknesses. End with one next action.",
        "Ray knows credit repair, business funding, trading; wants to help people at scale and make money, with proof not hype.",
        "",
        "LIVE NEXUS STATE (read-only):",
        f"- mode: {st.get('mode')} · oanda: {st.get('oanda_mode')} · IG: {st.get('instagram_status')}",
        f"- assets needing review: {appr.get('needs_review')} (top: {top})",
        "",
        "Ray asks:",
    ]
    return redact_sensitive_values("\n".join(sys_lines))
