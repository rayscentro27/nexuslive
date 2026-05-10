#!/usr/bin/env python3
"""
Nexus AI Control Center — Bloomberg-style master terminal.
Port: 4000 (localhost only)

Panels:
  AI Agents | Research Feed | Strategy Engine | Signals
  Leads     | Reputation    | Marketing       | System Health
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, make_response, render_template_string, request

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [CC] %(levelname)s %(message)s")
logger = logging.getLogger("ControlCenter")

app = Flask(__name__)

_KNOWLEDGE_CACHE_TTL_SECONDS = 120
_KNOWLEDGE_CACHE_LIMIT = 6
_KNOWLEDGE_CACHE_FETCH_LIMIT = 30
_knowledge_cache: dict[tuple, tuple[float, object]] = {}
_response_cache: dict[str, tuple[float, object]] = {}


def _cache_get(key: tuple):
    row = _knowledge_cache.get(key)
    if not row:
        return None
    expires_at, value = row
    if time.time() >= expires_at:
        _knowledge_cache.pop(key, None)
        return None
    return value


def _cache_set(key: tuple, value, ttl_seconds: int = _KNOWLEDGE_CACHE_TTL_SECONDS):
    _knowledge_cache[key] = (time.time() + max(1, int(ttl_seconds)), value)
    return value


def _response_cache_get(key: str, ttl: int = 60):
    row = _response_cache.get(key)
    if not row:
        return None
    expires_at, value = row
    if time.time() >= expires_at:
        _response_cache.pop(key, None)
        return None
    return value


def _response_cache_set(key: str, value, ttl: int = 60):
    _response_cache[key] = (time.time() + ttl, value)
    return value


def _cached_knowledge_pack(category: str, limit: int = None, fetch_limit: int = None):
    limit = _KNOWLEDGE_CACHE_LIMIT if limit is None else int(limit)
    fetch_limit = _KNOWLEDGE_CACHE_FETCH_LIMIT if fetch_limit is None else int(fetch_limit)
    key = ("knowledge_pack", category, limit, fetch_limit)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    from lib.hermes_knowledge_brain import build_source_aware_context_pack

    return _cache_set(key, build_source_aware_context_pack(category, limit=limit, fetch_limit=fetch_limit))


def _cached_knowledge_visibility(limit: int = None, fetch_limit: int = None, stale_days: int = 10):
    limit = _KNOWLEDGE_CACHE_LIMIT if limit is None else int(limit)
    fetch_limit = _KNOWLEDGE_CACHE_FETCH_LIMIT if fetch_limit is None else int(fetch_limit)
    key = ("knowledge_visibility", limit, fetch_limit, int(stale_days))
    cached = _cache_get(key)
    if cached is not None:
        return cached

    from lib.hermes_knowledge_brain import detect_stale_knowledge

    funding_ctx = _cached_knowledge_pack("funding", limit=limit, fetch_limit=fetch_limit)
    credit_ctx = _cached_knowledge_pack("credit", limit=limit, fetch_limit=fetch_limit)
    ops_ctx = _cached_knowledge_pack("operations", limit=limit, fetch_limit=fetch_limit)
    merged = (funding_ctx.get("top_ranked") or []) + (credit_ctx.get("top_ranked") or []) + (ops_ctx.get("top_ranked") or [])
    visibility = {
        "source_quality_summary": {
            **(funding_ctx.get("source_quality_summary") or {}),
            **(credit_ctx.get("source_quality_summary") or {}),
            **(ops_ctx.get("source_quality_summary") or {}),
        },
        "top_ranked_knowledge": {
            "funding": funding_ctx.get("top_ranked") or [],
            "credit": credit_ctx.get("top_ranked") or [],
            "operations": ops_ctx.get("top_ranked") or [],
        },
        "stale_warnings": (detect_stale_knowledge(merged, days=stale_days) or [])[: max(6, limit * 2)],
        "category_counts": {
            "funding": len(funding_ctx.get("top_ranked") or []),
            "credit": len(credit_ctx.get("top_ranked") or []),
            "operations": len(ops_ctx.get("top_ranked") or []),
        },
    }
    return _cache_set(key, visibility)


def _admin_authorized(req) -> bool:
    token = (os.getenv("CONTROL_CENTER_ADMIN_TOKEN") or "").strip()
    if not token:
        return False
    supplied = (req.headers.get("X-Admin-Token") or req.args.get("admin_token") or "").strip()
    return supplied == token


def _unauthorized_response():
    return jsonify({
        "ok": False,
        "error": "unauthorized",
        "code": 403,
        "read_only": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": None,
    }), 403


def _ok_response(data: dict, *, read_only: bool = True, extra: dict | None = None):
    payload = {
        "ok": True,
        "read_only": read_only,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    if extra:
        payload.update(extra)
    return jsonify(payload)


def _is_enabled(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


def _write_env_flag(name: str, value: bool) -> bool:
    """Persist flag to .env in a minimal, additive way."""
    env_path = Path(__file__).parent.parent / ".env"
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = text.splitlines()
    needle = f"{name}="
    rendered = f"{name}={'true' if value else 'false'}"
    replaced = False
    out: list[str] = []
    for line in lines:
        if line.startswith(needle):
            out.append(rendered)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(rendered)
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.environ[name] = "true" if value else "false"
    return True

# CORS — allow requests from Netlify functions (nexus-api.goclearonline.cc)
@app.after_request
def _add_cors(response):
    origin = 'https://nexus-api.goclearonline.cc'
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,OPTIONS'
    return response

# ─────────────────────────────────────────────
# Data API routes
# ─────────────────────────────────────────────

def _safe(fn):
    try:
        return fn()
    except Exception as e:
        return {"error": str(e)}


def _normalize_workflow_output_row(row: dict) -> dict:
    payload = row.get("payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {"payload_text": payload}

    raw_output = payload.get("raw_output") or {}
    if not isinstance(raw_output, dict):
        raw_output = {"draft_content": str(raw_output)}

    subject_type = (
        payload.get("subject_type")
        or payload.get("role")
        or raw_output.get("role")
        or "unknown"
    )

    return {
        "id": row.get("id"),
        "summary": row.get("summary"),
        "status": row.get("status"),
        "created_at": row.get("created_at"),
        "subject_type": subject_type,
        "priority": payload.get("priority"),
        "raw_output": raw_output,
        "payload": payload,
    }


def _prelaunch_tables() -> dict:
    from scripts.prelaunch_utils import table_exists

    return {
        "admin_user_access_overrides": table_exists("admin_user_access_overrides"),
        "prelaunch_testers": table_exists("prelaunch_testers"),
    }


def _decorate_user_rows(rows: list[dict]) -> list[dict]:
    from scripts.prelaunch_utils import latest_row

    tables = _prelaunch_tables()
    decorated = []
    for row in rows:
        user_id = row.get("id")
        override = None
        tester = None
        if tables["admin_user_access_overrides"] and user_id:
            override = latest_row(
                "admin_user_access_overrides",
                f"user_id=eq.{user_id}",
            )
        if tables["prelaunch_testers"] and user_id:
            tester = latest_row(
                "prelaunch_testers",
                f"user_id=eq.{user_id}",
            )
        row["access_override"] = override
        row["tester_record"] = tester
        decorated.append(row)
    return decorated


@app.route("/api/health")
def api_health():
    cached = _response_cache_get("health", ttl=60)
    if cached is not None:
        return jsonify(cached)
    from operations_center.operations_engine import get_system_health
    result = _safe(get_system_health)
    _response_cache_set("health", result, ttl=60)
    return jsonify(result)


@app.route("/api/research")
def api_research():
    from operations_center.operations_engine import check_research_brain
    from research.ai_research_brain import get_latest_strategies, get_status
    return jsonify({
        "brain": _safe(check_research_brain),
        "status": _safe(get_status),
        "latest_strategies": _safe(get_latest_strategies),
    })


@app.route("/api/signals")
def api_signals():
    cached = _response_cache_get("signals", ttl=45)
    if cached is not None:
        return jsonify(cached)
    from operations_center.hedge_fund_panel import get_panel_data
    result = _safe(get_panel_data)
    _response_cache_set("signals", result, ttl=45)
    return jsonify(result)


@app.route("/api/leads")
def api_leads():
    from lead_intelligence.lead_scoring_engine import get_lead_summary
    return jsonify(_safe(get_lead_summary))


@app.route("/api/marketing")
def api_marketing():
    from marketing_automation.marketing_engine import get_marketing_summary, get_performance_metrics
    return jsonify({
        "summary": _safe(get_marketing_summary),
        "performance": _safe(get_performance_metrics),
    })


@app.route("/api/reputation")
def api_reputation():
    from reputation_engine.review_analyzer import get_reputation_summary
    return jsonify(_safe(get_reputation_summary))


@app.route("/api/scheduler")
def api_scheduler():
    from operations_center.scheduler import get_schedule_status
    return jsonify(_safe(get_schedule_status))


@app.route("/api/prelaunch/audit")
def api_prelaunch_audit():
    from scripts.prelaunch_utils import (
        auth_users,
        count_by,
        count_rows,
        default_test_mode,
        list_launchd,
        pgrep_lines,
        probe_port,
        rest_select,
    )

    tables = _prelaunch_tables()
    superadmin = auth_users(email="rayscentro@yahoo.com")
    profile = rest_select(
        "user_profiles?select=id,full_name,role,subscription_plan,onboarding_complete"
        "&id=eq.2c9f45d6-4068-41d3-b3c2-ce6219e84406&limit=1"
    ) or []
    return jsonify({
        "test_mode_default": default_test_mode(),
        "tables": tables,
        "superadmin": {
            "auth_exists": bool(superadmin),
            "profile": profile[0] if profile else None,
        },
        "runtime": {
            "control_center_up": probe_port("127.0.0.1", 4000),
            "netcup_ollama_tunnel": probe_port("127.0.0.1", 11555),
            "scheduler_running": bool(pgrep_lines("operations_center/scheduler.py")),
            "ceo_routing_loop_running": bool(pgrep_lines("lib/ceo_routing_loop.py")),
            "ceo_routed_worker_running": bool(pgrep_lines("lib/ceo_routed_worker.py")),
            "telegram_processes": pgrep_lines("telegram_bot.py|hermes_status_bot.py|hermes_claude_bot.py"),
            "launchd": list_launchd(),
        },
        "supabase": {
            "system_events_total": count_rows("system_events"),
            "job_queue_total": count_rows("job_queue"),
            "workflow_outputs_total": count_rows("workflow_outputs"),
            "worker_heartbeats_total": count_rows("worker_heartbeats"),
            "job_queue_by_status": count_by("job_queue", "status"),
            "workflow_outputs_by_status": count_by("workflow_outputs", "status"),
        },
    })


@app.route("/api/admin/users")
def api_admin_users():
    from flask import request as flask_request
    from scripts.prelaunch_utils import combined_users

    limit = flask_request.args.get("limit", 12, type=int)
    email = (flask_request.args.get("email") or "").strip()
    rows = combined_users(limit=limit, email=email)
    return jsonify({
        "tables": _prelaunch_tables(),
        "users": _decorate_user_rows(rows),
        "count": len(rows),
    })


@app.route("/api/admin/knowledge-review")
def api_admin_knowledge_review_list():
    from flask import request as flask_request
    from lib.knowledge_review_queue import list_records

    status = (flask_request.args.get("status") or "").strip().lower()
    rows = list_records(status=status)
    return jsonify({"ok": True, "status": status or "all", "count": len(rows), "records": rows})


@app.route("/api/admin/knowledge-review", methods=["POST"])
def api_admin_knowledge_review_add():
    from flask import request as flask_request
    from lib.knowledge_review_queue import add_proposed_record

    body = flask_request.get_json(silent=True) or {}
    record = body.get("record") if isinstance(body.get("record"), dict) else {}
    source = (body.get("source") or "admin_api").strip() or "admin_api"
    added = add_proposed_record(record, source=source)
    return jsonify({"ok": True, "record": added})


@app.route("/api/admin/knowledge-review/<record_id>/status", methods=["POST"])
def api_admin_knowledge_review_status(record_id: str):
    from flask import request as flask_request
    from lib.knowledge_review_queue import update_status

    body = flask_request.get_json(silent=True) or {}
    status = (body.get("status") or "").strip().lower()
    reviewed_by = (body.get("reviewed_by") or "ray").strip() or "ray"
    notes = (body.get("notes") or "").strip()
    try:
        updated = update_status(record_id, status=status, reviewed_by=reviewed_by, notes=notes)
    except ValueError:
        return jsonify({"error": "invalid status"}), 400
    if not updated:
        return jsonify({"error": "record not found"}), 404
    return jsonify({"ok": True, "record": updated})


def _send_tester_email_live(to_email: str, subject: str, body: str) -> None:
    import smtplib
    from email.mime.text import MIMEText

    sender = os.getenv("NEXUS_EMAIL", "goclearonline@gmail.com")
    password = os.getenv("NEXUS_EMAIL_PASSWORD", "")
    if not password:
        raise RuntimeError("NEXUS_EMAIL_PASSWORD not configured")

    msg = MIMEText(body)
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(sender, password)
        smtp.send_message(msg)


@app.route("/api/admin/users/<user_id>/waive-payment", methods=["POST"])
def api_waive_payment(user_id: str):
    from flask import request as flask_request
    from scripts.prelaunch_utils import auth_users, supabase_request, utc_now_iso

    if not _prelaunch_tables()["admin_user_access_overrides"]:
        return jsonify({"error": "admin_user_access_overrides table missing; apply prelaunch migration first"}), 400

    body = flask_request.get_json(silent=True) or {}
    membership_level = (body.get("membership_level") or "").strip()
    if membership_level not in {"starter", "growth", "funding_pro", "admin_test"}:
        return jsonify({"error": "membership_level must be starter, growth, funding_pro, or admin_test"}), 400

    users = [u for u in auth_users(per_page=500) if u.get("id") == user_id]
    if not users:
        return jsonify({"error": "user not found"}), 404

    user = users[0]
    rows, _ = supabase_request(
        "admin_user_access_overrides",
        method="POST",
        body={
            "user_id": user_id,
            "email": user.get("email"),
            "membership_level": membership_level,
            "tester_access": bool(body.get("tester_access")),
            "waiver_reason": (body.get("waiver_reason") or "").strip(),
            "waived_by": (body.get("waived_by") or "ray").strip() or "ray",
            "waived_at": utc_now_iso(),
            "expires_at": (body.get("expires_at") or "").strip() or None,
            "revoked_by": None,
            "revoked_at": None,
            "revoke_reason": None,
        },
        prefer="resolution=merge-duplicates,return=representation",
    )
    supabase_request(
        f"user_profiles?id=eq.{user_id}",
        method="PATCH",
        body={"subscription_plan": membership_level, "updated_at": utc_now_iso()},
        prefer="return=representation",
    )
    return jsonify({"ok": True, "user_id": user_id, "override": rows[0] if rows else None})


@app.route("/api/admin/users/<user_id>/revoke-waiver", methods=["POST"])
def api_revoke_waiver(user_id: str):
    from flask import request as flask_request
    from scripts.prelaunch_utils import supabase_request, utc_now_iso

    if not _prelaunch_tables()["admin_user_access_overrides"]:
        return jsonify({"error": "admin_user_access_overrides table missing; apply prelaunch migration first"}), 400

    body = flask_request.get_json(silent=True) or {}
    rows, _ = supabase_request(
        f"admin_user_access_overrides?user_id=eq.{user_id}",
        method="PATCH",
        body={
            "revoked_by": (body.get("revoked_by") or "ray").strip() or "ray",
            "revoked_at": utc_now_iso(),
            "revoke_reason": (body.get("revoke_reason") or "").strip(),
        },
        prefer="return=representation",
    )
    return jsonify({"ok": True, "user_id": user_id, "override": rows[0] if rows else None})


@app.route("/api/admin/users/<user_id>/tester", methods=["POST"])
def api_upsert_tester(user_id: str):
    from flask import request as flask_request
    from scripts.prelaunch_utils import auth_users, supabase_request, utc_now_iso

    if not _prelaunch_tables()["prelaunch_testers"]:
        return jsonify({"error": "prelaunch_testers table missing; apply prelaunch migration first"}), 400

    body = flask_request.get_json(silent=True) or {}
    users = [u for u in auth_users(per_page=500) if u.get("id") == user_id]
    if not users:
        return jsonify({"error": "user not found"}), 404
    user = users[0]
    rows, _ = supabase_request(
        "prelaunch_testers",
        method="POST",
        body={
            "user_id": user_id,
            "email": user.get("email"),
            "tester_access": bool(body.get("tester_access", True)),
            "assigned_by": (body.get("assigned_by") or "ray").strip() or "ray",
            "assigned_at": utc_now_iso(),
            "notes": (body.get("notes") or "").strip(),
        },
        prefer="resolution=merge-duplicates,return=representation",
    )
    return jsonify({"ok": True, "user_id": user_id, "tester": rows[0] if rows else None})


@app.route("/api/admin/users/<user_id>/send-tester-email", methods=["POST"])
def api_send_tester_email(user_id: str):
    from flask import request as flask_request
    from scripts.prelaunch_utils import auth_users, build_tester_email, default_test_mode, supabase_request, utc_now_iso

    body = flask_request.get_json(silent=True) or {}
    users = [u for u in auth_users(per_page=500) if u.get("id") == user_id]
    if not users:
        return jsonify({"error": "user not found"}), 404
    user = users[0]
    preview = build_tester_email(
        name=(body.get("full_name") or user.get("user_metadata", {}).get("full_name") or "").strip(),
        login_link=(body.get("login_link") or os.getenv("NEXUS_LOGIN_URL") or "https://nexus.goclearonline.com/login").strip(),
        membership_level=(body.get("membership_level") or "admin_test").strip(),
        note=(body.get("note") or "").strip(),
    )

    mode = "preview"
    if not default_test_mode() and body.get("send") is True:
        _send_tester_email_live(user.get("email"), preview["subject"], preview["body"])
        mode = "sent"

    if _prelaunch_tables()["prelaunch_testers"]:
        patch_body = {"welcome_email_last_preview_at": utc_now_iso()}
        if mode == "sent":
            patch_body["welcome_email_last_sent_at"] = utc_now_iso()
        supabase_request(
            f"prelaunch_testers?user_id=eq.{user_id}",
            method="PATCH",
            body=patch_body,
            prefer="return=representation",
        )

    return jsonify({
        "ok": True,
        "mode": mode,
        "email": user.get("email"),
        "preview": preview,
        "test_mode_default": default_test_mode(),
    })


@app.route("/api/referral-link")
def api_referral_link():
    from flask import request as flask_request
    from lib.referral_system import build_referral_link

    user_id = (flask_request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    return jsonify(build_referral_link(user_id))


@app.route("/api/referral-stats")
def api_referral_stats():
    from scripts.prelaunch_utils import count_by, count_rows

    return jsonify({
        "links_total": count_rows("referral_links") if _prelaunch_tables() else 0,
        "referrals_total": count_rows("referrals") if _prelaunch_tables() else 0,
        "rewards_total": count_rows("referral_rewards") if _prelaunch_tables() else 0,
        "reward_statuses": count_by("referral_rewards", "status") if _prelaunch_tables() else {},
    })


@app.route("/api/admin/referrals/manual-credit", methods=["POST"])
def api_referral_manual_credit():
    from flask import request as flask_request
    from lib.growth_support import audit_payload, safe_insert

    body = flask_request.get_json(silent=True) or {}
    referral_id = (body.get("referral_id") or "").strip()
    reward_type = (body.get("reward_type") or "manual custom reward").strip()
    reward_value = body.get("reward_value", 0)
    review_note = (body.get("review_note") or "").strip()
    if not referral_id:
        return jsonify({"error": "referral_id is required"}), 400
    result = safe_insert("referral_rewards", audit_payload("manual_referral_credit", {
        "referral_id": referral_id,
        "reward_type": reward_type,
        "reward_value": reward_value,
        "status": "pending_review",
        "reviewed_by": (body.get("reviewed_by") or "ray").strip() or "ray",
        "review_note": review_note,
    }))
    if not result.get("ok"):
        return jsonify(result), 400
    return jsonify({"ok": True, "reward": (result.get("rows") or [None])[0]})


@app.route("/api/growth/summary")
def api_growth_summary():
    from scripts.prelaunch_utils import count_by, count_rows, rest_select

    def safe_counts(table: str, column: str | None = None):
        try:
            if column:
                return count_by(table, column)
            return count_rows(table)
        except Exception:
            return {} if column else 0

    def safe_recent(path: str):
        try:
            return rest_select(path) or []
        except Exception:
            return []

    return jsonify({
        "content_queue": {
            "topics_total": safe_counts("content_topics"),
            "variants_by_status": safe_counts("content_variants", "status"),
            "calendar_by_status": safe_counts("content_calendar", "status"),
            "approvals_by_decision": safe_counts("content_approvals", "decision"),
            "recent_topics": safe_recent("content_topics?select=slug,topic,theme,status&order=created_at.desc&limit=8"),
            "recent_variants": safe_recent(
                "content_variants?select=id,platform,status,hook_draft,caption_draft,created_at,topic_id"
                "&order=created_at.desc&limit=12"
            ),
        },
        "comments_pending": safe_counts("content_approvals", "decision"),
        "referrals": {
            "links_total": safe_counts("referral_links"),
            "referrals_total": safe_counts("referrals"),
            "rewards_by_status": safe_counts("referral_rewards", "status"),
        },
        "dm_drafts": {
            "leads_by_status": safe_counts("dm_leads", "status"),
            "messages_by_status": safe_counts("dm_messages", "status"),
        },
        "influencers": {
            "prospects_by_status": safe_counts("influencer_prospects", "status"),
            "messages_by_status": safe_counts("influencer_outreach_messages", "status"),
        },
        "lead_scores": {
            "segments": safe_counts("lead_scores", "segment"),
            "recent": safe_recent("lead_scores?select=lead_ref,lead_score,segment,recommended_agent&order=updated_at.desc&limit=8"),
        },
        "onboarding": {
            "dropoffs_by_risk": safe_counts("onboarding_dropoffs", "risk_level"),
            "recent_recommendations": safe_recent("onboarding_recommendations?select=user_ref,user_stage,recommended_agent&order=updated_at.desc&limit=8"),
        },
        "learning_notes": safe_recent("content_learning_notes?select=note_type,note,created_by,created_at&order=updated_at.desc&limit=8"),
        "feature_flags": {
            "AUTO_POST_ENABLED": os.getenv("AUTO_POST_ENABLED", "false"),
            "COMMENT_AUTO_REPLY": os.getenv("COMMENT_AUTO_REPLY", "false"),
            "COMMENT_REQUIRE_APPROVAL": os.getenv("COMMENT_REQUIRE_APPROVAL", "true"),
            "DM_AUTO_SEND": os.getenv("DM_AUTO_SEND", "false"),
            "DM_REQUIRE_APPROVAL": os.getenv("DM_REQUIRE_APPROVAL", "true"),
            "INFLUENCER_AUTO_SEND": os.getenv("INFLUENCER_AUTO_SEND", "false"),
            "INFLUENCER_REQUIRE_APPROVAL": os.getenv("INFLUENCER_REQUIRE_APPROVAL", "true"),
        },
    })


@app.route("/api/growth/approval-queue")
def api_growth_approval_queue():
    from flask import request as flask_request
    from scripts.prelaunch_utils import rest_select
    import urllib.parse

    limit = flask_request.args.get("limit", "24").strip()
    platform = (flask_request.args.get("platform") or "").strip()
    created_by = (flask_request.args.get("created_by") or "content_variant_generator").strip()
    try:
        limit_int = max(1, min(int(limit), 100))
    except ValueError:
        limit_int = 24

    query = (
        "content_variants?select="
        "id,topic_id,campaign_id,platform,status,hook_draft,script_draft,caption_draft,"
        "compliance_notes,created_at,cta,hashtags,created_by,content_topics(topic,slug,theme)"
        "&status=eq.pending_review"
        "&order=created_at.desc"
        f"&limit={limit_int}"
    )
    if platform and platform.lower() != "all":
        query += f"&platform=eq.{urllib.parse.quote(platform, safe='')}"
    if created_by and created_by.lower() != "all":
        query += f"&created_by=eq.{urllib.parse.quote(created_by, safe='')}"
    try:
        rows = rest_select(query) or []
    except Exception:
        rows = []
    return jsonify({
        "queue": rows,
        "limit": limit_int,
        "platform_filter": platform or "all",
        "created_by_filter": created_by or "all",
        "count": len(rows),
    })


@app.route("/api/funding/overview")
def api_funding_overview():
    from funding_engine.service import (
        get_recent_recommendation_errors,
        get_users_needing_recommendations,
        get_users_with_stale_recommendations,
    )
    from scripts.prelaunch_utils import count_rows, rest_select

    def safe_count(table: str, filter_query: str = "") -> int:
        try:
            return count_rows(table, filter_query)
        except Exception:
            return 0

    def safe_recent(path: str):
        try:
            return rest_select(path) or []
        except Exception:
            return []

    tier_rows = safe_recent(
        "user_tier_progress?select=user_id,current_tier,tier_1_status,tier_2_status,tier_3_status,"
        "business_readiness_score,relationship_score,updated_at&limit=250"
    )
    score_rows = safe_recent("user_business_score_inputs?select=user_id,tenant_id,created_at&limit=250")
    relationship_rows = safe_recent("banking_relationships?select=user_id,tenant_id,created_at&limit=250")

    tracked_users = {row.get("user_id") for row in tier_rows if row.get("user_id")}
    score_users = {row.get("user_id") for row in score_rows if row.get("user_id")}
    relationship_users = {row.get("user_id") for row in relationship_rows if row.get("user_id")}

    ready_for_tier_1 = sum(
        1 for row in tier_rows
        if (row.get("tier_1_status") in {"ready", "completed"})
        or float(row.get("business_readiness_score") or 0) >= 60
    )
    close_to_tier_2 = sum(
        1 for row in tier_rows
        if row.get("tier_2_status") != "unlocked"
        and float(row.get("business_readiness_score") or 0) >= 60
        and float(row.get("relationship_score") or 0) >= 8
    )
    recent_runs = safe_recent(
        "funding_recommendation_runs?select=user_id,tenant_id,reason,status,created_at,completed_at,error,skipped_reason"
        "&order=created_at.desc&limit=8"
    )
    last_generation_at = recent_runs[0].get("completed_at") if recent_runs else None

    return jsonify({
        "approval_data_ingestion_status": {
            "raw_results": safe_count("credit_approval_results"),
            "normalized_patterns": safe_count("card_approval_patterns"),
        },
        "lending_research_status": {
            "institutions": safe_count("lending_institutions"),
            "recent_institutions": safe_recent(
                "lending_institutions?select=institution_name,institution_type,product_types,created_at&order=created_at.desc&limit=5"
            ),
        },
        "users_ready_for_tier_1": ready_for_tier_1,
        "users_close_to_tier_2_unlock": close_to_tier_2,
        "recommendations_generated": safe_count("funding_recommendations"),
        "application_results_submitted": safe_count("application_results"),
        "pending_invoices": safe_count("success_fee_invoices", "status=eq.pending"),
        "pending_referral_earnings": safe_count("referral_earnings", "status=eq.pending"),
        "missing_business_score_inputs": max(len(tracked_users - score_users), 0),
        "missing_banking_relationship_inputs": max(len(tracked_users - relationship_users), 0),
        "users_needing_recommendation_generation": get_users_needing_recommendations(),
        "users_with_stale_recommendations": get_users_with_stale_recommendations()[:20],
        "last_recommendation_generation_time": last_generation_at,
        "generation_errors": get_recent_recommendation_errors(limit=12),
        "recent_recommendation_runs": recent_runs,
        "recent_tier_progress": tier_rows[:8],
    })


@app.route("/api/funding/recommendations", methods=["GET", "POST"])
def api_funding_recommendations():
    from flask import request as flask_request
    from funding_engine.service import generate_user_recommendations, persist_user_recommendations

    source = flask_request.args if flask_request.method == "GET" else (flask_request.get_json(silent=True) or {})
    user_id = (source.get("user_id") or "").strip()
    tenant_id = (source.get("tenant_id") or "").strip() or None
    tier = source.get("tier")
    try:
        tier = int(tier) if tier not in (None, "") else None
    except Exception:
        tier = None
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    if flask_request.method == "POST":
        return jsonify(persist_user_recommendations(user_id=user_id, tenant_id=tenant_id, tier=tier))
    return jsonify(generate_user_recommendations(user_id=user_id, tenant_id=tenant_id, tier=tier))


@app.route("/api/funding/recommendations/refresh", methods=["POST"])
def api_funding_recommendations_refresh():
    from flask import request as flask_request
    from funding_engine.service import create_or_refresh_user_recommendations

    body = flask_request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    tenant_id = (body.get("tenant_id") or "").strip() or None
    reason = (body.get("reason") or "manual_admin_refresh").strip() or "manual_admin_refresh"
    force = bool(body.get("force"))
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    return jsonify(create_or_refresh_user_recommendations(user_id=user_id, tenant_id=tenant_id, reason=reason, force=force))


@app.route("/api/funding/journey")
def api_funding_journey():
    from flask import request as flask_request
    from funding_engine.service import build_funding_journey_orchestrator

    user_id = (flask_request.args.get("user_id") or "").strip()
    tenant_id = (flask_request.args.get("tenant_id") or "").strip() or None
    auto_generate = str(flask_request.args.get("auto_generate") or "").strip().lower() in {"1", "true", "yes"}
    force_refresh = str(flask_request.args.get("force_refresh") or "").strip().lower() in {"1", "true", "yes"}
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    return jsonify(build_funding_journey_orchestrator(
        user_id=user_id,
        tenant_id=tenant_id,
        auto_generate_if_missing=auto_generate,
        force_refresh=force_refresh,
    ))


@app.route("/api/funding/journey/refresh", methods=["POST"])
def api_funding_journey_refresh():
    from flask import request as flask_request
    from funding_engine.service import build_funding_journey_orchestrator

    body = flask_request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    tenant_id = (body.get("tenant_id") or "").strip() or None
    force = bool(body.get("force"))
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    return jsonify(build_funding_journey_orchestrator(
        user_id=user_id,
        tenant_id=tenant_id,
        auto_generate_if_missing=True,
        force_refresh=force,
    ))


@app.route("/api/funding/tier-2-unlock")
def api_funding_tier_2_unlock():
    from flask import request as flask_request
    from funding_engine.service import build_funding_snapshot

    user_id = (flask_request.args.get("user_id") or "").strip()
    tenant_id = (flask_request.args.get("tenant_id") or "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    snapshot = build_funding_snapshot(user_id=user_id, tenant_id=tenant_id)
    return jsonify({
        "tier_progress": snapshot.get("tier_progress"),
        "missing_inputs": snapshot.get("missing_inputs"),
        "readiness": snapshot.get("readiness"),
        "relationship_score": snapshot.get("relationship_score"),
    })


@app.route("/api/funding/brief")
def api_funding_brief():
    from flask import request as flask_request
    from funding_engine.service import build_hermes_funding_brief

    user_id = (flask_request.args.get("user_id") or "").strip()
    tenant_id = (flask_request.args.get("tenant_id") or "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    return jsonify(build_hermes_funding_brief(user_id=user_id, tenant_id=tenant_id))


@app.route("/api/funding/business-score-inputs", methods=["POST"])
def api_funding_business_score_inputs():
    from flask import request as flask_request
    from scripts.prelaunch_utils import supabase_request

    body = flask_request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    payload = {
        "tenant_id": (body.get("tenant_id") or "").strip() or None,
        "user_id": user_id,
        "duns_status": body.get("duns_status"),
        "paydex_score": body.get("paydex_score"),
        "experian_business_score": body.get("experian_business_score"),
        "equifax_business_score": body.get("equifax_business_score"),
        "nav_grade": body.get("nav_grade"),
        "reporting_tradelines_count": body.get("reporting_tradelines_count"),
        "business_bank_account_age_months": body.get("business_bank_account_age_months"),
        "monthly_deposits": body.get("monthly_deposits"),
        "average_balance": body.get("average_balance"),
        "nsf_count": body.get("nsf_count"),
        "revenue_consistency": body.get("revenue_consistency"),
        "uploaded_report_url": body.get("uploaded_report_url"),
    }
    rows, _ = supabase_request("user_business_score_inputs", method="POST", body=payload, prefer="return=representation")
    # Refresh is handled by the DB trigger → funding_recommendation_jobs → scheduler path.
    return jsonify({"ok": True, "input": (rows or [None])[0], "refresh": {"queued": True}})


@app.route("/api/funding/banking-relationships", methods=["POST"])
def api_funding_banking_relationships():
    from flask import request as flask_request
    from scripts.prelaunch_utils import supabase_request

    body = flask_request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    payload = {
        "tenant_id": (body.get("tenant_id") or "").strip() or None,
        "user_id": user_id,
        "institution_name": body.get("institution_name"),
        "account_type": body.get("account_type"),
        "account_open_date": body.get("account_open_date"),
        "account_age_days": body.get("account_age_days"),
        "average_balance": body.get("average_balance"),
        "monthly_deposits": body.get("monthly_deposits"),
        "deposit_consistency": body.get("deposit_consistency"),
        "prior_products": body.get("prior_products") or [],
        "target_for_funding": bool(body.get("target_for_funding")),
        "relationship_score": body.get("relationship_score"),
        "verification_status": body.get("verification_status") or "self_reported",
        "proof_url": body.get("proof_url"),
    }
    rows, _ = supabase_request("banking_relationships", method="POST", body=payload, prefer="return=representation")
    # Refresh is handled by the DB trigger → funding_recommendation_jobs → scheduler path.
    return jsonify({"ok": True, "relationship": (rows or [None])[0], "refresh": {"queued": True}})


@app.route("/api/funding/onboarding-complete", methods=["POST"])
def api_funding_onboarding_complete():
    from flask import request as flask_request
    from scripts.prelaunch_utils import supabase_request, utc_now_iso

    body = flask_request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    rows, _ = supabase_request(
        f"user_profiles?id=eq.{user_id}",
        method="PATCH",
        body={"onboarding_complete": True, "updated_at": utc_now_iso()},
        prefer="return=representation",
    )
    # Refresh is handled by the DB trigger (onboarding_complete transition) → funding_recommendation_jobs → scheduler path.
    return jsonify({"ok": True, "profile": (rows or [None])[0], "refresh": {"queued": True}})


@app.route("/api/funding/application-results", methods=["GET", "POST"])
def api_funding_application_results():
    from flask import request as flask_request
    from funding_engine.billing_events import record_application_result
    from scripts.prelaunch_utils import rest_select
    import urllib.parse

    if flask_request.method == "GET":
        user_id = (flask_request.args.get("user_id") or "").strip()
        tenant_id = (flask_request.args.get("tenant_id") or "").strip() or None
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        filters = [f"user_id=eq.{urllib.parse.quote(user_id, safe='')}"]
        if tenant_id:
            filters.append(f"tenant_id=eq.{urllib.parse.quote(tenant_id, safe='')}")
        rows = rest_select(
            "application_results?select=*&order=created_at.desc&" + "&".join(filters)
        ) or []
        return jsonify({"results": rows})

    body = flask_request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    result = record_application_result(
        tenant_id=(body.get("tenant_id") or "").strip() or None,
        user_id=user_id,
        recommendation_id=(body.get("recommendation_id") or "").strip() or None,
        result_status=(body.get("result_status") or "").strip() or "reported",
        approved_amount=body.get("approved_amount") or 0,
        proof_url=(body.get("proof_url") or "").strip() or None,
        verified=bool(body.get("verified")),
    )
    return jsonify(result), (200 if result.get("ok") else 400)


@app.route("/api/funding/invoices")
def api_funding_invoices():
    from flask import request as flask_request
    from scripts.prelaunch_utils import rest_select
    import urllib.parse

    user_id = (flask_request.args.get("user_id") or "").strip()
    tenant_id = (flask_request.args.get("tenant_id") or "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    filters = [f"user_id=eq.{urllib.parse.quote(user_id, safe='')}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{urllib.parse.quote(tenant_id, safe='')}")
    rows = rest_select("success_fee_invoices?select=*&order=created_at.desc&" + "&".join(filters)) or []
    return jsonify({"invoices": rows})


@app.route("/api/funding/referral-dashboard")
def api_funding_referral_dashboard():
    from flask import request as flask_request
    from scripts.prelaunch_utils import rest_select
    import urllib.parse

    user_id = (flask_request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    q = urllib.parse.quote(user_id, safe="")
    referrals = rest_select(
        f"referrals?select=*&referrer_user_id=eq.{q}&order=created_at.desc"
    ) or []
    earnings = rest_select(
        f"referral_earnings?select=*&referrer_user_id=eq.{q}&order=created_at.desc"
    ) or []
    return jsonify({
        "referrals": referrals,
        "earnings": earnings,
        "pending_earnings": [row for row in earnings if row.get("status") == "pending"],
    })


@app.route("/api/growth/variants")
def api_growth_variants():
    from flask import request as flask_request
    from scripts.prelaunch_utils import rest_select
    import urllib.parse

    limit = flask_request.args.get("limit", "24").strip()
    status = flask_request.args.get("status", "pending_review").strip()
    try:
        limit_int = max(1, min(int(limit), 100))
    except ValueError:
        limit_int = 24

    query = (
        "content_variants?select="
        "id,topic_id,campaign_id,platform,status,hook_draft,script_draft,caption_draft,"
        "compliance_notes,created_at,cta,hashtags,created_by,content_topics(topic,slug,theme)"
        "&order=created_at.desc"
        f"&limit={limit_int}"
    )
    if status and status != "all":
        query += f"&status=eq.{urllib.parse.quote(status, safe='')}"
    try:
        rows = rest_select(query) or []
    except Exception:
        rows = []
    return jsonify({"variants": rows, "status_filter": status or "all", "limit": limit_int})


@app.route("/api/messages/review-summary")
def api_messages_review_summary():
    from scripts.prelaunch_utils import rest_select

    def safe_recent(path: str):
        try:
            return rest_select(path) or []
        except Exception:
            return []

    return jsonify({
        "pending_dm_drafts": safe_recent(
            "dm_messages?select=id,sequence_id,message_order,draft_text,status,created_at"
            "&status=eq.draft_pending_approval&order=created_at.desc&limit=20"
        ),
        "pending_comment_drafts": safe_recent(
            "social_comments?select=id,platform,external_ref,author_handle,content_topic,comment_text,reply_draft,status,created_at"
            "&status=eq.draft_pending_approval&order=created_at.desc&limit=20"
        ),
        "recent_message_logs": safe_recent(
            "message_logs?select=id,platform,direction,event_type,external_ref,content_topic,intent_category,status,created_at"
            "&order=created_at.desc&limit=20"
        ),
    })


@app.route("/api/messages/dm-drafts/<draft_id>", methods=["PATCH"])
def api_update_dm_draft(draft_id: str):
    from flask import request as flask_request
    from scripts.prelaunch_utils import supabase_request, utc_now_iso

    body = flask_request.get_json(silent=True) or {}
    action = (body.get("action") or "").strip().lower()
    if action not in {"approve", "reject"}:
        return jsonify({"error": "action must be approve or reject"}), 400

    status = "approved" if action == "approve" else "rejected"
    note = (body.get("note") or "").strip()
    reviewed_by = (body.get("reviewed_by") or "ray").strip() or "ray"

    rows, _ = supabase_request(
        f"dm_messages?id=eq.{draft_id}",
        method="PATCH",
        body={"status": status, "updated_at": utc_now_iso()},
        prefer="return=representation",
    )
    draft = (rows or [None])[0]
    if not draft:
        return jsonify({
            "ok": False,
            "draft_id": draft_id,
            "error": "dm draft not found",
        }), 404
    try:
        supabase_request(
            "dm_approvals",
            method="POST",
            body={
                "message_id": draft_id,
                "decision": status,
                "reviewed_by": reviewed_by,
                "review_note": note,
                "reviewed_at": utc_now_iso(),
            },
            prefer="return=representation",
        )
    except Exception:
        pass
    return jsonify({"ok": True, "draft_id": draft_id, "status": status, "draft": draft})


@app.route("/api/messages/comment-drafts/<draft_id>", methods=["PATCH"])
def api_update_comment_draft(draft_id: str):
    from flask import request as flask_request
    from scripts.prelaunch_utils import supabase_request, utc_now_iso

    body = flask_request.get_json(silent=True) or {}
    action = (body.get("action") or "").strip().lower()
    if action not in {"approve", "reject"}:
        return jsonify({"error": "action must be approve or reject"}), 400

    status = "approved" if action == "approve" else "rejected"
    rows, _ = supabase_request(
        f"social_comments?id=eq.{draft_id}",
        method="PATCH",
        body={"status": status, "updated_at": utc_now_iso()},
        prefer="return=representation",
    )
    draft = (rows or [None])[0]
    if not draft:
        return jsonify({
            "ok": False,
            "draft_id": draft_id,
            "error": "comment draft not found",
        }), 404
    return jsonify({"ok": True, "draft_id": draft_id, "status": status, "draft": draft})


@app.route("/api/all")
def api_all():
    from operations_center.operations_engine import get_full_ops_report
    return jsonify(_safe(get_full_ops_report))


@app.route("/api/mission-control")
def api_mission_control():
    from scripts.prelaunch_utils import rest_select

    def _safe_select(path: str) -> list[dict]:
        try:
            return rest_select(path) or []
        except Exception:
            return []

    worker_rows = _safe_select(
        "worker_heartbeats?select=worker_id,worker_type,status,last_seen_at&order=last_seen_at.desc&limit=120"
    )
    digest_rows = _safe_select(
        "hermes_aggregates?select=event_type,aggregated_summary,created_at,event_source,classification"
        "&order=created_at.desc&limit=200"
    )
    pending_recs = _safe_select(
        "owner_approval_queue?select=id,status,priority,description,payload,created_at"
        "&action_type=eq.chief_of_staff_recommendation&status=eq.pending&order=created_at.desc&limit=20"
    )
    failed_jobs = _safe_select("job_events?status=eq.failed&select=id,agent_name,created_at&order=created_at.desc&limit=20")
    brief_rows = _safe_select(
        "executive_briefings?select=briefing_type,content,urgency,created_at&order=created_at.desc&limit=6"
    )

    worker_cards = [
        "Hermes CEO",
        "Credit Repair Specialist",
        "Funding Strategist",
        "Grants Researcher",
        "Trading Analyst",
        "Opportunity Hunter",
        "CRM Copilot",
        "Operations Monitor",
    ]

    heartbeats_by_type: dict[str, dict] = {}
    for row in worker_rows:
        key = str(row.get("worker_type") or row.get("worker_id") or "unknown").lower()
        if key and key not in heartbeats_by_type:
            heartbeats_by_type[key] = row

    def _pick_worker(label: str) -> dict:
        lower = label.lower()
        match = None
        for k, row in heartbeats_by_type.items():
            if any(token in k for token in lower.split()):
                match = row
                break
        if not match:
            status = "degraded"
            return {
                "name": label,
                "worker_health": status,
                "active_task": "Awaiting telemetry linkage",
                "confidence_posture": "baseline confidence",
                "queue_depth": len(pending_recs),
                "recommendation_count": len(pending_recs),
                "alert_count": len(failed_jobs),
                "last_activity": "unknown",
                "status_indicator": status,
            }
        status = str(match.get("status") or "unknown")
        return {
            "name": label,
            "worker_health": status,
            "active_task": "Digest + recommendation operations",
            "confidence_posture": "emerging signal" if pending_recs else "baseline confidence",
            "queue_depth": len(pending_recs),
            "recommendation_count": len(pending_recs),
            "alert_count": len(failed_jobs),
            "last_activity": match.get("last_seen_at") or "unknown",
            "status_indicator": "healthy" if status in {"ok", "healthy", "online", "running"} else "degraded",
        }

    workforce = [_pick_worker(label) for label in worker_cards]

    grouped_feed: dict[str, list[dict]] = {
        "critical": [],
        "recommendations": [],
        "digest": [],
        "operations": [],
    }
    for row in digest_rows:
        et = str(row.get("event_type") or "").lower()
        text = str(row.get("aggregated_summary") or "")
        item = {
            "event_type": row.get("event_type"),
            "summary": text[:220],
            "created_at": row.get("created_at"),
        }
        if "critical" in et or "failed" in et:
            grouped_feed["critical"].append(item)
        elif "recommend" in et:
            grouped_feed["recommendations"].append(item)
        elif "digest" in et:
            grouped_feed["digest"].append(item)
        else:
            grouped_feed["operations"].append(item)

    top_recs = []
    for row in pending_recs[:6]:
        payload = row.get("payload") or {}
        details = payload.get("details") or {}
        top_recs.append(
            {
                "id": str(row.get("id") or "")[:8],
                "type": payload.get("recommendation_type") or "unknown",
                "title": payload.get("title") or row.get("description") or "untitled",
                "status": row.get("status") or "pending",
                "confidence": payload.get("confidence_band") or details.get("confidence_score") or "pending",
                "why": payload.get("rationale") or "Awaiting richer signal history.",
            }
        )

    weekly_focus = ""
    strategic_focus = ""
    try:
        from ceo_agent.chief_of_staff import build_weekly_focus

        weekly_focus = build_weekly_focus()
    except Exception:
        weekly_focus = "Weekly focus unavailable."

    try:
        from ceo_agent.client_success_intelligence import prioritize_this_week

        strategic_focus = prioritize_this_week()
    except Exception:
        strategic_focus = "Client strategic focus unavailable."

    sparse_warnings = []
    try:
        from ceo_agent.executive_review_console import sparse_data_diagnostics

        sparse_warnings.append(sparse_data_diagnostics())
    except Exception:
        sparse_warnings.append("Sparse-data diagnostics unavailable.")

    return jsonify(
        {
            "workforce": workforce,
            "executive_panel": {
                "weekly_priorities": weekly_focus,
                "critical_alerts": len(failed_jobs),
                "top_recommendations": top_recs,
                "funding_readiness_signals": strategic_focus,
                "client_momentum_churn": strategic_focus,
                "highest_roi_opportunities": [r.get("title") for r in top_recs[:3]],
                "strategic_focus": strategic_focus,
            },
            "operations_feed": grouped_feed,
            "recommendation_queue": top_recs,
            "review_drawer": {
                "reasoning": top_recs[0]["why"] if top_recs else "No pending recommendations.",
                "confidence": top_recs[0]["confidence"] if top_recs else "pending confidence",
                "sparse_data_warnings": sparse_warnings,
                "missing_telemetry": sparse_warnings,
                "historical_outcomes": [r.get("briefing_type") for r in brief_rows[:4]],
                "contributing_signals": ["ROI", "confidence", "automation", "alignment", "outcome history"],
            },
            "briefings": brief_rows,
        }
    )


@app.route("/api/admin/ai-ops/status")
def api_admin_ai_ops_status():
    if not _admin_authorized(request):
        return _unauthorized_response()

    from scripts.prelaunch_utils import rest_select

    def _safe_select(path: str) -> list[dict]:
        try:
            return rest_select(path) or []
        except Exception:
            return []

    def _flag(name: str, default: str) -> bool:
        return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}

    routing_tasks = [
        "funding_strategy",
        "credit_analysis",
        "telegram_reply",
        "cheap_summary",
        "research_worker",
        "coding_assistant",
    ]
    routing_preview_rows: list[dict] = []
    provider_default = "unknown"
    default_model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    configured_context = int(os.getenv("OPENROUTER_CTX", os.getenv("MODEL_CONTEXT_LENGTH", "128000")) or 128000)

    try:
        from lib.model_router import routing_preview, provider_summary

        providers = provider_summary()
        for p in providers:
            if p.get("name") == "openrouter":
                provider_default = "openrouter"
                break

        for task in routing_tasks:
            try:
                r = routing_preview(task)
                routing_preview_rows.append(r)
            except Exception as e:
                routing_preview_rows.append(
                    {
                        "requested_task": task,
                        "resolved_task": task,
                        "provider": "unavailable",
                        "model": "unavailable",
                        "max_context": 0,
                        "error": type(e).__name__,
                    }
                )
    except Exception:
        for task in routing_tasks:
            routing_preview_rows.append(
                {
                    "requested_task": task,
                    "resolved_task": task,
                    "provider": "unavailable",
                    "model": "unavailable",
                    "max_context": 0,
                    "error": "router_unavailable",
                }
            )

    worker_rows = _safe_select(
        "worker_heartbeats?select=worker_id,status,last_seen_at&order=last_seen_at.desc&limit=40"
    )
    worker_status_counts: dict[str, int] = {}
    for row in worker_rows:
        k = str(row.get("status") or "unknown").lower()
        worker_status_counts[k] = worker_status_counts.get(k, 0) + 1

    retry_rows = _safe_select(
        "hermes_aggregates?event_source=eq.ai_ops_retries"
        "&select=event_type,aggregated_summary,created_at"
        "&order=created_at.desc&limit=20"
    )
    usage_rows = _safe_select(
        "hermes_aggregates?event_source=eq.ai_ops_model_usage"
        "&select=event_type,aggregated_summary,created_at"
        "&order=created_at.desc&limit=20"
    )
    knowledge_visibility = {}
    if _is_enabled("KNOWLEDGE_DASHBOARD_ENABLED", "true"):
        try:
            knowledge_visibility = _cached_knowledge_visibility()
            knowledge_visibility["stale_warnings"] = (knowledge_visibility.get("stale_warnings") or [])[:8]
        except Exception:
            knowledge_visibility = {}

    intelligence_visibility = {}
    try:
        from lib.operational_intelligence import build_operational_intelligence_snapshot
        from lib.client_funding_intelligence import build_client_funding_intelligence_summary
        from lib.trading_intelligence_lab import build_trading_intelligence_report
        from lib.opportunity_intelligence import build_opportunity_intelligence_summary
        from lib.executive_strategy import build_executive_strategy_summary
        from lib.demo_readiness import run_demo_readiness_check

        op = build_operational_intelligence_snapshot(mode="compact")
        fi = build_client_funding_intelligence_summary()
        ti = build_trading_intelligence_report()
        oi = build_opportunity_intelligence_summary()
        es = build_executive_strategy_summary()
        dr = run_demo_readiness_check()
        intelligence_visibility = {
            "operational_intelligence": {
                "status": "ok",
                "enabled": bool(op.get("enabled")),
                "latest_summary": op.get("executive_summary"),
                "top_blocker": (op.get("degraded_components") or ["none"])[0],
                "recommended_next_action": op.get("recommended_next_action"),
                "confidence_risk_indicator": op.get("risk_level"),
            },
            "funding_intelligence": {
                "status": "ok",
                "enabled": bool(fi.get("enabled")),
                "latest_summary": "Funding readiness and blockers prepared.",
                "top_blocker": (fi.get("funding_blockers") or ["none"])[0],
                "recommended_next_action": fi.get("next_best_funding_action"),
                "confidence_risk_indicator": (fi.get("funding_readiness_summary") or {}).get("confidence", "low"),
            },
            "trading_intelligence_lab": {
                "status": "ok",
                "enabled": bool(ti.get("enabled")),
                "latest_summary": "Educational paper-trading strategy lab is in review mode.",
                "top_blocker": "live execution disabled by policy",
                "recommended_next_action": "Continue demo validation on launch-focus strategies.",
                "confidence_risk_indicator": ((ti.get("strategy_health") or {}).get("risk_score") or "moderate"),
            },
            "opportunity_intelligence": {
                "status": "ok",
                "enabled": bool(oi.get("enabled")),
                "latest_summary": "Opportunity shortlist and blockers prepared.",
                "top_blocker": (oi.get("application_readiness_blockers") or ["none"])[0],
                "recommended_next_action": oi.get("opportunity_next_action"),
                "confidence_risk_indicator": oi.get("opportunity_fit_score", "low"),
            },
            "executive_strategy_summary": {
                "status": "ok",
                "enabled": True,
                "latest_summary": "Cross-domain priorities and risks are available.",
                "top_blocker": (((es.get("cross_domain_risks") or {}).get("risks") or ["none"])[0]),
                "recommended_next_action": (((es.get("next_domain_focus") or {}).get("reason")) or "maintain supervision"),
                "confidence_risk_indicator": (((es.get("cross_domain_risks") or {}).get("overall_risk_level")) or "low"),
            },
            "demo_readiness": {
                "status": dr.get("status") or "unknown",
                "enabled": True,
                "latest_summary": f"Score {int(dr.get('score') or 0)} with {len(dr.get('blockers') or [])} blockers.",
                "top_blocker": ((dr.get("blockers") or ["none"])[0]),
                "recommended_next_action": dr.get("next_action") or "Run readiness checklist.",
                "confidence_risk_indicator": "high" if int(dr.get("score") or 0) >= 90 else "medium",
            },
        }
    except Exception:
        intelligence_visibility = {}

    data = {
            "model_config": {
                "active_default_provider": provider_default,
                "active_default_model": default_model,
                "configured_context_length": configured_context,
            },
            "telegram_mode": {
                "enabled": _flag("TELEGRAM_ENABLED", "true"),
                "manual_only": _flag("TELEGRAM_MANUAL_ONLY", "true"),
                "auto_reports_enabled": _flag("TELEGRAM_AUTO_REPORTS_ENABLED", "false"),
            },
            "routing_preview": routing_preview_rows,
            "worker_health_summary": {
                "total_rows": len(worker_rows),
                "status_counts": worker_status_counts,
                "latest": worker_rows[:8],
            },
            "telemetry": {
                "recent_retry_error_events": retry_rows,
                "recent_model_usage_events": usage_rows,
            },
            "knowledge_visibility": knowledge_visibility,
            "intelligence_visibility": intelligence_visibility,
        }
    return _ok_response(data, read_only=True, extra={"updated_at": datetime.now(timezone.utc).isoformat(), **data})


@app.route("/api/admin/ai-ops/telegram-mode", methods=["POST"])
def api_admin_ai_ops_telegram_mode():
    if not _admin_authorized(request):
        return _unauthorized_response()

    body = request.get_json(silent=True) or {}
    allowed = {
        "TELEGRAM_ENABLED": body.get("telegram_enabled"),
        "TELEGRAM_MANUAL_ONLY": body.get("telegram_manual_only"),
        "TELEGRAM_AUTO_REPORTS_ENABLED": body.get("telegram_auto_reports_enabled"),
    }

    updates: dict[str, bool] = {}
    for key, value in allowed.items():
        if value is None:
            continue
        updates[key] = bool(value)

    if not updates:
        return jsonify({"error": "no toggles provided"}), 400

    try:
        for key, value in updates.items():
            _write_env_flag(key, value)
        logger.info(
            "ai_ops.telegram_mode_update by=%s ip=%s updates=%s",
            request.headers.get("X-Admin-Actor", "control_center"),
            request.remote_addr,
            updates,
        )
        return jsonify({
            "ok": True,
            "updates": updates,
            "note": "Restart telegram service to apply runtime changes safely.",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error("ai_ops.telegram_mode_update failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/ai-ops/roles")
def api_admin_ai_ops_roles():
    if not _admin_authorized(request):
        return _unauthorized_response()

    from lib.ai_employee_registry import list_roles, role_routing_preview

    rows = []
    for role in list_roles():
        rid = role.get("role_id", "unknown")
        preview = role_routing_preview(rid)
        rows.append(
            {
                "role_id": rid,
                "display_name": role.get("display_name"),
                "description": role.get("description"),
                "allowed_task_types": role.get("allowed_task_types", []),
                "preferred_model_class": role.get("preferred_model_class"),
                "risk_level": role.get("risk_level"),
                "can_auto_execute": bool(role.get("can_auto_execute", False)),
                "requires_admin_approval": bool(role.get("requires_admin_approval", True)),
                "telegram_allowed": bool(role.get("telegram_allowed", False)),
                "telegram_scope": role.get("telegram_scope") or "none",
                "routing_preview": preview.get("routing_preview"),
                "routing_error": preview.get("error"),
            }
        )

    return _ok_response({"roles": rows}, read_only=True, extra={"roles": rows, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-ops/swarm-preview")
def api_admin_ai_ops_swarm_preview():
    if not _admin_authorized(request):
        return _unauthorized_response()

    from lib.swarm_orchestration_foundation import build_swarm_preview, get_allowed_delegates, list_handoff_rules

    initiating_role = (request.args.get("initiating_role") or "ceo_router").strip()
    objective = (request.args.get("objective") or "operator requested multi-role plan").strip()
    roles_raw = (request.args.get("delegated_roles") or "").strip()
    delegated_roles = [r.strip() for r in roles_raw.split(",") if r.strip()] if roles_raw else None

    preview = build_swarm_preview(
        initiating_role=initiating_role,
        objective=objective,
        delegated_roles=delegated_roles,
    )
    data = {
        "swarm_preview": preview,
        "allowed_delegates": get_allowed_delegates(initiating_role),
        "handoff_rules": list_handoff_rules().get(initiating_role, {}),
        "dry_run_only": True,
        "can_execute": False,
    }
    return _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-ops/swarm-scenarios")
def api_admin_ai_ops_swarm_scenarios():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.swarm_scenarios import list_swarm_scenarios

    rows = list_swarm_scenarios()
    return _ok_response({"scenarios": rows}, read_only=True, extra={"scenarios": rows, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-ops/swarm-scenario-preview")
def api_admin_ai_ops_swarm_scenario_preview():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.swarm_scenarios import build_scenario_preview

    scenario_id = (request.args.get("scenario_id") or "funding_onboarding").strip()
    payload = build_scenario_preview(scenario_id)
    data = {"scenario_preview": payload, "dry_run_only": True, "can_execute": False}
    return _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-ops/planned-runs")
def api_admin_ai_ops_planned_runs():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.swarm_approval_queue import list_planned_runs

    rows = list_planned_runs()
    data = {
        "planned_runs": rows,
        "execution_mode": "preview_only",
        "dry_run_only": True,
        "can_execute": False,
    }
    return _ok_response(data, read_only=False, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-ops/planned-run")
def api_admin_ai_ops_planned_run():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.swarm_approval_queue import get_planned_run

    planned_run_id = (request.args.get("planned_run_id") or "").strip()
    if not planned_run_id:
        return jsonify({"error": "planned_run_id_required"}), 400
    row = get_planned_run(planned_run_id)
    if not row:
        return jsonify({"error": "planned_run_not_found", "planned_run_id": planned_run_id}), 404
    data = {
        "planned_run": row,
        "execution_mode": "preview_only",
        "dry_run_only": True,
        "can_execute": False,
    }
    return _ok_response(data, read_only=False, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-ops/planned-run/create", methods=["POST"])
def api_admin_ai_ops_planned_run_create():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.swarm_approval_queue import create_planned_run

    body = request.get_json(silent=True) or {}
    scenario_id = (body.get("scenario_id") or "funding_onboarding").strip()
    actor = (request.headers.get("X-Admin-Actor") or body.get("requested_by") or "operator").strip()
    row = create_planned_run(scenario_id=scenario_id, requested_by=actor)
    if row.get("error"):
        return jsonify(row), 400
    logger.info("ai_ops.planned_run_create by=%s ip=%s planned_run_id=%s scenario_id=%s", actor, request.remote_addr, row.get("planned_run_id"), scenario_id)
    data = {"planned_run": row, "execution_mode": "preview_only", "dry_run_only": True, "can_execute": False}
    return _ok_response(data, read_only=False, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-ops/planned-run/approve", methods=["POST"])
def api_admin_ai_ops_planned_run_approve():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.swarm_approval_queue import approve_planned_run

    body = request.get_json(silent=True) or {}
    planned_run_id = (body.get("planned_run_id") or "").strip()
    actor = (request.headers.get("X-Admin-Actor") or "operator").strip() or "operator"
    if not planned_run_id:
        return jsonify({"error": "planned_run_id_required"}), 400
    row = approve_planned_run(planned_run_id, actor=actor)
    if row.get("error"):
        code = 404 if row.get("error") == "planned_run_not_found" else 400
        return jsonify(row), code
    logger.info("ai_ops.planned_run_approve by=%s ip=%s planned_run_id=%s", actor, request.remote_addr, planned_run_id)
    data = {"planned_run": row, "execution_mode": "preview_only", "dry_run_only": True, "can_execute": False}
    return _ok_response(data, read_only=False, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-ops/planned-run/reject", methods=["POST"])
def api_admin_ai_ops_planned_run_reject():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.swarm_approval_queue import reject_planned_run

    body = request.get_json(silent=True) or {}
    planned_run_id = (body.get("planned_run_id") or "").strip()
    reason = (body.get("reason") or "").strip()
    actor = (request.headers.get("X-Admin-Actor") or "operator").strip() or "operator"
    if not planned_run_id:
        return jsonify({"error": "planned_run_id_required"}), 400
    row = reject_planned_run(planned_run_id, actor=actor, reason=reason)
    if row.get("error"):
        code = 404 if row.get("error") == "planned_run_not_found" else 400
        return jsonify(row), code
    logger.info("ai_ops.planned_run_reject by=%s ip=%s planned_run_id=%s", actor, request.remote_addr, planned_run_id)
    data = {"planned_run": row, "execution_mode": "preview_only", "dry_run_only": True, "can_execute": False}
    return _ok_response(data, read_only=False, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-ops/planned-run/cancel", methods=["POST"])
def api_admin_ai_ops_planned_run_cancel():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.swarm_approval_queue import cancel_planned_run

    body = request.get_json(silent=True) or {}
    planned_run_id = (body.get("planned_run_id") or "").strip()
    reason = (body.get("reason") or "").strip()
    actor = (request.headers.get("X-Admin-Actor") or "operator").strip() or "operator"
    if not planned_run_id:
        return jsonify({"error": "planned_run_id_required"}), 400
    row = cancel_planned_run(planned_run_id, actor=actor, reason=reason)
    if row.get("error"):
        code = 404 if row.get("error") == "planned_run_not_found" else 400
        return jsonify(row), code
    logger.info("ai_ops.planned_run_cancel by=%s ip=%s planned_run_id=%s", actor, request.remote_addr, planned_run_id)
    data = {"planned_run": row, "execution_mode": "preview_only", "dry_run_only": True, "can_execute": False}
    return _ok_response(data, read_only=False, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


def _safe_select(path: str) -> list[dict]:
    from scripts.prelaunch_utils import rest_select

    try:
        return rest_select(path) or []
    except Exception:
        return []


def _approval_rows(limit: int = 40) -> list[dict]:
    return _safe_select(
        f"owner_approval_queue?select=id,action_type,status,requested_by,resolution_note,resolved_by,created_at,updated_at&order=created_at.desc&limit={limit}"
    )


@app.route("/api/admin/ai-operations/session")
def api_admin_ai_operations_session():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib import hermes_ops_memory

    mem = hermes_ops_memory.load_memory(updated_by="control_center")
    active = hermes_ops_memory.get_active_work_session(mem)
    data = {
        "active_work_session": active,
        "active_priorities": mem.get("active_priorities") or [],
        "current_tasks": mem.get("task_lifecycle") or {},
        "blocked_items": mem.get("blocked_priorities") or [],
        "pending_approvals": mem.get("pending_approval_refs") or [],
        "next_recommended_action": (mem.get("recent_recommendations") or ["Review top active priority"])[0],
    }
    return _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-operations/tasks")
def api_admin_ai_operations_tasks():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib import hermes_ops_memory

    mem = hermes_ops_memory.load_memory(updated_by="control_center")
    summary = mem.get("task_lifecycle_summary") or {}
    lifecycle = mem.get("task_lifecycle") or {}
    rows = [{"task_id": k, "status": v} for k, v in lifecycle.items()]
    rows = rows[:120]
    data = {
        "task_lifecycle_summary": {
            "queued": int(summary.get("queued", 0)),
            "running": int(summary.get("running", 0)),
            "waiting_for_approval": len(mem.get("pending_approval_refs") or []),
            "completed": int(summary.get("completed", 0)),
            "failed": int(summary.get("failed", 0)),
            "canceled": int(summary.get("canceled", 0)),
        },
        "task_lifecycle": rows,
    }
    return _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-operations/approvals")
def api_admin_ai_operations_approvals():
    if not _admin_authorized(request):
        return _unauthorized_response()
    rows = _approval_rows(limit=60)
    pending = [r for r in rows if str(r.get("status") or "").lower() == "pending"]
    data = {"pending_approvals": pending, "approval_history": rows}
    return _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-operations/swarm")
def api_admin_ai_operations_swarm():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.swarm_coordinator import list_agents
    from lib.swarm_approval_queue import list_planned_runs

    agents = list_agents()
    planned_runs = list_planned_runs()
    latest_plan = planned_runs[0] if planned_runs else None
    data = {
        "swarm_execution_enabled": False,
        "dry_run_only": True,
        "can_execute": False,
        "agents": agents,
        "assigned_dry_run_tasks": planned_runs,
        "suggested_delegation_plan": latest_plan,
    }
    return _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-operations/workforce")
def api_admin_ai_operations_workforce():
    if not _admin_authorized(request):
        return _unauthorized_response()

    rows = _safe_select(
        "worker_heartbeats?select=worker_id,status,last_seen_at,metadata&order=last_seen_at.desc&limit=100"
    )
    status_counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("status") or "unknown").lower()
        status_counts[key] = status_counts.get(key, 0) + 1
    data = {
        "worker_heartbeats": rows,
        "online_offline_summary": status_counts,
        "queue_load": _safe_select("job_queue?select=id,status,created_at&order=created_at.desc&limit=60"),
        "recent_activity": _safe_select("workflow_outputs?select=id,summary,status,created_at&order=created_at.desc&limit=30"),
    }
    return _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-operations/timeline")
def api_admin_ai_operations_timeline():
    if not _admin_authorized(request):
        return _unauthorized_response()

    timeline: list[dict] = []
    for row in _safe_select("system_events?select=id,event_type,status,created_at,payload&order=created_at.desc&limit=80"):
        event_type = str(row.get("event_type") or "event")
        status = str(row.get("status") or "unknown")
        label = "event_recorded"
        if status in {"pending", "queued"}:
            label = "task_queued"
        elif status in {"claimed", "running"}:
            label = "task_running"
        elif status == "completed":
            label = "task_completed"
        elif status == "failed":
            label = "task_failed"
        timeline.append({"at": row.get("created_at"), "type": label, "source": "system_events", "id": row.get("id"), "event_type": event_type, "status": status})

    for row in _safe_select("workflow_outputs?select=id,summary,status,created_at,workflow_type&order=created_at.desc&limit=60"):
        status = str(row.get("status") or "unknown").lower()
        label = "task_completed" if status in {"completed", "approved", "ready"} else ("task_failed" if status == "failed" else "workflow_output")
        timeline.append({"at": row.get("created_at"), "type": label, "source": "workflow_outputs", "id": row.get("id"), "event_type": row.get("workflow_type") or "workflow_output", "status": status, "summary": row.get("summary")})

    for row in _approval_rows(limit=40):
        status = str(row.get("status") or "unknown").lower()
        label = "approval_requested" if status == "pending" else "approval_granted"
        if status in {"rejected", "denied"}:
            label = "approval_rejected"
        timeline.append({"at": row.get("updated_at") or row.get("created_at"), "type": label, "source": "owner_approval_queue", "id": row.get("id"), "event_type": row.get("action_type") or "approval", "status": status})

    timeline.sort(key=lambda x: str(x.get("at") or ""), reverse=True)
    data = {"timeline": timeline[:160]}
    return _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-operations/overview")
def api_admin_ai_operations_overview():
    if not _admin_authorized(request):
        return _unauthorized_response()
    cached_resp = _response_cache_get("overview", ttl=60)
    if cached_resp is not None:
        return jsonify(cached_resp)
    from lib import hermes_ops_memory
    from lib.ai_ops_scorecard import build_ai_ops_scorecard
    from lib.agent_collaboration import dry_run_collaboration_plan

    mem = hermes_ops_memory.load_memory(updated_by="control_center")
    active = hermes_ops_memory.get_active_work_session(mem)
    approvals = _approval_rows(limit=40)
    pending = [r for r in approvals if str(r.get("status") or "").lower() == "pending"]
    workforce = _safe_select("worker_heartbeats?select=worker_id,status,last_seen_at&order=last_seen_at.desc&limit=40")
    workforce_status_counts: dict[str, int] = {}
    for row in workforce:
        k = str(row.get("status") or "unknown").lower()
        workforce_status_counts[k] = workforce_status_counts.get(k, 0) + 1
    knowledge = {}
    if _is_enabled("KNOWLEDGE_DASHBOARD_ENABLED", "true"):
        try:
            knowledge = _cached_knowledge_visibility()
            knowledge["stale_warnings"] = (knowledge.get("stale_warnings") or [])[:10]
        except Exception:
            knowledge = {}
    task_lifecycle_summary = mem.get("task_lifecycle_summary") or {}
    scorecard = build_ai_ops_scorecard(
        worker_summary=workforce_status_counts,
        task_summary=task_lifecycle_summary,
        pending_approvals=len(pending),
        knowledge_snapshot=knowledge,
        agent_activation={
            "ops_monitor": "read-only" if _is_enabled("OPS_MONITOR_READ_ONLY", "true") else "disabled",
            "qa_test": "test-only" if _is_enabled("QA_TEST_AGENT_ENABLED", "false") else "disabled",
            "report_writer": "email-only" if _is_enabled("REPORT_WRITER_AGENT_ENABLED", "false") else "disabled",
            "telegram_comms": "approval-only" if _is_enabled("TELEGRAM_COMMS_AGENT_APPROVAL_ONLY", "false") else "disabled",
            "funding_strategy": "review-only" if _is_enabled("FUNDING_STRATEGY_AGENT_REVIEW_ONLY", "false") else "disabled",
            "credit_workflow": "review-only" if _is_enabled("CREDIT_WORKFLOW_AGENT_REVIEW_ONLY", "false") else "disabled",
            "grants_research": "review-only" if _is_enabled("GRANTS_RESEARCH_AGENT_REVIEW_ONLY", "true") else "disabled",
            "business_setup": "review-only" if _is_enabled("BUSINESS_SETUP_AGENT_REVIEW_ONLY", "true") else "disabled",
            "trading_research": "research-only" if _is_enabled("TRADING_RESEARCH_AGENT_RESEARCH_ONLY", "true") else "disabled",
        },
        latest_agent_runs=mem.get("latest_agent_runs") or {},
        stale_workers=int(workforce_status_counts.get("stale", 0)),
        email_failures=0,
    )
    data = {
        "feature_flags": {
            "ai_operations_dashboard_enabled": _is_enabled("AI_OPERATIONS_DASHBOARD_ENABLED", "true"),
            "swarm_visibility_enabled": _is_enabled("SWARM_VISIBILITY_ENABLED", "true"),
            "swarm_execution_enabled": _is_enabled("SWARM_EXECUTION_ENABLED", "false"),
            "ai_approval_center_enabled": _is_enabled("AI_APPROVAL_CENTER_ENABLED", "true"),
            "live_operations_timeline_enabled": _is_enabled("LIVE_OPERATIONS_TIMELINE_ENABLED", "true"),
            "ops_monitor_agent_enabled": _is_enabled("OPS_MONITOR_AGENT_ENABLED", "false"),
            "qa_test_agent_enabled": _is_enabled("QA_TEST_AGENT_ENABLED", "false"),
            "report_writer_agent_enabled": _is_enabled("REPORT_WRITER_AGENT_ENABLED", "false"),
            "telegram_comms_agent_approval_only": _is_enabled("TELEGRAM_COMMS_AGENT_APPROVAL_ONLY", "false"),
            "funding_strategy_agent_review_only": _is_enabled("FUNDING_STRATEGY_AGENT_REVIEW_ONLY", "false"),
            "credit_workflow_agent_review_only": _is_enabled("CREDIT_WORKFLOW_AGENT_REVIEW_ONLY", "false"),
            "controlled_agent_collaboration_enabled": _is_enabled("CONTROLLED_AGENT_COLLABORATION_ENABLED", "true"),
            "executive_reports_enabled": _is_enabled("EXECUTIVE_REPORTS_ENABLED", "true"),
            "ai_operations_scoring_enabled": _is_enabled("AI_OPERATIONS_SCORING_ENABLED", "true"),
            "knowledge_source_ranking_enabled": _is_enabled("KNOWLEDGE_SOURCE_RANKING_ENABLED", "true"),
        },
        "agent_activation": {
            "ops_monitor": "read-only" if _is_enabled("OPS_MONITOR_READ_ONLY", "true") else "disabled",
            "qa_test": "test-only" if _is_enabled("QA_TEST_AGENT_ENABLED", "false") else "disabled",
            "report_writer": "email-only" if _is_enabled("REPORT_WRITER_AGENT_ENABLED", "false") else "disabled",
            "telegram_comms": "approval-only" if _is_enabled("TELEGRAM_COMMS_AGENT_APPROVAL_ONLY", "false") else "disabled",
            "funding_strategy": "review-only" if _is_enabled("FUNDING_STRATEGY_AGENT_REVIEW_ONLY", "false") else "disabled",
            "credit_workflow": "review-only" if _is_enabled("CREDIT_WORKFLOW_AGENT_REVIEW_ONLY", "false") else "disabled",
        },
        "active_work_session": active,
        "operational_memory": {
            "recent_recommendations": mem.get("recent_recommendations") or [],
            "recent_completed": mem.get("recent_completed") or [],
            "recent_failed": mem.get("recent_failed") or [],
            "last_user_instruction": mem.get("last_user_instruction") or "",
            "latest_ops_monitor_run": mem.get("latest_ops_monitor_run"),
            "latest_agent_runs": mem.get("latest_agent_runs") or {},
        },
        "knowledge": knowledge,
        "task_lifecycle_summary": task_lifecycle_summary,
        "ai_ops_scorecard": scorecard,
        "collaboration_preview": dry_run_collaboration_plan("daily operational intelligence"),
        "pending_approval_count": len(pending),
        "worker_count": len(workforce),
        "dry_run_only": True,
        "can_execute": False,
        "swarm_execution_enabled": False,
        "telegram_policy": {
            "manual_only": _is_enabled("TELEGRAM_MANUAL_ONLY", "true"),
            "auto_reports_enabled": _is_enabled("TELEGRAM_AUTO_REPORTS_ENABLED", "false"),
            "conversational_mode": _is_enabled("TELEGRAM_CONVERSATIONAL_MODE", "true"),
            "openrouter_only_for_chat": not _is_enabled("TELEGRAM_USE_OLLAMA", "false"),
        },
    }
    response_payload = _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})
    _response_cache_set("overview", response_payload.get_json(), ttl=60)
    return response_payload


@app.route("/api/admin/ai-operations/executive-report")
def api_admin_ai_operations_executive_report():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.executive_reports import build_executive_report, build_weekly_ceo_report, build_ai_workforce_summary, build_knowledge_brain_report

    report_type = (request.args.get("type") or "daily").strip().lower()
    if report_type == "weekly":
        payload = build_weekly_ceo_report()
    elif report_type == "workforce":
        payload = {"report_type": "ai_workforce_summary", "timestamp": datetime.now(timezone.utc).isoformat(), "data": build_ai_workforce_summary()}
    elif report_type == "knowledge":
        payload = {"report_type": "knowledge_brain_summary", "timestamp": datetime.now(timezone.utc).isoformat(), "data": build_knowledge_brain_report()}
    else:
        payload = build_executive_report()
    return _ok_response({"report": payload}, read_only=True, extra={"report": payload, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-operations/knowledge")
def api_admin_ai_operations_knowledge():
    if not _admin_authorized(request):
        return _unauthorized_response()
    from lib.hermes_knowledge_brain import (
        audit_knowledge_sources,
        get_recent_knowledge,
        search_knowledge,
        get_related_workflows,
        get_recent_recommendations,
        get_funding_knowledge,
        get_credit_knowledge,
        knowledge_dashboard_snapshot,
        get_top_ranked_knowledge,
        build_source_aware_context_pack,
        explain_knowledge_ranking,
    )

    category = (request.args.get("category") or "operations").strip().lower()
    query = (request.args.get("query") or "").strip()
    compact_arg = str(request.args.get("compact") or "").strip().lower()
    compact = compact_arg not in {"0", "false", "no", "off"}
    if compact:
        source_ctx = _cached_knowledge_pack(category)
        visibility = _cached_knowledge_visibility()
        top = source_ctx.get("top_ranked") or []
        top_by_category = visibility.get("top_ranked_knowledge") or {}
        data = {
            "audit": {
                "normalization_mode": "retrieval_time",
                "notes": ["compact mode"],
            },
            "snapshot": {
                "top_ranked_knowledge": {category: top},
                "source_quality_summary": source_ctx.get("source_quality_summary") or {},
                "stale_warnings": (source_ctx.get("stale_warnings") or [])[:6],
            },
            "recent": top,
            "search_results": [],
            "related_workflows": get_related_workflows(category, limit=8),
            "recent_recommendations": get_recent_recommendations(limit=6),
            "funding": top_by_category.get("funding") or [],
            "credit": top_by_category.get("credit") or [],
            "top_ranked": top,
            "source_aware_context": source_ctx,
        }
        if data["top_ranked"]:
            data["ranking_explain_first"] = explain_knowledge_ranking(data["top_ranked"][0], category=category)
        return _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})

    data = {
        "audit": audit_knowledge_sources(),
        "snapshot": knowledge_dashboard_snapshot(),
        "recent": get_recent_knowledge(category, limit=20),
        "search_results": search_knowledge(query, limit=20) if query else [],
        "related_workflows": get_related_workflows(category, limit=12),
        "recent_recommendations": get_recent_recommendations(limit=8),
        "funding": get_funding_knowledge(limit=8),
        "credit": get_credit_knowledge(limit=8),
        "top_ranked": get_top_ranked_knowledge(category, limit=10),
        "source_aware_context": build_source_aware_context_pack(category, limit=8),
    }
    if data["top_ranked"]:
        data["ranking_explain_first"] = explain_knowledge_ranking(data["top_ranked"][0], category=category)
    return _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})


@app.route("/api/admin/ai-operations/dev-agents")
def api_admin_ai_operations_dev_agents():
    if not _admin_authorized(request):
        return _unauthorized_response()
    cached = _response_cache_get("dev_agents", ttl=120)
    if cached is not None:
        return jsonify(cached)
    try:
        from lib.hermes_dev_agent_bridge import (
            build_cli_agent_inventory,
            get_recent_handoffs,
            validate_cli_agent_config,
        )
        inventory = build_cli_agent_inventory()
        recent_handoffs = get_recent_handoffs(limit=10)
        pending = [h for h in recent_handoffs if h.get("status") == "pending_approval"]
        failed = [h for h in recent_handoffs if h.get("status") == "failed"]
        config_check = validate_cli_agent_config()
        data = {
            "inventory": inventory.get("inventory", []),
            "installed_count": sum(1 for a in inventory.get("inventory", []) if a.get("installed")),
            "total_count": len(inventory.get("inventory", [])),
            "config": config_check,
            "recent_handoffs": recent_handoffs,
            "pending_handoff_count": len(pending),
            "failed_handoff_count": len(failed),
            "execution_enabled": False,
            "dry_run_mode": inventory.get("dry_run_mode", True),
            "can_execute": False,
            "safe_for_execution": False,
        }
    except Exception as e:
        logger.error("dev-agents endpoint error: %s", e)
        data = {"error": str(e), "inventory": [], "execution_enabled": False, "can_execute": False}
    result = _ok_response(data, read_only=True, extra={**data, "updated_at": datetime.now(timezone.utc).isoformat()})
    _response_cache_set("dev_agents", result.get_json(), ttl=120)
    return result


@app.route("/admin/ai-operations")
def admin_ai_operations_page():
    if not _admin_authorized(request):
        return _unauthorized_response()
    response = make_response(render_template_string(TERMINAL_HTML))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ─────────────────────────────────────────────
# Bloomberg-style HTML terminal
# ─────────────────────────────────────────────

TERMINAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXUS AI CONTROL CENTER</title>
<style>
  :root {
    --bg:       #0a0c0f;
    --panel:    #0f1318;
    --border:   #1e2530;
    --accent:   #f0a500;
    --green:    #00d4aa;
    --red:      #ff3b5c;
    --blue:     #2196f3;
    --purple:   #9c27b0;
    --text:     #c8d0db;
    --dim:      #5a6475;
    --header:   #141820;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { height:100%; background:var(--bg); color:var(--text);
              font-family:'Courier New',Courier,monospace; font-size:12px; }

  /* ── TOP BAR ── */
  #topbar {
    background:var(--header);
    border-bottom:2px solid var(--accent);
    padding:6px 16px;
    display:flex; align-items:center; justify-content:space-between;
  }
  #topbar .logo { color:var(--accent); font-size:15px; font-weight:bold; letter-spacing:3px; }
  #topbar .meta { color:var(--dim); font-size:11px; }
  #clock { color:var(--green); font-size:13px; font-weight:bold; }

  /* ── TAB NAV ── */
  #tabnav {
    background:var(--header);
    border-bottom:1px solid var(--border);
    display:flex; gap:0; overflow-x:auto;
  }
  .tab {
    padding:7px 18px; cursor:pointer; border-right:1px solid var(--border);
    color:var(--dim); font-size:11px; letter-spacing:1px; white-space:nowrap;
    transition:all .2s;
  }
  .tab:hover { background:#1a2030; color:var(--text); }
  .tab.active { color:var(--accent); background:var(--panel);
                border-bottom:2px solid var(--accent); }

  /* ── MAIN GRID ── */
  #workspace { display:flex; flex-direction:column; height:calc(100vh - 72px); }
  .page { display:none; padding:10px; gap:10px; height:100%; overflow:auto; }
  .page.active { display:grid; }
  .page.single { grid-template-columns:1fr; }
  .page.two    { grid-template-columns:1fr 1fr; }
  .page.three  { grid-template-columns:1fr 1fr 1fr; }
  .page.quad   { grid-template-columns:1fr 1fr; grid-template-rows:1fr 1fr; }

  /* ── PANELS ── */
  .panel {
    background:var(--panel); border:1px solid var(--border);
    border-radius:4px; overflow:hidden; display:flex; flex-direction:column;
    min-height:200px;
  }
  .panel-header {
    background:var(--header); padding:6px 10px;
    border-bottom:1px solid var(--border);
    display:flex; align-items:center; justify-content:space-between;
  }
  .panel-title { color:var(--accent); font-size:11px; font-weight:bold; letter-spacing:1px; }
  .panel-badge { font-size:10px; padding:1px 6px; border-radius:2px; }
  .badge-green { background:#003d2e; color:var(--green); }
  .badge-red   { background:#2d0f17; color:var(--red); }
  .badge-blue  { background:#0a1929; color:var(--blue); }
  .badge-amber { background:#1a1200; color:var(--accent); }
  .panel-body { padding:8px 10px; flex:1; overflow-y:auto; }

  /* ── METRICS ── */
  .metric-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(110px,1fr)); gap:6px; }
  .metric {
    background:#141820; border:1px solid var(--border);
    border-radius:3px; padding:8px; text-align:center;
  }
  .metric .val { font-size:22px; font-weight:bold; }
  .metric .lbl { color:var(--dim); font-size:10px; margin-top:2px; }
  .green { color:var(--green); }
  .red   { color:var(--red); }
  .amber { color:var(--accent); }
  .blue  { color:var(--blue); }
  .purple{ color:var(--purple); }

  /* ── STATUS DOTS ── */
  .dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px; }
  .dot-green  { background:var(--green); box-shadow:0 0 6px var(--green); }
  .dot-red    { background:var(--red);   box-shadow:0 0 6px var(--red); }
  .dot-amber  { background:var(--accent);box-shadow:0 0 6px var(--accent); }

  /* ── TABLES ── */
  .data-table { width:100%; border-collapse:collapse; }
  .data-table th { color:var(--dim); font-size:10px; text-align:left;
                   padding:4px 6px; border-bottom:1px solid var(--border); }
  .data-table td { padding:5px 6px; border-bottom:1px solid #151b24;
                   font-size:11px; vertical-align:top; }
  .data-table tr:hover td { background:#141c28; }

  /* ── FEED ── */
  .feed-item { padding:6px 0; border-bottom:1px solid #151b24; }
  .feed-item:last-child { border:none; }
  .feed-time { color:var(--dim); font-size:10px; }
  .feed-text { color:var(--text); margin-top:2px; line-height:1.5; }

  /* ── SENTIMENT BAR ── */
  .sent-bar { display:flex; height:14px; border-radius:3px; overflow:hidden; margin:6px 0; }
  .sent-bull { background:var(--green); }
  .sent-bear { background:var(--red); }
  .sent-neu  { background:var(--dim); }

  /* ── REFRESH BTN ── */
  .refresh-btn {
    background:none; border:1px solid var(--border); color:var(--dim);
    padding:2px 8px; border-radius:3px; cursor:pointer; font-family:inherit;
    font-size:10px; transition:all .2s;
  }
  .refresh-btn:hover { border-color:var(--accent); color:var(--accent); }

  .draft-card {
    background:#141820; border:1px solid var(--border);
    border-radius:4px; padding:10px; margin-bottom:10px;
  }
  .draft-top {
    display:flex; align-items:flex-start; justify-content:space-between;
    gap:10px; margin-bottom:8px;
  }
  .draft-role { color:var(--accent); font-size:12px; letter-spacing:1px; }
  .draft-meta { color:var(--dim); font-size:10px; margin-top:3px; }
  .status-badge {
    display:inline-block; padding:3px 8px; border-radius:999px;
    border:1px solid var(--border); font-size:10px;
    text-transform:uppercase; letter-spacing:.8px;
  }
  .status-pending_review { background:#1a1200; color:var(--accent); }
  .status-approved { background:#003d2e; color:var(--green); }
  .status-rejected { background:#2d0f17; color:var(--red); }
  .status-revision_requested { background:#0a1929; color:var(--blue); }
  .draft-summary {
    white-space:pre-wrap; line-height:1.5; font-size:11px; margin-bottom:8px;
  }
  .draft-note {
    width:100%; min-height:68px; resize:vertical;
    background:#0f1318; color:var(--text);
    border:1px solid var(--border); border-radius:4px;
    padding:8px; font-family:inherit; font-size:11px; margin-bottom:8px;
  }
  .draft-actions { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
  .action-btn {
    border:1px solid var(--border); background:#10161d; color:var(--text);
    border-radius:4px; padding:6px 10px; cursor:pointer;
    font-family:inherit; font-size:11px;
  }
  .action-btn:hover { border-color:var(--accent); color:var(--accent); }
  .action-btn.approve:hover { border-color:var(--green); color:var(--green); }
  .action-btn.revise:hover { border-color:var(--blue); color:var(--blue); }
  .action-btn.reject:hover { border-color:var(--red); color:var(--red); }
  .draft-flash { font-size:10px; color:var(--dim); }
  .draft-flash.ok { color:var(--green); }
  .draft-flash.err { color:var(--red); }
  .draft-detail {
    margin-top:8px; padding-top:8px; border-top:1px solid #151b24;
    color:var(--dim); font-size:10px;
  }
  .user-card {
    background:#141820; border:1px solid var(--border);
    border-radius:4px; padding:10px; margin-bottom:10px;
  }
  .user-name { color:var(--accent); font-size:12px; }
  .user-meta { color:var(--dim); font-size:10px; margin:4px 0 8px; line-height:1.5; }
  .mini-label { color:var(--dim); font-size:10px; display:block; margin-bottom:4px; }
  .mini-input, .mini-select {
    width:100%; background:#0f1318; color:var(--text); border:1px solid var(--border);
    border-radius:4px; padding:6px 8px; font-family:inherit; font-size:11px; margin-bottom:8px;
  }
  .user-actions { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
  .user-flash { font-size:10px; color:var(--dim); margin-top:6px; white-space:pre-wrap; }
  .audit-pre {
    white-space:pre-wrap; font-size:11px; line-height:1.5; color:var(--text);
  }
  /* ── WORKER CARDS ── */
  .worker-card {
    background:#141820; border:1px solid var(--border);
    border-radius:4px; padding:8px 10px; margin-bottom:6px;
  }
  .worker-header { display:flex; align-items:center; gap:6px; margin-bottom:2px; }
  .worker-name { color:var(--text); font-size:11px; }
  .worker-meta { color:var(--dim); font-size:10px; }
  /* ── SCORE BARS ── */
  .score-row { display:flex; align-items:center; gap:8px; margin-bottom:7px; }
  .score-label { color:var(--dim); font-size:10px; width:120px; flex-shrink:0; letter-spacing:.5px; }
  .score-bar { flex:1; height:5px; background:#151b24; border-radius:3px; overflow:hidden; }
  .score-fill { height:100%; border-radius:3px; }
  .score-num { color:var(--text); font-size:10px; width:28px; text-align:right; font-weight:bold; }
  .message-card {
    background:#141820; border:1px solid var(--border);
    border-radius:4px; padding:10px; margin-bottom:10px;
  }
  .message-title { color:var(--accent); font-size:12px; }
  .message-meta { color:var(--dim); font-size:10px; margin:4px 0 8px; line-height:1.5; }
  .message-body { white-space:pre-wrap; line-height:1.5; font-size:11px; margin-bottom:8px; }

  /* ── FOOTER ── */
  #footer {
    position:fixed; bottom:0; left:0; right:0;
    background:var(--header); border-top:1px solid var(--border);
    padding:3px 14px; display:flex; gap:20px; align-items:center;
  }
  .footer-item { font-size:10px; color:var(--dim); }
  .footer-item span { color:var(--text); }

  /* SCROLLBAR */
  ::-webkit-scrollbar { width:4px; height:4px; }
  ::-webkit-scrollbar-track { background:var(--bg); }
  ::-webkit-scrollbar-thumb { background:var(--border); border-radius:2px; }
</style>
</head>
<body>

<!-- TOP BAR -->
<div id="topbar">
  <div class="logo">⬡ NEXUS AI CONTROL CENTER</div>
  <div class="meta">v2.0 | localhost | DRY_RUN=TRUE</div>
  <div id="clock">--:--:--</div>
</div>

<!-- TAB NAV -->
<div id="tabnav">
  <div class="tab active" onclick="showPage('overview')">OVERVIEW</div>
  <div class="tab" onclick="showPage('research')">RESEARCH BRAIN</div>
  <div class="tab" onclick="showPage('signals')">HEDGE FUND</div>
  <div class="tab" onclick="showPage('leads')">LEAD INTEL</div>
  <div class="tab" onclick="showPage('marketing')">MARKETING</div>
  <div class="tab" onclick="showPage('reputation')">REPUTATION</div>
  <div class="tab" onclick="showPage('health')">SYSTEM HEALTH</div>
  <div class="tab" onclick="showPage('scheduler')">SCHEDULER</div>
  <div class="tab" onclick="showPage('drafts')">CEO DRAFTS</div>
  <div class="tab" onclick="showPage('prelaunch')">PRELAUNCH</div>
  <div class="tab" onclick="showPage('growth')">GROWTH</div>
  <div class="tab" onclick="showPage('messages')">MESSAGES</div>
  <div class="tab" onclick="showPage('approvals')">SIGNAL QUEUE</div>
  <div class="tab" onclick="showPage('mission')">MISSION CONTROL</div>
  <div class="tab" onclick="showPage('aiops')">AI OPS</div>
</div>

<!-- WORKSPACE -->
<div id="workspace">

  <!-- ── OVERVIEW ── -->
  <div id="page-overview" class="page quad active">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">⬡ AI AGENT STATUS</span>
        <button class="refresh-btn" onclick="loadAll()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="agents-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">📊 MARKET SENTIMENT</span>
        <span class="panel-badge badge-amber" id="sentiment-badge">—</span>
      </div>
      <div class="panel-body" id="sentiment-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">🧠 RESEARCH FEED</span>
        <span class="panel-badge badge-blue" id="research-count">—</span>
      </div>
      <div class="panel-body" id="research-feed">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">🔔 ALERTS</span>
        <span class="panel-badge badge-red" id="alert-count">—</span>
      </div>
      <div class="panel-body" id="alerts-panel">Loading...</div>
    </div>
  </div>

  <!-- ── RESEARCH ── -->
  <div id="page-research" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🧠 RESEARCH PIPELINE STATUS</span></div>
      <div class="panel-body" id="research-status">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">📄 LATEST STRATEGY SUMMARIES</span></div>
      <div class="panel-body" id="strategy-feed">Loading...</div>
    </div>
  </div>

  <!-- ── SIGNALS / HEDGE FUND ── -->
  <div id="page-signals" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">📈 SIGNAL CANDIDATES</span>
        <span class="panel-badge badge-green">DRY RUN ✓</span>
      </div>
      <div class="panel-body" id="signals-table">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🌡 SENTIMENT ANALYSIS</span></div>
      <div class="panel-body" id="sentiment-detail">Loading...</div>
    </div>
  </div>

  <!-- ── LEADS ── -->
  <div id="page-leads" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🔥 LEAD INTELLIGENCE</span></div>
      <div class="panel-body" id="leads-summary">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">⭐ HIGH-VALUE LEADS</span></div>
      <div class="panel-body" id="leads-table">Loading...</div>
    </div>
  </div>

  <!-- ── MARKETING ── -->
  <div id="page-marketing" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">📣 MARKETING PERFORMANCE</span></div>
      <div class="panel-body" id="marketing-summary">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">⭐ TOP TESTIMONIALS</span></div>
      <div class="panel-body" id="testimonials-feed">Loading...</div>
    </div>
  </div>

  <!-- ── REPUTATION ── -->
  <div id="page-reputation" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">⭐ REPUTATION SCORE</span></div>
      <div class="panel-body" id="reputation-summary">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">⚠️ FLAGGED REVIEWS</span></div>
      <div class="panel-body" id="flagged-reviews">Loading...</div>
    </div>
  </div>

  <!-- ── SYSTEM HEALTH ── -->
  <div id="page-health" class="page single" style="display:none">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">💻 SYSTEM HEALTH</span>
        <button class="refresh-btn" onclick="loadHealth()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="health-panel">Loading...</div>
    </div>
  </div>

  <!-- ── SCHEDULER ── -->
  <div id="page-scheduler" class="page single" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">⏱ OPERATIONS SCHEDULER</span></div>
      <div class="panel-body" id="scheduler-panel">Loading...</div>
    </div>
  </div>

  <!-- ── CEO DRAFTS ── -->
  <div id="page-drafts" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">🧾 PENDING CEO DRAFTS</span>
        <button class="refresh-btn" onclick="loadDraftsPage()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="drafts-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">✅ RECENT REVIEW DECISIONS</span></div>
      <div class="panel-body" id="draft-review-history">Loading...</div>
    </div>
  </div>

  <!-- ── PRELAUNCH ── -->
  <div id="page-prelaunch" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">🧪 PRELAUNCH TESTING</span>
        <button class="refresh-btn" onclick="loadPrelaunchPage()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="prelaunch-audit-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">👥 TESTERS & WAIVERS</span></div>
      <div class="panel-body" id="prelaunch-users-panel">Loading...</div>
    </div>
  </div>

  <div id="page-growth" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">📈 GROWTH ENGINE</span>
        <button class="refresh-btn" onclick="loadGrowthPage()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="growth-summary-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🧾 GROWTH DETAILS</span></div>
      <div class="panel-body" id="growth-detail-panel">Loading...</div>
    </div>
  </div>

  <div id="page-messages" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">💬 MESSAGE DRAFT REVIEW</span>
        <button class="refresh-btn" onclick="loadMessagesPage()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="message-review-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🧾 RECENT MESSAGE LOGS</span></div>
      <div class="panel-body" id="message-log-panel">Loading...</div>
    </div>
  </div>

  <!-- ── SIGNAL QUEUE ── -->
  <div id="page-approvals" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">⏳ PENDING SIGNAL APPROVALS</span>
        <button class="refresh-btn" onclick="loadApprovalsPage()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="approvals-pending-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">✅ RECENTLY ACTIONED</span></div>
      <div class="panel-body" id="approvals-recent-panel">Loading...</div>
    </div>
  </div>

  <div id="page-mission" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">🧭 WORKFORCE GRID</span>
        <button class="refresh-btn" onclick="loadMissionControlPage()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="mission-workforce-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🎯 EXECUTIVE INTELLIGENCE</span></div>
      <div class="panel-body" id="mission-executive-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">📰 LIVE OPERATIONS FEED</span></div>
      <div class="panel-body" id="mission-feed-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">✅ RECOMMENDATION QUEUE + REVIEW</span></div>
      <div class="panel-body" id="mission-queue-panel">Loading...</div>
    </div>
  </div>

  <div id="page-aiops" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🧭 ACTIVE WORK SESSION</span></div>
      <div class="panel-body" id="aiops-session-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">📊 AI OPS SCORECARD & MEMORY</span></div>
      <div class="panel-body" id="aiops-memory-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">🧠 AI OPS CONFIG</span>
        <button class="refresh-btn" onclick="loadAiOpsPage()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="aiops-config-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🛡 OPERATOR CONTROLS (ADMIN)</span></div>
      <div class="panel-body" id="aiops-controls-panel">
        <div style="margin-bottom:8px;color:var(--amber)">Manual-only mode is recommended for production safety.</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:8px">
          <input id="aiops-admin-token" type="password" placeholder="Admin token" style="background:#0f131a;border:1px solid var(--border);color:var(--text);padding:6px;min-width:220px" />
          <input id="aiops-admin-actor" type="text" placeholder="actor (optional)" style="background:#0f131a;border:1px solid var(--border);color:var(--text);padding:6px;min-width:180px" />
        </div>
        <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:8px">
          <label><input type="checkbox" id="aiops-flag-enabled"/> Telegram enabled</label>
          <label><input type="checkbox" id="aiops-flag-manual"/> Manual-only</label>
          <label><input type="checkbox" id="aiops-flag-auto"/> Auto reports enabled</label>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="refresh-btn" onclick="saveAiOpsTelegramMode()">SAVE TELEGRAM MODE</button>
          <button class="refresh-btn" onclick="loadAiOpsPage()">REFRESH PREVIEW</button>
        </div>
        <div id="aiops-controls-feedback" class="message-meta" style="margin-top:8px"></div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🧭 ROUTING PREVIEW</span></div>
      <div class="panel-body" id="aiops-routing-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🟢 WORKER HEALTH SUMMARY</span></div>
      <div class="panel-body" id="aiops-workers-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">📚 TASK LIFECYCLE</span></div>
      <div class="panel-body" id="aiops-lifecycle-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">📉 RETRIES / MODEL USAGE</span></div>
      <div class="panel-body" id="aiops-telemetry-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">👥 AI EMPLOYEES</span></div>
      <div class="panel-body" id="aiops-roles-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🕸 SWARM PREVIEW (SAFE)</span></div>
      <div class="panel-body" style="padding-bottom:0">
        <label style="color:var(--dim);font-size:11px">Swarm Scenario</label>
        <select id="aiops-swarm-scenario" style="margin-left:8px;background:#0f131a;border:1px solid var(--border);color:var(--text);padding:4px">
          <option value="funding_onboarding">Funding Onboarding</option>
          <option value="credit_remediation">Credit Remediation</option>
          <option value="grant_research">Grant Research</option>
          <option value="ops_incident_triage">Ops Incident Triage</option>
          <option value="business_setup_readiness">Business Setup Readiness</option>
          <option value="trading_research_review">Trading Research Review</option>
        </select>
        <button class="refresh-btn" style="margin-left:8px" onclick="loadSelectedSwarmScenario()">LOAD SCENARIO</button>
      </div>
      <div class="panel-body" id="aiops-swarm-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">✅ APPROVAL QUEUE</span></div>
      <div class="panel-body" style="padding-bottom:0">
        <div style="margin-bottom:8px;color:var(--amber)">Execution remains disabled in this phase.</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <button class="refresh-btn" onclick="createPlannedRunFromScenario()">CREATE PLANNED RUN</button>
          <button class="refresh-btn" onclick="loadApprovalQueue()">REFRESH QUEUE</button>
        </div>
        <div id="aiops-approval-feedback" class="message-meta" style="margin-top:8px"></div>
      </div>
      <div class="panel-body" id="aiops-approval-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🕒 LIVE OPERATIONS TIMELINE</span></div>
      <div class="panel-body" id="aiops-timeline-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">📈 TRADING INTELLIGENCE LAB</span>
        <span class="panel-badge badge-blue">ARCHITECTURE PREVIEW</span>
      </div>
      <div class="panel-body">
        <div style="color:var(--amber);font-size:10px;margin-bottom:10px">Read-only intelligence layer — no broker execution. All outputs are CEO-gated research artifacts.</div>
        <div class="metric-grid" style="margin-bottom:12px">
          <div class="metric"><div class="val" style="color:var(--dim)">—</div><div class="lbl">SIGNALS</div></div>
          <div class="metric"><div class="val" style="color:var(--dim)">—</div><div class="lbl">PATTERNS</div></div>
          <div class="metric"><div class="val" style="color:var(--dim)">—</div><div class="lbl">RESEARCH CYCLES</div></div>
          <div class="metric"><div class="val" style="color:var(--dim)">—</div><div class="lbl">CONFIDENCE</div></div>
        </div>
        <table class="data-table">
          <thead><tr><th>MODULE</th><th>STATUS</th><th>ROLE</th><th>OUTPUT TYPE</th></tr></thead>
          <tbody>
            <tr><td>Strategy Research Agent</td><td class="amber">planned</td><td>research-only</td><td>pattern summaries</td></tr>
            <tr><td>Signal Correlation Engine</td><td class="amber">planned</td><td>analysis-only</td><td>confidence scores</td></tr>
            <tr><td>Risk Profile Scanner</td><td class="amber">planned</td><td>review-only</td><td>risk flags</td></tr>
            <tr><td>Trade Setup Reviewer</td><td class="amber">planned</td><td>approval-required</td><td>CEO-gated proposals</td></tr>
          </tbody>
        </table>
        <div style="color:var(--dim);font-size:10px;margin-top:10px">⚠ NO BROKER EXECUTION — Nexus AI is a data producer only.</div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">🤖 DEV AGENT BRIDGE</span>
        <button class="refresh-btn" onclick="loadDevAgentsPanel()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="aiops-dev-agents-panel">Loading...</div>
    </div>
  </div>

</div><!-- /workspace -->

<!-- FOOTER -->
<div id="footer">
  <div class="footer-item">STATUS: <span id="footer-status" class="green">ONLINE</span></div>
  <div class="footer-item">LAST UPDATE: <span id="footer-updated">—</span></div>
  <div class="footer-item">RESEARCH: <span id="footer-research">—</span></div>
  <div class="footer-item">SIGNALS: <span id="footer-signals">—</span></div>
  <div class="footer-item">LEADS: <span id="footer-leads">—</span></div>
  <div class="footer-item" style="margin-left:auto">⬡ NEXUS AI — DATA PRODUCER | NO BROKER EXECUTION</div>
</div>

<script>
// ── Clock ──
function tick() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}) + '  ' +
    now.toTimeString().slice(0,8);
}
tick(); setInterval(tick, 1000);

// ── Tab routing ──
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.style.display='none');
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('page-'+name).style.display='grid';
  const tabMap = {
    overview: 'OVERVIEW',
    research: 'RESEARCH BRAIN',
    signals: 'HEDGE FUND',
    leads: 'LEAD INTEL',
    marketing: 'MARKETING',
    reputation: 'REPUTATION',
    health: 'SYSTEM HEALTH',
    scheduler: 'SCHEDULER',
    drafts: 'CEO DRAFTS',
    prelaunch: 'PRELAUNCH',
    growth: 'GROWTH',
    messages: 'MESSAGES',
    approvals: 'SIGNAL QUEUE',
    mission: 'MISSION CONTROL',
    aiops: 'AI OPS',
  };
  const label = tabMap[name];
  const tab = label
    ? [...document.querySelectorAll('.tab')].find(t => t.textContent.trim() === label)
    : null;
  if (tab) tab.classList.add('active');
  loadPage(name);
}

const TAB_NAME_BY_LABEL = {
  'OVERVIEW': 'overview',
  'RESEARCH BRAIN': 'research',
  'HEDGE FUND': 'signals',
  'LEAD INTEL': 'leads',
  'MARKETING': 'marketing',
  'REPUTATION': 'reputation',
  'SYSTEM HEALTH': 'health',
  'SCHEDULER': 'scheduler',
  'CEO DRAFTS': 'drafts',
  'PRELAUNCH': 'prelaunch',
  'GROWTH': 'growth',
  'MESSAGES': 'messages',
  'SIGNAL QUEUE': 'approvals',
  'MISSION CONTROL': 'mission',
  'AI OPS': 'aiops',
};

function bindTabClicks() {
  document.querySelectorAll('#tabnav .tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const label = (tab.textContent || '').trim();
      const name = TAB_NAME_BY_LABEL[label];
      if (name) showPage(name);
    });
  });
}

function dot(up) {
  return `<span class="dot ${up?'dot-green':'dot-red'}"></span>`;
}
function badge(val, cls='green') {
  return `<span style="color:var(--${cls});font-weight:bold">${val}</span>`;
}
function ts(iso) {
  if(!iso) return '—';
  try { return new Date(iso).toLocaleString(); } catch(e) { return iso; }
}
function pct_bar(bull, bear, neu) {
  return `<div class="sent-bar">
    <div class="sent-bull" style="width:${bull}%"></div>
    <div class="sent-bear" style="width:${bear}%"></div>
    <div class="sent-neu"  style="width:${neu}%"></div>
  </div>
  <div style="display:flex;gap:14px;font-size:10px;color:var(--dim);margin-top:2px">
    <span><span class="green">▲</span> Bull ${bull}%</span>
    <span><span class="red">▼</span> Bear ${bear}%</span>
    <span><span style="color:var(--dim)">◆</span> Neu ${neu}%</span>
  </div>`;
}

// ── Fetch helpers ──
async function get(url) {
  const r = await fetch(url);
  return r.json();
}

async function patchJson(url, body) {
  const r = await fetch(url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(data.error || 'Request failed');
  }
  return data;
}

async function postJson(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(data.error || 'Request failed');
  }
  return data;
}

function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function statusBadge(status) {
  const safe = status || 'unknown';
  return `<span class="status-badge status-${safe}">${safe.replace(/_/g,' ')}</span>`;
}

let draftNotice = '';
function setDraftNotice(message, cls='') {
  draftNotice = message ? `<div class="draft-flash ${cls}" style="margin-bottom:10px">${esc(message)}</div>` : '';
}

// ── Loaders ──
async function loadHealth() {
  try {
    const d = await get('/api/health');
    const svcs = d.services || {};
    let rows = Object.entries(svcs).map(([k,v]) =>
      `<tr>
        <td>${dot(v.running)} ${v.name||k}</td>
        <td>${v.port ? ':'+v.port : '—'}</td>
        <td>${v.running ? badge('ONLINE','green') : badge('OFFLINE','red')}</td>
        <td style="color:var(--dim)">${v.pid||'—'}</td>
      </tr>`
    ).join('');
    document.getElementById('health-panel').innerHTML = `
      <table class="data-table">
        <thead><tr><th>SERVICE</th><th>PORT</th><th>STATUS</th><th>PID</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div style="margin-top:14px">
        <div style="color:var(--accent);font-size:10px;margin-bottom:6px">RESEARCH BRAIN</div>
        <table class="data-table">
          <tr><td>Status</td><td>${badge(d.research?.status||'?','amber')}</td></tr>
          <tr><td>Transcripts</td><td>${d.research?.transcripts||0}</td></tr>
          <tr><td>Summaries</td><td>${d.research?.summaries||0}</td></tr>
          <tr><td>Strategies</td><td>${d.research?.strategies||0}</td></tr>
          <tr><td>Last Run</td><td>${ts(d.research?.last_run)}</td></tr>
        </table>
      </div>`;

    // Footer
    const online = Object.values(svcs).filter(v=>v.running).length;
    document.getElementById('footer-status').textContent = online+'/'+Object.keys(svcs).length+' UP';
    document.getElementById('footer-updated').textContent = new Date().toTimeString().slice(0,8);
    document.getElementById('footer-research').textContent =
      (d.research?.strategies||0)+' strategies';
  } catch(e) {
    document.getElementById('health-panel').innerHTML = `<div class="red">Error: ${e}</div>`;
  }
}

async function loadAgents() {
  try {
    const d = await get('/api/health');
    const svcs = d.services||{};
    let html = '<div class="metric-grid">';
    const order = ['gateway','dashboard','signal_router','telegram','control_center'];
    order.forEach(k => {
      const v = svcs[k]||{};
      html += `<div class="metric">
        <div class="val ${v.running?'green':'red'}">${v.running?'●':'○'}</div>
        <div class="lbl">${(v.name||k).toUpperCase()}</div>
      </div>`;
    });
    html += '</div>';
    document.getElementById('agents-panel').innerHTML = html;
  } catch(e) {
    document.getElementById('agents-panel').innerHTML = `<div class="red">Agent status error: ${esc(e.message)}</div>`;
  }
}

async function loadSentiment() {
  try {
    const d = await get('/api/signals');
    const s = d.market_sentiment||{};
    const dom = (s.dominant||'neutral').toUpperCase();
    const badge = document.getElementById('sentiment-badge');
    if (badge) badge.textContent = dom;
    document.getElementById('sentiment-panel').innerHTML = `
      <div class="metric-grid">
        <div class="metric"><div class="val ${s.dominant==='bullish'?'green':s.dominant==='bearish'?'red':'amber'}">${dom}</div><div class="lbl">MARKET BIAS</div></div>
        <div class="metric"><div class="val green">${s.bullish_pct||0}%</div><div class="lbl">BULLISH</div></div>
        <div class="metric"><div class="val red">${s.bearish_pct||0}%</div><div class="lbl">BEARISH</div></div>
        <div class="metric"><div class="val amber">${s.files_analyzed||0}</div><div class="lbl">ANALYZED</div></div>
      </div>
      ${pct_bar(s.bullish_pct||0, s.bearish_pct||0, s.neutral_pct||0)}
      <div style="margin-top:8px;color:var(--dim);font-size:10px">Updated: ${ts(s.updated)}</div>`;
    const fsig = document.getElementById('footer-signals');
    if (fsig) fsig.textContent = (d.strategy_count||0)+' strategies';
  } catch(e) {
    document.getElementById('sentiment-panel').innerHTML = `<div class="red">Sentiment error: ${esc(e.message)}</div>`;
  }
}

async function loadResearchFeed() {
  try {
    const d = await get('/api/research');
    const strats = d.latest_strategies||[];
    const rc = document.getElementById('research-count');
    if (rc) rc.textContent = strats.length+' recent';
    let html = strats.map(s =>
      `<div class="feed-item">
        <div class="feed-time">${ts(s.modified)}</div>
        <div class="feed-text" style="color:var(--accent)">${esc(s.title||'')}</div>
        <div class="feed-text" style="font-size:11px">${esc((s.content||'').slice(0,300))}...</div>
      </div>`
    ).join('') || '<div style="color:var(--dim)">No strategies yet. Run research pipeline.</div>';
    document.getElementById('research-feed').innerHTML = html;
  } catch(e) {
    document.getElementById('research-feed').innerHTML = `<div class="red">Research feed error: ${esc(e.message)}</div>`;
  }
}

async function loadAlerts() {
  try {
    const [leads, rep, mkt] = await Promise.all([
      get('/api/leads'), get('/api/reputation'), get('/api/marketing')
    ]);
    const items = [];
    (leads.recent_high_value||[]).forEach(l =>
      items.push({icon:'🔥',text:`High-Value Lead: ${l.name||'?'} (score ${l.score})`,cls:'amber'})
    );
    (rep.recent_flagged||[]).forEach(r =>
      items.push({icon:'⚠️',text:`Negative Review: ${(r.text||'').slice(0,80)}`,cls:'red'})
    );
    (mkt.summary?.negative_alerts||[]).forEach(m =>
      items.push({icon:'📣',text:`Negative Mention on ${m.platform}: ${(m.text||'').slice(0,60)}`,cls:'red'})
    );
    const ac = document.getElementById('alert-count');
    if (ac) ac.textContent = items.length+' alerts';
    document.getElementById('alerts-panel').innerHTML = items.length
      ? items.map(i=>`<div class="feed-item"><div class="feed-text ${i.cls}">${i.icon} ${esc(i.text)}</div></div>`).join('')
      : '<div style="color:var(--green)">✓ No active alerts</div>';
  } catch(e) {
    document.getElementById('alerts-panel').innerHTML = `<div class="red">Alerts error: ${esc(e.message)}</div>`;
  }
}

async function loadResearchPage() {
  try {
    const d = await get('/api/research');
    const st = d.status||{};
    document.getElementById('research-status').innerHTML = `
      <table class="data-table">
        <tr><td>Pipeline Status</td><td>${badge(st.pipeline_status||'idle','amber')}</td></tr>
        <tr><td>Transcripts</td><td>${badge(st.transcript_count||0,'blue')}</td></tr>
        <tr><td>Summaries</td><td>${badge(st.summary_count||0,'blue')}</td></tr>
        <tr><td>Strategies</td><td>${badge(st.strategy_count||0,'green')}</td></tr>
        <tr><td>Last Run</td><td>${ts(st.last_run)}</td></tr>
        <tr><td>Last Error</td><td style="color:var(--red)">${st.last_error||'None'}</td></tr>
      </table>`;
    const strats = d.latest_strategies||[];
    document.getElementById('strategy-feed').innerHTML = strats.map(s =>
      `<div class="feed-item">
        <div class="feed-time">${ts(s.modified)}</div>
        <div style="color:var(--accent);margin:3px 0">${s.title}</div>
        <div style="font-size:11px;white-space:pre-wrap;line-height:1.6">${s.content.slice(0,600)}...</div>
      </div>`
    ).join('') || '<div style="color:var(--dim)">No strategies yet.</div>';
  } catch(e) {}
}

async function loadSignalsPage() {
  try {
    const d = await get('/api/signals');
    const sigs = d.recent_signals||[];
    document.getElementById('signals-table').innerHTML = sigs.length ? `
      <table class="data-table">
        <thead><tr><th>ID</th><th>SOURCE</th><th>SENTIMENT</th><th>CONF</th><th>DRY RUN</th></tr></thead>
        <tbody>${sigs.slice(-15).reverse().map(s=>`<tr>
          <td style="color:var(--dim)">${s.id}</td>
          <td style="font-size:10px">${(s.source||'').slice(0,40)}</td>
          <td class="${s.sentiment==='bullish'?'green':s.sentiment==='bearish'?'red':'amber'}">${(s.sentiment||'').toUpperCase()}</td>
          <td>${s.confidence||0}%</td>
          <td class="green">✓</td>
        </tr>`).join('')}</tbody>
      </table>` : '<div style="color:var(--dim)">No signals yet.</div>';
    const s = d.market_sentiment||{};
    document.getElementById('sentiment-detail').innerHTML = `
      <div class="metric-grid" style="margin-bottom:12px">
        <div class="metric"><div class="val ${s.dominant==='bullish'?'green':s.dominant==='bearish'?'red':'amber'}">${(s.dominant||'?').toUpperCase()}</div><div class="lbl">BIAS</div></div>
        <div class="metric"><div class="val green">${s.bullish_pct||0}%</div><div class="lbl">BULL</div></div>
        <div class="metric"><div class="val red">${s.bearish_pct||0}%</div><div class="lbl">BEAR</div></div>
        <div class="metric"><div class="val amber">${s.neutral_pct||0}%</div><div class="lbl">NEUTRAL</div></div>
      </div>
      ${pct_bar(s.bullish_pct||0, s.bearish_pct||0, s.neutral_pct||0)}
      <div style="margin-top:14px;color:var(--amber);font-size:10px">⚠ SIGNAL ONLY — NO BROKER EXECUTION — DRY RUN ACTIVE</div>`;
  } catch(e) {}
}

async function loadLeadsPage() {
  try {
    const d = await get('/api/leads');
    document.getElementById('leads-summary').innerHTML = `
      <div class="metric-grid">
        <div class="metric"><div class="val blue">${d.total||0}</div><div class="lbl">TOTAL LEADS</div></div>
        <div class="metric"><div class="val green">${d.high_value||0}</div><div class="lbl">HIGH VALUE</div></div>
        <div class="metric"><div class="val amber">${d.medium||0}</div><div class="lbl">MEDIUM</div></div>
        <div class="metric"><div class="val dim">${d.low||0}</div><div class="lbl">LOW</div></div>
        <div class="metric"><div class="val purple">${d.avg_score||0}</div><div class="lbl">AVG SCORE</div></div>
      </div>
      ${Object.entries(d.source_distribution||{}).map(([k,v])=>
        `<div style="display:flex;justify-content:space-between;margin:4px 0;font-size:11px">
          <span style="color:var(--dim)">${k}</span><span>${v}</span>
        </div>`
      ).join('')}`;
    const hvl = d.recent_high_value||[];
    document.getElementById('leads-table').innerHTML = hvl.length ?
      `<table class="data-table">
        <thead><tr><th>NAME</th><th>SOURCE</th><th>INTEREST</th><th>SCORE</th></tr></thead>
        <tbody>${hvl.slice().reverse().map(l=>`<tr>
          <td class="amber">${l.name||'?'}</td>
          <td>${l.source||'?'}</td>
          <td style="font-size:10px">${l.interest||'?'}</td>
          <td class="green">${l.score}/100</td>
        </tr>`).join('')}</tbody>
      </table>` : '<div style="color:var(--dim)">No high-value leads yet.</div>';
    document.getElementById('footer-leads').textContent = (d.total||0)+' leads';
  } catch(e) {}
}

async function loadMarketingPage() {
  try {
    const d = await get('/api/marketing');
    const s = d.summary||{};
    const p = d.performance||{};
    document.getElementById('marketing-summary').innerHTML = `
      <div class="metric-grid" style="margin-bottom:10px">
        <div class="metric"><div class="val blue">${s.total_mentions||0}</div><div class="lbl">TOTAL MENTIONS</div></div>
        <div class="metric"><div class="val green">${(s.sentiment||{}).positive||0}</div><div class="lbl">POSITIVE</div></div>
        <div class="metric"><div class="val red">${(s.sentiment||{}).negative||0}</div><div class="lbl">NEGATIVE</div></div>
        <div class="metric"><div class="val">${p.testimonials_total||0}</div><div class="lbl">TESTIMONIALS</div></div>
      </div>
      <div style="color:var(--accent);font-size:10px;margin-bottom:6px">TOP INSIGHTS</div>
      ${(s.top_insights||[]).map(i=>`<div class="feed-item"><div class="feed-text">${i}</div></div>`).join('')
        || '<div style="color:var(--dim)">Add mentions to generate insights.</div>'}`;
    const tst = (s.testimonials||[]);
    document.getElementById('testimonials-feed').innerHTML = tst.length ?
      tst.slice().reverse().map(t =>
        `<div class="feed-item">
          <div class="feed-time">${t.platform||'?'} · ${t.author||'?'}</div>
          <div class="feed-text green">"${(t.text||'').slice(0,200)}"</div>
        </div>`
      ).join('') : '<div style="color:var(--dim)">No testimonials recorded yet.</div>';
  } catch(e) {}
}

async function loadReputationPage() {
  try {
    const d = await get('/api/reputation');
    document.getElementById('reputation-summary').innerHTML = `
      <div class="metric-grid">
        <div class="metric"><div class="val ${d.avg_score>=4?'green':d.avg_score>=3?'amber':'red'}">${d.avg_score||0}</div><div class="lbl">AVG SCORE</div></div>
        <div class="metric"><div class="val blue">${d.total_reviews||0}</div><div class="lbl">REVIEWS</div></div>
        <div class="metric"><div class="val green">${d.positive||0}</div><div class="lbl">POSITIVE</div></div>
        <div class="metric"><div class="val red">${d.negative||0}</div><div class="lbl">NEGATIVE</div></div>
        <div class="metric"><div class="val red">${d.flagged_count||0}</div><div class="lbl">FLAGGED</div></div>
      </div>
      <div style="margin-top:14px;color:var(--accent);font-size:10px">RECENT REVIEWS</div>
      ${(d.recent_reviews||[]).map(r=>
        `<div class="feed-item">
          <div class="feed-time">${r.source||'?'} · ${r.reviewer_name||'?'} · ${r.star_rating||'?'}★</div>
          <div class="feed-text ${r.sentiment==='positive'?'green':r.sentiment==='negative'?'red':''}">${(r.text||'').slice(0,150)}</div>
        </div>`
      ).join('') || '<div style="color:var(--dim)">No reviews yet.</div>'}`;
    const flagged = d.recent_flagged||[];
    document.getElementById('flagged-reviews').innerHTML = flagged.length ?
      flagged.map(r =>
        `<div class="feed-item">
          <div class="feed-time red">⚠️ ${r.source||'?'} — ${r.reviewer_name||'?'}</div>
          <div class="feed-text">${(r.text||'').slice(0,200)}</div>
          <div style="margin-top:6px;color:var(--blue);font-size:11px">SUGGESTED: ${(r.suggested_response||'').slice(0,150)}...</div>
        </div>`
      ).join('') : '<div style="color:var(--green)">✓ No flagged reviews</div>';
  } catch(e) {}
}

async function loadSchedulerPage() {
  try {
    const d = await get('/api/scheduler');
    document.getElementById('scheduler-panel').innerHTML = `
      <table class="data-table">
        <thead><tr><th>TASK</th><th>INTERVAL</th><th>LAST RUN</th><th>NEXT RUN</th></tr></thead>
        <tbody>${Object.entries(d).map(([k,v])=>`<tr>
          <td class="amber">${k.replace(/_/g,' ').toUpperCase()}</td>
          <td>${v.interval_hours}h</td>
          <td style="color:var(--dim)">${ts(v.last_run)}</td>
          <td>${v.next_run==='now (never run)'?badge('PENDING NOW','green'):ts(v.next_run)}</td>
        </tr>`).join('')}</tbody>
      </table>
      <div style="margin-top:14px;color:var(--dim);font-size:11px">
        Start scheduler: <span style="color:var(--accent)">python3 operations_center/scheduler.py</span>
      </div>`;
  } catch(e) {
    document.getElementById('scheduler-panel').innerHTML = `<div style="color:var(--dim)">Scheduler not running.</div>`;
  }
}

function renderDraftCard(draft, includeActions=true) {
  const raw = draft.raw_output || {};
  const content = raw.draft_content || draft.summary || 'No draft content available.';
  const detail = raw.task_type || raw.llm_source || raw.model_used
    ? `<div class="draft-detail">
        task_type=${esc(raw.task_type || '—')} |
        llm_source=${esc(raw.llm_source || '—')} |
        model=${esc(raw.model_used || '—')}
      </div>`
    : '';

  return `<div class="draft-card">
    <div class="draft-top">
      <div>
        <div class="draft-role">${esc((draft.subject_type || 'unknown').replace(/_/g,' ').toUpperCase())}</div>
        <div class="draft-meta">${ts(draft.created_at)} | id ${esc(draft.id)}</div>
      </div>
      <div>${statusBadge(draft.status)}</div>
    </div>
    <div class="draft-summary">${esc(content)}</div>
    ${includeActions ? `
      <textarea id="draft-note-${esc(draft.id)}" class="draft-note" placeholder="Optional review note..."></textarea>
      <div class="draft-actions">
        <button class="action-btn approve" onclick="reviewDraft('${esc(draft.id)}','approve')">Approve</button>
        <button class="action-btn revise" onclick="reviewDraft('${esc(draft.id)}','request_changes')">Request Changes</button>
        <button class="action-btn reject" onclick="reviewDraft('${esc(draft.id)}','reject')">Reject</button>
        <span id="draft-flash-${esc(draft.id)}" class="draft-flash"></span>
      </div>
    ` : ''}
    ${detail}
  </div>`;
}

async function reviewDraft(draftId, action) {
  const flash = document.getElementById(`draft-flash-${draftId}`);
  const noteEl = document.getElementById(`draft-note-${draftId}`);
  const note = noteEl ? noteEl.value.trim() : '';
  if (flash) {
    flash.className = 'draft-flash';
    flash.textContent = 'Saving...';
  }

  try {
    const result = await patchJson(`/api/drafts/${draftId}`, {
      action,
      reviewed_by: 'ray',
      note,
    });
    setDraftNotice(`Draft ${draftId} updated: ${result.status || action}`, 'ok');
    await loadDraftsPage();
  } catch (e) {
    setDraftNotice(`Unable to update draft ${draftId}: ${e.message}`, 'err');
    if (flash) {
      flash.className = 'draft-flash err';
      flash.textContent = `Error: ${e.message}`;
    }
  }
}

async function loadDraftsPage() {
  try {
    const [pending, reviewed] = await Promise.all([
      get('/api/drafts?status=pending_review&limit=20'),
      get('/api/drafts?status=all&limit=20'),
    ]);

    const pendingRows = pending.drafts || [];
    document.getElementById('drafts-panel').innerHTML = draftNotice + (
      pendingRows.length
        ? pendingRows.map(d => renderDraftCard(d, true)).join('')
        : '<div style="color:var(--green)">No pending CEO drafts.</div>'
    );

    const reviewedRows = (reviewed.drafts || [])
      .filter(d => d.status && d.status !== 'pending_review')
      .slice(0, 12);
    document.getElementById('draft-review-history').innerHTML = reviewedRows.length
      ? reviewedRows.map(d => renderDraftCard(d, false)).join('')
      : '<div style="color:var(--dim)">No reviewed drafts yet.</div>';
  } catch (e) {
    const msg = `<div class="red">Unable to load drafts: ${esc(e.message)}</div>`;
    document.getElementById('drafts-panel').innerHTML = msg;
    document.getElementById('draft-review-history').innerHTML = msg;
  }
}

function renderUserCard(user) {
  const override = user.access_override || {};
  const tester = user.tester_record || {};
  const currentLevel = override.membership_level || user.subscription_plan || 'starter';
  const testerChecked = (tester.tester_access || override.tester_access) ? 'checked' : '';
  return `<div class="user-card">
    <div class="user-name">${esc(user.full_name || user.email || user.id)}</div>
    <div class="user-meta">
      ${esc(user.email || 'no email')}<br>
      role=${esc(user.role || 'unknown')} | plan=${esc(user.subscription_plan || 'free')} | id=${esc(user.id)}
    </div>
    <label class="mini-label">Membership level</label>
    <select id="membership-${esc(user.id)}" class="mini-select">
      ${['starter','growth','funding_pro','admin_test'].map(level =>
        `<option value="${level}" ${currentLevel === level ? 'selected' : ''}>${level}</option>`
      ).join('')}
    </select>
    <label class="mini-label">Optional note / waiver reason</label>
    <textarea id="note-${esc(user.id)}" class="draft-note" placeholder="Reason, tester notes, or review context..."></textarea>
    <label class="mini-label">Optional expiry</label>
    <input id="expires-${esc(user.id)}" class="mini-input" placeholder="2026-05-31T23:59:00Z">
    <label class="mini-label"><input type="checkbox" id="tester-${esc(user.id)}" ${testerChecked}> tester access</label>
    <div class="user-actions">
      <button class="action-btn approve" onclick="waivePayment('${esc(user.id)}')">Waive Payment</button>
      <button class="action-btn" onclick="toggleTester('${esc(user.id)}')">Save Tester</button>
      <button class="action-btn revise" onclick="previewTesterEmail('${esc(user.id)}')">Preview Welcome Email</button>
      <button class="action-btn reject" onclick="revokeWaiver('${esc(user.id)}')">Revoke Waiver</button>
    </div>
    <div id="user-flash-${esc(user.id)}" class="user-flash"></div>
  </div>`;
}

function setUserFlash(userId, text, cls='') {
  const el = document.getElementById(`user-flash-${userId}`);
  if (!el) return;
  el.className = `user-flash ${cls}`.trim();
  el.textContent = text;
}

async function waivePayment(userId) {
  const membershipLevel = document.getElementById(`membership-${userId}`).value;
  const note = document.getElementById(`note-${userId}`).value.trim();
  const expiresAt = document.getElementById(`expires-${userId}`).value.trim();
  const testerAccess = document.getElementById(`tester-${userId}`).checked;
  setUserFlash(userId, 'Saving waiver...');
  try {
    await postJson(`/api/admin/users/${userId}/waive-payment`, {
      membership_level: membershipLevel,
      waiver_reason: note,
      expires_at: expiresAt || null,
      tester_access: testerAccess,
      waived_by: 'ray',
    });
    setUserFlash(userId, `Waiver saved: ${membershipLevel}`, 'ok');
    await loadPrelaunchPage();
  } catch (e) {
    setUserFlash(userId, e.message, 'err');
  }
}

async function revokeWaiver(userId) {
  const note = document.getElementById(`note-${userId}`).value.trim();
  setUserFlash(userId, 'Revoking...');
  try {
    await postJson(`/api/admin/users/${userId}/revoke-waiver`, {
      revoked_by: 'ray',
      revoke_reason: note,
    });
    setUserFlash(userId, 'Waiver revoked', 'ok');
    await loadPrelaunchPage();
  } catch (e) {
    setUserFlash(userId, e.message, 'err');
  }
}

async function toggleTester(userId) {
  const note = document.getElementById(`note-${userId}`).value.trim();
  const testerAccess = document.getElementById(`tester-${userId}`).checked;
  setUserFlash(userId, 'Saving tester status...');
  try {
    await postJson(`/api/admin/users/${userId}/tester`, {
      tester_access: testerAccess,
      notes: note,
      assigned_by: 'ray',
    });
    setUserFlash(userId, testerAccess ? 'Tester access saved' : 'Tester access removed', 'ok');
    await loadPrelaunchPage();
  } catch (e) {
    setUserFlash(userId, e.message, 'err');
  }
}

async function previewTesterEmail(userId) {
  const note = document.getElementById(`note-${userId}`).value.trim();
  const membershipLevel = document.getElementById(`membership-${userId}`).value;
  setUserFlash(userId, 'Building preview...');
  try {
    const result = await postJson(`/api/admin/users/${userId}/send-tester-email`, {
      membership_level: membershipLevel,
      note,
      send: false,
    });
    setUserFlash(userId, `${result.mode.toUpperCase()}\n${result.preview.subject}\n\n${result.preview.body}`, 'ok');
  } catch (e) {
    setUserFlash(userId, e.message, 'err');
  }
}

async function loadPrelaunchPage() {
  try {
    const [audit, users] = await Promise.all([
      get('/api/prelaunch/audit'),
      get('/api/admin/users?limit=12'),
    ]);
    const summaryLines = [
      `TEST_MODE default: ${audit.test_mode_default}`,
      `superadmin auth exists: ${audit.superadmin?.auth_exists}`,
      `superadmin role: ${audit.superadmin?.profile?.role || 'missing'}`,
      `control center: ${audit.runtime?.control_center_up}`,
      `netcup tunnel: ${audit.runtime?.netcup_ollama_tunnel}`,
      `scheduler running: ${audit.runtime?.scheduler_running}`,
      `CEO routing loop: ${audit.runtime?.ceo_routing_loop_running}`,
      `CEO routed worker: ${audit.runtime?.ceo_routed_worker_running}`,
      `override table: ${audit.tables?.admin_user_access_overrides}`,
      `tester table: ${audit.tables?.prelaunch_testers}`,
      `system_events total: ${audit.supabase?.system_events_total}`,
      `job_queue total: ${audit.supabase?.job_queue_total}`,
      `workflow_outputs total: ${audit.supabase?.workflow_outputs_total}`,
      `worker_heartbeats total: ${audit.supabase?.worker_heartbeats_total}`,
      `telegram processes: ${(audit.runtime?.telegram_processes || []).length}`,
    ];
    document.getElementById('prelaunch-audit-panel').innerHTML =
      `<div class="audit-pre">${esc(summaryLines.join('\\n'))}</div>`;
    const userRows = users.users || [];
    document.getElementById('prelaunch-users-panel').innerHTML = userRows.length
      ? userRows.map(renderUserCard).join('')
      : '<div style="color:var(--dim)">No users found.</div>';
  } catch (e) {
    const msg = `<div class="red">Unable to load prelaunch tools: ${esc(e.message)}</div>`;
    document.getElementById('prelaunch-audit-panel').innerHTML = msg;
    document.getElementById('prelaunch-users-panel').innerHTML = msg;
  }
}

async function loadGrowthPage() {
  try {
    const [d, variantFeed, approvalQueue, fundingOverview] = await Promise.all([
      get('/api/growth/summary'),
      get('/api/growth/variants?status=all&limit=12'),
      get('/api/growth/approval-queue?limit=18'),
      get('/api/funding/overview'),
    ]);
    const flags = d.feature_flags || {};
    const queue = d.content_queue || {};
    const referrals = d.referrals || {};
    const dms = d.dm_drafts || {};
    const influencers = d.influencers || {};
    const leadScores = d.lead_scores || {};
    const onboarding = d.onboarding || {};
    const noteRows = d.learning_notes || [];
    const pendingApprovals = (queue.approvals_by_decision || {}).pending || 0;
    const approvalRows = approvalQueue.queue || [];
    const funding = fundingOverview || {};

    document.getElementById('growth-summary-panel').innerHTML = `
      <div class="metric-grid">
        <div class="metric"><div class="val blue">${queue.topics_total || 0}</div><div class="lbl">TOPICS</div></div>
        <div class="metric"><div class="val amber">${Object.values(queue.variants_by_status || {}).reduce((a,b)=>a+b,0)}</div><div class="lbl">CONTENT DRAFTS</div></div>
        <div class="metric"><div class="val red">${pendingApprovals}</div><div class="lbl">PENDING APPROVALS</div></div>
        <div class="metric"><div class="val green">${funding.users_ready_for_tier_1 || 0}</div><div class="lbl">READY FOR TIER 1</div></div>
        <div class="metric"><div class="val blue">${funding.users_close_to_tier_2_unlock || 0}</div><div class="lbl">CLOSE TO TIER 2</div></div>
        <div class="metric"><div class="val purple">${funding.pending_invoices || 0}</div><div class="lbl">PENDING INVOICES</div></div>
      </div>
      <div style="margin-top:12px" class="audit-pre">Flags
AUTO_POST_ENABLED=${esc(flags.AUTO_POST_ENABLED)}
COMMENT_AUTO_REPLY=${esc(flags.COMMENT_AUTO_REPLY)}
COMMENT_REQUIRE_APPROVAL=${esc(flags.COMMENT_REQUIRE_APPROVAL)}
DM_AUTO_SEND=${esc(flags.DM_AUTO_SEND)}
DM_REQUIRE_APPROVAL=${esc(flags.DM_REQUIRE_APPROVAL)}
INFLUENCER_AUTO_SEND=${esc(flags.INFLUENCER_AUTO_SEND)}
INFLUENCER_REQUIRE_APPROVAL=${esc(flags.INFLUENCER_REQUIRE_APPROVAL)}</div>
    `;

    const recentTopics = (queue.recent_topics || []).map(row => `• ${row.topic} [${row.status}]`).join('\\n') || '• none yet';
    const recentVariants = (variantFeed.variants || []).map(renderGrowthVariantCard).join('') || '<div style="color:var(--dim)">No content variants yet.</div>';
    const approvalCards = approvalRows.map(renderGrowthApprovalCard).join('') || '<div style="color:var(--dim)">No pending content approvals.</div>';
    const recentScores = (leadScores.recent || []).map(row => `• ${row.lead_ref}: ${row.lead_score} (${row.segment}) → ${row.recommended_agent}`).join('\\n') || '• none yet';
    const recentOnboarding = (onboarding.recent_recommendations || []).map(row => `• ${row.user_ref}: ${row.user_stage} → ${row.recommended_agent}`).join('\\n') || '• none yet';
    const learningNotes = noteRows.map(row => `• ${row.note}`).join('\\n') || '• none yet';
    const recentTierProgress = (funding.recent_tier_progress || []).map(
      row => `• ${row.user_id}: tier=${row.current_tier} | readiness=${row.business_readiness_score || 0} | relationship=${row.relationship_score || 0} | t2=${row.tier_2_status || 'n/a'}`
    ).join('\\n') || '• none yet';
    const recommendationNeeds = (funding.users_needing_recommendation_generation || []).map(
      row => `• ${row.user_id}: ${row.reason || 'needs generation'}`
    ).join('\\n') || '• none yet';
    const staleRecommendations = (funding.users_with_stale_recommendations || []).map(
      row => `• ${row.user_id}: ${row.product_name || 'recommendation'} | last=${row.last_generated_at || 'unknown'}`
    ).join('\\n') || '• none yet';
    const generationErrors = (funding.generation_errors || []).map(
      row => `• ${row.user_id}: ${row.error || row.skipped_reason || row.status}`
    ).join('\\n') || '• none yet';

    document.getElementById('growth-detail-panel').innerHTML = `
      <div style="margin-bottom:12px">
        <div class="message-title">Funding Journey AI Operator</div>
        <div class="message-meta">Inspect one user at a time and trigger safe backend actions only. Nothing is sent to lenders or auto-submitted.</div>
        <div class="draft-actions">
          <input id="journey-user-id" class="mini-input" placeholder="user_id">
          <input id="journey-tenant-id" class="mini-input" placeholder="tenant_id optional">
          <button class="action-btn" onclick="loadFundingJourneyOrchestrator()">Load Journey</button>
          <button class="action-btn revise" onclick="refreshFundingJourneyOrchestrator(false)">Refresh Recs</button>
          <button class="action-btn approve" onclick="refreshFundingJourneyOrchestrator(true)">Force Refresh</button>
        </div>
        <div id="journey-orchestrator-flash" class="draft-flash"></div>
        <div id="journey-orchestrator-panel" class="audit-pre">Enter a user id to load one user&apos;s Funding Journey.</div>
      </div>
      <div style="margin-bottom:12px">
        <div class="message-title">Approval Queue</div>
        <div class="message-meta">Draft-only queue for human review. Nothing here is posted or scheduled automatically.</div>
        ${approvalCards}
      </div>
      <div style="margin-bottom:12px">
        <div class="message-title">Recent Content Variants</div>
        ${recentVariants}
      </div>
      <div class="audit-pre">Content Queue
${esc(JSON.stringify(queue.variants_by_status || {}, null, 2))}

Funding Engine
approval_results_raw=${esc(String((funding.approval_data_ingestion_status || {}).raw_results || 0))}
approval_patterns=${esc(String((funding.approval_data_ingestion_status || {}).normalized_patterns || 0))}
lending_institutions=${esc(String((funding.lending_research_status || {}).institutions || 0))}
recommendations_generated=${esc(String(funding.recommendations_generated || 0))}
application_results=${esc(String(funding.application_results_submitted || 0))}
pending_invoices=${esc(String(funding.pending_invoices || 0))}
pending_referral_earnings=${esc(String(funding.pending_referral_earnings || 0))}
missing_business_score_inputs=${esc(String(funding.missing_business_score_inputs || 0))}
missing_banking_relationship_inputs=${esc(String(funding.missing_banking_relationship_inputs || 0))}
last_recommendation_generation_time=${esc(String(funding.last_recommendation_generation_time || 'none'))}

Recent Topics
${esc(recentTopics)}

Referral Rewards
${esc(JSON.stringify(referrals.rewards_by_status || {}, null, 2))}

DM Drafts
${esc(JSON.stringify(dms.messages_by_status || {}, null, 2))}

Influencer Drafts
${esc(JSON.stringify(influencers.messages_by_status || {}, null, 2))}

Lead Scores
${esc(recentScores)}

Onboarding Dropoffs
${esc(recentOnboarding)}

Tier Progress
${esc(recentTierProgress)}

Users Needing Recommendation Generation
${esc(recommendationNeeds)}

Users With Stale Recommendations
${esc(staleRecommendations)}

Recommendation Generation Errors
${esc(generationErrors)}

Learning Notes
${esc(learningNotes)}</div>
    `;

    const storedUserId = localStorage.getItem('journey_user_id') || '';
    const storedTenantId = localStorage.getItem('journey_tenant_id') || '';
    const userInput = document.getElementById('journey-user-id');
    const tenantInput = document.getElementById('journey-tenant-id');
    if (userInput) userInput.value = storedUserId;
    if (tenantInput) tenantInput.value = storedTenantId;
    if (storedUserId) {
      await loadFundingJourneyOrchestrator();
    }
  } catch (e) {
    const msg = `<div class="red">Unable to load growth summary: ${esc(e.message)}</div>`;
    document.getElementById('growth-summary-panel').innerHTML = msg;
    document.getElementById('growth-detail-panel').innerHTML = msg;
  }
}

function setJourneyFlash(message, cls='') {
  const el = document.getElementById('journey-orchestrator-flash');
  if (!el) return;
  el.className = `draft-flash ${cls}`.trim();
  el.textContent = message || '';
}

function getJourneyContext() {
  const userId = (document.getElementById('journey-user-id')?.value || '').trim();
  const tenantId = (document.getElementById('journey-tenant-id')?.value || '').trim();
  return { userId, tenantId };
}

function renderJourneyActionButtons(actions) {
  return (actions || []).map(action => `
    <button class="action-btn" onclick="runFundingJourneyAction('${esc(action.type)}')">${esc(action.label || action.type)}</button>
  `).join('');
}

function renderFundingJourneyPanel(journey) {
  const readiness = journey.readiness || {};
  const funding = journey.funding || {};
  const nextAction = journey.next_best_action || {};
  const topRecommendations = (funding.top_recommendations || []).map(row =>
    `• Tier ${row.tier || '?'} | ${row.institution_name || 'Institution'} | ${row.product_name || 'Product'} | score=${row.approval_score || 0}`
  ).join('\\n') || '• none yet';
  const missingInputs = (journey.missing_inputs || []).map(item => `• ${item}`).join('\\n') || '• none';
  const warnings = (journey.warnings || []).map(item => `• ${item}`).join('\\n') || '• none';
  const incompleteSections = (readiness.incomplete_sections || []).map(section =>
    `• ${section.section}: ${Math.round((section.pct || 0) * 100)}%`
  ).join('\\n') || '• none';

  return `
    <div class="message-card">
      <div class="message-title">Current Phase: ${esc(funding.current_phase || 'readiness')}</div>
      <div class="message-meta">generated=${ts(journey.generated_at)} | recommendations=${esc(String(funding.active_recommendation_count || 0))} | stale=${esc(String(funding.stale_recommendation_count || 0))}</div>
      <div class="message-body"><strong>Next Best Action:</strong> ${esc(nextAction.title || 'Review the Funding Journey.')}</div>
      <div class="message-body">${esc(nextAction.detail || '')}</div>
      <div class="draft-actions">${renderJourneyActionButtons(journey.available_actions || [])}</div>
    </div>
    <div class="audit-pre">Readiness
score=${esc(String(readiness.overall_score || 0))}
completion_pct=${esc(String(readiness.completion_pct || 0))}
pending_tasks=${esc(String(readiness.pending_task_count || 0))}
grant_ready=${esc(String(readiness.grant_ready || false))}
trading_eligible=${esc(String(readiness.trading_eligible || false))}

Incomplete Sections
${esc(incompleteSections)}

Funding
strategy_phase=${esc(String(funding.current_phase || 'readiness'))}
estimated_funding_low=${esc(String(funding.estimated_funding_low || 0))}
estimated_funding_high=${esc(String(funding.estimated_funding_high || 0))}
relationship_score=${esc(String(funding.relationship_score || 0))}
last_recommendation_generated_at=${esc(String(funding.last_recommendation_generated_at || 'none'))}

Top Recommendations
${esc(topRecommendations)}

Missing Inputs
${esc(missingInputs)}

Warnings
${esc(warnings)}

Disclaimer
${esc(journey.disclaimer || '')}</div>
  `;
}

async function loadFundingJourneyOrchestrator() {
  const { userId, tenantId } = getJourneyContext();
  if (!userId) {
    setJourneyFlash('user_id required', 'err');
    return;
  }
  localStorage.setItem('journey_user_id', userId);
  localStorage.setItem('journey_tenant_id', tenantId);
  setJourneyFlash('Loading journey...');
  try {
    const query = new URLSearchParams({ user_id: userId });
    if (tenantId) query.set('tenant_id', tenantId);
    const journey = await get(`/api/funding/journey?${query.toString()}`);
    window.latestFundingJourney = journey;
    document.getElementById('journey-orchestrator-panel').innerHTML = renderFundingJourneyPanel(journey);
    setJourneyFlash(`Loaded journey for ${userId}`, 'ok');
  } catch (e) {
    setJourneyFlash(e.message, 'err');
    document.getElementById('journey-orchestrator-panel').innerHTML = `<div class="red">Unable to load journey: ${esc(e.message)}</div>`;
  }
}

async function refreshFundingJourneyOrchestrator(force=false) {
  const { userId, tenantId } = getJourneyContext();
  if (!userId) {
    setJourneyFlash('user_id required', 'err');
    return;
  }
  setJourneyFlash(force ? 'Force refreshing journey...' : 'Refreshing recommendations...');
  try {
    const journey = await postJson('/api/funding/journey/refresh', {
      user_id: userId,
      tenant_id: tenantId || null,
      force,
    });
    window.latestFundingJourney = journey;
    document.getElementById('journey-orchestrator-panel').innerHTML = renderFundingJourneyPanel(journey);
    setJourneyFlash(force ? 'Journey force refresh complete' : 'Journey refresh complete', 'ok');
  } catch (e) {
    setJourneyFlash(e.message, 'err');
  }
}

async function runFundingJourneyAction(actionType) {
  const journey = window.latestFundingJourney || {};
  const actions = journey.available_actions || [];
  const action = actions.find(row => row.type === actionType);
  if (!action || !action.endpoint) {
    setJourneyFlash(`Unknown action: ${actionType}`, 'err');
    return;
  }
  setJourneyFlash(`Running ${action.label || action.type}...`);
  try {
    if ((action.method || 'POST').toUpperCase() === 'POST') {
      await postJson(action.endpoint, action.body || {});
    } else {
      await get(action.endpoint);
    }
    await loadFundingJourneyOrchestrator();
    setJourneyFlash(`${action.label || action.type} complete`, 'ok');
  } catch (e) {
    setJourneyFlash(e.message, 'err');
  }
}

function renderGrowthApprovalCard(row) {
  const topic = row.content_topics?.topic || row.topic_id || 'Unknown topic';
  const theme = row.content_topics?.theme || 'general education';
  const hashtags = Array.isArray(row.hashtags) ? row.hashtags.join(' ') : '';
  const createdBy = row.created_by || 'unknown';
  return `<div class="draft-card">
    <div class="draft-top">
      <div>
        <div class="draft-role">${esc((row.platform || 'content').toUpperCase())}</div>
        <div class="draft-meta">${ts(row.created_at)} | status=${esc(row.status || 'pending_review')} | by ${esc(createdBy)}</div>
      </div>
      <div>${statusBadge(row.status || 'pending_review')}</div>
    </div>
    <div class="message-title">${esc(topic)}</div>
    <div class="message-meta">theme=${esc(theme)} | topic_id=${esc(row.topic_id || 'n/a')}</div>
    <div class="message-body">Hook: ${esc(row.hook_draft || 'n/a')}</div>
    <div class="message-body">${esc(row.script_draft || '')}</div>
    <div class="message-body">${esc(row.caption_draft || '')}</div>
    <div class="draft-detail">CTA: ${esc(row.cta || 'embedded in caption/compliance notes')}</div>
    <div class="draft-detail">Hashtags: ${esc(hashtags || 'embedded in caption')}</div>
    <div class="draft-detail">${esc(row.compliance_notes || '')}</div>
  </div>`;
}

function renderApprovalQueueCard(row) {
  const sym    = (row.symbol || '?').replace('_','');
  const side   = (row.side || '?').toUpperCase();
  const conf   = row.ai_confidence != null ? (row.ai_confidence * 100).toFixed(0) + '%' : '—';
  const strat  = (row.strategy_id || '—').slice(0, 24);
  const tf     = row.timeframe || '—';
  const entry  = row.entry_price != null ? row.entry_price : '—';
  const sl     = row.stop_loss != null ? row.stop_loss : '—';
  const tp     = row.take_profit != null ? row.take_profit : '—';
  const notes  = (row.risk_notes || '').slice(0, 80);
  const st     = row.status || 'pending';
  const stBadge = st === 'pending' ? 'badge-amber' : st === 'executed' ? 'badge-green' : 'badge-red';
  const shortId = (row.id || '').slice(0,8);
  return `<div class="message-card">
    <div class="draft-top">
      <div>
        <div class="draft-role">${esc(sym)} ${esc(side)} — ${esc(tf)}</div>
        <div class="draft-meta">${ts(row.created_at)} | conf=${esc(conf)} | <span class="panel-badge ${stBadge}">${esc(st.toUpperCase())}</span></div>
      </div>
    </div>
    <div class="message-title">${esc(sym)} ${esc(side)} @ ${esc(String(entry))}</div>
    <div class="message-meta">SL: ${esc(String(sl))} | TP: ${esc(String(tp))}</div>
    <div class="message-meta">Strategy: ${esc(strat)} | AI Confidence: ${esc(conf)}</div>
    ${notes ? `<div class="message-meta" style="color:var(--dim)">${esc(notes)}</div>` : ''}
    <div class="message-meta" style="color:var(--dim)">ID: ${esc(shortId)}</div>
    <div class="draft-actions">
      <button class="action-btn approve" onclick="actOnApproval('${esc(row.id)}','approve',this)">✅ Allow</button>
      <button class="action-btn reject"  onclick="actOnApproval('${esc(row.id)}','block',this)">🚫 Block</button>
      <span id="approval-flash-${esc(shortId)}" class="draft-flash"></span>
    </div>
  </div>`;
}

async function actOnApproval(itemId, action, btn) {
  const shortId = itemId.slice(0,8);
  const flash = document.getElementById(`approval-flash-${shortId}`);
  if (flash) flash.textContent = 'Saving...';
  if (btn) btn.disabled = true;
  try {
    await patchJson(`/api/trading/approval-queue/${itemId}`, { action });
    if (flash) { flash.className = 'draft-flash ok'; flash.textContent = action === 'approve' ? '✅ Allowed — auto-executor will run it' : '🚫 Blocked'; }
    setTimeout(loadApprovalsPage, 1000);
  } catch (e) {
    if (flash) { flash.className = 'draft-flash err'; flash.textContent = e.message; }
    if (btn) btn.disabled = false;
  }
}

async function loadApprovalsPage() {
  try {
    const d = await get('/api/trading/approval-queue');
    const pending  = d.pending  || [];
    const recent   = d.recent   || [];
    const pipeline = d.pipeline || [];
    document.getElementById('approvals-pending-panel').innerHTML = pending.length
      ? pending.map(renderApprovalQueueCard).join('')
      : '<div style="color:var(--green)">No pending proposals. Queue is clear.</div>';
    const recentHtml = recent.map(r => {
      const sym  = (r.symbol||'?').replace('_','');
      const side = (r.side||'?').toUpperCase();
      const st   = r.status || '?';
      const stBadge = st === 'executed' ? 'badge-green' : st === 'blocked' ? 'badge-red' : 'badge-amber';
      const conf = r.ai_confidence != null ? (r.ai_confidence*100).toFixed(0)+'%' : '—';
      return `<div class="feed-item">
        <div class="feed-time">${ts(r.created_at)} | ${esc(sym)} ${esc(side)} | conf=${esc(conf)}</div>
        <div class="feed-text"><span class="panel-badge ${stBadge}">${esc(st.toUpperCase())}</span> ${esc((r.risk_notes||'').slice(0,60))}</div>
      </div>`;
    }).join('');
    const pipeHtml = pipeline.length ? `<div style="color:var(--accent);margin-top:12px;font-size:11px">SIGNAL PIPELINE</div>` + pipeline.map(r => {
      const sym = (r.symbol||'?').replace('_','');
      return `<div class="feed-item"><div class="feed-time">${ts(r.created_at)} | ${esc(sym)} ${esc((r.side||'').toUpperCase())} ${esc(r.timeframe||'')}</div><div class="feed-text">status: ${esc(r.status||'?')}</div></div>`;
    }).join('') : '';
    document.getElementById('approvals-recent-panel').innerHTML =
      (recentHtml || '<div style="color:var(--dim)">No recently actioned proposals.</div>') + pipeHtml;
  } catch (e) {
    const msg = `<div class="red">Error loading signal queue: ${esc(e.message)}</div>`;
    document.getElementById('approvals-pending-panel').innerHTML = msg;
    document.getElementById('approvals-recent-panel').innerHTML = msg;
  }
}

function renderGrowthVariantCard(row) {
  const topic = row.content_topics?.topic || row.topic_id || 'Unknown topic';
  return `<div class="message-card">
    <div class="message-title">${esc((row.platform || 'variant').toUpperCase())} Variant #${esc(row.id)}</div>
    <div class="message-meta">${ts(row.created_at)} | status=${esc(row.status || 'pending_review')} | ${esc(topic)}</div>
    <div class="message-body">Hook: ${esc(row.hook_draft || 'n/a')}</div>
    <div class="message-body">${esc(row.caption_draft || '')}</div>
  </div>`;
}

function renderDmDraftCard(row) {
  return `<div class="message-card">
    <div class="message-title">DM Draft #${esc(row.id)}</div>
    <div class="message-meta">sequence=${esc(row.sequence_id)} | order=${esc(row.message_order)} | ${ts(row.created_at)}</div>
    <div class="message-body">${esc(row.draft_text)}</div>
    <textarea id="message-note-${esc(row.id)}" class="draft-note" placeholder="Optional review note..."></textarea>
    <div class="draft-actions">
      <button class="action-btn approve" onclick="reviewMessageDraft('${esc(row.id)}','approve')">Approve</button>
      <button class="action-btn reject" onclick="reviewMessageDraft('${esc(row.id)}','reject')">Reject</button>
      <span id="message-flash-${esc(row.id)}" class="draft-flash"></span>
    </div>
  </div>`;
}

function renderCommentDraftCard(row) {
  return `<div class="message-card">
    <div class="message-title">${esc((row.platform || 'comment').toUpperCase())} Comment Draft #${esc(row.id)}</div>
    <div class="message-meta">author=${esc(row.author_handle || 'unknown')} | topic=${esc(row.content_topic || 'n/a')} | ${ts(row.created_at)}</div>
    <div class="message-body">Comment: ${esc(row.comment_text)}</div>
    <div class="message-body">Reply Draft: ${esc(row.reply_draft)}</div>
    <textarea id="comment-note-${esc(row.id)}" class="draft-note" placeholder="Optional review note..."></textarea>
    <div class="draft-actions">
      <button class="action-btn approve" onclick="reviewCommentDraft('${esc(row.id)}','approve')">Approve</button>
      <button class="action-btn reject" onclick="reviewCommentDraft('${esc(row.id)}','reject')">Reject</button>
      <span id="comment-flash-${esc(row.id)}" class="draft-flash"></span>
    </div>
  </div>`;
}

async function reviewMessageDraft(draftId, action) {
  const flash = document.getElementById(`message-flash-${draftId}`);
  const note = (document.getElementById(`message-note-${draftId}`)?.value || '').trim();
  if (flash) flash.textContent = 'Saving...';
  try {
    await patchJson(`/api/messages/dm-drafts/${draftId}`, { action, reviewed_by: 'ray', note });
    if (flash) { flash.className = 'draft-flash ok'; flash.textContent = `Saved: ${action}`; }
    await loadMessagesPage();
  } catch (e) {
    if (flash) { flash.className = 'draft-flash err'; flash.textContent = e.message; }
  }
}

async function reviewCommentDraft(draftId, action) {
  const flash = document.getElementById(`comment-flash-${draftId}`);
  const note = (document.getElementById(`comment-note-${draftId}`)?.value || '').trim();
  if (flash) flash.textContent = 'Saving...';
  try {
    await patchJson(`/api/messages/comment-drafts/${draftId}`, { action, reviewed_by: 'ray', note });
    if (flash) { flash.className = 'draft-flash ok'; flash.textContent = `Saved: ${action}`; }
    await loadMessagesPage();
  } catch (e) {
    if (flash) { flash.className = 'draft-flash err'; flash.textContent = e.message; }
  }
}

async function loadMessagesPage() {
  try {
    const d = await get('/api/messages/review-summary');
    const dmRows = d.pending_dm_drafts || [];
    const commentRows = d.pending_comment_drafts || [];
    const logs = d.recent_message_logs || [];
    document.getElementById('message-review-panel').innerHTML =
      (dmRows.map(renderDmDraftCard).join('') + commentRows.map(renderCommentDraftCard).join(''))
      || '<div style="color:var(--green)">No pending message drafts.</div>';
    document.getElementById('message-log-panel').innerHTML = logs.length
      ? logs.map(row => `<div class="feed-item"><div class="feed-time">${ts(row.created_at)} | ${esc(row.platform)} | ${esc(row.event_type)} | ${esc(row.status)}</div><div class="feed-text">${esc((row.content_topic || row.intent_category || row.external_ref || 'log event'))}</div></div>`).join('')
      : '<div style="color:var(--dim)">No message logs yet.</div>';
  } catch (e) {
    const msg = `<div class="red">Unable to load message review: ${esc(e.message)}</div>`;
    document.getElementById('message-review-panel').innerHTML = msg;
    document.getElementById('message-log-panel').innerHTML = msg;
  }
}

function renderMissionWorkerCard(row) {
  const status = (row.status_indicator || 'degraded') === 'healthy' ? 'badge-green' : 'badge-amber';
  return `<div class="message-card">
    <div class="message-title">${esc(row.name || 'Worker')}</div>
    <div class="message-meta"><span class="panel-badge ${status}">${esc((row.worker_health || 'unknown').toUpperCase())}</span> | last=${ts(row.last_activity)}</div>
    <div class="message-body">active task: ${esc(row.active_task || 'n/a')}</div>
    <div class="message-meta">confidence: ${esc(String(row.confidence_posture || 'pending confidence'))} | queue=${esc(String(row.queue_depth || 0))} | recs=${esc(String(row.recommendation_count || 0))} | alerts=${esc(String(row.alert_count || 0))}</div>
  </div>`;
}

function renderMissionFeedGroup(title, rows) {
  const body = (rows || []).slice(0, 6).map(r => `<div class="feed-item"><div class="feed-time">${ts(r.created_at)} | ${esc(r.event_type || 'event')}</div><div class="feed-text">${esc(r.summary || '')}</div></div>`).join('');
  return `<div style="margin-bottom:10px"><div class="message-title">${esc(title)}</div>${body || '<div style="color:var(--dim)">No recent events.</div>'}</div>`;
}

function renderMissionQueueCard(row) {
  const id = row.id || '';
  const title = row.title || 'Untitled recommendation';
  const kind = row.type || 'unknown';
  const confidence = row.confidence || 'pending confidence';
  const why = row.why || 'Awaiting richer outcome history.';
  return `<div class="message-card">
    <div class="message-title">[${esc(id)}] ${esc(kind)} — ${esc(title)}</div>
    <div class="message-meta">status=${esc(row.status || 'pending')} | confidence=${esc(String(confidence))}</div>
    <div class="message-body">why: ${esc(why)}</div>
    <div class="draft-actions">
      <button class="action-btn approve" onclick="missionCommand('approve recommendation ${esc(id)}')">Approve</button>
      <button class="action-btn reject" onclick="missionCommand('reject recommendation ${esc(id)}')">Reject</button>
      <button class="action-btn" onclick="missionCommand('generate website brief for the top opportunity')">Build Brief</button>
      <button class="action-btn" onclick="missionCommand('generate build plan for recommendation ${esc(id)}')">Launch Plan</button>
      <button class="action-btn revise" onclick="missionCommand('show recommendation reasoning')">Explain</button>
    </div>
  </div>`;
}

async function missionCommand(cmd) {
  try {
    await postJson('/api/route-job', { message: cmd, channel: 'mission_control' });
    await loadMissionControlPage();
  } catch (e) {
    console.error('missionCommand error', e);
  }
}

async function loadMissionControlPage() {
  try {
    const d = await get('/api/mission-control');
    const workers = d.workforce || [];
    const panel = d.executive_panel || {};
    const feed = d.operations_feed || {};
    const queue = d.recommendation_queue || [];
    const review = d.review_drawer || {};

    document.getElementById('mission-workforce-panel').innerHTML = workers.length
      ? workers.map(renderMissionWorkerCard).join('')
      : '<div style="color:var(--dim)">No workforce telemetry yet.</div>';

    document.getElementById('mission-executive-panel').innerHTML = `
      <div class="message-card"><div class="message-title">Weekly Priorities</div><div class="message-body">${esc(panel.weekly_priorities || 'n/a')}</div></div>
      <div class="message-card"><div class="message-title">Strategic Focus</div><div class="message-body">${esc(panel.strategic_focus || 'n/a')}</div></div>
      <div class="message-meta">critical alerts=${esc(String(panel.critical_alerts || 0))} | top ROI opportunities=${esc((panel.highest_roi_opportunities || []).join(', ') || 'none')}</div>
    `;

    document.getElementById('mission-feed-panel').innerHTML =
      renderMissionFeedGroup('Critical', feed.critical) +
      renderMissionFeedGroup('Recommendations', feed.recommendations) +
      renderMissionFeedGroup('Digest', feed.digest) +
      renderMissionFeedGroup('Operations', feed.operations);

    document.getElementById('mission-queue-panel').innerHTML =
      (queue.length ? queue.map(renderMissionQueueCard).join('') : '<div style="color:var(--dim)">No pending recommendations.</div>') +
      `<div class="audit-pre" style="margin-top:10px">Review Drawer
reasoning=${esc(String(review.reasoning || 'n/a'))}
confidence=${esc(String(review.confidence || 'pending confidence'))}
sparse_data_warnings=${esc(JSON.stringify(review.sparse_data_warnings || []))}
missing_telemetry=${esc(JSON.stringify(review.missing_telemetry || []))}
historical_outcomes=${esc(JSON.stringify(review.historical_outcomes || []))}
contributing_signals=${esc(JSON.stringify(review.contributing_signals || []))}</div>`;
  } catch (e) {
    const msg = `<div class="red">Mission control unavailable: ${esc(e.message)}</div>`;
    document.getElementById('mission-workforce-panel').innerHTML = msg;
    document.getElementById('mission-executive-panel').innerHTML = msg;
    document.getElementById('mission-feed-panel').innerHTML = msg;
    document.getElementById('mission-queue-panel').innerHTML = msg;
  }
}

function renderAiOpsConfig(d) {
  const mc = d.model_config || {};
  const tg = d.telegram_mode || {};
  const modelBadge = `${mc.active_default_provider || 'unknown'}:${mc.active_default_model || 'unknown'}`;
  return `<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
    <span class="panel-badge badge-green">Telegram: Conversational</span>
    <span class="panel-badge badge-blue">Reports: Email Only</span>
    <span class="panel-badge badge-amber">Swarm: Dry Run Only</span>
    <span class="panel-badge badge-red">Execution: Disabled</span>
    <span class="panel-badge badge-blue">Model: ${esc(modelBadge)}</span>
    <span class="panel-badge badge-green">Auth: Protected</span>
  </div>
  <table class="data-table"><tbody>
    <tr><td style="color:var(--dim)">telegram_enabled</td><td>${esc(String(tg.enabled))}</td></tr>
    <tr><td style="color:var(--dim)">manual_only</td><td>${esc(String(tg.manual_only))}</td></tr>
    <tr><td style="color:var(--dim)">auto_reports</td><td>${esc(String(tg.auto_reports_enabled))}</td></tr>
    <tr><td style="color:var(--dim)">context_length</td><td>${esc(String(mc.configured_context_length || 'unknown'))}</td></tr>
    <tr><td style="color:var(--dim)">reports_destination</td><td>email</td></tr>
    <tr><td style="color:var(--dim)">safety</td><td class="amber">Swarm disabled | Approvals required | No auto-execution</td></tr>
  </tbody></table>`;
}

function renderAiOpsSession(d) {
  const s = d?.active_work_session || {};
  if (!Object.keys(s).length) return '<div style="color:var(--dim)">No active work session. Start one from Telegram with "start work session".</div>';
  const activeTasks = s.active_tasks || [];
  const blocked = s.blocked_items || [];
  const pending = s.pending_approvals || [];
  const st = (s.status || 'unknown').toLowerCase();
  const stBadge = st === 'active' ? 'badge-green' : st === 'paused' ? 'badge-amber' : 'badge-blue';
  const nextAction = d.next_recommended_action || 'Review top active priority';
  return `<div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap">
    <span class="panel-badge ${stBadge}" style="font-size:11px;padding:3px 10px">${esc(st.toUpperCase())}</span>
    <span style="color:var(--text);font-size:12px">${esc(s.current_goal || 'No goal set')}</span>
  </div>
  <div class="metric-grid" style="margin-bottom:10px">
    <div class="metric"><div class="val green">${activeTasks.length}</div><div class="lbl">ACTIVE TASKS</div></div>
    <div class="metric"><div class="val ${blocked.length > 0 ? 'red' : ''}">${blocked.length}</div><div class="lbl">BLOCKED</div></div>
    <div class="metric"><div class="val ${pending.length > 0 ? 'amber' : ''}">${pending.length}</div><div class="lbl">AWAITING APPROVAL</div></div>
  </div>
  <div style="color:var(--dim);font-size:10px;margin-bottom:4px">NEXT RECOMMENDED ACTION</div>
  <div style="font-size:11px;padding:8px;background:#141820;border-left:3px solid var(--accent);border-radius:2px">${esc(nextAction)}</div>`;
}

function renderAiOpsMemory(d) {
  const m = d?.operational_memory || {};
  const k = d?.knowledge || {};
  const sc = d?.ai_ops_scorecard || {};
  const kc = k.category_counts || {};
  const scoreItems = [
    { key: 'operational_health', label: 'OPS HEALTH' },
    { key: 'agent_readiness', label: 'AGENT READINESS' },
    { key: 'knowledge_freshness', label: 'KNOWLEDGE' },
    { key: 'funding_credit_intelligence', label: 'FUNDING/CREDIT' },
    { key: 'risk_blocker', label: 'RISK BLOCKER' },
  ];
  let html = '';
  if (Object.keys(sc).length > 1) {
    html += '<div style="color:var(--dim);font-size:10px;margin-bottom:8px;letter-spacing:1px">AI OPS SCORECARD</div>';
    html += scoreItems.map(({ key, label }) => {
      const item = sc[key] || {};
      const num = typeof item.score === 'number' ? item.score : null;
      const clr = num === null ? 'var(--dim)' : num >= 75 ? 'var(--green)' : num >= 50 ? 'var(--accent)' : 'var(--red)';
      const pct = num !== null ? num : 0;
      return `<div class="score-row" title="${esc(item.reason || '')}"><div class="score-label">${label}</div><div class="score-bar"><div class="score-fill" style="width:${pct}%;background:${clr}"></div></div><div class="score-num" style="color:${clr}">${num !== null ? num : '—'}</div></div>`;
    }).join('');
    html += '<div style="margin-bottom:12px"></div>';
  }
  const lastInstr = m.last_user_instruction || '';
  if (lastInstr) {
    html += `<div style="color:var(--dim);font-size:10px;margin-bottom:4px">LAST INSTRUCTION</div><div style="font-size:11px;padding:6px 8px;background:#141820;border-left:2px solid var(--accent);border-radius:2px;margin-bottom:10px">${esc(lastInstr.slice(0, 120))}</div>`;
  }
  const recs = (m.recent_recommendations || []).slice(0, 3);
  if (recs.length) {
    html += '<div style="color:var(--dim);font-size:10px;margin-bottom:4px">RECOMMENDATIONS</div>';
    html += recs.map(r => `<div class="feed-item"><div class="feed-text">${esc(typeof r === 'string' ? r.slice(0, 100) : JSON.stringify(r).slice(0, 100))}</div></div>`).join('');
  }
  const completed = (m.recent_completed || []).slice(0, 3);
  if (completed.length) {
    html += '<div style="color:var(--dim);font-size:10px;margin:8px 0 4px">RECENTLY COMPLETED</div>';
    html += completed.map(r => `<div class="feed-item"><div class="feed-text green">✓ ${esc(typeof r === 'string' ? r.slice(0, 100) : JSON.stringify(r).slice(0, 100))}</div></div>`).join('');
  }
  const kcKeys = Object.keys(kc);
  if (kcKeys.length) {
    html += '<div style="color:var(--dim);font-size:10px;margin:8px 0 4px">KNOWLEDGE COVERAGE</div>';
    html += '<div style="display:flex;gap:6px;flex-wrap:wrap">' + kcKeys.slice(0, 10).map(cat => `<span class="panel-badge badge-blue">${esc(cat)}: ${kc[cat]}</span>`).join('') + '</div>';
  }
  return html || '<div style="color:var(--dim)">No operational memory available.</div>';
}

function renderAiOpsLifecycle(d) {
  const s = d?.task_lifecycle_summary || {};
  const rows = d?.task_lifecycle || [];
  const failed = Number(s.failed || 0);
  const waiting = Number(s.waiting_for_approval || 0);
  let html = `<div class="metric-grid" style="margin-bottom:12px">
    <div class="metric"><div class="val blue">${s.queued || 0}</div><div class="lbl">QUEUED</div></div>
    <div class="metric"><div class="val green">${s.running || 0}</div><div class="lbl">RUNNING</div></div>
    <div class="metric"><div class="val ${waiting > 0 ? 'amber' : ''}">${waiting}</div><div class="lbl">AWAITING</div></div>
    <div class="metric"><div class="val green">${s.completed || 0}</div><div class="lbl">COMPLETED</div></div>
    <div class="metric"><div class="val ${failed > 0 ? 'red' : ''}">${failed}</div><div class="lbl">FAILED</div></div>
    <div class="metric"><div class="val">${s.canceled || 0}</div><div class="lbl">CANCELED</div></div>
  </div>`;
  const failedRows = rows.filter(r => (r.status || '').toLowerCase() === 'failed').slice(0, 5);
  if (failedRows.length) {
    html += '<div style="color:var(--red);font-size:10px;margin-bottom:4px">FAILED TASKS</div>';
    html += failedRows.map(r => `<div class="feed-item"><div class="feed-time">${ts(r.created_at || r.at)} | ${esc(r.task_type || r.type || 'task')}</div><div class="feed-text red">${esc(r.error || r.reason || 'failed')}</div></div>`).join('');
  } else if (failed === 0) {
    html += '<div style="color:var(--green);font-size:10px">All tasks nominal — no failures detected.</div>';
  }
  return html;
}

function renderAiOpsTimeline(d) {
  const rows = d?.timeline || [];
  if (!rows.length) return '<div style="color:var(--dim)">No timeline events yet.</div>';
  return rows.slice(0, 40).map(r => {
    const st = (r.status || 'unknown').toLowerCase();
    const stCls = st === 'success' || st === 'completed' ? 'green' : st === 'failed' || st === 'error' ? 'red' : 'amber';
    const dotCls = st === 'success' || st === 'completed' ? 'dot-green' : st === 'failed' || st === 'error' ? 'dot-red' : 'dot-amber';
    return `<div class="feed-item"><div class="feed-time"><span class="dot ${dotCls}"></span>${ts(r.at)} | <span class="${stCls}">${esc(r.type || 'event')}</span> | ${esc(r.source || '?')}</div><div class="feed-text">${esc(r.event_type || '')}${r.status ? ' — ' + esc(st) : ''}</div></div>`;
  }).join('');
}

function renderAiOpsRouting(rows) {
  const list = rows || [];
  if (!list.length) return '<div style="color:var(--dim)">No routing preview available.</div>';
  return `<table class="data-table"><thead><tr><th>TASK</th><th>PROVIDER</th><th>MODEL</th><th>CTX</th></tr></thead><tbody>` +
    list.map(r => {
      const req = r.requested_task || 'unknown';
      const p = r.provider || 'unknown';
      const m = r.model || 'unknown';
      const c = Number(r.max_context || 0);
      return `<tr><td>${esc(req)}</td><td class="blue">${esc(p)}</td><td>${esc(m)}</td><td style="color:var(--dim)">${c.toLocaleString()}</td></tr>`;
    }).join('') +
    `</tbody></table>`;
}

function renderAiOpsWorkers(summary) {
  const s = summary || {};
  const counts = s.status_counts || {};
  const latest = s.latest || [];
  const total = Number(s.total_rows || 0);
  const _workerCls = (st) => {
    const s = (st || '').toLowerCase();
    if (s === 'running' || s === 'active') return { dot: 'dot-green', badge: 'badge-green', val: 'green' };
    if (s === 'idle' || s === 'stale') return { dot: 'dot-amber', badge: 'badge-amber', val: 'amber' };
    return { dot: 'dot-red', badge: 'badge-red', val: 'red' };
  };
  const countKeys = Object.keys(counts);
  const metricTiles = countKeys.map(k => {
    const n = Number(counts[k]);
    const cls = _workerCls(k).val;
    return `<div class="metric"><div class="val ${cls}">${n}</div><div class="lbl">${esc(k.toUpperCase())}</div></div>`;
  }).join('');
  let html = `<div class="metric-grid" style="margin-bottom:12px">${metricTiles}<div class="metric"><div class="val blue">${total}</div><div class="lbl">TOTAL</div></div></div>`;
  if (latest.length) {
    html += latest.slice(0, 6).map(w => {
      const wid = w.worker_id || 'unknown';
      const st = (w.status || 'unknown').toLowerCase();
      const cls = _workerCls(st);
      return `<div class="worker-card"><div class="worker-header"><span class="dot ${cls.dot}"></span><span class="worker-name">${esc(wid)}</span><span class="panel-badge ${cls.badge}" style="margin-left:auto">${esc(st.toUpperCase())}</span></div><div class="worker-meta">last seen: ${ts(w.last_seen_at)}</div></div>`;
    }).join('');
  } else {
    html += '<div style="color:var(--dim)">No worker heartbeat data available.</div>';
  }
  return html;
}

function renderAiOpsTelemetry(tel) {
  const t = tel || {};
  const retries = t.recent_retry_error_events || [];
  const usage = t.recent_model_usage_events || [];
  let html = `<div class="metric-grid" style="margin-bottom:12px">
    <div class="metric"><div class="val ${retries.length > 0 ? 'amber' : 'green'}">${retries.length}</div><div class="lbl">RETRY ERRORS</div></div>
    <div class="metric"><div class="val blue">${usage.length}</div><div class="lbl">MODEL CALLS</div></div>
  </div>`;
  if (retries.length) {
    html += '<div style="color:var(--amber);font-size:10px;margin-bottom:4px">RECENT RETRY ERRORS</div>';
    html += retries.slice(0, 5).map(e => {
      const payload = e.payload ? JSON.stringify(e.payload).slice(0, 80) : '';
      return `<div class="feed-item"><div class="feed-time">${ts(e.created_at || e.at)} | ${esc(e.event_source || e.source || 'system')}</div><div class="feed-text amber">${esc(e.event_type || 'retry_error')}${payload ? ': ' + esc(payload) : ''}</div></div>`;
    }).join('');
  }
  if (usage.length) {
    html += '<div style="color:var(--dim);font-size:10px;margin:8px 0 4px">RECENT MODEL USAGE</div>';
    html += usage.slice(0, 5).map(e => {
      const payload = e.payload ? JSON.stringify(e.payload).slice(0, 80) : '';
      return `<div class="feed-item"><div class="feed-time">${ts(e.created_at || e.at)} | ${esc(e.event_source || e.source || 'system')}</div><div class="feed-text">${esc(e.event_type || 'model_call')}${payload ? ': ' + esc(payload) : ''}</div></div>`;
    }).join('');
  }
  if (!retries.length && !usage.length) {
    html += '<div style="color:var(--dim)">No telemetry events recorded yet.</div>';
  }
  return html;
}

function renderAiOpsRoles(rows) {
  const list = rows || [];
  if (!list.length) return '<div style="color:var(--dim)">No role registry data available.</div>';
  return list.map(r => {
    const tasks = (r.allowed_task_types || []).join(', ') || 'none';
    const preview = r.routing_preview
      ? `${r.routing_preview.provider || '?'} / ${r.routing_preview.model || '?'} / ctx=${r.routing_preview.max_context || 0}`
      : `unavailable (${r.routing_error || 'unknown'})`;
    return `<div class="message-card">
      <div class="message-title">${esc(r.display_name || r.role_id || 'role')}</div>
      <div class="message-meta">role_id=${esc(r.role_id || '')} | risk=${esc(String(r.risk_level || 'unknown'))}</div>
      <div class="message-body">${esc(r.description || '')}</div>
      <div class="message-meta">allowed_tasks=${esc(tasks)}</div>
      <div class="message-meta">preferred_model_class=${esc(String(r.preferred_model_class || 'unknown'))} | routing=${esc(preview)}</div>
      <div class="message-meta">auto_execute=${esc(String(!!r.can_auto_execute))} | requires_admin_approval=${esc(String(!!r.requires_admin_approval))} | telegram_allowed=${esc(String(!!r.telegram_allowed))} (${esc(String(r.telegram_scope || 'none'))})</div>
    </div>`;
  }).join('');
}

function renderAiOpsSwarm(data) {
  const wrapper = (data || {}).scenario_preview || {};
  const scenario = wrapper.scenario || {};
  const sp = wrapper.swarm_preview || {};
  const seq = sp.task_sequence || [];
  if (!sp || !Object.keys(sp).length) {
    return '<div style="color:var(--dim)">No swarm plans yet.</div>';
  }
  const header = `<div class="audit-pre">scenario=${esc(String(scenario.display_name || scenario.scenario_id || 'unknown'))}
scenario_description=${esc(String(scenario.description || ''))}
initiating_role=${esc(String(sp.initiating_role || 'unknown'))}
objective=${esc(String(sp.objective || ''))}
delegated_roles=${esc(JSON.stringify(sp.delegated_roles || []))}
approval_required=${esc(String(!!sp.approval_required))}
risk/status=${esc(String(sp.status || 'unknown'))}
can_execute=${esc(String(!!sp.can_execute))}
execution_mode=${esc(String(sp.execution_mode || 'preview_only'))}
reason=${esc(String(sp.reason || ''))}</div>`;
  const steps = seq.length
    ? `<div class="audit-pre" style="margin-top:8px">` + seq.map(s =>
        `step=${s.step} role=${s.role_id} task=${s.task_type} model=${s.model_class} risk=${s.risk_level} status=${s.status} allowed=${s.allowed} reason=${s.reason}`
      ).join('\\n') + `</div>`
    : '<div style="color:var(--dim)">No task sequence generated.</div>';
  return header + steps;
}

function renderDevAgents(d) {
  const data = d?.data || d || {};
  const inventory = data.inventory || [];
  const handoffs = data.recent_handoffs || [];
  const pending = data.pending_handoff_count || 0;
  const cfg = data.config || {};

  // Safety status bar
  const execEnabled = !!data.execution_enabled;
  const dryRun = data.dry_run_mode !== false;
  const safeColor = execEnabled ? 'var(--red)' : 'var(--green)';
  let html = `<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
    <span class="panel-badge ${execEnabled ? 'badge-red' : 'badge-green'}">Execution: ${execEnabled ? 'ENABLED' : 'DISABLED'}</span>
    <span class="panel-badge ${dryRun ? 'badge-green' : 'badge-amber'}">Dry-run: ${dryRun ? 'ON' : 'OFF'}</span>
    <span class="panel-badge badge-blue">Approval Required: ${data.approval_required !== false ? 'YES' : 'NO'}</span>
    ${pending > 0 ? `<span class="panel-badge badge-amber">${pending} PENDING APPROVAL</span>` : ''}
  </div>`;

  if (!inventory.length) {
    return html + '<div style="color:var(--dim)">No agent inventory available.</div>';
  }

  // Agent cards
  html += '<div style="color:var(--dim);font-size:10px;margin-bottom:6px">DETECTED CLI AGENTS</div>';
  html += inventory.map(a => {
    const inst = !!a.installed;
    const dotCls = inst ? 'dot-green' : 'dot-red';
    const badgeCls = inst ? 'badge-green' : 'badge-red';
    const modeCls = a.effective_mode === 'read_only' ? 'badge-green' : a.effective_mode === 'dry_run' ? 'badge-blue' : 'badge-amber';
    const ver = a.version ? ` v${esc(a.version)}` : '';
    const bestFor = (a.best_for || []).slice(0, 3).join(', ');
    return `<div class="worker-card">
      <div class="worker-header">
        <span class="dot ${dotCls}"></span>
        <span class="worker-name">${esc(a.display_name || a.name)}</span>
        <span class="panel-badge ${badgeCls}" style="margin-left:auto">${inst ? 'INSTALLED' : 'MISSING'}</span>
      </div>
      <div class="worker-meta">${inst ? esc(a.path || '') + ver : 'not found in PATH'}</div>
      ${inst ? `<div class="worker-meta">mode: <span class="panel-badge ${modeCls}">${esc(a.effective_mode || 'unknown')}</span> | best for: ${esc(bestFor)}</div>` : ''}
    </div>`;
  }).join('');

  // Recent handoffs
  const recentHandoffs = handoffs.slice(0, 5);
  if (recentHandoffs.length) {
    html += '<div style="color:var(--dim);font-size:10px;margin:10px 0 4px">RECENT HANDOFFS</div>';
    html += recentHandoffs.map(h => {
      const st = (h.status || 'unknown');
      const stCls = st === 'completed' ? 'badge-green' : st === 'failed' ? 'badge-red' : 'badge-amber';
      return `<div class="feed-item">
        <div class="feed-time">${ts(h.created_at)} | ${esc(h.display_name || h.target_agent || '?')}</div>
        <div class="feed-text">${esc((h.goal || '').slice(0, 80))} <span class="panel-badge ${stCls}">${esc(st.toUpperCase())}</span></div>
      </div>`;
    }).join('');
  } else {
    html += '<div style="color:var(--dim);font-size:10px;margin-top:8px">No handoffs yet — use Telegram: "ask gemini to review..."</div>';
  }

  return html;
}

async function loadDevAgentsPanel() {
  try {
    const token = aiOpsAdminToken();
    const sep = token ? '?admin_token=' + encodeURIComponent(token) : '';
    const d = await aiOpsGet('/api/admin/ai-operations/dev-agents' + (token ? '?admin_token=' + encodeURIComponent(token) : ''));
    document.getElementById('aiops-dev-agents-panel').innerHTML = renderDevAgents(d);
  } catch(e) {
    document.getElementById('aiops-dev-agents-panel').innerHTML = `<div class="red">Dev Agent Bridge unavailable: ${esc(e.message)}</div><div style="color:var(--dim)">Fallback mode.</div>`;
  }
}

function renderApprovalQueue(data) {
  const rows = (data || {}).planned_runs || [];
  if (!rows.length) return '<div style="color:var(--dim)">No pending approvals.</div>';
  return rows.map(r => `
    <div class="message-card">
      <div class="message-title">${esc(r.planned_run_id || 'planned_run')}</div>
      <div class="message-meta">scenario=${esc(r.scenario_id || 'unknown')} | role=${esc(r.initiating_role || 'unknown')} | risk=${esc(String(r.risk_level || 'unknown'))}</div>
      <div class="message-meta">status=${esc(String(r.approval_status || 'planned'))} | requested_by=${esc(r.requested_by || 'operator')} | created_at=${esc(ts(r.created_at))}</div>
      <div class="message-meta">approval_required=${esc(String(!!r.approval_required))} | can_execute=${esc(String(!!r.can_execute))} | execution_mode=${esc(String(r.execution_mode || 'preview_only'))}</div>
      <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
        <button class="refresh-btn" onclick="approvePlannedRun('${esc(r.planned_run_id || '')}')">APPROVE</button>
        <button class="refresh-btn" onclick="rejectPlannedRun('${esc(r.planned_run_id || '')}')">REJECT</button>
        <button class="refresh-btn" onclick="cancelPlannedRun('${esc(r.planned_run_id || '')}')">CANCEL</button>
      </div>
    </div>
  `).join('');
}

async function loadApprovalQueue() {
  try {
    const q = await aiOpsGet('/api/admin/ai-ops/planned-runs');
    const payload = q.data || q;
    document.getElementById('aiops-approval-panel').innerHTML = renderApprovalQueue(payload);
    const fb = document.getElementById('aiops-approval-feedback');
    if (fb) fb.textContent = `queue updated: ${ts(q.timestamp || q.updated_at)}`;
  } catch (e) {
    const msg = `<div class="red">Approval queue unavailable: ${esc(e.message)}</div><div style="color:var(--dim)">Fallback mode active.</div>`;
    document.getElementById('aiops-approval-panel').innerHTML = msg;
  }
}

async function createPlannedRunFromScenario() {
  const fb = document.getElementById('aiops-approval-feedback');
  try {
    const scenarioId = (document.getElementById('aiops-swarm-scenario')?.value || 'funding_onboarding');
    const res = await aiOpsPost('/api/admin/ai-ops/planned-run/create', { scenario_id: scenarioId, requested_by: aiOpsAdminActor() || 'operator' });
    if (fb) fb.textContent = `planned run created: ${res?.planned_run?.planned_run_id || 'ok'}`;
    await loadApprovalQueue();
  } catch (e) {
    if (fb) fb.textContent = `create failed: ${e.message}`;
  }
}

async function approvePlannedRun(plannedRunId) {
  const fb = document.getElementById('aiops-approval-feedback');
  try {
    await aiOpsPost('/api/admin/ai-ops/planned-run/approve', { planned_run_id: plannedRunId });
    if (fb) fb.textContent = `approved: ${plannedRunId}`;
    await loadApprovalQueue();
  } catch (e) {
    if (fb) fb.textContent = `approve failed: ${e.message}`;
  }
}

async function rejectPlannedRun(plannedRunId) {
  const fb = document.getElementById('aiops-approval-feedback');
  try {
    await aiOpsPost('/api/admin/ai-ops/planned-run/reject', { planned_run_id: plannedRunId, reason: 'rejected in AI OPS review' });
    if (fb) fb.textContent = `rejected: ${plannedRunId}`;
    await loadApprovalQueue();
  } catch (e) {
    if (fb) fb.textContent = `reject failed: ${e.message}`;
  }
}

async function cancelPlannedRun(plannedRunId) {
  const fb = document.getElementById('aiops-approval-feedback');
  try {
    await aiOpsPost('/api/admin/ai-ops/planned-run/cancel', { planned_run_id: plannedRunId, reason: 'cancelled in AI OPS review' });
    if (fb) fb.textContent = `cancelled: ${plannedRunId}`;
    await loadApprovalQueue();
  } catch (e) {
    if (fb) fb.textContent = `cancel failed: ${e.message}`;
  }
}

async function loadSelectedSwarmScenario() {
  try {
    const sel = document.getElementById('aiops-swarm-scenario');
    const scenarioId = (sel?.value || 'funding_onboarding');
    const data = await aiOpsGet(`/api/admin/ai-ops/swarm-scenario-preview?scenario_id=${encodeURIComponent(scenarioId)}`);
    document.getElementById('aiops-swarm-panel').innerHTML = renderAiOpsSwarm(data.data || data);
  } catch (e) {
    const msg = `<div class="red">Swarm scenario unavailable: ${esc(e.message)}</div><div style="color:var(--dim)">Fallback mode active.</div>`;
    document.getElementById('aiops-swarm-panel').innerHTML = msg;
  }
}

function aiOpsAdminToken() {
  return (document.getElementById('aiops-admin-token')?.value || '').trim();
}

function aiOpsAdminActor() {
  return (document.getElementById('aiops-admin-actor')?.value || '').trim();
}

async function aiOpsGet(url) {
  const token = aiOpsAdminToken();
  const sep = url.includes('?') ? '&' : '?';
  const finalUrl = token ? `${url}${sep}admin_token=${encodeURIComponent(token)}` : url;
  const r = await fetch(finalUrl);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || 'Request failed');
  return data;
}

async function aiOpsPost(url, body) {
  const headers = { 'Content-Type': 'application/json' };
  const token = aiOpsAdminToken();
  if (token) headers['X-Admin-Token'] = token;
  const actor = aiOpsAdminActor();
  if (actor) headers['X-Admin-Actor'] = actor;
  const r = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || 'Request failed');
  return data;
}

async function loadAiOpsPage() {
  const errMsg = (label) => `<div class="red">${esc(label)} unavailable</div><div style="color:var(--dim)">Fallback mode active.</div>`;
  const safe = (p) => p.catch(e => ({ _error: e.message }));

  const [d, overview, session, tasks, timeline, roleData, scenarios, swarm, approvals] = await Promise.all([
    safe(aiOpsGet('/api/admin/ai-ops/status')),
    safe(aiOpsGet('/api/admin/ai-operations/overview')),
    safe(aiOpsGet('/api/admin/ai-operations/session')),
    safe(aiOpsGet('/api/admin/ai-operations/tasks')),
    safe(aiOpsGet('/api/admin/ai-operations/timeline')),
    safe(aiOpsGet('/api/admin/ai-ops/roles')),
    safe(aiOpsGet('/api/admin/ai-ops/swarm-scenarios')),
    safe(aiOpsGet('/api/admin/ai-ops/swarm-scenario-preview?scenario_id=funding_onboarding')),
    safe(aiOpsGet('/api/admin/ai-ops/planned-runs')),
  ]);

  const statusData = (!d._error) ? (d.data || d) : null;
  const overviewData = (!overview._error) ? (overview.data || overview) : null;
  const sessionData = (!session._error) ? (session.data || session) : null;
  const tasksData = (!tasks._error) ? (tasks.data || tasks) : null;
  const timelineData = (!timeline._error) ? (timeline.data || timeline) : null;
  const roleRows = (!roleData._error) ? ((roleData.data || roleData).roles || []) : [];
  const scenarioRows = (!scenarios._error) ? ((scenarios.data || scenarios).scenarios || []) : [];

  document.getElementById('aiops-session-panel').innerHTML = sessionData ? renderAiOpsSession(sessionData) : errMsg('Session');
  document.getElementById('aiops-memory-panel').innerHTML = overviewData ? renderAiOpsMemory(overviewData) : errMsg('Memory');
  document.getElementById('aiops-config-panel').innerHTML = statusData ? renderAiOpsConfig(statusData) : errMsg('Config');
  document.getElementById('aiops-routing-panel').innerHTML = statusData ? renderAiOpsRouting(statusData.routing_preview) : errMsg('Routing');
  document.getElementById('aiops-workers-panel').innerHTML = statusData ? renderAiOpsWorkers(statusData.worker_health_summary) : errMsg('Workers');
  document.getElementById('aiops-lifecycle-panel').innerHTML = tasksData ? renderAiOpsLifecycle(tasksData) : errMsg('Lifecycle');
  document.getElementById('aiops-telemetry-panel').innerHTML = statusData ? renderAiOpsTelemetry(statusData.telemetry) : errMsg('Telemetry');
  document.getElementById('aiops-roles-panel').innerHTML = renderAiOpsRoles(roleRows);
  document.getElementById('aiops-timeline-panel').innerHTML = timelineData ? renderAiOpsTimeline(timelineData) : errMsg('Timeline');

  // Dev Agent Bridge panel — loaded independently (has its own cache TTL)
  loadDevAgentsPanel();

  const sel = document.getElementById('aiops-swarm-scenario');
  if (sel && scenarioRows.length) {
    sel.innerHTML = scenarioRows.map(r => `<option value="${esc(r.scenario_id)}">${esc(r.display_name)}</option>`).join('');
  }
  if (!swarm._error) {
    document.getElementById('aiops-swarm-panel').innerHTML = renderAiOpsSwarm(swarm.data || swarm);
  }
  if (!approvals._error) {
    const approvalsPayload = approvals.data || approvals;
    document.getElementById('aiops-approval-panel').innerHTML = renderApprovalQueue(approvalsPayload);
    const fb = document.getElementById('aiops-approval-feedback');
    if (fb) fb.textContent = `queue updated: ${ts(approvals.timestamp || approvals.updated_at)}`;
  }

  if (statusData) {
    const tg = statusData.telegram_mode || {};
    const enabledEl = document.getElementById('aiops-flag-enabled');
    const manualEl = document.getElementById('aiops-flag-manual');
    const autoEl = document.getElementById('aiops-flag-auto');
    if (enabledEl) enabledEl.checked = !!tg.enabled;
    if (manualEl) manualEl.checked = !!tg.manual_only;
    if (autoEl) autoEl.checked = !!tg.auto_reports_enabled;
    const fb = document.getElementById('aiops-controls-feedback');
    if (fb) fb.textContent = `last updated: ${ts(d.timestamp || d.updated_at)} | reports: email only | execution: disabled`;
  }
}

async function saveAiOpsTelegramMode() {
  const fb = document.getElementById('aiops-controls-feedback');
  if (fb) fb.textContent = 'saving...';
  try {
    const payload = {
      telegram_enabled: !!document.getElementById('aiops-flag-enabled')?.checked,
      telegram_manual_only: !!document.getElementById('aiops-flag-manual')?.checked,
      telegram_auto_reports_enabled: !!document.getElementById('aiops-flag-auto')?.checked,
    };
    const res = await aiOpsPost('/api/admin/ai-ops/telegram-mode', payload);
    if (fb) fb.textContent = `saved @ ${ts(res.updated_at)} — restart telegram service to apply changes.`;
    await loadAiOpsPage();
  } catch (e) {
    if (fb) fb.textContent = `save failed: ${e.message}`;
  }
}

// ── Page routing ──
function loadPage(name) {
  const map = {
    overview:   () => { loadAgents(); loadSentiment(); loadResearchFeed(); loadAlerts(); },
    research:   loadResearchPage,
    signals:    loadSignalsPage,
    leads:      loadLeadsPage,
    marketing:  loadMarketingPage,
    reputation: loadReputationPage,
    health:     loadHealth,
    scheduler:  loadSchedulerPage,
    drafts:     loadDraftsPage,
    prelaunch:  loadPrelaunchPage,
    growth:     loadGrowthPage,
    messages:   loadMessagesPage,
    approvals:  loadApprovalsPage,
    mission:    loadMissionControlPage,
    aiops:      loadAiOpsPage,
  };
  if (map[name]) map[name]();
}

async function loadAll() { loadPage('overview'); }

if (window.location.pathname === '/admin/ai-operations') {
  setTimeout(() => {
    const aiopsTab = [...document.querySelectorAll('.tab')].find(el => el.textContent.trim() === 'AI OPS');
    if (aiopsTab) aiopsTab.click();
  }, 0);
}

// ── Auto-refresh every 30s ──
loadAll();
bindTabClicks();
setInterval(loadAll, 30000);
</script>
</body>
</html>"""


@app.route("/api/route-job", methods=["POST"])
def api_route_job():
    """
    Submit a task for CEO auto-routing.

    Body (JSON): {"message": "...", "channel": "admin_portal"}
    Returns: {"event_id": "uuid", "status": "pending"} or {"error": "..."}
    """
    from flask import request as flask_request
    from lib.event_intake import submit_ceo_route_request

    try:
        body    = flask_request.get_json(silent=True) or {}
        message = (body.get("message") or "").strip()
        if not message:
            return jsonify({"error": "message is required"}), 400

        result = submit_ceo_route_request(
            message=message,
            source="admin_portal",
            channel=body.get("channel", "control_center"),
            client_id=body.get("client_id"),
            metadata=body.get("metadata"),
        )
        status_code = 400 if "error" in result else 200
        return jsonify(result), status_code
    except Exception as exc:
        logger.exception("route-job error")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/drafts")
def api_drafts():
    """
    List workflow_outputs rows for CEO-routed drafts.

    Query params:
        limit   (int, default 20)
        role    (str, optional — filter by subject_type)
        status  (str, optional, default pending_review; use "all" for all review states)
    """
    from flask import request as flask_request
    import urllib.request as _urllib_req

    limit = flask_request.args.get("limit", 20, type=int)
    role  = flask_request.args.get("role", "")
    status = (flask_request.args.get("status", "pending_review") or "pending_review").strip()

    def _fetch_drafts():
        supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            return {"error": "Supabase not configured"}

        filters = (
            "workflow_outputs"
            "?workflow_type=eq.ceo_routed_draft"
            f"&order=created_at.desc"
            f"&limit={limit}"
            "&select=id,summary,status,created_at,payload"
        )
        if status != "all":
            filters += f"&status=eq.{status}"

        url = f"{supabase_url}/rest/v1/{filters}"
        headers = {
            "apikey":        supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type":  "application/json",
        }
        req = _urllib_req.Request(url, headers=headers)
        try:
            import json as _json
            with _urllib_req.urlopen(req, timeout=10) as r:
                rows = _json.loads(r.read()) or []
            drafts = [_normalize_workflow_output_row(row) for row in rows]
            if role:
                drafts = [row for row in drafts if row.get("subject_type") == role]
            return {"drafts": drafts, "count": len(drafts)}
        except Exception as exc:
            return {"error": str(exc), "drafts": []}

    return jsonify(_safe(_fetch_drafts))


@app.route("/api/drafts/<draft_id>", methods=["PATCH"])
def api_update_draft(draft_id: str):
    """
    Update a CEO-routed draft review status.

    Body (JSON):
      {"action": "approve" | "request_changes", "reviewed_by": "...", "note": "..."}
    """
    from flask import request as flask_request
    import urllib.request as _urllib_req
    import urllib.parse as _urllib_parse

    body = flask_request.get_json(silent=True) or {}
    action = (body.get("action") or "approve").strip().lower()
    reviewed_by = (body.get("reviewed_by") or "admin_portal").strip() or "admin_portal"
    note = (body.get("note") or "").strip()

    action_map = {
        "approve": ("approved", "ready"),
        "request_changes": ("revision_requested", "draft"),
        "reject": ("rejected", "draft"),
    }
    if action not in action_map:
        return jsonify({"error": "action must be 'approve', 'request_changes', or 'reject'"}), 400

    status, _ = action_map[action]

    def _update_draft():
        supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            return {"error": "Supabase not configured"}

        encoded_id = _urllib_parse.quote(str(draft_id), safe="")
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }

        fetch_url = (
            f"{supabase_url}/rest/v1/workflow_outputs"
            f"?id=eq.{encoded_id}"
            f"&workflow_type=eq.ceo_routed_draft"
            f"&select=id,status,payload"
            f"&limit=1"
        )
        fetch_req = _urllib_req.Request(fetch_url, headers=headers)
        with _urllib_req.urlopen(fetch_req, timeout=10) as response:
            rows = json.loads(response.read()) or []

        if not rows:
            return {"error": "draft not found"}, 404

        draft = rows[0]
        payload = draft.get("payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {"payload_text": payload}

        review = payload.get("review") or {}
        if not isinstance(review, dict):
            review = {"previous_review": str(review)}

        review.update({
            "action": action,
            "reviewed_by": reviewed_by,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "note": note,
        })
        payload["review"] = review

        patch_body = {
            "status": status,
            "payload": payload,
        }
        patch_req = _urllib_req.Request(
            f"{supabase_url}/rest/v1/workflow_outputs?id=eq.{encoded_id}&workflow_type=eq.ceo_routed_draft",
            data=json.dumps(patch_body).encode(),
            headers={**headers, "Prefer": "return=representation"},
            method="PATCH",
        )
        with _urllib_req.urlopen(patch_req, timeout=10) as response:
            updated_rows = json.loads(response.read()) or []

        return {
            "draft_id": draft_id,
            "action": action,
            "status": status,
            "updated": bool(updated_rows),
            "draft": _normalize_workflow_output_row(updated_rows[0]) if updated_rows else None,
        }

    result = _safe(_update_draft)
    if isinstance(result, tuple):
        payload, status_code = result
        return jsonify(payload), status_code
    return jsonify(result)


# ── Readiness Engine Endpoints ────────────────────────────────────────────────

@app.route("/api/readiness/profile")
def api_readiness_profile():
    from flask import request as flask_request
    from readiness_engine.service import build_readiness_snapshot
    user_id = flask_request.args.get("user_id", "").strip()
    tenant_id = flask_request.args.get("tenant_id", "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    return jsonify(_safe(lambda: build_readiness_snapshot(user_id, tenant_id)))


@app.route("/api/readiness/business-foundation", methods=["POST"])
def api_readiness_business_foundation():
    from flask import request as flask_request
    from readiness_engine.service import save_business_foundation
    body = flask_request.get_json(silent=True) or {}
    user_id = body.get("user_id", "").strip()
    tenant_id = body.get("tenant_id", "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    data = {k: v for k, v in body.items() if k not in {"user_id", "tenant_id"}}
    return jsonify(save_business_foundation(user_id, tenant_id, data))


@app.route("/api/readiness/credit-profile", methods=["POST"])
def api_readiness_credit_profile():
    from flask import request as flask_request
    from readiness_engine.service import save_credit_profile
    body = flask_request.get_json(silent=True) or {}
    user_id = body.get("user_id", "").strip()
    tenant_id = body.get("tenant_id", "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    data = {k: v for k, v in body.items() if k not in {"user_id", "tenant_id"}}
    return jsonify(save_credit_profile(user_id, tenant_id, data))


@app.route("/api/readiness/banking", methods=["POST"])
def api_readiness_banking():
    from flask import request as flask_request
    from readiness_engine.service import save_banking_profile
    body = flask_request.get_json(silent=True) or {}
    user_id = body.get("user_id", "").strip()
    tenant_id = body.get("tenant_id", "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    data = {k: v for k, v in body.items() if k not in {"user_id", "tenant_id"}}
    return jsonify(save_banking_profile(user_id, tenant_id, data))


@app.route("/api/readiness/grants", methods=["POST"])
def api_readiness_grants():
    from flask import request as flask_request
    from readiness_engine.service import save_grant_profile
    body = flask_request.get_json(silent=True) or {}
    user_id = body.get("user_id", "").strip()
    tenant_id = body.get("tenant_id", "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    data = {k: v for k, v in body.items() if k not in {"user_id", "tenant_id"}}
    return jsonify(save_grant_profile(user_id, tenant_id, data))


@app.route("/api/readiness/trading", methods=["POST"])
def api_readiness_trading():
    from flask import request as flask_request
    from readiness_engine.service import save_trading_profile
    body = flask_request.get_json(silent=True) or {}
    user_id = body.get("user_id", "").strip()
    tenant_id = body.get("tenant_id", "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    data = {k: v for k, v in body.items() if k not in {"user_id", "tenant_id"}}
    return jsonify(save_trading_profile(user_id, tenant_id, data))


@app.route("/api/readiness/tasks")
def api_readiness_tasks():
    from flask import request as flask_request
    from readiness_engine.service import get_readiness_tasks
    user_id = flask_request.args.get("user_id", "").strip()
    tenant_id = flask_request.args.get("tenant_id", "").strip() or None
    status = flask_request.args.get("status", "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    return jsonify(get_readiness_tasks(user_id, tenant_id, status))


@app.route("/api/readiness/tasks/<task_id>/complete", methods=["POST"])
def api_readiness_task_complete(task_id: str):
    from readiness_engine.service import complete_task
    return jsonify(complete_task(task_id))


@app.route("/api/readiness/recalculate", methods=["POST"])
def api_readiness_recalculate():
    from flask import request as flask_request
    from readiness_engine.service import recalculate_readiness
    body = flask_request.get_json(silent=True) or {}
    user_id = body.get("user_id", "").strip()
    tenant_id = body.get("tenant_id", "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    return jsonify(recalculate_readiness(user_id, tenant_id))


# ── Funding Strategy Endpoints ────────────────────────────────────────────────

@app.route("/api/funding/strategy")
def api_funding_strategy():
    from flask import request as flask_request
    from funding_engine.strategy_engine import get_active_strategy
    user_id = (flask_request.args.get("user_id") or "").strip()
    tenant_id = (flask_request.args.get("tenant_id") or "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    strategy = get_active_strategy(user_id, tenant_id)
    if not strategy:
        return jsonify({"strategy": None, "message": "No active strategy found. Run a recommendation refresh to generate one."}), 200
    return jsonify({
        "strategy_status": strategy.get("strategy_status"),
        "strategy_summary": strategy.get("strategy_summary"),
        "next_best_action": strategy.get("next_best_action"),
        "current_phase": strategy.get("current_phase"),
        "estimated_funding_low": strategy.get("estimated_funding_low"),
        "estimated_funding_high": strategy.get("estimated_funding_high"),
        "application_step_count": len(strategy.get("application_sequence") or []),
        "generated_at": strategy.get("generated_at"),
        "updated_at": strategy.get("updated_at"),
    })


@app.route("/api/funding/strategy/full")
def api_funding_strategy_full():
    from flask import request as flask_request
    from funding_engine.strategy_engine import get_active_strategy
    user_id = (flask_request.args.get("user_id") or "").strip()
    tenant_id = (flask_request.args.get("tenant_id") or "").strip() or None
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    return jsonify(get_active_strategy(user_id, tenant_id) or {})


@app.route("/api/funding/strategy/refresh", methods=["POST"])
def api_funding_strategy_refresh():
    from flask import request as flask_request
    from funding_engine.service import build_funding_snapshot, generate_user_recommendations
    from funding_engine.strategy_engine import build_and_persist_strategy
    body = flask_request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    tenant_id = (body.get("tenant_id") or "").strip() or None
    force = bool(body.get("force", False))
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    data = generate_user_recommendations(user_id=user_id, tenant_id=tenant_id)
    snap = data.get("snapshot") or {}
    result = build_and_persist_strategy(
        user_id=user_id,
        tenant_id=tenant_id,
        user_profile=snap.get("user_profile") or {},
        readiness_profile=snap.get("readiness") or {},
        recommendations=data.get("recommendations") or [],
        relationships=snap.get("banking_relationships") or [],
        force=force,
    )
    return jsonify({
        "persisted": result.get("persisted"),
        "action": result.get("action"),
        "next_best_action": (result.get("strategy") or {}).get("next_best_action"),
        "current_phase": (result.get("strategy") or {}).get("current_phase"),
        "estimated_funding_low": (result.get("strategy") or {}).get("estimated_funding_low"),
        "estimated_funding_high": (result.get("strategy") or {}).get("estimated_funding_high"),
    })


@app.route("/api/trading/approval-queue")
def api_trading_approval_queue():
    from scripts.prelaunch_utils import rest_select
    # Proposals queued for auto-execution (not yet executed/blocked/rejected)
    pending = _safe(lambda: rest_select(
        "reviewed_signal_proposals"
        "?select=id,symbol,side,timeframe,strategy_id,entry_price,stop_loss,take_profit,ai_confidence,status,risk_notes,created_at"
        "&status=not.in.(executed,blocked,rejected)"
        "&order=created_at.desc&limit=20"
    ) or [])
    # Recently actioned (executed, blocked, rejected)
    recent = _safe(lambda: rest_select(
        "reviewed_signal_proposals"
        "?select=id,symbol,side,timeframe,ai_confidence,status,risk_notes,created_at"
        "&status=in.(executed,blocked,rejected)"
        "&order=created_at.desc&limit=10"
    ) or [])
    # Pipeline view: enriched signals waiting for signal_poller review
    pipeline = _safe(lambda: rest_select(
        "tv_normalized_signals"
        "?select=id,symbol,side,timeframe,status,created_at"
        "&status=not.in.(skipped,reviewed,rejected)"
        "&order=created_at.desc&limit=10"
    ) or [])
    return jsonify({"pending": pending, "recent": recent, "pipeline": pipeline})


@app.route("/api/trading/approval-queue/<item_id>", methods=["PATCH"])
def api_update_approval_queue(item_id: str):
    from flask import request as flask_request
    from scripts.prelaunch_utils import supabase_request

    body = flask_request.get_json(silent=True) or {}
    action = (body.get("action") or "").strip().lower()
    if action not in {"approve", "block"}:
        return jsonify({"error": "action must be approve or block"}), 400

    # "approve" = leave as pending (auto_executor will run it)
    # "block"   = set status=blocked so auto_executor skips it
    new_status = "pending" if action == "approve" else "blocked"
    try:
        rows, _ = supabase_request(
            f"reviewed_signal_proposals?id=eq.{item_id}",
            method="PATCH",
            body={"status": new_status},
            prefer="return=representation",
            timeout=10,
        )
        row = (rows or [None])[0]
        if not row:
            return jsonify({"ok": False, "error": "proposal not found"}), 404
        return jsonify({"ok": True, "id": item_id, "status": new_status, "row": row})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/trading/status")
def api_trading_status():
    from scripts.prelaunch_utils import rest_select

    status_file = Path(__file__).parent.parent / "logs" / "trading_engine_status.json"
    engine_status = {}
    if status_file.exists():
        try:
            engine_status = json.loads(status_file.read_text())
        except Exception:
            pass

    recent_trades = _safe(lambda: rest_select(
        "paper_trading_journal_entries"
        "?select=id,symbol,asset_class,thesis,entry_status,stop_loss,target_price,opened_at,tags"
        "&order=opened_at.desc&limit=20"
    ) or [])

    signal_review_log = _safe(lambda: (
        Path(__file__).parent.parent / "logs" / "signal_review.log"
    ).read_text().splitlines()[-10:] if (
        Path(__file__).parent.parent / "logs" / "signal_review.log"
    ).exists() else [])

    return jsonify({
        "engine": {
            "stage": engine_status.get("stage"),
            "dry_run": engine_status.get("dry_run"),
            "live_trading": engine_status.get("live_trading"),
            "auto_trading": engine_status.get("auto_trading"),
            "broker_type": engine_status.get("broker_type"),
            "broker_connected": engine_status.get("broker_connected"),
            "active_positions": engine_status.get("active_positions", 0),
            "signals_processed": engine_status.get("signals_processed", 0),
            "updated_at": engine_status.get("updated_at"),
            "last_signal": engine_status.get("last_signal"),
            "last_result": engine_status.get("last_result"),
        },
        "recent_paper_trades": recent_trades,
        "signal_review_tail": signal_review_log,
    })


@app.route("/")
def index():
    response = make_response(render_template_string(TERMINAL_HTML))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=4000)
    p.add_argument("--debug", action="store_true")
    args = p.parse_args()
    logger.info(f"🚀 Nexus Control Center starting on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
