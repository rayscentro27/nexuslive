#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.executive_strategy import (
    build_executive_strategy_summary,
    rank_operational_priorities,
    recommend_next_domain_focus,
    summarize_ai_workforce_status,
    summarize_cross_domain_risks,
)
import lib.executive_strategy as es


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    orig_ops = es.build_operational_intelligence_snapshot
    orig_funding = es.build_client_funding_intelligence_summary
    orig_trading = es.build_trading_intelligence_report
    orig_opp = es.build_opportunity_intelligence_summary
    es.build_operational_intelligence_snapshot = lambda mode="compact": {
        "risk_level": "medium",
        "recommended_next_action": "Clear queue blockers.",
        "worker_health": {"failure_count": 1},
        "queue_pressure": {"pending_count": 2},
    }
    es.build_client_funding_intelligence_summary = lambda: {"missing_data": ["credit profile"], "next_best_funding_action": "Collect credit docs."}
    es.build_trading_intelligence_report = lambda: {"trading_paper_only": True}
    es.build_opportunity_intelligence_summary = lambda: {"application_readiness_blockers": ["deadline docs"], "opportunity_next_action": "Prep forms."}
    try:
        summary = build_executive_strategy_summary()
        ok &= check("executive strategy summary has priorities", isinstance(summary.get("priorities"), list))
        ok &= check("executive strategy has next domain focus", isinstance(summary.get("next_domain_focus"), dict))
        ok &= check("cross domain risks shape", isinstance(summarize_cross_domain_risks().get("risks"), list))
        ok &= check("workforce status supervised", summarize_ai_workforce_status().get("supervised_mode") is True)
        ok &= check("operational priorities ranked", len(rank_operational_priorities()) >= 1)
        ok &= check("recommended next domain exists", isinstance(recommend_next_domain_focus().get("domain"), str))
    finally:
        es.build_operational_intelligence_snapshot = orig_ops
        es.build_client_funding_intelligence_summary = orig_funding
        es.build_trading_intelligence_report = orig_trading
        es.build_opportunity_intelligence_summary = orig_opp
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
