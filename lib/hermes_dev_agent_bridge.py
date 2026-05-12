"""
hermes_dev_agent_bridge.py

Safe bridge between Hermes and external CLI coding/research agents.

Execution is OFF by default. All actions require explicit approval unless
classified as read-only. No arbitrary shell commands are permitted.

Feature flags (all default to safe):
  HERMES_DEV_AGENT_BRIDGE_ENABLED  = true   (detection + planning only)
  HERMES_CLI_EXECUTION_ENABLED     = false   (actual CLI invocation)
  HERMES_CLI_DRY_RUN               = true    (generate plan, never run)
  HERMES_CLI_APPROVAL_REQUIRED     = true    (all edits need approval)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("HermesDevAgentBridge")

ROOT = Path(__file__).resolve().parent.parent
_HANDOFF_STORE = ROOT / ".hermes_cli_handoffs.json"

# ─────────────────────────────────────────────────────────
# Feature flags
# ─────────────────────────────────────────────────────────

def _flag(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


def bridge_enabled() -> bool:
    return _flag("HERMES_DEV_AGENT_BRIDGE_ENABLED", "true")


def execution_enabled() -> bool:
    return _flag("HERMES_CLI_EXECUTION_ENABLED", "false")


def dry_run_mode() -> bool:
    return _flag("HERMES_CLI_DRY_RUN", "true")


def approval_required() -> bool:
    return _flag("HERMES_CLI_APPROVAL_REQUIRED", "true")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────
# CLI Agent Role Registry
# ─────────────────────────────────────────────────────────

CLI_AGENT_ROLES: dict[str, dict[str, Any]] = {
    "gemini": {
        "display_name": "Gemini CLI",
        "provider": "google",
        "role": "large-context reviewer / architecture planner",
        "description": "Best for large repo review, architecture analysis, documentation, and planning across huge contexts.",
        "default_mode": "read_only",
        "allowed_actions": ["read", "analyze", "summarize", "plan", "review", "document"],
        "requires_approval_for": ["write", "edit", "execute", "install", "deploy", "delete", "config"],
        "forbidden_actions": ["live_trading", "billing", "migrate", "drop", "rm"],
        "best_for": ["large_repo_review", "architecture_review", "documentation", "planning", "summarization"],
        "safe_for_execution": False,
        "telegram_allowed": False,
        "output_destination": "report",
    },
    "opencode": {
        "display_name": "OpenCode CLI",
        "provider": "opencode-ai",
        "role": "implementation assistant / code editor",
        "description": "Best for implementing features, editing files, running tests, and generating diffs after approval.",
        "default_mode": "approval_required",
        "allowed_actions": ["read", "analyze", "plan", "diff", "test"],
        "requires_approval_for": ["write", "edit", "execute", "install", "create", "delete", "config"],
        "forbidden_actions": ["live_trading", "billing", "migrate", "drop", "deploy_production"],
        "best_for": ["implementation", "code_editing", "test_running", "diff_generation", "refactoring"],
        "safe_for_execution": False,
        "telegram_allowed": False,
        "output_destination": "report",
    },
    "claude": {
        "display_name": "Claude CLI (Claude Code)",
        "provider": "anthropic",
        "role": "reasoning reviewer / code review / implementation planner",
        "description": "Best for code review, reasoning review, risk analysis, and implementation planning.",
        "default_mode": "approval_required",
        "allowed_actions": ["read", "analyze", "review", "plan", "summarize", "reason"],
        "requires_approval_for": ["write", "edit", "execute", "install", "deploy", "delete", "config"],
        "forbidden_actions": ["live_trading", "billing", "migrate", "drop"],
        "best_for": ["code_review", "reasoning_review", "risk_analysis", "implementation_planning", "architecture_critique"],
        "safe_for_execution": False,
        "telegram_allowed": False,
        "output_destination": "report",
    },
    "codex": {
        "display_name": "Codex / OpenAI CLI",
        "provider": "openai",
        "role": "implementation assistant / patch generator",
        "description": "Best for generating patches, implementing features, and test repair after approval.",
        "default_mode": "approval_required",
        "allowed_actions": ["read", "analyze", "plan", "patch", "test"],
        "requires_approval_for": ["write", "edit", "execute", "install", "create", "delete", "config"],
        "forbidden_actions": ["live_trading", "billing", "migrate", "drop", "deploy_production"],
        "best_for": ["implementation", "patch_generation", "refactoring", "test_repair", "summaries"],
        "safe_for_execution": False,
        "telegram_allowed": False,
        "output_destination": "report",
    },
}

# ─────────────────────────────────────────────────────────
# Safety policy
# ─────────────────────────────────────────────────────────

_READ_ONLY_ACTIONS = {
    "read", "analyze", "summarize", "review", "plan", "document",
    "diff", "inspect", "audit", "check", "status", "list", "detect",
    "describe", "describe_task", "recommend", "reason", "search",
}

_APPROVAL_REQUIRED_ACTIONS = {
    "write", "edit", "create", "modify", "patch", "refactor",
    "execute", "run", "install", "test", "update", "generate",
}

_FORBIDDEN_ACTIONS = {
    "live_trading", "billing", "drop", "truncate", "delete_table",
    "migrate_production", "deploy_production", "rm_rf", "overwrite_env",
    "send_client_message", "autonomous_loop", "unrestricted_shell",
}

# Dangerous substrings — any command containing these is blocked
_FORBIDDEN_COMMAND_PATTERNS = [
    r"\brm\s+-rf\b", r"\bdrop\s+table\b", r"\btruncate\b",
    r"\bdeploy\s+prod\b", r"\bgit\s+push\s+--force\b",
    r"\bsudo\b", r"\bcurl\b.*\|\s*bash", r"\bchmod\s+777\b",
    r"\.env\b.*write", r"\bsupabase\s+db\s+push\b",
    r"\bstripe\b", r"\bbilling\b", r"\blive_trad",
]


def classify_cli_action_risk(action: str) -> str:
    """Return 'read_only', 'approval_required', or 'forbidden'."""
    a = action.lower().strip()
    if a in _FORBIDDEN_ACTIONS:
        return "forbidden"
    if any(re.search(p, a) for p in _FORBIDDEN_COMMAND_PATTERNS):
        return "forbidden"
    if a in _APPROVAL_REQUIRED_ACTIONS:
        return "approval_required"
    if a in _READ_ONLY_ACTIONS:
        return "read_only"
    # Default to approval_required if ambiguous
    return "approval_required"


def requires_cli_approval(action: str) -> bool:
    risk = classify_cli_action_risk(action)
    return risk in ("approval_required", "forbidden")


def validate_cli_command(command: str) -> dict[str, Any]:
    """Validate a raw command string. Returns {valid, blocked, reason, risk_level}."""
    cmd = (command or "").strip()
    if not cmd:
        return {"valid": False, "blocked": True, "reason": "empty command", "risk_level": "unknown"}

    for pattern in _FORBIDDEN_COMMAND_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return {
                "valid": False,
                "blocked": True,
                "reason": f"matches forbidden pattern: {pattern}",
                "risk_level": "forbidden",
            }

    # Check for shell meta-characters that could enable injection
    dangerous_chars = [";", "&&", "||", "`", "$(", ">!", "2>&1 rm"]
    for char in dangerous_chars:
        if char in cmd:
            return {
                "valid": False,
                "blocked": True,
                "reason": f"contains dangerous shell construct: {char!r}",
                "risk_level": "forbidden",
            }

    return {"valid": True, "blocked": False, "reason": "", "risk_level": "low"}


_SECRET_PATTERNS = [
    (r"(sk-[A-Za-z0-9]{20,})", "<sk-REDACTED>"),
    (r"(Bearer\s+[A-Za-z0-9._\-]{10,})", "Bearer <REDACTED>"),
    (r"(SUPABASE_[A-Z_]+\s*=\s*[^\s]+)", "<SUPABASE_REDACTED>"),
    (r"(eyJ[A-Za-z0-9._\-]{20,})", "<JWT-REDACTED>"),
    (r"([A-Za-z0-9]{32,64})", lambda m: m.group(0)[:6] + "...<REDACTED>" if len(m.group(0)) >= 40 else m.group(0)),
]


def redact_cli_output(output: str) -> str:
    """Strip secrets and tokens from CLI output."""
    result = output
    for pattern, replacement in _SECRET_PATTERNS:
        if callable(replacement):
            result = re.sub(pattern, replacement, result)
        else:
            result = re.sub(pattern, replacement, result)
    return result


# ─────────────────────────────────────────────────────────
# CLI Detection
# ─────────────────────────────────────────────────────────

def _detect_single_cli(name: str, version_flag: str = "--version") -> dict[str, Any]:
    """Detect one CLI tool. Never raises."""
    path = shutil.which(name)
    if not path:
        return {
            "name": name,
            "installed": False,
            "path": None,
            "version": None,
            "provider": CLI_AGENT_ROLES.get(name, {}).get("provider", "unknown"),
            "safe_for_execution": False,
            "detection_error": None,
        }
    try:
        result = subprocess.run(
            [path, version_flag],
            capture_output=True, text=True, timeout=8,
        )
        raw = ((result.stdout or "") + (result.stderr or "")).strip()
        # Extract first version-like token
        m = re.search(r"(\d+\.\d+[\.\d]*)", raw)
        version = m.group(1) if m else raw[:40] or "unknown"
    except Exception as e:
        version = f"error: {e}"

    return {
        "name": name,
        "installed": True,
        "path": path,
        "version": version,
        "provider": CLI_AGENT_ROLES.get(name, {}).get("provider", "unknown"),
        "safe_for_execution": False,
        "detection_error": None,
    }


def detect_cli_agents() -> list[dict[str, Any]]:
    """Detect all target CLI agents. Never fails if a tool is missing."""
    agents = []
    targets = [
        ("gemini", "--version"),
        ("opencode", "--version"),
        ("claude", "--version"),
        ("codex", "--version"),
    ]
    for name, flag in targets:
        info = _detect_single_cli(name, flag)
        agents.append(info)
    return agents


def get_cli_agent_status() -> dict[str, Any]:
    """Return full status dict of detected CLI agents."""
    agents = detect_cli_agents()
    installed = [a for a in agents if a["installed"]]
    missing = [a for a in agents if not a["installed"]]
    return {
        "generated_at": _now(),
        "bridge_enabled": bridge_enabled(),
        "execution_enabled": execution_enabled(),
        "dry_run_mode": dry_run_mode(),
        "approval_required": approval_required(),
        "agents": agents,
        "installed_count": len(installed),
        "missing_count": len(missing),
        "installed_names": [a["name"] for a in installed],
        "missing_names": [a["name"] for a in missing],
        "safe_for_execution": False,
    }


def validate_cli_agent_config() -> dict[str, Any]:
    """Validate safety posture of the bridge configuration."""
    issues = []
    warnings = []

    if execution_enabled():
        issues.append("HERMES_CLI_EXECUTION_ENABLED=true — CLI execution is live")
    if not dry_run_mode():
        issues.append("HERMES_CLI_DRY_RUN=false — dry-run protection is off")
    if not approval_required():
        warnings.append("HERMES_CLI_APPROVAL_REQUIRED=false — approvals are not enforced")
    if not bridge_enabled():
        warnings.append("HERMES_DEV_AGENT_BRIDGE_ENABLED=false — bridge is disabled")

    return {
        "valid": len(issues) == 0,
        "safe": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "execution_enabled": execution_enabled(),
        "dry_run_mode": dry_run_mode(),
        "approval_required": approval_required(),
    }


def build_cli_agent_inventory() -> dict[str, Any]:
    """Full inventory combining detection + role registry + safety config."""
    agents = detect_cli_agents()
    config = validate_cli_agent_config()
    inventory = []
    for agent in agents:
        name = agent["name"]
        role = CLI_AGENT_ROLES.get(name, {})
        inventory.append({
            **agent,
            "display_name": role.get("display_name", name),
            "role": role.get("role", "unknown"),
            "description": role.get("description", ""),
            "default_mode": role.get("default_mode", "approval_required"),
            "allowed_actions": role.get("allowed_actions", []),
            "requires_approval_for": role.get("requires_approval_for", []),
            "forbidden_actions": role.get("forbidden_actions", []),
            "best_for": role.get("best_for", []),
            "effective_mode": (
                "unavailable" if not agent["installed"]
                else "dry_run" if dry_run_mode()
                else role.get("default_mode", "approval_required")
            ),
        })
    return {
        "generated_at": _now(),
        "inventory": inventory,
        "config": config,
        "execution_enabled": execution_enabled(),
        "dry_run_mode": dry_run_mode(),
        "can_execute": False,
    }


# ─────────────────────────────────────────────────────────
# Routing Recommendations
# ─────────────────────────────────────────────────────────

_ROUTING_RULES: list[tuple[list[str], str, str]] = [
    # (keywords, agent_name, reason)
    (["large repo", "huge context", "architecture", "architecture review",
      "whole codebase", "entire repo", "big picture", "design review",
      "documentation", "planning", "summarize repo"],
     "gemini", "large-context review and architecture planning"),

    (["implement", "implementation", "code change", "edit file", "write code",
      "feature", "add function", "refactor", "fix bug", "patch", "test-driven",
      "tdd", "unit test", "generate code"],
     "opencode", "implementation, file editing, and test-driven changes"),

    (["code review", "review this", "review code", "reasoning", "risk review",
      "critique", "assess", "evaluate", "should we", "is this safe",
      "implementation plan", "approach", "trade-off"],
     "claude", "reasoning review, code review, and risk analysis"),

    (["patch", "diff", "fix test", "repair test", "test repair",
      "small refactor", "targeted fix", "openai", "codex"],
     "codex", "patch generation and test repair"),
]


def recommend_dev_agent_for_task(task: str) -> dict[str, Any]:
    """Recommend which CLI agent to use for a given task description."""
    lowered = (task or "").lower()
    detected = {a["name"]: a["installed"] for a in detect_cli_agents()}

    matches: list[tuple[str, str, int]] = []
    for keywords, agent, reason in _ROUTING_RULES:
        score = sum(1 for kw in keywords if kw in lowered)
        if score > 0:
            matches.append((agent, reason, score))

    matches.sort(key=lambda x: -x[2])

    recommendations = []
    for agent, reason, score in matches:
        recommendations.append({
            "agent": agent,
            "display_name": CLI_AGENT_ROLES.get(agent, {}).get("display_name", agent),
            "reason": reason,
            "installed": detected.get(agent, False),
            "score": score,
            "mode": CLI_AGENT_ROLES.get(agent, {}).get("default_mode", "approval_required"),
        })

    # Fallback
    if not recommendations:
        recommendations.append({
            "agent": "gemini",
            "display_name": "Gemini CLI",
            "reason": "general-purpose large-context analysis (default fallback)",
            "installed": detected.get("gemini", False),
            "score": 0,
            "mode": "read_only",
        })

    primary = recommendations[0]
    return {
        "task": task,
        "primary_recommendation": primary,
        "all_recommendations": recommendations,
        "can_execute": False,
        "requires_approval": requires_cli_approval("execute"),
        "next_step": (
            f"Prepare a handoff prompt for {primary['display_name']} — approval required before execution."
            if primary["installed"]
            else f"{primary['display_name']} is not installed. Consider installing it first."
        ),
    }


# ─────────────────────────────────────────────────────────
# Handoff Objects
# ─────────────────────────────────────────────────────────

def _load_handoffs() -> list[dict[str, Any]]:
    if _HANDOFF_STORE.exists():
        try:
            return json.loads(_HANDOFF_STORE.read_text())
        except Exception:
            pass
    return []


def _save_handoffs(handoffs: list[dict[str, Any]]) -> None:
    try:
        _HANDOFF_STORE.write_text(json.dumps(handoffs, indent=2, default=str))
    except Exception as e:
        logger.warning("Could not save handoffs: %s", e)


def create_cli_handoff(
    target_agent: str,
    goal: str,
    context_summary: str = "",
    allowed_actions: list[str] | None = None,
    required_tests: list[str] | None = None,
    expected_output: str = "",
    requester: str = "operator",
) -> dict[str, Any]:
    """Create a safe handoff object for a CLI agent task."""
    agent_role = CLI_AGENT_ROLES.get(target_agent, {})
    handoff_id = f"handoff-{uuid.uuid4().hex[:12]}"

    # Only allow actions within the agent's permitted set
    permitted = set(agent_role.get("allowed_actions", []))
    effective_allowed = [a for a in (allowed_actions or agent_role.get("allowed_actions", []))]
    # Strip anything approval-required from auto-allowed
    safe_allowed = [a for a in effective_allowed if classify_cli_action_risk(a) == "read_only"]

    handoff = {
        "handoff_id": handoff_id,
        "target_agent": target_agent,
        "display_name": agent_role.get("display_name", target_agent),
        "goal": goal,
        "context_summary": context_summary,
        "safety_rules": [
            "No autonomous execution without explicit approval",
            "No file writes without approval",
            "No deploys, migrations, or config changes",
            "No live trading or billing actions",
            "Output goes to report — not Telegram",
            "Secrets must not appear in output",
        ],
        "allowed_actions": effective_allowed,
        "safe_without_approval": safe_allowed,
        "forbidden_actions": agent_role.get("forbidden_actions", []),
        "required_tests": required_tests or [],
        "expected_output": expected_output,
        "approval_required": True,
        "approved": False,
        "approved_by": None,
        "approved_at": None,
        "status": "pending_approval",
        "created_at": _now(),
        "updated_at": _now(),
        "created_by": requester,
        "dry_run": dry_run_mode(),
        "execution_enabled": execution_enabled(),
        "prompt": _build_handoff_prompt(target_agent, goal, context_summary, safe_allowed, expected_output),
    }

    handoffs = _load_handoffs()
    handoffs.append(handoff)
    # Keep last 50
    handoffs = handoffs[-50:]
    _save_handoffs(handoffs)
    logger.info("CLI handoff created: %s for %s", handoff_id, target_agent)
    return handoff


def _build_handoff_prompt(
    agent: str,
    goal: str,
    context: str,
    allowed_actions: list[str],
    expected_output: str,
) -> str:
    role = CLI_AGENT_ROLES.get(agent, {})
    forbidden = ", ".join(role.get("forbidden_actions", []))
    allowed_str = ", ".join(allowed_actions) if allowed_actions else "read-only analysis"
    return f"""# Nexus AI — Dev Agent Handoff
Agent: {role.get('display_name', agent)}
Role: {role.get('role', 'assistant')}

## Goal
{goal}

## Context
{context or 'See attached repository context.'}

## Allowed Actions
{allowed_str}

## Safety Rules
- Do NOT write or modify files without explicit approval
- Do NOT run shell commands beyond what is listed above
- Do NOT access live trading, billing, or client messaging systems
- Do NOT expose secrets or tokens in output
- Forbidden actions: {forbidden or 'none additional'}

## Expected Output
{expected_output or 'Analysis, review, or plan in structured text. No code execution.'}

## Output Destination
Report only — do NOT send to Telegram directly.
"""


def summarize_cli_handoff(handoff: dict[str, Any]) -> str:
    """Return a short one-line summary suitable for Telegram."""
    hid = handoff.get("handoff_id", "?")[:16]
    agent = handoff.get("display_name", handoff.get("target_agent", "?"))
    goal = handoff.get("goal", "")[:60]
    status = handoff.get("status", "unknown")
    return f"[{hid}] {agent} — {goal}... ({status})"


def _update_handoff(handoff_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    handoffs = _load_handoffs()
    for i, h in enumerate(handoffs):
        if h.get("handoff_id") == handoff_id:
            handoffs[i] = {**h, **updates, "updated_at": _now()}
            _save_handoffs(handoffs)
            return handoffs[i]
    return None


def mark_cli_handoff_approved(handoff_id: str, approved_by: str = "operator") -> dict[str, Any] | None:
    return _update_handoff(handoff_id, {
        "approved": True,
        "approved_by": approved_by,
        "approved_at": _now(),
        "status": "approved",
    })


def mark_cli_handoff_completed(handoff_id: str, output_summary: str = "") -> dict[str, Any] | None:
    return _update_handoff(handoff_id, {
        "status": "completed",
        "output_summary": output_summary[:500],
        "completed_at": _now(),
    })


def mark_cli_handoff_failed(handoff_id: str, reason: str = "") -> dict[str, Any] | None:
    return _update_handoff(handoff_id, {
        "status": "failed",
        "failure_reason": reason[:200],
        "failed_at": _now(),
    })


def get_recent_handoffs(limit: int = 10) -> list[dict[str, Any]]:
    handoffs = _load_handoffs()
    return handoffs[-limit:]


# ─────────────────────────────────────────────────────────
# Telegram-safe response builder
# ─────────────────────────────────────────────────────────

def build_telegram_dev_agent_response(intent: str, raw_text: str) -> str:
    """Return a short Telegram-safe response for dev agent commands."""
    status = get_cli_agent_status()
    installed = status.get("installed_names", [])
    missing = status.get("missing_names", [])

    if intent == "list_dev_agents":
        lines = ["🤖 Dev Agent Bridge — installed tools:"]
        for agent in status["agents"]:
            icon = "✅" if agent["installed"] else "❌"
            ver = f" v{agent['version']}" if agent.get("version") else ""
            lines.append(f"  {icon} {agent['name']}{ver}")
        lines.append("")
        lines.append("Execution: DISABLED (dry-run mode)")
        lines.append("Details at AI Ops dashboard → Dev Agents panel.")
        return "\n".join(lines)

    if intent == "dev_agent_status":
        count = len(installed)
        return (
            f"🤖 Dev Agent Bridge: {count}/{len(status['agents'])} installed\n"
            f"Installed: {', '.join(installed) or 'none'}\n"
            f"Execution: {'ENABLED' if execution_enabled() else 'DISABLED'} | "
            f"Dry-run: {'ON' if dry_run_mode() else 'OFF'}\n"
            f"See AI Ops dashboard for full details."
        )

    if intent == "recommend_dev_agent":
        rec = recommend_dev_agent_for_task(raw_text)
        primary = rec["primary_recommendation"]
        avail = "✅ installed" if primary["installed"] else "❌ not installed"
        return (
            f"🤖 Recommended: {primary['display_name']} ({avail})\n"
            f"Reason: {primary['reason']}\n"
            f"Mode: {primary['mode']}\n"
            f"Approval required before execution."
        )

    if intent == "prepare_dev_handoff":
        # Extract target agent from text
        target = "gemini"  # default
        for name in CLI_AGENT_ROLES:
            if name in raw_text.lower():
                target = name
                break
        goal = raw_text[:120]
        handoff = create_cli_handoff(
            target_agent=target,
            goal=goal,
            context_summary="Requested via Telegram — context to be added.",
            requester="telegram",
        )
        summary = summarize_cli_handoff(handoff)
        return (
            f"📋 Handoff created: {summary}\n"
            f"Status: pending_approval\n"
            f"Approve in AI Ops dashboard before execution."
        )

    # Fallback
    return (
        "🤖 Dev Agent Bridge\n"
        f"Installed: {', '.join(installed) or 'none'}\n"
        "Use: 'list dev agents' | 'which coding agents' | 'prepare prompt for gemini'"
    )
