"""Executive credit + funding intelligence helpers for Hermes."""

from __future__ import annotations

from collections import Counter

from ceo_agent.telemetry_rollups import _sb_get


def _latest_rollup(event_type: str) -> str | None:
    rows = _sb_get(
        "hermes_aggregates?select=aggregated_summary,created_at"
        "&event_source=eq.executive_telemetry"
        f"&event_type=eq.{event_type}&order=created_at.desc&limit=1"
    )
    if not rows:
        return None
    return str(rows[0].get("aggregated_summary") or "").split("\n", 1)[0]


def _recommend_missing_credit() -> str:
    return (
        "Insufficient credit outcome history. Capture utilization deltas, dispute outcomes by bureau, "
        "and at least 3 score snapshots per client over 30+ days."
    )


def _recommend_missing_funding() -> str:
    return (
        "Insufficient funding outcome history. Capture application status, approval/denial, limit terms, "
        "and readiness profile attributes for each submission."
    )


def credit_actions_work_best() -> str:
    rows = _sb_get(
        "credit_boost_actions?select=id,name,status,opportunity_id,created_at&order=created_at.desc&limit=300"
    )
    opps = _sb_get("credit_boost_opportunities?select=id,category,name")
    opp_map = {str(o.get("id")): o for o in opps}
    if not rows:
        return _recommend_missing_credit()
    by_cat = Counter()
    for r in rows:
        if str(r.get("status") or "") != "completed":
            continue
        opp = opp_map.get(str(r.get("opportunity_id") or ""), {})
        by_cat[str(opp.get("category") or "unknown")] += 1
    if not by_cat:
        return "No completed credit actions yet. Prioritize a repeatable first sequence: utilization cleanup, dispute filing, then tradeline support."
    top, count = by_cat.most_common(1)[0]
    return f"Top-performing credit action category: {top} ({count} completed actions). Prioritize this sequence where profile fit is strong."


def credit_strategies_improve_scores_fastest() -> str:
    rows = _sb_get("credit_fundability_scores?select=user_id,score,created_at&order=created_at.asc&limit=600")
    if len(rows) < 6:
        return _recommend_missing_credit()
    first = {}
    last = {}
    for r in rows:
        uid = str(r.get("user_id") or "")
        if not uid:
            continue
        first.setdefault(uid, r)
        last[uid] = r
    deltas = []
    for uid, start in first.items():
        end = last.get(uid)
        if not end:
            continue
        delta = float(end.get("score") or 0) - float(start.get("score") or 0)
        deltas.append(delta)
    if not deltas:
        return _recommend_missing_credit()
    avg_delta = round(sum(deltas) / len(deltas), 2)
    return (
        f"Average observed score improvement across tracked profiles: {avg_delta} points. "
        "Fastest patterns typically combine utilization reduction + dispute cleanup + tradeline reinforcement."
    )


def funding_blockers() -> str:
    rollup = _latest_rollup("daily_funding_rollup")
    pending_apps = _sb_get("application_results?select=id,result_status&result_status=eq.pending&limit=200")
    stale = len(pending_apps)
    if not rollup and stale == 0:
        return _recommend_missing_funding()
    return (
        f"Primary blocker pattern: {stale} pending funding outcomes plus readiness gaps (DUNS/banking depth/utilization profile). "
        "Improve profile completeness before net-new applications."
    )


def lenders_approve_most_often() -> str:
    rows = _sb_get("credit_approval_results?select=bank_name,approved,credit_limit&order=application_date.desc&limit=500")
    if not rows:
        return _recommend_missing_funding()
    stats = {}
    for r in rows:
        bank = str(r.get("bank_name") or "unknown")
        s = stats.setdefault(bank, {"ok": 0, "total": 0})
        s["total"] += 1
        if bool(r.get("approved")):
            s["ok"] += 1
    ranked = sorted(stats.items(), key=lambda kv: (kv[1]["ok"] / max(kv[1]["total"], 1), kv[1]["total"]), reverse=True)
    top = ranked[0]
    rate = round(top[1]["ok"] / max(top[1]["total"], 1) * 100, 1)
    return f"Highest observed lender approval rate: {top[0]} at {rate}% ({top[1]['ok']}/{top[1]['total']} samples)."


def profile_patterns_succeed() -> str:
    rows = _sb_get("user_tier_progress?select=current_tier,tier_1_status,tier_2_status,tier_3_status,business_readiness_score,relationship_score&limit=300")
    if not rows:
        return _recommend_missing_funding()
    ready = [r for r in rows if float(r.get("business_readiness_score") or 0) >= 70 and float(r.get("relationship_score") or 0) >= 60]
    return (
        f"Successful profile pattern: readiness >=70 and relationship score >=60 ({len(ready)}/{len(rows)} profiles). "
        "These profiles are strongest candidates for Tier 1/Tier 2 progression."
    )


def improve_before_applying() -> str:
    return (
        "Before applying: reduce utilization, verify DUNS/EIN readiness, strengthen average banking balance/deposit consistency, "
        "and complete open readiness tasks to improve approval odds."
    )


def closest_to_tier1() -> str:
    rows = _sb_get("user_tier_progress?select=user_id,current_tier,business_readiness_score,relationship_score,tier_1_status&order=updated_at.desc&limit=300")
    if not rows:
        return _recommend_missing_funding()
    candidates = [r for r in rows if int(r.get("current_tier") or 1) <= 1]
    if not candidates:
        return "No Tier 1 pipeline candidates currently visible."
    candidates.sort(key=lambda r: (float(r.get("business_readiness_score") or 0), float(r.get("relationship_score") or 0)), reverse=True)
    top = candidates[0]
    return (
        f"Closest Tier 1 readiness candidate: user {str(top.get('user_id'))[:8]} | "
        f"readiness {top.get('business_readiness_score') or 0} | relationship {top.get('relationship_score') or 0}."
    )
