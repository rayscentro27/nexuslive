"""
Hermes CEO Decision Policy
Classifies every Hermes action as AUTONOMOUS_ALLOWED, APPROVAL_REQUIRED, or BLOCKED.
Every decision is logged to docs/reports/hermes_decisions/.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

DECISIONS_DIR = Path("docs/reports/hermes_decisions")
DECISIONS_DIR.mkdir(parents=True, exist_ok=True)

DECISION_LOG = DECISIONS_DIR / "hermes_decision_log.jsonl"


class DecisionClass(str, Enum):
    AUTONOMOUS_ALLOWED   = "autonomous_allowed"
    APPROVAL_REQUIRED    = "approval_required"
    BLOCKED              = "blocked"


# ── Policy tables ──────────────────────────────────────────────────────────────

AUTONOMOUS_ALLOWED: list[dict] = [
    {"action": "read_artifact",        "description": "Read any existing Nexus artifact or report"},
    {"action": "run_validation_cycle", "description": "Run operating cycle in validation or quick mode"},
    {"action": "run_credit_repair",    "description": "Run credit repair research (educational, no client contact)"},
    {"action": "run_github_trends",    "description": "Run GitHub trend research"},
    {"action": "run_risky_opportunity","description": "Run risky opportunity analysis"},
    {"action": "run_compliance_review","description": "Run compliance review gate"},
    {"action": "run_continue_research","description": "Run continue-research synthesis"},
    {"action": "run_content_pipeline", "description": "Run content pipeline (no public publish)"},
    {"action": "save_ray_feedback",    "description": "Save Ray feedback to docs/reports/ray_feedback/"},
    {"action": "update_mistake_memory","description": "Add or update Hermes mistake memory patterns"},
    {"action": "resolve_premium_blockers", "description": "Research alternatives to paid tool blockers"},
    {"action": "generate_ceo_packet",  "description": "Generate CEO review packet"},
    {"action": "hermes_conversation",  "description": "Strategic discussion with Ray via Telegram"},
    {"action": "run_demo_broker_test", "description": "Run OANDA practice-environment demo test (DEMO_ENABLED=true required)"},
    {"action": "send_telegram_notification", "description": "Send proactive Telegram status update to Ray"},
    {"action": "send_discord_notification",  "description": "Send Discord delivery notification"},
    {"action": "create_action_handoff",      "description": "Create structured handoff packet for Ray"},
]

APPROVAL_REQUIRED: list[dict] = [
    {"action": "publish_content",      "description": "Publish any content publicly (YouTube, newsletter, social)"},
    {"action": "spend_money",          "description": "Any purchase or API spend beyond free tier"},
    {"action": "enable_paid_llm",      "description": "Enable paid LLM provider beyond existing .env key"},
    {"action": "git_commit_push",      "description": "Commit or push any code changes"},
    {"action": "deploy_production",    "description": "Deploy any change to production or live environment"},
    {"action": "enable_oanda_demo",    "description": "Flip OANDA_DEMO_ENABLED=true (requires Ray explicit approval)"},
    {"action": "send_client_email",    "description": "Send any email to a client or prospect"},
    {"action": "add_client_safe_label","description": "Label any credit/funding strategy as client_safe_education_candidate"},
    {"action": "new_product_module",   "description": "Build a new client-facing product module"},
    {"action": "share_api_key",        "description": "Share, rotate, or expose any API key"},
    {"action": "run_overnight_cycle",  "description": "Run overnight (long-running) operating cycle"},
]

BLOCKED: list[dict] = [
    {"action": "live_trading",         "description": "Execute any live trade via any broker"},
    {"action": "connect_live_broker",  "description": "Connect to live broker account or live endpoint"},
    {"action": "guarantee_outcomes",   "description": "Claim guaranteed credit, income, trading, or funding results"},
    {"action": "hide_failures",        "description": "Delete logs, hide errors, or claim completion without artifacts"},
    {"action": "fake_sources",         "description": "Fabricate citations, data, or source URLs"},
    {"action": "expose_public_api",    "description": "Bind any internal API to a public network interface"},
    {"action": "enable_shell_tools",   "description": "Enable shell-capable tools (VIBE_TRADING_ENABLE_SHELL_TOOLS must stay 0)"},
    {"action": "delete_logs",          "description": "Delete audit logs, decision logs, or compliance records"},
    {"action": "disable_compliance_gate","description": "Skip or disable compliance review gate for any strategy"},
    {"action": "credit_repair_advice", "description": "Provide specific credit repair advice as legal/financial guidance"},
    {"action": "oanda_live_env",       "description": "Use OANDA_ENVIRONMENT=live or OANDA_ALLOW_LIVE=true"},
    {"action": "bank_account_connection","description": "Connect any bank account or live financial account"},
]


# ── Classifier ─────────────────────────────────────────────────────────────────

class HermesCEODecisionPolicy:
    """
    Call .classify(action_key, context) before executing any Hermes action.
    Every call is logged regardless of outcome.
    """

    def classify(
        self,
        action: str,
        context: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        decision_class, rule = self._lookup(action)
        record = self._log(action, decision_class, rule, context, metadata or {})
        return {
            "action": action,
            "decision": decision_class.value,
            "rule": rule,
            "context": context,
            "logged_at": record["logged_at"],
            "log_file": str(DECISION_LOG),
        }

    def is_allowed(self, action: str, context: str = "") -> bool:
        result = self.classify(action, context)
        return result["decision"] == DecisionClass.AUTONOMOUS_ALLOWED.value

    def require_approval(self, action: str, context: str = "") -> bool:
        result = self.classify(action, context)
        return result["decision"] == DecisionClass.APPROVAL_REQUIRED.value

    def is_blocked(self, action: str, context: str = "") -> bool:
        result = self.classify(action, context)
        return result["decision"] == DecisionClass.BLOCKED.value

    # ── internals ──────────────────────────────────────────────────────────────

    def _lookup(self, action: str) -> tuple[DecisionClass, str]:
        for rule in BLOCKED:
            if rule["action"] == action:
                return DecisionClass.BLOCKED, rule["description"]
        for rule in APPROVAL_REQUIRED:
            if rule["action"] == action:
                return DecisionClass.APPROVAL_REQUIRED, rule["description"]
        for rule in AUTONOMOUS_ALLOWED:
            if rule["action"] == action:
                return DecisionClass.AUTONOMOUS_ALLOWED, rule["description"]
        # Unknown actions require approval by default
        return DecisionClass.APPROVAL_REQUIRED, f"Unknown action '{action}' — approval required by default"

    def _log(
        self,
        action: str,
        decision_class: DecisionClass,
        rule: str,
        context: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        record = {
            "logged_at": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "decision": decision_class.value,
            "rule": rule,
            "context": context,
            "metadata": metadata,
        }
        with open(DECISION_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def policy_summary(self) -> str:
        lines = ["# Hermes CEO Decision Policy\n"]
        lines.append(f"## Autonomous Allowed ({len(AUTONOMOUS_ALLOWED)})")
        for r in AUTONOMOUS_ALLOWED:
            lines.append(f"- **{r['action']}**: {r['description']}")
        lines.append(f"\n## Approval Required ({len(APPROVAL_REQUIRED)})")
        for r in APPROVAL_REQUIRED:
            lines.append(f"- **{r['action']}**: {r['description']}")
        lines.append(f"\n## Blocked ({len(BLOCKED)})")
        for r in BLOCKED:
            lines.append(f"- **{r['action']}**: {r['description']}")
        return "\n".join(lines)

    def recent_decisions(self, n: int = 20) -> list[dict]:
        if not DECISION_LOG.exists():
            return []
        lines = DECISION_LOG.read_text().strip().splitlines()
        return [json.loads(l) for l in lines[-n:] if l.strip()]


# ── Convenience singleton ───────────────────────────────────────────────────────
_policy = HermesCEODecisionPolicy()


def classify_action(action: str, context: str = "", **metadata) -> dict[str, Any]:
    return _policy.classify(action, context, metadata)


def assert_allowed(action: str, context: str = "") -> None:
    result = _policy.classify(action, context)
    if result["decision"] == DecisionClass.BLOCKED.value:
        raise PermissionError(f"[POLICY BLOCKED] {action}: {result['rule']}")
    if result["decision"] == DecisionClass.APPROVAL_REQUIRED.value:
        raise PermissionError(f"[POLICY APPROVAL_REQUIRED] {action}: {result['rule']}")
