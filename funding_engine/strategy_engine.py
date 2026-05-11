"""
strategy_engine.py — Nexus Funding Strategy Engine.

Generates a structured, step-by-step funding plan based on readiness data,
recommendations, and banking relationships.

All outputs are educational guidance only.
Results vary. Approval is determined by the lender and is not guaranteed.
"""
from __future__ import annotations

import urllib.parse
from typing import Any

from funding_engine.constants import DISCLAIMER
from lib.growth_support import safe_insert, safe_patch
from scripts.prelaunch_utils import rest_select, table_exists, utc_now_iso

STRATEGY_DISCLAIMER = (
    "Results vary. Approval is determined by the lender and is not guaranteed. "
    "This funding plan is educational guidance only. Nexus does not guarantee "
    "funding amounts, approval outcomes, or credit limits."
)

# Institutions known to offer soft-pull prequalification
_SOFT_PULL_BRANDS = {"amex", "american express", "american express business", "capital one"}

# High-limit lenders that use comparables (existing limits raise approvals)
_COMPARABLES_LENDERS = {"amex", "american express", "american express business", "chase", "us bank"}


def _q(v: str | None) -> str:
    return urllib.parse.quote(str(v or ""), safe="")


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def _as_int(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def _institution_is_soft_pull(name: str) -> bool:
    return any(brand in name.lower() for brand in _SOFT_PULL_BRANDS)


def _institution_uses_comparables(name: str) -> bool:
    return any(brand in name.lower() for brand in _COMPARABLES_LENDERS)


def _safe_select(path: str) -> list[dict[str, Any]]:
    try:
        return rest_select(path) or []
    except Exception:
        return []


# ── Phase builders ────────────────────────────────────────────────────────────

def _build_prequalification_phase(
    recommendations: list[dict[str, Any]],
    user_profile: dict[str, Any],
) -> dict[str, Any]:
    credit_score = _as_int(
        user_profile.get("personal_credit_score") or user_profile.get("personal_credit_score_estimate")
    )
    soft_pull_opps: list[dict[str, Any]] = []

    for rec in recommendations:
        institution = rec.get("institution_name") or ""
        if not _institution_is_soft_pull(institution):
            continue
        soft_pull_opps.append({
            "institution_name": institution,
            "product_name": rec.get("product_name"),
            "product_type": rec.get("product_type"),
            "approval_score": rec.get("approval_score"),
            "expected_limit_low": rec.get("expected_limit_low"),
            "expected_limit_high": rec.get("expected_limit_high"),
            "action": f"Check prequalification at {institution} before applying — may avoid a hard inquiry.",
            "why": "Soft-pull prequalification may let you gauge approval odds without affecting credit.",
        })

    steps: list[str] = []
    if soft_pull_opps:
        steps.append("Check prequalification tools for soft-pull lenders before submitting formal applications.")
        steps.append("Soft-pull checks typically do not affect credit scores.")
        steps.append("Only proceed to a full application after reviewing prequalification results.")
    else:
        steps.append(
            "No soft-pull lender identified in current recommendations. "
            "Proceed with application sequencing when readiness conditions are met."
        )

    if credit_score < 680:
        steps.append("Credit score below 680 — consider improving score before broad applications.")

    return {
        "opportunities": soft_pull_opps,
        "steps": steps,
        "note": "Soft-pull prequalification may help gauge odds without a hard inquiry. Results vary.",
    }


def _build_relationship_phase(
    recommendations: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    user_profile: dict[str, Any],
) -> dict[str, Any]:
    existing_institutions = {
        str(r.get("institution_name") or "").lower()
        for r in relationships
        if r.get("institution_name")
    }

    avg_balance = _as_float(user_profile.get("average_balance"))
    monthly_deposits = _as_float(user_profile.get("monthly_deposits"))

    actions: list[dict[str, Any]] = []
    seen_institutions: set[str] = set()

    for rec in recommendations:
        institution = rec.get("institution_name") or ""
        institution_key = institution.lower()
        if not institution or institution_key in seen_institutions:
            continue
        seen_institutions.add(institution_key)

        already_has = institution_key in existing_institutions
        rel_score = 0.0
        if already_has:
            matching = [r for r in relationships if str(r.get("institution_name") or "").lower() == institution_key]
            if matching:
                rel_score = _as_float(matching[0].get("relationship_score"))

        if not already_has:
            deposit_target = "$2,000–$5,000"
            wait_days = "30–60 days"
            actions.append({
                "institution_name": institution,
                "status": "no_relationship",
                "action": f"Open a business checking account at {institution}.",
                "deposit_recommendation": deposit_target,
                "wait_period": wait_days,
                "steps": [
                    f"Open a business checking account at {institution} if eligible.",
                    f"Deposit {deposit_target} and maintain consistent monthly activity.",
                    f"Wait {wait_days} before submitting a credit application.",
                    "Document the relationship inside Nexus with a statement or screenshot.",
                ],
                "why": (
                    "A banking relationship may improve approval likelihood at this institution. "
                    "Results vary and are not guaranteed."
                ),
            })
        elif rel_score < 10:
            actions.append({
                "institution_name": institution,
                "status": "weak_relationship",
                "current_score": rel_score,
                "action": f"Strengthen existing relationship at {institution}.",
                "steps": [
                    f"Increase average balance toward $5,000–$10,000 at {institution} if practical.",
                    "Maintain consistent monthly deposits and clean account history.",
                    "Upload updated proof or statements inside Nexus.",
                ],
                "why": (
                    "A stronger relationship may improve approval likelihood. "
                    "Results vary and are not guaranteed."
                ),
            })

    summary_steps: list[str] = []
    if actions:
        missing = [a for a in actions if a["status"] == "no_relationship"]
        weak = [a for a in actions if a["status"] == "weak_relationship"]
        if missing:
            summary_steps.append(
                f"Open business accounts at {len(missing)} target institution(s) "
                "and allow 30–60 days for relationship history to build."
            )
        if weak:
            summary_steps.append(
                f"Strengthen {len(weak)} existing relationship(s) by increasing "
                "average balance and maintaining consistent deposits."
            )
        if avg_balance < 5000:
            summary_steps.append("Build toward a $5,000+ average balance before broad applications, if practical.")
        if monthly_deposits < 2500:
            summary_steps.append("Consistent monthly deposits may improve relationship scores over time.")
    else:
        summary_steps.append("Existing relationships appear adequate. Maintain consistent activity.")

    return {
        "institution_actions": actions,
        "summary_steps": summary_steps,
        "note": (
            "Opening accounts and building relationships may improve approval likelihood. "
            "Results vary. Nexus does not store or access bank account credentials — "
            "only manual status and proof fields are used."
        ),
    }


def _build_application_sequence(
    recommendations: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    readiness_score: float,
) -> list[dict[str, Any]]:
    existing_rel_map: dict[str, float] = {
        str(r.get("institution_name") or "").lower(): _as_float(r.get("relationship_score"))
        for r in relationships
        if r.get("institution_name")
    }

    def _seq_sort_key(rec: dict[str, Any]) -> tuple:
        institution = str(rec.get("institution_name") or "").lower()
        rel_score = existing_rel_map.get(institution, 0.0)
        uses_comp = 1 if _institution_uses_comparables(institution) else 2
        approval = _as_float(rec.get("approval_score"))
        tier = _as_int(rec.get("tier"), 1)
        has_rel = 0 if rel_score >= 10 else (1 if rel_score > 0 else 2)
        return (tier, has_rel, uses_comp, -approval)

    funding_recs = [
        r for r in recommendations
        if r.get("recommendation_type") == "funding_product"
    ]
    funding_recs.sort(key=_seq_sort_key)

    sequence: list[dict[str, Any]] = []
    for i, rec in enumerate(funding_recs):
        institution = rec.get("institution_name") or ""
        institution_key = institution.lower()
        rel_score = existing_rel_map.get(institution_key, 0.0)
        wait_days = 0
        if i > 0:
            # Recommend 14-day spacing between applications to avoid inquiry clustering
            wait_days = 14

        step: dict[str, Any] = {
            "step": i + 1,
            "institution_name": institution,
            "product_name": rec.get("product_name"),
            "product_type": rec.get("product_type"),
            "tier": rec.get("tier"),
            "approval_score": rec.get("approval_score"),
            "expected_limit_low": rec.get("expected_limit_low"),
            "expected_limit_high": rec.get("expected_limit_high"),
            "relationship_score": rel_score,
            "wait_before_days": wait_days,
            "action": (
                f"Apply for {rec.get('product_name') or institution + ' product'}"
                + (f" — wait {wait_days} days after the prior application." if wait_days else ".")
            ),
            "uses_comparables": _institution_uses_comparables(institution),
            "linked_recommendation_id": rec.get("id"),
            "disclaimer": DISCLAIMER,
        }

        if _institution_uses_comparables(institution):
            step["comparables_note"] = (
                "This institution commonly considers existing credit limits when evaluating applications. "
                "Higher existing limits may be associated with higher approvals — based on observed patterns."
            )

        sequence.append(step)

    return sequence


def _build_optimization_notes(
    user_profile: dict[str, Any],
    readiness_score: float,
    application_sequence: list[dict[str, Any]],
) -> dict[str, Any]:
    credit_score = _as_int(
        user_profile.get("personal_credit_score") or user_profile.get("personal_credit_score_estimate")
    )
    utilization = _as_float(user_profile.get("credit_utilization"))
    inquiries = _as_int(user_profile.get("inquiries_count"))
    negative_items = _as_int(user_profile.get("negative_items_count"))
    avg_balance = _as_float(user_profile.get("average_balance"))

    notes: list[str] = []

    # Utilization guidance
    if utilization > 0.30:
        notes.append(
            f"Current credit utilization appears above 30% ({round(utilization * 100, 1)}%). "
            "Reducing utilization before applications may improve approval likelihood — based on observed patterns."
        )
    elif utilization > 0.10:
        notes.append(
            "Keep credit utilization below 30% before and during the application window."
        )
    else:
        notes.append("Credit utilization appears favorable. Maintain current levels.")

    # Inquiry spacing
    if inquiries >= 4:
        notes.append(
            f"Recent inquiry count is elevated ({inquiries}). "
            "Space applications at least 14 days apart to avoid clustering. "
            "Fewer inquiries in a short window may improve approval likelihood."
        )
    else:
        notes.append(
            "Space applications at least 14 days apart to reduce inquiry impact."
        )

    # Timing
    if len(application_sequence) > 2:
        total_wait = sum(s.get("wait_before_days", 0) for s in application_sequence[1:])
        notes.append(
            f"Estimated sequence duration: approximately {total_wait}+ days across "
            f"{len(application_sequence)} steps. Follow the recommended spacing to reduce inquiry clustering."
        )

    # Negative items
    if negative_items > 0:
        notes.append(
            f"{negative_items} negative item(s) detected on profile. "
            "Addressing inaccuracies through the credit bureaus may help over time — results vary."
        )

    # Relationship strengthening
    if avg_balance < 5000:
        notes.append(
            "Building toward a $5,000+ average business bank balance before applications "
            "may strengthen relationship scores — based on observed patterns."
        )

    # Readiness-based timing
    if readiness_score < 55:
        notes.append(
            f"Internal readiness score ({round(readiness_score, 1)}/100) is below 55. "
            "Completing readiness tasks before broad applications is commonly recommended."
        )
    elif readiness_score >= 70:
        notes.append(
            f"Internal readiness score ({round(readiness_score, 1)}/100) is above 70 — "
            "good time to begin the application sequence."
        )

    return {
        "notes": notes,
        "utilization_target": "below 30% before applications",
        "inquiry_spacing_days": 14,
        "timing_note": "Complete relationship-building steps before the application sequence begins.",
    }


def _estimate_funding_range(
    recommendations: list[dict[str, Any]],
    readiness_score: float,
) -> tuple[float, float]:
    top_recs = sorted(
        [r for r in recommendations if r.get("recommendation_type") == "funding_product"],
        key=lambda r: -_as_float(r.get("approval_score")),
    )[:5]

    if not top_recs:
        base = max(0.0, readiness_score / 100.0) * 15000
        return round(base * 0.5, 2), round(base, 2)

    total_low = sum(_as_float(r.get("expected_limit_low")) for r in top_recs)
    total_high = sum(_as_float(r.get("expected_limit_high")) for r in top_recs)

    confidence_mult = max(0.5, min(1.0, readiness_score / 100.0))
    return round(total_low * confidence_mult, 2), round(total_high, 2)


def _determine_current_phase(
    readiness_score: float,
    relationship_phase: dict[str, Any],
    prequal_phase: dict[str, Any],
    app_sequence: list[dict[str, Any]],
) -> str:
    """
    Determine which funding phase the user is currently in.

    Phases (in priority order):
      readiness          — score too low or critical setup missing
      relationship_building — no banking relationship at a target institution
      prequalification   — soft-pull check available before hard inquiry
      application        — ready to begin application sequence
      optimization       — sequence complete; focus on profile improvement
    """
    if readiness_score < 40:
        return "readiness"
    rel_actions = relationship_phase.get("institution_actions") or []
    no_rel = [a for a in rel_actions if a.get("status") == "no_relationship"]
    if no_rel and readiness_score < 65:
        return "relationship_building"
    prequal_opps = prequal_phase.get("opportunities") or []
    if prequal_opps:
        return "prequalification"
    if app_sequence:
        return "application"
    return "optimization"


def _build_next_best_action(
    prequalification_phase: dict[str, Any],
    relationship_phase: dict[str, Any],
    application_sequence: list[dict[str, Any]],
    readiness_score: float,
) -> dict[str, Any]:
    # Readiness is too low — complete readiness tasks first
    if readiness_score < 40:
        return {
            "phase": "readiness",
            "action": "Complete readiness tasks before starting the funding sequence.",
            "detail": (
                f"Internal readiness score is {round(readiness_score, 1)}/100. "
                "Complete high-priority readiness tasks (EIN, business bank account, credit report upload) "
                "before beginning credit applications."
            ),
            "priority": "high",
        }

    # Relationship steps pending
    rel_actions = relationship_phase.get("institution_actions") or []
    no_rel = [a for a in rel_actions if a.get("status") == "no_relationship"]
    if no_rel and readiness_score < 65:
        first = no_rel[0]
        return {
            "phase": "relationship_building",
            "action": first.get("action"),
            "detail": (
                f"Open a business account at {first['institution_name']}, "
                f"deposit {first.get('deposit_recommendation', '$2,000–$5,000')}, "
                f"and wait {first.get('wait_period', '30–60 days')} before applying."
            ),
            "institution_name": first.get("institution_name"),
            "priority": "high",
        }

    # Soft-pull prequal available
    prequal_opps = prequalification_phase.get("opportunities") or []
    if prequal_opps:
        opp = prequal_opps[0]
        return {
            "phase": "prequalification",
            "action": opp.get("action"),
            "detail": f"Check prequalification at {opp.get('institution_name')} before a hard-pull application.",
            "institution_name": opp.get("institution_name"),
            "priority": "medium",
        }

    # First application step
    if application_sequence:
        step = application_sequence[0]
        return {
            "phase": "application",
            "action": step.get("action"),
            "detail": (
                f"Apply for {step.get('product_name') or step.get('institution_name')}. "
                f"Estimated limit range: "
                f"${step.get('expected_limit_low', 0):,.0f}–${step.get('expected_limit_high', 0):,.0f}."
            ),
            "institution_name": step.get("institution_name"),
            "step_number": step.get("step"),
            "priority": "medium",
        }

    return {
        "phase": "complete",
        "action": "All identified steps are complete or no sequence available. Maintain readiness profile.",
        "priority": "low",
    }


def _build_strategy_summary(
    prequalification_phase: dict[str, Any],
    relationship_phase: dict[str, Any],
    application_sequence: list[dict[str, Any]],
    estimated_low: float,
    estimated_high: float,
    readiness_score: float,
) -> str:
    rel_actions = relationship_phase.get("institution_actions") or []
    no_rel_count = sum(1 for a in rel_actions if a.get("status") == "no_relationship")
    prequal_count = len(prequalification_phase.get("opportunities") or [])
    app_count = len(application_sequence)

    lines = ["Funding Strategy Overview:"]

    if readiness_score < 55:
        lines.append(
            f"Current readiness score is {round(readiness_score, 1)}/100. "
            "Complete readiness tasks before beginning the application sequence."
        )

    if prequal_count:
        lines.append(
            f"Step 1: Check prequalification at {prequal_count} soft-pull lender(s) "
            "before formal applications — may help gauge odds without a hard inquiry."
        )

    if no_rel_count:
        lines.append(
            f"Step 2: Open business account(s) at {no_rel_count} target institution(s). "
            "Deposit $2,000–$5,000 and allow 30–60 days before applying."
        )

    if app_count:
        lines.append(
            f"Step 3: Apply across {app_count} product(s) in sequence, "
            "spaced at least 14 days apart to limit inquiry clustering."
        )

    lines.append(
        f"Estimated Funding Range: ${estimated_low:,.0f}–${estimated_high:,.0f} "
        "(based on internal scoring and observed patterns — not a guarantee)."
    )
    lines.append("")
    lines.append(STRATEGY_DISCLAIMER)
    return "\n".join(lines)


# ── Core public function ──────────────────────────────────────────────────────

def build_funding_strategy(
    user_profile: dict[str, Any],
    readiness_profile: dict[str, Any],
    recommendations: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build a structured funding strategy from profile data and recommendations.

    Returns a strategy dict ready for Supabase persistence and Hermes brief.
    Does not guarantee approval, funding amounts, or credit limits.
    """
    user_profile = user_profile or {}
    readiness_profile = readiness_profile or {}
    recommendations = recommendations or []
    relationships = relationships or []

    readiness_score = _as_float(
        readiness_profile.get("score")
        or readiness_profile.get("overall_score")
        or user_profile.get("readiness_score")
    )

    prequal_phase = _build_prequalification_phase(recommendations, user_profile)
    rel_phase = _build_relationship_phase(recommendations, relationships, user_profile)
    app_sequence = _build_application_sequence(recommendations, relationships, readiness_score)
    opt_notes = _build_optimization_notes(user_profile, readiness_score, app_sequence)
    est_low, est_high = _estimate_funding_range(recommendations, readiness_score)
    current_phase = _determine_current_phase(readiness_score, rel_phase, prequal_phase, app_sequence)
    next_action = _build_next_best_action(prequal_phase, rel_phase, app_sequence, readiness_score)

    summary = _build_strategy_summary(
        prequal_phase, rel_phase, app_sequence, est_low, est_high, readiness_score
    )

    linked_ids = [
        step["linked_recommendation_id"]
        for step in app_sequence
        if step.get("linked_recommendation_id")
    ]

    source_snapshot = {
        "readiness_score": readiness_score,
        "recommendations_count": len(recommendations),
        "relationships_count": len(relationships),
        "generated_at": utc_now_iso(),
    }

    return {
        "strategy_summary": summary,
        "prequalification_phase": prequal_phase,
        "relationship_building_phase": rel_phase,
        "application_sequence": app_sequence,
        "optimization_notes": opt_notes,
        "estimated_funding_low": est_low,
        "estimated_funding_high": est_high,
        "next_best_action": next_action,
        "current_phase": current_phase,
        "linked_recommendation_ids": linked_ids,
        "source_snapshot": source_snapshot,
        "disclaimer": STRATEGY_DISCLAIMER,
        "generated_at": utc_now_iso(),
    }


# ── Supabase persistence ──────────────────────────────────────────────────────

def get_active_strategy(user_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    filters = [f"user_id=eq.{_q(user_id)}", "strategy_status=eq.active"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_q(tenant_id)}")
    rows = _safe_select(
        "funding_strategies?select=*&order=created_at.desc&limit=1&" + "&".join(filters)
    )
    return rows[0] if rows else None


def _archive_old_strategies(user_id: str, tenant_id: str | None) -> None:
    try:
        filters = [f"user_id=eq.{_q(user_id)}", "strategy_status=eq.active"]
        if tenant_id:
            filters.append(f"tenant_id=eq.{_q(tenant_id)}")
        safe_patch(
            "funding_strategies?" + "&".join(filters),
            {"strategy_status": "archived", "updated_at": utc_now_iso()},
        )
    except Exception:
        pass


def persist_funding_strategy(
    user_id: str,
    tenant_id: str | None,
    strategy: dict[str, Any],
    force: bool = False,
) -> dict[str, Any]:
    if not table_exists("funding_strategies"):
        return {"ok": False, "error": "table_missing:funding_strategies", "strategy": strategy}

    existing = get_active_strategy(user_id, tenant_id)

    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "strategy_status": "active",
        "strategy_summary": strategy.get("strategy_summary"),
        "prequalification_phase": strategy.get("prequalification_phase"),
        "relationship_building_phase": strategy.get("relationship_building_phase"),
        "application_sequence": strategy.get("application_sequence"),
        "optimization_notes": strategy.get("optimization_notes"),
        "estimated_funding_low": strategy.get("estimated_funding_low"),
        "estimated_funding_high": strategy.get("estimated_funding_high"),
        "next_best_action": strategy.get("next_best_action"),
        "current_phase": strategy.get("current_phase"),
        "linked_recommendation_ids": strategy.get("linked_recommendation_ids"),
        "source_snapshot": strategy.get("source_snapshot"),
        "disclaimer": strategy.get("disclaimer", STRATEGY_DISCLAIMER),
        "generated_at": strategy.get("generated_at") or utc_now_iso(),
        "updated_at": utc_now_iso(),
    }

    if existing and not force:
        result = safe_patch(
            f"funding_strategies?id=eq.{_q(existing.get('id'))}",
            payload,
        )
        result["action"] = "updated"
        return result

    if existing and force:
        _archive_old_strategies(user_id, tenant_id)

    payload["created_at"] = utc_now_iso()
    result = safe_insert("funding_strategies", payload)
    result["action"] = "created"
    return result


def build_and_persist_strategy(
    user_id: str,
    tenant_id: str | None,
    user_profile: dict[str, Any],
    readiness_profile: dict[str, Any],
    recommendations: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    force: bool = False,
) -> dict[str, Any]:
    strategy = build_funding_strategy(
        user_profile=user_profile,
        readiness_profile=readiness_profile,
        recommendations=recommendations,
        relationships=relationships,
    )
    persist_result = persist_funding_strategy(user_id, tenant_id, strategy, force=force)
    return {
        "strategy": strategy,
        "persisted": persist_result.get("ok", False),
        "action": persist_result.get("action"),
        "error": persist_result.get("error"),
    }


# ── Hermes strategy brief ─────────────────────────────────────────────────────

def build_hermes_strategy_brief(
    user_id: str,
    tenant_id: str | None = None,
    strategy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a Hermes-ready brief from a persisted or live funding strategy.
    Reads from Supabase first; falls back to the provided strategy dict.
    """
    if strategy is None:
        strategy = get_active_strategy(user_id, tenant_id)

    if not strategy:
        return {
            "brief_text": (
                "No funding strategy on file. Complete readiness tasks and run a recommendation "
                "refresh to generate your funding plan."
            ),
            "disclaimer": STRATEGY_DISCLAIMER,
        }

    next_action = strategy.get("next_best_action") or {}
    app_seq = strategy.get("application_sequence") or []
    est_low = _as_float(strategy.get("estimated_funding_low"))
    est_high = _as_float(strategy.get("estimated_funding_high"))
    opt = strategy.get("optimization_notes") or {}
    rel_phase = strategy.get("relationship_building_phase") or {}
    rel_actions = rel_phase.get("institution_actions") or []
    current_phase = strategy.get("current_phase") or next_action.get("phase") or "readiness"

    _PHASE_LABELS: dict[str, str] = {
        "readiness": "Complete your readiness tasks before beginning the funding sequence.",
        "relationship_building": "Build banking relationships at target institutions before applying.",
        "prequalification": "Check soft-pull prequalification tools before formal applications.",
        "application": "You are ready to begin your credit application sequence.",
        "optimization": "Continue optimizing your credit profile and business financials.",
        "complete": "All identified steps are complete. Maintain your readiness profile.",
    }
    phase_label = current_phase.replace("_", " ").title()
    phase_note = _PHASE_LABELS.get(current_phase, "Review your funding plan.")

    lines = [
        "Funding Plan:",
        f"Current Phase: {phase_label} — {phase_note}",
        "",
    ]

    # Relationship building comes first if needed
    no_rel = [a for a in rel_actions if a.get("status") == "no_relationship"]
    weak_rel = [a for a in rel_actions if a.get("status") == "weak_relationship"]
    step_num = 1
    if no_rel:
        for action in no_rel[:2]:
            lines.append(
                f"Step {step_num}: Open business checking account at "
                f"{action['institution_name']} and deposit "
                f"{action.get('deposit_recommendation', '$2,000–$5,000')}."
            )
            step_num += 1
        lines.append(f"Step {step_num}: Wait {no_rel[0].get('wait_period', '30–60 days')} for relationship history to build.")
        step_num += 1

    # Application steps
    for app_step in app_seq[:4]:
        wait = app_step.get("wait_before_days", 0)
        if wait:
            lines.append(f"Step {step_num}: Wait {wait} days, then apply for {app_step.get('product_name') or app_step.get('institution_name')}.")
        else:
            lines.append(f"Step {step_num}: Apply for {app_step.get('product_name') or app_step.get('institution_name')}.")
        step_num += 1

    if len(app_seq) > 4:
        lines.append(f"  ... and {len(app_seq) - 4} more application step(s) in your full plan.")

    lines.append("")
    lines.append("Next Best Action:")
    lines.append(f"  {next_action.get('action') or 'Review your funding plan.'}")

    lines.append("")
    lines.append("Expected Outcome:")
    lines.append(
        f"  ${est_low:,.0f}–${est_high:,.0f} potential funding range "
        "(based on internal scoring and observed patterns)."
    )

    opt_notes = opt.get("notes") or []
    if opt_notes:
        lines.append("")
        lines.append("Key Optimization Notes:")
        for note in opt_notes[:3]:
            lines.append(f"  - {note}")

    lines.append("")
    lines.append(STRATEGY_DISCLAIMER)

    return {
        "brief_text": "\n".join(lines),
        "next_best_action": next_action,
        "estimated_funding_low": est_low,
        "estimated_funding_high": est_high,
        "current_phase": current_phase,
        "phase_label": phase_label,
        "phase_note": phase_note,
        "application_step_count": len(app_seq),
        "disclaimer": STRATEGY_DISCLAIMER,
    }
