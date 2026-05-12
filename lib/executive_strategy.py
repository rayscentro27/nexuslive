from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from lib.client_funding_intelligence import build_client_funding_intelligence_summary
from lib.opportunity_intelligence import build_opportunity_intelligence_summary
from lib.operational_intelligence import build_operational_intelligence_snapshot
from lib.trading_intelligence_lab import build_trading_intelligence_report


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rank_operational_priorities() -> list[dict[str, Any]]:
    ops = build_operational_intelligence_snapshot(mode="compact")
    funding = build_client_funding_intelligence_summary()
    opportunity = build_opportunity_intelligence_summary()
    priorities = [
        {
            "domain": "operations",
            "priority_score": 90 if (ops.get("risk_level") in {"high", "medium"}) else 65,
            "reason": ops.get("recommended_next_action"),
        },
        {
            "domain": "funding",
            "priority_score": 80 if (funding.get("missing_data") or []) else 60,
            "reason": funding.get("next_best_funding_action"),
        },
        {
            "domain": "opportunity",
            "priority_score": 75 if (opportunity.get("application_readiness_blockers") or []) else 55,
            "reason": opportunity.get("opportunity_next_action"),
        },
    ]
    priorities.sort(key=lambda x: int(x.get("priority_score") or 0), reverse=True)
    return priorities


def recommend_next_domain_focus() -> dict[str, Any]:
    ranked = rank_operational_priorities()
    return ranked[0] if ranked else {"domain": "operations", "priority_score": 50, "reason": "Maintain baseline monitoring."}


def summarize_cross_domain_risks() -> dict[str, Any]:
    ops = build_operational_intelligence_snapshot(mode="compact")
    funding = build_client_funding_intelligence_summary()
    trading = build_trading_intelligence_report()
    opportunity = build_opportunity_intelligence_summary()
    risks = []
    if ops.get("risk_level") in {"high", "medium"}:
        risks.append("Operational reliability requires close supervision.")
    if funding.get("missing_data"):
        risks.append("Funding readiness has missing evidence that can reduce recommendation confidence.")
    if not bool(trading.get("trading_paper_only")):
        risks.append("Trading paper-only guardrail is not active.")
    if opportunity.get("application_readiness_blockers"):
        risks.append("Opportunity execution readiness is blocked by missing prerequisites.")
    return {
        "risk_count": len(risks),
        "risks": risks,
        "overall_risk_level": "high" if len(risks) >= 3 else ("medium" if len(risks) >= 1 else "low"),
    }


def summarize_ai_workforce_status() -> dict[str, Any]:
    ops = build_operational_intelligence_snapshot(mode="compact")
    return {
        "supervised_mode": True,
        "swarm_execution_enabled": False,
        "worker_health": ops.get("worker_health") or {},
        "queue_pressure": ops.get("queue_pressure") or {},
        "recommended_next_action": ops.get("recommended_next_action"),
    }


def build_executive_strategy_summary() -> dict[str, Any]:
    priorities = rank_operational_priorities()
    focus = recommend_next_domain_focus()
    risks = summarize_cross_domain_risks()
    workforce = summarize_ai_workforce_status()
    return {
        "timestamp": _now(),
        "executive_role": "ai_coo",
        "priorities": priorities,
        "next_domain_focus": focus,
        "cross_domain_risks": risks,
        "ai_workforce_status": workforce,
        "cross_domain_recommendations": [
            "Clear operations blockers before expanding strategy throughput.",
            "Address funding readiness gaps to improve capital recommendation quality.",
            "Keep trading intelligence in educational paper-mode until consistency improves.",
        ],
    }
