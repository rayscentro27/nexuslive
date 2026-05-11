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

    required_top = {"model_config", "telegram_mode", "routing_preview", "worker_health_summary", "telemetry", "knowledge_visibility", "read_only"}
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
    unauth_body = unauth.get_json(silent=True) or {}
    ok &= check("unauthorized shape stable", unauth_body.get('ok') is False and unauth_body.get('error') == 'unauthorized' and 'timestamp' in unauth_body)

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

    planned_runs_unauth = client.get('/api/admin/ai-ops/planned-runs')
    ok &= check("planned runs endpoint rejects unauthorized", planned_runs_unauth.status_code == 403)
    planned_runs_auth = client.get('/api/admin/ai-ops/planned-runs?admin_token=test-token')
    ok &= check("planned runs endpoint responds authorized", planned_runs_auth.status_code == 200)
    pr_body = planned_runs_auth.get_json(silent=True) or {}
    ok &= check("planned runs endpoint shape", isinstance(pr_body.get('planned_runs'), list))

    create_unauth = client.post('/api/admin/ai-ops/planned-run/create', json={"scenario_id": "funding_onboarding"})
    ok &= check("planned run create rejects unauthorized", create_unauth.status_code == 403)

    create_auth = client.post(
        '/api/admin/ai-ops/planned-run/create',
        json={"scenario_id": "funding_onboarding", "requested_by": "test-suite"},
        headers={"X-Admin-Token": "test-token", "X-Admin-Actor": "test-suite"},
    )
    ok &= check("planned run create responds authorized", create_auth.status_code == 200)
    created = (create_auth.get_json(silent=True) or {}).get('planned_run') or {}
    run_id = created.get('planned_run_id')
    ok &= check("planned run create shape", bool(run_id) and created.get('can_execute') is False and created.get('execution_mode') == 'preview_only')

    approve_auth = client.post(
        '/api/admin/ai-ops/planned-run/approve',
        json={"planned_run_id": run_id},
        headers={"X-Admin-Token": "test-token", "X-Admin-Actor": "test-suite"},
    )
    ok &= check("planned run approve updates state", ((approve_auth.get_json(silent=True) or {}).get('planned_run') or {}).get('approval_status') == 'approved')
    ok &= check("planned run approve remains non-executable", ((approve_auth.get_json(silent=True) or {}).get('planned_run') or {}).get('can_execute') is False)

    reject_after_approve = client.post(
        '/api/admin/ai-ops/planned-run/reject',
        json={"planned_run_id": run_id, "reason": "invalid transition check"},
        headers={"X-Admin-Token": "test-token", "X-Admin-Actor": "test-suite"},
    )
    ok &= check("invalid transition blocked", reject_after_approve.status_code == 400)

    get_run_auth = client.get(f'/api/admin/ai-ops/planned-run?admin_token=test-token&planned_run_id={run_id}')
    ok &= check("planned run get endpoint shape", isinstance(((get_run_auth.get_json(silent=True) or {}).get('planned_run') or {}).get('audit_log'), list))

    # AI Operations dashboard route
    ui_ops_unauth = client.get('/admin/ai-operations')
    ok &= check("ai-operations page rejects unauthorized", ui_ops_unauth.status_code == 403)
    ui_ops = client.get('/admin/ai-operations?admin_token=test-token')
    ok &= check("ai-operations page responds with token", ui_ops.status_code == 200)
    ui_text = ui_ops.get_data(as_text=True) or ""
    ok &= check("ai-operations page contains AI OPS", "AI OPS" in ui_text)
    ok &= check("dashboard safety badges present", "Swarm: Dry Run Only" in ui_text and "Reports: Email Only" in ui_text and "Execution: Disabled" in ui_text)
    ok &= check("dashboard empty states present", "No active work session" in ui_text and "No pending approvals" in ui_text and "No timeline events yet" in ui_text)
    ok &= check("dashboard does not expose raw tokens", "sk-or-" not in ui_text and "OPENROUTER_API_KEY" not in ui_text and "TELEGRAM_BOT_TOKEN" not in ui_text)

    # New AI operations API family auth + shape
    new_unauth = client.get('/api/admin/ai-operations/overview')
    ok &= check("new overview endpoint rejects unauthorized", new_unauth.status_code == 403)

    overview = client.get('/api/admin/ai-operations/overview?admin_token=test-token')
    obody = overview.get_json(silent=True) or {}
    ok &= check("new overview endpoint responds authorized", overview.status_code == 200)
    ok &= check("new overview contains feature flags", isinstance(obody.get('feature_flags'), dict))
    ok &= check("overview includes agent activation modes", isinstance(obody.get('agent_activation'), dict))
    ok &= check("overview includes ai ops scorecard", isinstance(obody.get('ai_ops_scorecard'), dict))
    ok &= check("swarm execution remains disabled", obody.get('swarm_execution_enabled') is False)
    ok &= check("new overview stable shape", obody.get('ok') is True and isinstance(obody.get('data'), dict) and isinstance(obody.get('timestamp'), str))

    session = client.get('/api/admin/ai-operations/session?admin_token=test-token')
    sbody = session.get_json(silent=True) or {}
    ok &= check("session endpoint responds authorized", session.status_code == 200)
    ok &= check("session endpoint has next action", 'next_recommended_action' in sbody)
    ok &= check("session endpoint stable shape", sbody.get('ok') is True and isinstance(sbody.get('data'), dict) and sbody.get('read_only') is True)

    tasks = client.get('/api/admin/ai-operations/tasks?admin_token=test-token')
    tbody = tasks.get_json(silent=True) or {}
    ok &= check("tasks endpoint responds authorized", tasks.status_code == 200)
    ok &= check("tasks endpoint summary shape", isinstance(tbody.get('task_lifecycle_summary'), dict))
    ok &= check("tasks endpoint stable shape", tbody.get('ok') is True and isinstance(tbody.get('data'), dict))

    approvals = client.get('/api/admin/ai-operations/approvals?admin_token=test-token')
    abody = approvals.get_json(silent=True) or {}
    ok &= check("approvals endpoint responds authorized", approvals.status_code == 200)
    ok &= check("approvals endpoint history shape", isinstance(abody.get('approval_history'), list))
    ok &= check("approvals endpoint stable shape", abody.get('ok') is True and isinstance(abody.get('data'), dict))

    swarm = client.get('/api/admin/ai-operations/swarm?admin_token=test-token')
    swbody = swarm.get_json(silent=True) or {}
    ok &= check("swarm endpoint responds authorized", swarm.status_code == 200)
    ok &= check("swarm endpoint dry-run only", swbody.get('dry_run_only') is True and swbody.get('swarm_execution_enabled') is False)
    ok &= check("swarm endpoint can_execute false", swbody.get('can_execute') is False)
    ok &= check("swarm endpoint stable shape", swbody.get('ok') is True and isinstance(swbody.get('data'), dict))

    workforce = client.get('/api/admin/ai-operations/workforce?admin_token=test-token')
    wbody = workforce.get_json(silent=True) or {}
    ok &= check("workforce endpoint responds authorized", workforce.status_code == 200)
    ok &= check("workforce endpoint heartbeats shape", isinstance(wbody.get('worker_heartbeats'), list))
    ok &= check("workforce endpoint stable shape", wbody.get('ok') is True and isinstance(wbody.get('data'), dict))

    timeline = client.get('/api/admin/ai-operations/timeline?admin_token=test-token')
    tlbody = timeline.get_json(silent=True) or {}
    ok &= check("timeline endpoint responds authorized", timeline.status_code == 200)
    ok &= check("timeline endpoint shape", isinstance(tlbody.get('timeline'), list))
    ok &= check("timeline endpoint stable shape", tlbody.get('ok') is True and isinstance(tlbody.get('data'), dict))

    # Read-only contracts should not expose execution capability
    ok &= check("overview endpoint remains non-executable", obody.get('swarm_execution_enabled') is False and obody.get('dry_run_only') is True)
    ok &= check("swarm endpoint remains non-executable", swbody.get('dry_run_only') is True and swbody.get('swarm_execution_enabled') is False)

    knowledge = client.get('/api/admin/ai-operations/knowledge?admin_token=test-token&category=funding&query=funding')
    kbody = knowledge.get_json(silent=True) or {}
    ok &= check("knowledge endpoint responds authorized", knowledge.status_code == 200)
    ok &= check("knowledge endpoint includes audit and snapshot", isinstance(kbody.get('audit'), dict) and isinstance(kbody.get('snapshot'), dict))
    ok &= check("knowledge endpoint includes read-only retrieval fields", isinstance(kbody.get('recent'), list) and isinstance(kbody.get('search_results'), list))
    ok &= check("knowledge endpoint includes ranked views", isinstance(kbody.get('top_ranked'), list) and isinstance(kbody.get('source_aware_context'), dict))

    exec_daily = client.get('/api/admin/ai-operations/executive-report?admin_token=test-token&type=daily')
    ex_body = exec_daily.get_json(silent=True) or {}
    ok &= check("executive report endpoint responds", exec_daily.status_code == 200)
    ok &= check("executive report endpoint shape", isinstance((ex_body.get('report') or {}).get('operational_memory'), dict))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
