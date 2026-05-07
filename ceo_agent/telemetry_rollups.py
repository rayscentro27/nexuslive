"""Telemetry capture + daily rollups for Hermes executive intelligence."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")


def _sb_get(path: str) -> list:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _sb_post(path: str, body: dict) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=12)
        return True
    except Exception:
        return False


def _exists(event_type: str, classification: str) -> bool:
    rows = _sb_get(
        "hermes_aggregates?select=id"
        f"&event_source=eq.executive_telemetry&event_type=eq.{event_type}"
        f"&classification=eq.{urllib.parse.quote(classification)}&limit=1"
    )
    return bool(rows)


def _record(event_type: str, classification: str, summary: str, payload: dict | None = None) -> bool:
    if _exists(event_type, classification):
        return True
    text = summary[:500]
    if payload:
        payload_text = json.dumps(payload, default=str)[:3000]
        text = f"{text}\n{payload_text}"
    return _sb_post(
        "hermes_aggregates",
        {
            "event_source": "executive_telemetry",
            "event_type": event_type,
            "classification": classification,
            "aggregated_summary": text,
            "alert_sent": False,
        },
    )


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _result_quality(pnl: float, risk_reward: float, drawdown: float) -> str:
    if pnl > 0 and risk_reward >= 2.0 and drawdown >= -1.5:
        return "high_quality"
    if pnl >= 0 and risk_reward >= 1.3 and drawdown >= -3.0:
        return "acceptable"
    return "needs_improvement"


def capture_trading_outcomes(days: int = 30) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = _sb_get(
        "trade_logs?select=*"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=500"
    )
    captured = 0
    completed = []
    for row in rows:
        status = str(row.get("status") or "").lower()
        if status and status not in {"closed", "completed", "filled", "win", "loss"}:
            continue
        trade_id = str(row.get("id") or "")
        if not trade_id:
            continue
        pnl = _safe_float(row.get("pnl"), 0.0)
        entry = _safe_float(row.get("entry_price"), 0.0)
        stop = _safe_float(row.get("stop_loss"), 0.0)
        target = _safe_float(row.get("take_profit"), 0.0)
        risk = abs(entry - stop)
        reward = abs(target - entry)
        rr = reward / risk if risk > 0 else 0.0
        drawdown = _safe_float(row.get("drawdown"), min(pnl, 0.0))
        win_loss = "win" if pnl > 0 else "loss" if pnl < 0 else "flat"
        gross_win = max(pnl, 0.0)
        gross_loss = abs(min(pnl, 0.0))
        profit_factor = gross_win / max(gross_loss, 1e-9) if gross_loss else (gross_win if gross_win else 0.0)
        payload = {
            "strategy_id": row.get("strategy_id") or "unattributed",
            "entry_reason": row.get("entry_reason") or row.get("signal_reason") or "not_captured",
            "exit_reason": row.get("exit_reason") or row.get("close_reason") or "not_captured",
            "timeframe": row.get("timeframe") or "not_captured",
            "market_conditions": row.get("market_conditions") or row.get("session") or "not_captured",
            "win_loss": win_loss,
            "drawdown": round(drawdown, 4),
            "profit_factor": round(profit_factor, 4),
            "risk_reward": round(rr, 4),
            "execution_timestamp": row.get("created_at") or datetime.now(timezone.utc).isoformat(),
            "result_quality": _result_quality(pnl, rr, drawdown),
            "symbol": row.get("symbol"),
            "pnl": pnl,
        }
        if _record("trading_outcome", f"trade:{trade_id}", f"trade outcome {trade_id[:8]} {win_loss}", payload):
            captured += 1
        completed.append(payload)
    return {"rows_scanned": len(rows), "completed_trades": len(completed), "captured_events": captured, "items": completed}


def capture_business_outcomes(days: int = 30) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = _sb_get(
        "business_opportunities?select=*"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=250"
    )
    captured = 0
    items = []
    for row in rows:
        rid = str(row.get("id") or "")
        if not rid:
            continue
        desc = str(row.get("description") or "").lower()
        launched = bool(row.get("launched") or str(row.get("status") or "").lower() in {"launched", "live", "active"})
        website_created = bool(row.get("website_created") or any(k in desc for k in ("landing page", "website", "domain")))
        lead_activity = bool(row.get("lead_generation_activity") or any(k in desc for k in ("lead", "inbound", "outreach")))
        monetization_activity = bool(row.get("monetization_activity") or any(k in desc for k in ("revenue", "pricing", "checkout", "sales")))
        startup_cost = _safe_float(row.get("startup_cost"), 0.0)
        estimated_roi = _safe_float(row.get("estimated_roi") or row.get("roi_estimate"), 0.0)
        actual_roi = _safe_float(row.get("actual_roi"), 0.0)
        automation_burden = _safe_float(row.get("automation_burden"), 0.0)
        recurring_revenue_potential = _safe_float(row.get("recurring_revenue_potential"), 0.0)
        payload = {
            "title": row.get("title") or "Untitled",
            "opportunity_type": row.get("opportunity_type") or row.get("niche") or "general",
            "launched": launched,
            "website_created": website_created,
            "lead_generation_activity": lead_activity,
            "monetization_activity": monetization_activity,
            "estimated_roi": estimated_roi,
            "actual_roi": actual_roi,
            "startup_cost": startup_cost,
            "automation_burden": automation_burden,
            "recurring_revenue_potential": recurring_revenue_potential,
            "operator_decision": row.get("operator_decision") or "pending",
        }
        if _record("business_outcome", f"business:{rid}", f"business outcome {rid[:8]}", payload):
            captured += 1
        items.append(payload)
    return {"rows_scanned": len(rows), "captured_events": captured, "items": items}


def capture_recommendation_outcomes(days: int = 60) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = _sb_get(
        "owner_approval_queue?select=*"
        f"&action_type=eq.chief_of_staff_recommendation&created_at=gt.{urllib.parse.quote(cutoff)}"
        "&order=created_at.desc&limit=400"
    )
    captured = 0
    items = []
    for row in rows:
        rid = str(row.get("id") or "")
        if not rid:
            continue
        payload = row.get("payload") or {}
        details = payload.get("details") or {}
        status = str(row.get("status") or "pending").lower()
        quality = "pending"
        if status in {"approved", "completed", "success", "succeeded"}:
            quality = "positive"
        elif status in {"rejected", "failed", "error"}:
            quality = "negative"
        item = {
            "recommendation_category": payload.get("recommendation_type") or "unknown",
            "approval_status": "approved" if status in {"approved", "completed", "success", "succeeded"} else "not_approved" if status in {"rejected"} else "pending",
            "execution_status": status,
            "outcome_quality": quality,
            "roi_estimate": _safe_float(details.get("expected_roi"), 0.0),
            "completion_timestamp": row.get("reviewed_at") or row.get("updated_at") or row.get("created_at"),
            "repeatability_signal": details.get("historical_performance_score") or 0.0,
            "title": payload.get("title") or row.get("description") or "Untitled",
        }
        if _record("recommendation_outcome", f"recommendation:{rid}", f"recommendation outcome {rid[:8]} {status}", item):
            captured += 1
        items.append(item)
    return {"rows_scanned": len(rows), "captured_events": captured, "items": items}


def _rollup_classification() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def daily_trading_rollup(trading_items: list[dict]) -> str:
    wins = sum(1 for i in trading_items if i.get("win_loss") == "win")
    losses = sum(1 for i in trading_items if i.get("win_loss") == "loss")
    quality = sum(1 for i in trading_items if i.get("result_quality") == "high_quality")
    avg_rr = round(sum(_safe_float(i.get("risk_reward"), 0.0) for i in trading_items) / max(len(trading_items), 1), 2)
    if not trading_items:
        return "Trading rollup: insufficient outcomes; collect 20+ completed trades with entry/exit reasons and timeframe metadata."
    return f"Trading rollup: trades={len(trading_items)} wins={wins} losses={losses} high_quality={quality} avg_rr={avg_rr}."


def daily_business_rollup(business_items: list[dict]) -> str:
    if not business_items:
        return "Business rollup: insufficient outcomes; capture launch status, website creation, lead activity, and ROI deltas."
    launched = sum(1 for i in business_items if i.get("launched"))
    websites = sum(1 for i in business_items if i.get("website_created"))
    monetized = sum(1 for i in business_items if i.get("monetization_activity"))
    return f"Business rollup: opportunities={len(business_items)} launched={launched} websites={websites} monetization_active={monetized}."


def daily_recommendation_rollup(reco_items: list[dict]) -> str:
    if not reco_items:
        return "Recommendation rollup: insufficient outcomes; capture approval decisions and execution completion states."
    approved = sum(1 for i in reco_items if i.get("approval_status") == "approved")
    pending = sum(1 for i in reco_items if i.get("approval_status") == "pending")
    positive = sum(1 for i in reco_items if i.get("outcome_quality") == "positive")
    return f"Recommendation rollup: items={len(reco_items)} approved={approved} pending={pending} positive_outcomes={positive}."


def daily_system_rollup() -> str:
    failed = _sb_get("job_events?status=eq.failed&select=id&limit=200")
    pending = _sb_get("owner_approval_queue?status=eq.pending&select=id&limit=200")
    digest_events = _sb_get(
        "hermes_aggregates?event_source=eq.digest_collector&classification=eq.digest_item&select=id&limit=500"
    )
    return (
        "System rollup: "
        f"failed_jobs={len(failed)} pending_approvals={len(pending)} digest_items={len(digest_events)}."
    )


def capture_credit_outcomes(days: int = 45) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    scores = _sb_get(
        "credit_fundability_scores?select=*"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=500"
    )
    actions = _sb_get(
        "credit_boost_actions?select=*"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=500"
    )
    opportunities = _sb_get("credit_boost_opportunities?select=id,name,category")
    opp_map = {str(o.get("id")): o for o in opportunities}
    rent = _sb_get(
        "user_rent_reporting?select=*"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=300"
    )
    vendor = _sb_get(
        "user_vendor_accounts?select=*"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=300"
    )

    score_by_user: dict[str, list[dict]] = {}
    for s in reversed(scores):
        uid = str(s.get("user_id") or "")
        if uid:
            score_by_user.setdefault(uid, []).append(s)

    captured = 0
    items = []
    for uid, series in score_by_user.items():
        first = _safe_float(series[0].get("score"), 0.0)
        last = _safe_float(series[-1].get("score"), first)
        delta = round(last - first, 2)
        velocity = round(delta / max(len(series), 1), 2)
        payload = {
            "user_id": uid,
            "score_start": first,
            "score_latest": last,
            "score_change": delta,
            "score_velocity": velocity,
            "utilization_factor": series[-1].get("utilization_factor"),
            "inquiries_factor": series[-1].get("inquiries_factor"),
            "negative_items_factor": series[-1].get("negative_items_factor"),
            "tradelines_factor": series[-1].get("tradelines_factor"),
            "late_payments": series[-1].get("late_payments") or "not_captured",
            "collections": series[-1].get("collections") or "not_captured",
            "charge_offs": series[-1].get("charge_offs") or "not_captured",
            "bureau_outcomes": {
                "experian": series[-1].get("experian_delta") or "not_captured",
                "equifax": series[-1].get("equifax_delta") or "not_captured",
                "transunion": series[-1].get("transunion_delta") or "not_captured",
            },
        }
        if _record("credit_outcome", f"credit-score:{uid}", f"credit score trend {uid[:8]} delta {delta}", payload):
            captured += 1
        items.append(payload)

    for a in actions:
        aid = str(a.get("id") or "")
        if not aid:
            continue
        opp = opp_map.get(str(a.get("opportunity_id") or ""), {})
        category = opp.get("category") or "unknown"
        payload = {
            "user_id": a.get("user_id"),
            "action_name": a.get("name") or opp.get("name") or "credit action",
            "action_category": category,
            "status": a.get("status") or "considering",
            "dispute_submission": True if category == "dispute" else False,
            "dispute_outcome": a.get("status") if category == "dispute" else "n/a",
            "recommendation_link": a.get("opportunity_id") or "not_linked",
            "completed_at": a.get("completed_at"),
        }
        if _record("credit_action_outcome", f"credit-action:{aid}", f"credit action {category}", payload):
            captured += 1

    for r in rent:
        rid = str(r.get("id") or "")
        if rid:
            payload = {
                "user_id": r.get("user_id"),
                "rent_reporting_status": r.get("status") or "pending",
                "verification_status": r.get("verification_status") or "unverified",
                "rent_reporting_impact": "potential_positive_history",
            }
            if _record("credit_rent_reporting", f"rent:{rid}", "rent reporting telemetry", payload):
                captured += 1

    for v in vendor:
        vid = str(v.get("id") or "")
        if vid:
            payload = {
                "user_id": v.get("user_id"),
                "tradeline_vendor": v.get("vendor_name"),
                "tradeline_status": v.get("status"),
                "credit_limit": v.get("credit_limit"),
                "authorized_user_impact": "not_captured",
            }
            if _record("credit_tradeline_outcome", f"tradeline:{vid}", "tradeline telemetry", payload):
                captured += 1

    return {
        "scores": len(scores),
        "actions": len(actions),
        "rent_reporting": len(rent),
        "tradelines": len(vendor),
        "captured_events": captured,
        "items": items,
    }


def capture_funding_outcomes(days: int = 60) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    applications = _sb_get(
        "application_results?select=*"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=500"
    )
    recs = _sb_get(
        "funding_recommendations?select=*"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=500"
    )
    profiles = _sb_get(
        "user_business_score_inputs?select=*"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=300"
    )
    relationships = _sb_get(
        "banking_relationships?select=*"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=300"
    )
    tiers = _sb_get(
        "user_tier_progress?select=*"
        f"&updated_at=gt.{urllib.parse.quote(cutoff)}&order=updated_at.desc&limit=300"
    )

    captured = 0
    for a in applications:
        aid = str(a.get("id") or "")
        if not aid:
            continue
        payload = {
            "user_id": a.get("user_id"),
            "recommendation_id": a.get("recommendation_id"),
            "funding_application_status": a.get("result_status") or "pending",
            "approved_amount": _safe_float(a.get("approved_amount"), 0.0),
            "completion_timestamp": a.get("created_at"),
            "outcome_quality": "positive" if str(a.get("result_status") or "").lower() in {"approved", "funded"} else "negative" if str(a.get("result_status") or "").lower() in {"denied", "rejected"} else "pending",
        }
        if _record("funding_application_outcome", f"funding-application:{aid}", "funding application telemetry", payload):
            captured += 1

    for r in recs:
        rid = str(r.get("id") or "")
        if not rid:
            continue
        payload = {
            "user_id": r.get("user_id"),
            "lender_type": r.get("recommendation_type") or r.get("institution_name") or "unknown",
            "approval_probability": _safe_float(r.get("approval_score"), 0.0),
            "limit_received": _safe_float(r.get("expected_limit_high"), 0.0),
            "apr_or_zero_percent_terms": r.get("product_type") or "not_captured",
            "recommendation_to_outcome_link": rid,
            "confidence_level": r.get("confidence_level") or "baseline",
        }
        if _record("funding_recommendation_outcome", f"funding-recommendation:{rid}", "funding recommendation telemetry", payload):
            captured += 1

    profile_by_user = {str(p.get("user_id") or ""): p for p in profiles if p.get("user_id")}
    relationship_by_user: dict[str, dict] = {}
    for rel in relationships:
        uid = str(rel.get("user_id") or "")
        if uid and uid not in relationship_by_user:
            relationship_by_user[uid] = rel

    for t in tiers:
        tid = str(t.get("id") or "")
        uid = str(t.get("user_id") or "")
        if not tid or not uid:
            continue
        profile = profile_by_user.get(uid, {})
        rel = relationship_by_user.get(uid, {})
        payload = {
            "user_id": uid,
            "tier_1_readiness": t.get("tier_1_status") or "unknown",
            "sba_readiness": t.get("tier_3_status") or "unknown",
            "business_age_signal": profile.get("business_bank_account_age_months") or "not_captured",
            "ein_duns_readiness": profile.get("duns_status") or "not_captured",
            "banking_relationship_indicator": rel.get("relationship_score") or 0,
            "balances": profile.get("average_balance") or rel.get("average_balance") or 0,
            "utilization_profile": profile.get("paydex_score") or "not_captured",
            "inquiry_profile": "not_captured",
            "approval_sequence": t.get("current_tier") or 1,
        }
        if _record("funding_profile_outcome", f"funding-profile:{tid}", "funding readiness telemetry", payload):
            captured += 1

    return {
        "applications": len(applications),
        "recommendations": len(recs),
        "profiles": len(profiles),
        "relationships": len(relationships),
        "tiers": len(tiers),
        "captured_events": captured,
    }


def daily_credit_rollup(credit: dict) -> str:
    if credit.get("scores", 0) == 0 and credit.get("actions", 0) == 0:
        return "Credit rollup: insufficient telemetry; capture score snapshots, dispute outcomes, and utilization deltas."
    return (
        "Credit rollup: "
        f"score_snapshots={credit.get('scores',0)} actions={credit.get('actions',0)} "
        f"rent_reporting={credit.get('rent_reporting',0)} tradelines={credit.get('tradelines',0)}."
    )


def daily_funding_rollup(funding: dict) -> str:
    if funding.get("applications", 0) == 0 and funding.get("recommendations", 0) == 0:
        return "Funding rollup: insufficient telemetry; capture applications, approvals/denials, limits, and readiness signals."
    return (
        "Funding rollup: "
        f"applications={funding.get('applications',0)} recommendations={funding.get('recommendations',0)} "
        f"profiles={funding.get('profiles',0)} tier_updates={funding.get('tiers',0)}."
    )


def capture_client_success_outcomes(days: int = 45) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    users = _sb_get(
        "user_profiles?select=id,full_name,onboarding_complete,subscription_plan,updated_at,created_at"
        f"&updated_at=gt.{urllib.parse.quote(cutoff)}&limit=400"
    )
    readiness = _sb_get(
        "user_tier_progress?select=user_id,business_readiness_score,current_tier,tier_1_status,tier_2_status,tier_3_status,updated_at"
        f"&updated_at=gt.{urllib.parse.quote(cutoff)}&limit=500"
    )
    recommendations = _sb_get(
        "funding_recommendations?select=user_id,status,created_at"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&limit=800"
    )
    app_results = _sb_get(
        "application_results?select=user_id,result_status,created_at"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&limit=800"
    )
    readiness_by_user = {str(r.get("user_id") or ""): r for r in readiness if r.get("user_id")}
    rec_by_user: dict[str, int] = {}
    for r in recommendations:
        uid = str(r.get("user_id") or "")
        if uid:
            rec_by_user[uid] = rec_by_user.get(uid, 0) + 1
    app_by_user: dict[str, dict] = {}
    for a in app_results:
        uid = str(a.get("user_id") or "")
        if not uid:
            continue
        s = app_by_user.setdefault(uid, {"approved": 0, "denied": 0, "pending": 0})
        status = str(a.get("result_status") or "pending").lower()
        if status in {"approved", "funded"}:
            s["approved"] += 1
        elif status in {"denied", "rejected"}:
            s["denied"] += 1
        else:
            s["pending"] += 1

    captured = 0
    for u in users:
        uid = str(u.get("id") or "")
        if not uid:
            continue
        tier = readiness_by_user.get(uid, {})
        apps = app_by_user.get(uid, {"approved": 0, "denied": 0, "pending": 0})
        payload = {
            "client_id": uid,
            "client_name": u.get("full_name") or f"client-{uid[:8]}",
            "onboarding_completion": bool(u.get("onboarding_complete")),
            "funding_readiness_progression": _safe_float(tier.get("business_readiness_score"), 0.0),
            "funding_approvals": apps["approved"],
            "engagement_frequency": "active" if str(u.get("updated_at") or "") >= cutoff else "stale",
            "portal_activity": str(u.get("updated_at") or u.get("created_at") or ""),
            "missed_actions_tasks": apps["pending"],
            "document_completion": "unknown",
            "recommendation_adoption": rec_by_user.get(uid, 0),
            "churn_risk_indicator": "elevated" if apps["denied"] >= 2 and not u.get("onboarding_complete") else "normal",
            "subscription_continuity": u.get("subscription_plan") or "unknown",
            "client_responsiveness": "high" if str(u.get("updated_at") or "") >= cutoff else "low",
        }
        if _record("client_lifecycle_outcome", f"client:{uid}", "client lifecycle telemetry", payload):
            captured += 1
    return {
        "clients": len(users),
        "readiness_rows": len(readiness),
        "recommendation_rows": len(recommendations),
        "application_rows": len(app_results),
        "captured_events": captured,
    }


def daily_client_success_rollup(client: dict) -> str:
    if client.get("clients", 0) == 0:
        return "Client success rollup: insufficient telemetry; capture onboarding, readiness, engagement, and recommendation adoption."
    return (
        "Client success rollup: "
        f"clients={client.get('clients',0)} readiness_updates={client.get('readiness_rows',0)} "
        f"recommendation_events={client.get('recommendation_rows',0)} funding_results={client.get('application_rows',0)}."
    )


def generate_daily_rollups() -> dict:
    trading = capture_trading_outcomes(days=30)
    business = capture_business_outcomes(days=30)
    recommendations = capture_recommendation_outcomes(days=60)
    credit = capture_credit_outcomes(days=45)
    funding = capture_funding_outcomes(days=60)
    client = capture_client_success_outcomes(days=45)

    day = _rollup_classification()
    t_summary = daily_trading_rollup(trading["items"])
    b_summary = daily_business_rollup(business["items"])
    r_summary = daily_recommendation_rollup(recommendations["items"])
    s_summary = daily_system_rollup()
    c_summary = daily_credit_rollup(credit)
    f_summary = daily_funding_rollup(funding)
    client_summary = daily_client_success_rollup(client)

    _record("daily_trading_rollup", f"daily:{day}", t_summary, trading)
    _record("daily_business_rollup", f"daily:{day}", b_summary, business)
    _record("daily_recommendation_rollup", f"daily:{day}", r_summary, recommendations)
    _record("daily_credit_rollup", f"daily:{day}", c_summary, credit)
    _record("daily_funding_rollup", f"daily:{day}", f_summary, funding)
    _record("daily_client_success_rollup", f"daily:{day}", client_summary, client)
    _record("daily_system_rollup", f"daily:{day}", s_summary, {"day": day})

    return {
        "date": day,
        "trading": t_summary,
        "business": b_summary,
        "recommendations": r_summary,
        "credit": c_summary,
        "funding": f_summary,
        "client_success": client_summary,
        "system": s_summary,
    }
