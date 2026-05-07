#!/usr/bin/env python3
"""Lightweight tests for AI Ops control center endpoint/UI contract."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True

    from control_center.control_center_server import app, TERMINAL_HTML

    os.environ['CONTROL_CENTER_ADMIN_TOKEN'] = 'test-token'
    client = app.test_client()
    resp = client.get('/api/admin/ai-ops/status?admin_token=test-token')
    ok &= check("endpoint responds 200", resp.status_code == 200)
    payload = resp.get_json(silent=True) or {}

    required_top = {"model_config", "telegram_mode", "routing_preview", "worker_health_summary", "telemetry", "read_only"}
    ok &= check("endpoint shape keys present", required_top.issubset(set(payload.keys())))
    ok &= check("routing preview is list", isinstance(payload.get("routing_preview"), list))
    ok &= check("read_only true", payload.get("read_only") is True)

    # Telemetry unavailable path should not crash
    old_url = os.environ.get("SUPABASE_URL")
    old_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    os.environ["SUPABASE_URL"] = ""
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
    resp2 = client.get('/api/admin/ai-ops/status?admin_token=test-token')
    ok &= check("endpoint survives missing Supabase env", resp2.status_code == 200)
    if old_url is not None:
        os.environ["SUPABASE_URL"] = old_url
    if old_key is not None:
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = old_key

    # UI fallback contract marker exists in JS
    ok &= check("UI includes fallback marker", "Fallback mode active." in TERMINAL_HTML)

    # Unauthorized checks
    unauth = client.get('/api/admin/ai-ops/status')
    ok &= check("status endpoint rejects unauthorized", unauth.status_code == 403)

    post_unauth = client.post('/api/admin/ai-ops/telegram-mode', json={"telegram_enabled": True})
    ok &= check("toggle endpoint rejects unauthorized", post_unauth.status_code == 403)

    # Authorized toggle should not expose secrets
    post_auth = client.post(
        '/api/admin/ai-ops/telegram-mode',
        json={"telegram_enabled": True, "telegram_manual_only": True, "telegram_auto_reports_enabled": False},
        headers={"X-Admin-Token": "test-token", "X-Admin-Actor": "test-suite"},
    )
    body = post_auth.get_json(silent=True) or {}
    ok &= check("toggle endpoint accepts authorized request", post_auth.status_code == 200)
    flat = str(body)
    ok &= check("toggle endpoint hides secrets", "OPENROUTER_API_KEY" not in flat and "sk-or-" not in flat)

    # Roles endpoint auth + safe payload
    roles_unauth = client.get('/api/admin/ai-ops/roles')
    ok &= check("roles endpoint rejects unauthorized", roles_unauth.status_code == 403)
    roles_auth = client.get('/api/admin/ai-ops/roles?admin_token=test-token')
    ok &= check("roles endpoint responds authorized", roles_auth.status_code == 200)
    roles_body = roles_auth.get_json(silent=True) or {}
    ok &= check("roles endpoint shape", isinstance(roles_body.get('roles'), list))
    ok &= check("roles endpoint hides secrets", "OPENROUTER_API_KEY" not in str(roles_body) and "sk-or-" not in str(roles_body))

    swarm_unauth = client.get('/api/admin/ai-ops/swarm-preview')
    ok &= check("swarm endpoint rejects unauthorized", swarm_unauth.status_code == 403)
    swarm_auth = client.get('/api/admin/ai-ops/swarm-preview?admin_token=test-token&initiating_role=ceo_router')
    ok &= check("swarm endpoint responds authorized", swarm_auth.status_code == 200)
    swarm_body = swarm_auth.get_json(silent=True) or {}
    ok &= check("swarm endpoint shape", isinstance((swarm_body.get('swarm_preview') or {}).get('task_sequence'), list))
    ok &= check("swarm endpoint is preview-only", (swarm_body.get('swarm_preview') or {}).get('can_execute') is False)
    ok &= check("swarm endpoint hides secrets", "OPENROUTER_API_KEY" not in str(swarm_body) and "sk-or-" not in str(swarm_body))

    scenarios_unauth = client.get('/api/admin/ai-ops/swarm-scenarios')
    ok &= check("swarm scenarios endpoint rejects unauthorized", scenarios_unauth.status_code == 403)
    scenarios_auth = client.get('/api/admin/ai-ops/swarm-scenarios?admin_token=test-token')
    ok &= check("swarm scenarios endpoint responds authorized", scenarios_auth.status_code == 200)
    scenarios_body = scenarios_auth.get_json(silent=True) or {}
    ok &= check("swarm scenarios shape", isinstance(scenarios_body.get('scenarios'), list))

    scenario_preview_unauth = client.get('/api/admin/ai-ops/swarm-scenario-preview?scenario_id=funding_onboarding')
    ok &= check("scenario preview endpoint rejects unauthorized", scenario_preview_unauth.status_code == 403)
    scenario_preview_auth = client.get('/api/admin/ai-ops/swarm-scenario-preview?admin_token=test-token&scenario_id=funding_onboarding')
    ok &= check("scenario preview endpoint responds authorized", scenario_preview_auth.status_code == 200)
    sp_body = scenario_preview_auth.get_json(silent=True) or {}
    ok &= check("scenario preview shape", isinstance(((sp_body.get('scenario_preview') or {}).get('swarm_preview') or {}).get('task_sequence'), list))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
