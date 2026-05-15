from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from revenue_engine.revenue_foundation import suggest_revenue_bundle


def build_experiment_record(opportunity_name: str, category: str = "", confidence: float = 0.0) -> dict[str, Any]:
    bundle = suggest_revenue_bundle(opportunity_name, category)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "planned",
        "opportunity_name": opportunity_name,
        "category": category,
        "confidence": confidence,
        "recommendations": bundle,
        "constraints": {
            "paid_ads_autopublish": False,
            "auto_spend_enabled": False,
            "auto_payment_processing": False,
            "real_payment_flows_enabled": False,
        },
        "metrics": {
            "impressions": 0,
            "clicks": 0,
            "leads": 0,
            "conversions": 0,
            "estimated_revenue": 0.0,
            "confirmed_revenue": 0.0,
        },
    }
