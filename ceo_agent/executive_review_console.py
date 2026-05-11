"""Executive Intelligence Review Console foundations for Hermes."""

from __future__ import annotations

from ceo_agent.telemetry_rollups import _sb_get


def _latest(event_type: str) -> str:
    rows = _sb_get(
        "hermes_aggregates?select=aggregated_summary,created_at"
        "&event_source=eq.executive_telemetry"
        f"&event_type=eq.{event_type}&order=created_at.desc&limit=1"
    )
    if not rows:
        return "not available"
    return str(rows[0].get("aggregated_summary") or "not available").split("\n", 1)[0]


def _confidence_label(sample_count: int) -> str:
    if sample_count <= 0:
        return "pending confidence"
    if sample_count < 5:
        return "baseline confidence"
    if sample_count < 20:
        return "emerging signal"
    return "high confidence"


def _missing_data_points() -> list[str]:
    checks = {
        "trading outcomes": _sb_get("hermes_aggregates?select=id&event_source=eq.executive_telemetry&event_type=eq.trading_outcome&limit=1"),
        "business outcomes": _sb_get("hermes_aggregates?select=id&event_source=eq.executive_telemetry&event_type=eq.business_outcome&limit=1"),
        "recommendation outcomes": _sb_get("hermes_aggregates?select=id&event_source=eq.executive_telemetry&event_type=eq.recommendation_outcome&limit=1"),
        "credit outcomes": _sb_get("hermes_aggregates?select=id&event_source=eq.executive_telemetry&event_type=eq.credit_outcome&limit=1"),
        "funding outcomes": _sb_get("hermes_aggregates?select=id&event_source=eq.executive_telemetry&event_type=eq.funding_application_outcome&limit=1"),
        "client lifecycle outcomes": _sb_get("hermes_aggregates?select=id&event_source=eq.executive_telemetry&event_type=eq.client_lifecycle_outcome&limit=1"),
    }
    missing = [k for k, v in checks.items() if not v]
    return missing


def show_recommendation_reasoning() -> str:
    try:
        from ceo_agent.recommendation_queue import ranked_recommendations
    except Exception as e:
        return f"Recommendation reasoning unavailable: {e}"
    ranked = ranked_recommendations(limit=1)
    if not ranked:
        return "No pending recommendations to explain yet."
    top = ranked[0]
    payload = top.get("payload") or {}
    details = payload.get("details") or {}
    base = top.get("base_score", 0)
    boost = top.get("learning_boost", 0)
    final = top.get("final_score", 0)
    return "\n".join(
        [
            "Recommendation reasoning:",
            f"- Top recommendation: {payload.get('recommendation_type','unknown')} — {payload.get('title','untitled')}",
            f"- Why it ranks high: base composite {base} with learning boost {boost}, final {final}",
            f"- Contributing signals: confidence={details.get('confidence_score','n/a')}, ROI={details.get('expected_roi','n/a')}, automation={details.get('automation_potential','n/a')}, strategic_alignment={details.get('strategic_alignment','n/a')}",
            f"- Confidence level: {_confidence_label(1 if final else 0)}",
            f"- Sparse-data warning: {'yes' if final == 0 else 'no'}",
        ]
    )


def why_did_hermes_recommend_this() -> str:
    return show_recommendation_reasoning()


def signals_influencing_score() -> str:
    return (
        "Score signal model: expected ROI, confidence score, launch speed, automation potential, execution difficulty, "
        "strategic alignment, and historical performance. Learning boosts categories with stronger approve/success outcomes."
    )


def sparse_data_diagnostics() -> str:
    missing = _missing_data_points()
    if not missing:
        return "Sparse-data diagnostics: telemetry coverage looks healthy across core domains."
    return (
        "Sparse-data diagnostics: missing or weak datasets in "
        + ", ".join(missing)
        + ". Capture more operational outcomes before trusting trend-level conclusions."
    )


def why_client_high_priority() -> str:
    try:
        from ceo_agent.client_success_intelligence import prioritize_this_week

        return (
            "Client priority reasoning: prioritization weighs long-term value, readiness momentum, and churn risk.\n"
            f"Current view: {prioritize_this_week()}"
        )
    except Exception as e:
        return f"Client priority reasoning unavailable: {e}"


def why_strategy_ranked_highly() -> str:
    try:
        from ceo_agent.chief_of_staff import best_performing_strategy

        return (
            "Strategy ranking reasoning: win rate, profit factor, drawdown stability, and consistency drive ranking.\n"
            f"Current view: {best_performing_strategy()}"
        )
    except Exception as e:
        return f"Strategy reasoning unavailable: {e}"


def executive_review_snapshot() -> str:
    missing = _missing_data_points()
    return "\n".join(
        [
            "<b>Executive Review Snapshot</b>",
            f"Trading: {_latest('daily_trading_rollup')}",
            f"Business: {_latest('daily_business_rollup')}",
            f"Funding: {_latest('daily_funding_rollup')}",
            f"Credit: {_latest('daily_credit_rollup')}",
            f"Client success: {_latest('daily_client_success_rollup')}",
            f"Recommendations: {_latest('daily_recommendation_rollup')}",
            f"Confidence posture: {_confidence_label(6 - len(missing))}",
            f"Missing telemetry: {', '.join(missing) if missing else 'none critical'}",
        ]
    )
