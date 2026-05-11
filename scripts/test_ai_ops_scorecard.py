#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from control_center.control_center_server import app
from lib.ai_ops_scorecard import build_ai_ops_scorecard


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    scorecard = build_ai_ops_scorecard(
        worker_summary={"online": 4, "offline": 1},
        task_summary={"queued": 3, "running": 1, "failed": 1},
        pending_approvals=2,
        knowledge_snapshot={
            "stale_warnings": [{}],
            "category_counts": {"funding": 2, "credit": 1},
            "recent_funding_insights": [{}],
            "recent_credit_insights": [],
        },
        agent_activation={"ops_monitor": "read-only", "qa_test": "test-only"},
        latest_agent_runs={},
        stale_workers=1,
        email_failures=0,
    )
    ok &= check("scorecard returns stable shape", all(k in scorecard for k in ["operational_health", "knowledge_freshness", "agent_readiness", "risk_blocker"]))
    ok &= check("scorecard read-only marker", scorecard.get("read_only") is True)

    os.environ["CONTROL_CENTER_ADMIN_TOKEN"] = "test-token"
    client = app.test_client()
    overview = client.get('/api/admin/ai-operations/overview?admin_token=test-token')
    body = overview.get_json(silent=True) or {}
    ok &= check("dashboard includes scores", isinstance((body.get("ai_ops_scorecard") or body.get("data", {}).get("ai_ops_scorecard")), dict))
    ok &= check("overview remains read-only", body.get("read_only") is True)
    ok &= check("no secrets exposed", "OPENROUTER_API_KEY" not in str(body) and "sk-or-" not in str(body))

    unauth = client.get('/api/admin/ai-operations/overview')
    ok &= check("unauthorized still rejected", unauth.status_code == 403)
    ok &= check("swarm remains disabled", (body.get("swarm_execution_enabled") is False) or ((body.get("data") or {}).get("swarm_execution_enabled") is False))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
