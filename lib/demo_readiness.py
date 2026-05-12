from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import os

from lib.hermes_dev_agent_bridge import get_cli_agent_status
from lib.client_funding_intelligence import build_client_funding_summary
from lib.trading_intelligence_lab import build_trading_intelligence_report
from lib.opportunity_intelligence import build_opportunity_summary


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def build_demo_readiness_report() -> dict[str, Any]:
    checks = [
        _check("telegram_conversational", _flag("TELEGRAM_CONVERSATIONAL_MODE", "true"), "TELEGRAM_CONVERSATIONAL_MODE"),
        _check("telegram_manual_only", _flag("TELEGRAM_MANUAL_ONLY", "true"), "TELEGRAM_MANUAL_ONLY"),
        _check("telegram_auto_reports_disabled", not _flag("TELEGRAM_AUTO_REPORTS_ENABLED", "false"), "TELEGRAM_AUTO_REPORTS_ENABLED=false"),
        _check("telegram_full_reports_disabled", not _flag("TELEGRAM_FULL_REPORTS_ENABLED", "false"), "TELEGRAM_FULL_REPORTS_ENABLED=false"),
        _check("swarm_execution_disabled", not _flag("SWARM_EXECUTION_ENABLED", "false"), "SWARM_EXECUTION_ENABLED=false"),
        _check("swarm_dry_run", _flag("HERMES_SWARM_DRY_RUN", "true"), "HERMES_SWARM_DRY_RUN=true"),
        _check("cli_execution_disabled", not _flag("HERMES_CLI_EXECUTION_ENABLED", "false"), "HERMES_CLI_EXECUTION_ENABLED=false"),
        _check("cli_dry_run", _flag("HERMES_CLI_DRY_RUN", "true"), "HERMES_CLI_DRY_RUN=true"),
        _check("cli_approval_required", _flag("HERMES_CLI_APPROVAL_REQUIRED", "true"), "HERMES_CLI_APPROVAL_REQUIRED=true"),
        _check("trading_live_disabled", not _flag("TRADING_LIVE_EXECUTION_ENABLED", "false"), "TRADING_LIVE_EXECUTION_ENABLED=false"),
        _check("trading_paper_only", _flag("TRADING_PAPER_ONLY", "true"), "TRADING_PAPER_ONLY=true"),
        _check("email_reports_enabled", _flag("EMAIL_REPORTS_ENABLED", "true"), "EMAIL_REPORTS_ENABLED=true"),
    ]
    passed = len([c for c in checks if c["ok"]])
    total = len(checks)
    score = int((passed / total) * 100) if total else 0
    blockers = [c["name"] for c in checks if not c["ok"]]
    status = "ready" if score >= 90 and not blockers else "attention_required"
    return {
        "timestamp": _now(),
        "status": status,
        "score": score,
        "checks": checks,
        "blockers": blockers,
        "recommended_fixes": [f"Review {b}" for b in blockers],
        "next_action": "Run phone checklist and send executive report." if not blockers else "Resolve blockers before live demo.",
        "dev_agent_bridge": get_cli_agent_status(),
        "funding_intelligence": build_client_funding_summary(),
        "trading_intelligence": build_trading_intelligence_report(),
        "opportunity_intelligence": build_opportunity_summary(),
        "marketing_plan_inputs_needed": {
            "target_audience_assumptions": ["Founders needing funding readiness", "Operators wanting AI-assisted execution visibility"],
            "core_offer": "Nexus as an operational intelligence and execution-coordination layer.",
            "demo_story": "From operator message to safe prioritized action with transparent guardrails.",
            "main_benefits": ["Faster prioritization", "Safer AI operations", "Unified intelligence rollups"],
            "proof_points_needed": ["test pass evidence", "dashboard snapshots", "email report output", "safety flag confirmation"],
            "recommended_content_angles": ["AI COO workflow", "Funding readiness clarity", "Educational trading lab"],
            "next_marketing_build_prompt_outline": "Build a 7-day content plan using demo readiness proof points and safety-first positioning.",
        },
    }


def run_demo_readiness_check() -> dict[str, Any]:
    return build_demo_readiness_report()
