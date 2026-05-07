"""Client success intelligence for Hermes executive guidance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ceo_agent.telemetry_rollups import _safe_float, _sb_get


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _status_score(value: str, good: set[str], medium: set[str]) -> float:
    v = str(value or "").lower()
    if v in good:
        return 1.0
    if v in medium:
        return 0.6
    return 0.2


def _build_client_rows(limit: int = 200) -> list[dict]:
    users = _sb_get(
        "user_profiles?select=id,full_name,onboarding_complete,subscription_plan,updated_at,created_at&limit="
        + str(limit)
    )
    if not users:
        return []

    readiness = _sb_get(
        "user_tier_progress?select=user_id,business_readiness_score,relationship_score,current_tier,tier_1_status,tier_2_status,tier_3_status,updated_at&order=updated_at.desc&limit=500"
    )
    readiness_by_user: dict[str, dict] = {}
    for row in readiness:
        uid = str(row.get("user_id") or "")
        if uid and uid not in readiness_by_user:
            readiness_by_user[uid] = row

    recs = _sb_get(
        "funding_recommendations?select=user_id,status,created_at&order=created_at.desc&limit=1000"
    )
    rec_counts: dict[str, int] = {}
    for row in recs:
        uid = str(row.get("user_id") or "")
        if uid:
            rec_counts[uid] = rec_counts.get(uid, 0) + 1

    app = _sb_get(
        "application_results?select=user_id,result_status,created_at&order=created_at.desc&limit=1000"
    )
    app_stats: dict[str, dict] = {}
    for row in app:
        uid = str(row.get("user_id") or "")
        if not uid:
            continue
        s = app_stats.setdefault(uid, {"approved": 0, "denied": 0, "pending": 0})
        status = str(row.get("result_status") or "pending").lower()
        if status in {"approved", "funded"}:
            s["approved"] += 1
        elif status in {"denied", "rejected"}:
            s["denied"] += 1
        else:
            s["pending"] += 1

    tasks = _sb_get("coord_tasks?select=agent,status,created_at,updated_at&order=created_at.desc&limit=1200")
    pending_tasks = sum(1 for t in tasks if str(t.get("status") or "").lower() in {"pending", "todo", "open"})

    client_rows = []
    for u in users:
        uid = str(u.get("id") or "")
        r = readiness_by_user.get(uid, {})
        ap = app_stats.get(uid, {"approved": 0, "denied": 0, "pending": 0})
        client_rows.append(
            {
                "user_id": uid,
                "name": u.get("full_name") or f"client-{uid[:8]}",
                "onboarding_complete": bool(u.get("onboarding_complete")),
                "subscription_plan": u.get("subscription_plan") or "unknown",
                "updated_at": u.get("updated_at") or u.get("created_at") or _now_iso(),
                "readiness_score": _safe_float(r.get("business_readiness_score"), 0.0),
                "relationship_score": _safe_float(r.get("relationship_score"), 0.0),
                "current_tier": int(r.get("current_tier") or 1),
                "tier_1_status": r.get("tier_1_status") or "unknown",
                "tier_2_status": r.get("tier_2_status") or "unknown",
                "tier_3_status": r.get("tier_3_status") or "unknown",
                "recommendation_count": rec_counts.get(uid, 0),
                "funding_approved": ap["approved"],
                "funding_denied": ap["denied"],
                "funding_pending": ap["pending"],
                "global_pending_tasks": pending_tasks,
            }
        )
    return client_rows


def _score_client(c: dict) -> dict:
    readiness = min(max(c.get("readiness_score", 0.0), 0.0), 100.0)
    engagement = 75.0 if c.get("onboarding_complete") else 35.0
    if c.get("recommendation_count", 0) > 5:
        engagement += 10
    execution = min(100.0, c.get("funding_approved", 0) * 25.0 + 40.0 if c.get("onboarding_complete") else 20.0)
    momentum = min(100.0, (readiness * 0.5) + (execution * 0.3) + (engagement * 0.2))

    denial_penalty = c.get("funding_denied", 0) * 10.0
    inactivity_penalty = 20.0 if str(c.get("updated_at") or "") < _days_ago(21) else 0.0
    churn = min(100.0, max(0.0, 55.0 - (engagement * 0.5) + denial_penalty + inactivity_penalty))

    scaling = min(100.0, (readiness * 0.6) + (c.get("relationship_score", 0.0) * 0.4))
    ltv = min(100.0, (momentum * 0.45) + (scaling * 0.35) + ((100.0 - churn) * 0.2))

    c.update(
        {
            "funding_readiness_score": round(readiness, 1),
            "engagement_score": round(engagement, 1),
            "execution_score": round(execution, 1),
            "momentum_score": round(momentum, 1),
            "churn_risk_score": round(churn, 1),
            "scaling_potential_score": round(scaling, 1),
            "long_term_value_score": round(ltv, 1),
        }
    )
    return c


def _scored_clients(limit: int = 200) -> list[dict]:
    return [_score_client(c) for c in _build_client_rows(limit=limit)]


def _top_line(title: str, rows: list[dict], key: str, reverse: bool = True, n: int = 5) -> str:
    if not rows:
        return f"{title}: insufficient client telemetry."
    ranked = sorted(rows, key=lambda r: _safe_float(r.get(key), 0.0), reverse=reverse)[:n]
    body = ", ".join(f"{r['name']} ({r.get(key)})" for r in ranked)
    return f"{title}: {body}"


def clients_closest_to_funding() -> str:
    rows = [r for r in _scored_clients() if int(r.get("current_tier") or 1) <= 1]
    return _top_line("Closest to funding", rows, "funding_readiness_score")


def clients_stuck() -> str:
    rows = [r for r in _scored_clients() if _safe_float(r.get("momentum_score"), 0) < 45 or r.get("funding_pending", 0) > 1]
    return _top_line("Stalled clients", rows, "momentum_score", reverse=False)


def clients_likely_to_churn() -> str:
    rows = [r for r in _scored_clients() if _safe_float(r.get("churn_risk_score"), 0) >= 60]
    return _top_line("Churn-risk clients", rows, "churn_risk_score")


def clients_need_intervention() -> str:
    rows = [
        r
        for r in _scored_clients()
        if _safe_float(r.get("churn_risk_score"), 0) >= 55 or _safe_float(r.get("execution_score"), 0) < 45
    ]
    if not rows:
        return "Intervention list: no urgent intervention candidates right now."
    ranked = sorted(rows, key=lambda r: (r.get("churn_risk_score", 0), -r.get("execution_score", 0)), reverse=True)[:5]
    lines = ["Intervention priority list:"]
    for r in ranked:
        lines.append(
            f"- {r['name']}: churn risk {r['churn_risk_score']}, execution {r['execution_score']}. "
            "Action: outreach + onboarding/funding task review."
        )
    return "\n".join(lines)


def highest_momentum_clients() -> str:
    return _top_line("Highest momentum clients", _scored_clients(), "momentum_score")


def highest_value_clients() -> str:
    return _top_line("Highest value clients", _scored_clients(), "long_term_value_score")


def prioritize_this_week() -> str:
    rows = _scored_clients()
    if not rows:
        return "Weekly client priority: insufficient telemetry; capture onboarding, readiness, and recommendation adoption events."
    ranked = sorted(rows, key=lambda r: (r.get("long_term_value_score", 0) - r.get("churn_risk_score", 0)), reverse=True)[:5]
    return "Weekly client priority: " + ", ".join(
        f"{r['name']} (value {r['long_term_value_score']}, churn {r['churn_risk_score']})" for r in ranked
    )


def clients_need_outreach() -> str:
    rows = [r for r in _scored_clients() if _safe_float(r.get("engagement_score"), 0) < 50 or _safe_float(r.get("churn_risk_score"), 0) > 60]
    return _top_line("Outreach priorities", rows, "churn_risk_score")


def client_momentum_report() -> str:
    return highest_momentum_clients()


def client_churn_summary() -> str:
    return clients_likely_to_churn()


def client_intervention_summary() -> str:
    return clients_need_intervention()


def client_success_trends() -> str:
    rows = _scored_clients()
    if not rows:
        return "Client success trend: insufficient telemetry history."
    avg_momentum = round(sum(r.get("momentum_score", 0) for r in rows) / len(rows), 1)
    avg_churn = round(sum(r.get("churn_risk_score", 0) for r in rows) / len(rows), 1)
    avg_readiness = round(sum(r.get("funding_readiness_score", 0) for r in rows) / len(rows), 1)
    return f"Client trend snapshot: readiness {avg_readiness}, momentum {avg_momentum}, churn risk {avg_churn}."


def intervention_recommendations() -> str:
    return (
        "Intervention recommendations: prioritize outreach to low-engagement clients, complete onboarding blockers, "
        "sequence funding preparation steps, and automate reminder cadences for missed actions."
    )
