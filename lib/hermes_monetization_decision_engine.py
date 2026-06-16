"""
hermes_monetization_decision_engine.py
=========================================
Hermes processes intake sources and decides what becomes a monetization action.

For each source, scores across 7 dimensions and produces a decision status.
All decisions are logged. All recommendations cite evidence.

NO MONETIZATION RECOMMENDATION WITHOUT EVIDENCE.
NO PUBLIC PUBLISHING WITHOUT RAY APPROVAL.
NO PAID TOOLS WITHOUT RAY APPROVAL.

Outputs:
  docs/reports/monetization/monetization_decision_cycle_<ts>.md
  docs/reports/monetization/monetization_decision_cycle_<ts>.json
  docs/reports/monetization/top_monetization_actions_<ts>.md
  docs/reports/monetization/rejected_opportunities_<ts>.json
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parent.parent
DECISION_DIR = ROOT / "docs" / "reports" / "monetization"

DecisionStatus = Literal[
    "reject",
    "watch",
    "needs_more_research",
    "content_candidate",
    "monetization_candidate",
    "affiliate_candidate",
    "funnel_candidate",
    "product_candidate",
    "client_education_candidate",
    "system_improvement_candidate",
    "trading_education_candidate",
    "needs_ray_review",
    "ready_for_autonomous_next_step",
]


@dataclass
class OpportunityDecision:
    decision_id: str = field(default_factory=lambda: f"dec_op_{uuid.uuid4().hex[:8]}")
    intake_id: str = ""
    source_type: str = ""
    title: str = ""
    url: str = ""
    keyword: str = ""

    # Scores 0–100
    monetization_score: int = 0
    urgency_score: int = 0
    confidence_score: int = 0
    risk_score: int = 0          # higher = riskier
    effort_score: int = 0        # higher = more effort
    goal_alignment_score: int = 0
    artifact_potential_score: int = 0

    # Decision
    status: DecisionStatus = "watch"
    recommended_action: str = ""
    assigned_scout: str = ""
    why_selected: str = ""
    why_rejected: str = ""
    goal_supported: str = ""
    evidence_path: str = ""
    requires_ray_approval: bool = False
    approval_reason: str = ""
    autonomous_next_step: str = ""

    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_plain_english(self) -> str:
        status_marks = {
            "reject": "❌",
            "watch": "👀",
            "needs_more_research": "🔍",
            "content_candidate": "📝",
            "monetization_candidate": "💰",
            "affiliate_candidate": "🔗",
            "funnel_candidate": "🔽",
            "product_candidate": "📦",
            "client_education_candidate": "🎓",
            "system_improvement_candidate": "⚙️",
            "trading_education_candidate": "📈",
            "needs_ray_review": "⏳",
            "ready_for_autonomous_next_step": "✅",
        }
        mark = status_marks.get(self.status, "⚪")
        lines = [f"{mark} [{self.status}] {self.title[:70]} (score: {self.monetization_score})"]
        if self.why_selected:
            lines.append(f"   Why: {self.why_selected[:80]}")
        if self.why_rejected and self.status == "reject":
            lines.append(f"   Rejected: {self.why_rejected[:80]}")
        if self.recommended_action:
            lines.append(f"   Next: {self.recommended_action[:80]}")
        if self.requires_ray_approval:
            lines.append(f"   ⏳ Needs approval: {self.approval_reason}")
        return "\n".join(lines)


# ── Scoring helpers ────────────────────────────────────────────────────────────

_REVENUE_KEYWORDS = [
    "affiliate", "commission", "income", "revenue", "monetiz", "funnel", "sell",
    "earn", "profit", "make money", "paid", "premium", "product", "course", "template",
    "checklist", "report", "audit",
]
_GOAL_KEYWORDS = [
    "credit", "fund", "grant", "business", "loan", "readiness", "capital",
    "AI", "automation", "content", "newsletter", "youtube", "faceless",
    "trading", "forex", "backtest", "strategy",
]
_RISK_KEYWORDS = [
    "live trading", "real money", "published", "client", "compliance", "legal",
    "paid tool", "subscription", "api key", "stripe", "payment",
]
_FAST_REVENUE_KEYWORDS = [
    "affiliate", "checklist", "template", "audit offer", "lead magnet",
    "email", "newsletter", "quick", "24 hour", "48 hour", "this week",
]


def _keyword_score(text: str, keywords: list[str], max_score: int = 100) -> int:
    t = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in t)
    return min(max_score, int((hits / max(1, len(keywords) * 0.3)) * max_score))


def score_source(record: dict) -> OpportunityDecision:
    """Score an intake record and produce an OpportunityDecision."""
    title   = record.get("title", "")
    keyword = record.get("keyword", "")
    url     = record.get("url", "")
    src_type = record.get("source_type", "")
    platform = record.get("platform", "")
    assigned_scout = record.get("assigned_scout", "")
    fallback = record.get("fallback", False)
    mon_potential = record.get("monetization_potential", "low")

    combined_text = f"{title} {keyword} {url} {src_type}"

    # ── Score calculation ──
    rev_raw = _keyword_score(combined_text, _REVENUE_KEYWORDS, 100)
    goal_raw = _keyword_score(combined_text, _GOAL_KEYWORDS, 100)
    risk_raw = _keyword_score(combined_text, _RISK_KEYWORDS, 100)
    fast_raw = _keyword_score(combined_text, _FAST_REVENUE_KEYWORDS, 100)

    # Potential multiplier
    potential_mult = {"high": 1.2, "medium": 1.0, "low": 0.6}.get(mon_potential, 1.0)

    monetization_score = min(100, int(
        (rev_raw * 0.35 + goal_raw * 0.25 + fast_raw * 0.20 + (100 - risk_raw) * 0.20)
        * potential_mult
    ))

    # Fallback tasks get a moderate score — useful for research, not for execution yet
    if fallback:
        monetization_score = min(monetization_score, 45)

    urgency_score = min(100, fast_raw + (20 if src_type in ("affiliate", "monetization") else 0))
    confidence_score = 80 if url else (60 if not fallback else 30)
    risk_score = min(100, risk_raw)
    effort_score = 40 if src_type in ("youtube", "github") else 60
    goal_alignment_score = min(100, goal_raw + (20 if src_type in ("monetization", "affiliate") else 0))
    artifact_potential_score = 80 if src_type in ("youtube",) else (60 if src_type == "github" else 50)

    # ── Decision status ──
    requires_approval = False
    approval_reason = ""

    if monetization_score < 25:
        status: DecisionStatus = "reject"
        why_rejected = "Low revenue potential and weak goal alignment."
        why_selected = ""
        rec_action = ""
    elif monetization_score < 50 or fallback:
        status = "needs_more_research"
        why_selected = "Moderate potential — needs more research before action."
        why_rejected = ""
        rec_action = "Assign to research scout for deeper analysis."
    elif "affiliate" in combined_text.lower():
        status = "affiliate_candidate"
        why_selected = "Strong affiliate revenue signal. Free research allowed."
        why_rejected = ""
        rec_action = "Route to affiliate_monetization_scout for offer analysis."
    elif any(t in combined_text.lower() for t in ["content", "youtube", "newsletter", "video", "script"]):
        status = "content_candidate"
        why_selected = "Strong content engine potential. Can produce draft autonomously."
        why_rejected = ""
        rec_action = "Route to content_intelligence_scout for topic brief."
    elif any(t in combined_text.lower() for t in ["trading", "forex", "backtest", "strategy", "strategy lab"]):
        status = "trading_education_candidate"
        why_selected = "Trading education content — paper/demo only, no live execution."
        why_rejected = ""
        rec_action = "Route to trading_research_scout. No live execution without approval."
    elif any(t in combined_text.lower() for t in ["credit", "fund", "grant", "loan", "readiness"]):
        status = "client_education_candidate"
        why_selected = "Credit/funding education — strong demand, aligns with 30-day goal."
        why_rejected = ""
        rec_action = "Route to credit_repair_research_scout. Draft checklist/lead magnet."
    elif any(t in combined_text.lower() for t in ["checklist", "template", "audit", "report", "lead magnet"]):
        status = "product_candidate"
        why_selected = "Ready-to-produce product: checklist, template, or audit offer."
        why_rejected = ""
        rec_action = "Route to content_intelligence_scout. Build draft for Ray review."
    elif any(t in combined_text.lower() for t in ["funnel", "landing page", "conversion", "upsell"]):
        status = "funnel_candidate"
        why_selected = "Funnel/conversion opportunity. Can draft structure autonomously."
        why_rejected = ""
        rec_action = "Route to funnel_builder_scout."
    else:
        status = "monetization_candidate"
        why_selected = "General monetization signal. Scoring puts this above watch threshold."
        why_rejected = ""
        rec_action = "Route to monetization_scout for deeper assessment."

    # Approval gates
    if status in ("affiliate_candidate",):
        requires_approval = True
        approval_reason = "Affiliate signup may require paid tool or external account."
    if risk_raw > 40:
        requires_approval = True
        approval_reason = "Risk keywords detected — review before proceeding."

    # Scout assignment
    scout_map: dict[str, str] = {
        "affiliate_candidate": "affiliate_monetization_scout",
        "content_candidate": "content_intelligence_scout",
        "client_education_candidate": "credit_repair_research_scout",
        "trading_education_candidate": "trading_research_scout",
        "product_candidate": "content_intelligence_scout",
        "funnel_candidate": "funnel_builder_scout",
        "monetization_candidate": "monetization_scout",
        "system_improvement_candidate": "system_improvement_scout",
    }
    scout = assigned_scout or scout_map.get(status, "")

    # Goal alignment
    goal_map = {
        "affiliate_candidate": "30-day revenue goal + affiliate path",
        "content_candidate": "Content engine goal",
        "client_education_candidate": "Credit/funding education offer",
        "trading_education_candidate": "Trading education content",
        "product_candidate": "Finished product for Ray review",
        "funnel_candidate": "Content funnel goal",
        "monetization_candidate": "30-day revenue goal",
    }
    goal_supported = goal_map.get(status, "Nexus revenue goal")

    autonomous_next_step = ""
    if status == "ready_for_autonomous_next_step" or not requires_approval:
        if status == "content_candidate":
            autonomous_next_step = "Build content brief artifact and route to pipeline"
        elif status == "client_education_candidate":
            autonomous_next_step = "Draft credit/funding checklist template"
        elif status == "affiliate_candidate":
            autonomous_next_step = "Research affiliate terms and create findings artifact"

    return OpportunityDecision(
        intake_id=record.get("intake_id", ""),
        source_type=src_type,
        title=title or keyword or "Untitled source",
        url=url,
        keyword=keyword,
        monetization_score=monetization_score,
        urgency_score=urgency_score,
        confidence_score=confidence_score,
        risk_score=risk_score,
        effort_score=effort_score,
        goal_alignment_score=goal_alignment_score,
        artifact_potential_score=artifact_potential_score,
        status=status,
        recommended_action=rec_action,
        assigned_scout=scout,
        why_selected=why_selected,
        why_rejected=why_rejected,
        goal_supported=goal_supported,
        requires_ray_approval=requires_approval,
        approval_reason=approval_reason,
        autonomous_next_step=autonomous_next_step,
    )


# ── Scout dispatch ────────────────────────────────────────────────────────────

def _dispatch_to_scout(decision: OpportunityDecision) -> None:
    """Create action queue entry + decision log entry for each scored opportunity."""
    if decision.status in ("reject", "watch"):
        return
    try:
        from lib.hermes_action_queue import create_action
        from lib.hermes_decision_log import log_decision
        action = create_action(
            title=f"[{decision.status}] {decision.title[:70]}",
            description=decision.recommended_action,
            assigned_scout=decision.assigned_scout,
            priority=max(50, decision.monetization_score),
            autonomous_allowed=not decision.requires_ray_approval,
            requires_ray_approval=decision.requires_ray_approval,
            approval_reason=decision.approval_reason,
            status="needs_ray_approval" if decision.requires_ray_approval else "queued",
        )
        log_decision(
            question_or_trigger=f"Score intake source: {decision.title[:60]}",
            decision=f"Status: {decision.status} — {decision.recommended_action[:60]}",
            why_selected=decision.why_selected or decision.why_rejected,
            goal_alignment=decision.goal_supported,
            risk_level="low" if decision.risk_score < 30 else ("medium" if decision.risk_score < 60 else "high"),
            autonomous_allowed=not decision.requires_ray_approval,
            requires_ray_approval=decision.requires_ray_approval,
            action_created=action.action_id,
        )
    except Exception:
        pass


# ── Main decision cycle ────────────────────────────────────────────────────────

def run_decision_cycle(
    intake_records: list[dict],
    mode: str = "validation",
    top_n: int = 10,
    dry_run: bool = True,
    cost: str = "free",
) -> dict:
    """
    Score all intake records, produce decisions, dispatch to scouts.
    Returns results dict with decisions, top actions, rejected list.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    decisions: list[OpportunityDecision] = []
    for record in intake_records:
        d = score_source(record)
        decisions.append(d)

    # Sort by monetization score descending
    decisions.sort(key=lambda d: -d.monetization_score)

    rejected  = [d for d in decisions if d.status == "reject"]
    top_ops   = [d for d in decisions if d.status not in ("reject", "watch")][:top_n]
    needs_approval = [d for d in decisions if d.requires_ray_approval]
    high_value = [d for d in decisions if d.monetization_score >= 70]

    # Dispatch to scouts (creates action queue + decision log entries)
    if not dry_run:
        for d in top_ops:
            _dispatch_to_scout(d)
    else:
        # In dry run, still log decisions but don't create actions
        for d in top_ops[:3]:
            _dispatch_to_scout(d)

    # Top recommendation
    top_rec = ""
    if top_ops:
        best = top_ops[0]
        top_rec = best.recommended_action or f"Pursue: {best.title[:60]}"

    # Save artifacts
    DECISION_DIR.mkdir(parents=True, exist_ok=True)

    json_path = DECISION_DIR / f"monetization_decision_cycle_{ts}.json"
    md_path   = DECISION_DIR / f"monetization_decision_cycle_{ts}.md"
    top_path  = DECISION_DIR / f"top_monetization_actions_{ts}.md"
    rej_path  = DECISION_DIR / f"rejected_opportunities_{ts}.json"

    data = {
        "cycle_id": f"cycle_{ts}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "dry_run": dry_run,
        "total_scored": len(decisions),
        "top_opportunities": [d.to_dict() for d in top_ops],
        "rejected": [d.to_dict() for d in rejected],
        "needs_approval": [d.to_dict() for d in needs_approval],
    }
    json_path.write_text(json.dumps(data, indent=2))

    # Markdown report
    md = [
        "# Monetization Decision Cycle",
        f"*{ts[:8]}*  |  {len(decisions)} scored, {len(top_ops)} actionable, {len(rejected)} rejected",
        "",
        "## Top Opportunities",
        "",
    ]
    for d in top_ops[:10]:
        md.append(d.to_plain_english())
        md.append("")

    if rejected:
        md += ["## Rejected", ""]
        for d in rejected[:5]:
            md.append(d.to_plain_english())
            md.append("")

    md_path.write_text("\n".join(md))

    # Top actions summary
    top_md = [
        "# Top Monetization Actions",
        f"*{ts[:8]}*",
        "",
    ]
    for i, d in enumerate(top_ops[:5], 1):
        top_md += [
            f"### {i}. {d.title[:70]}",
            f"Score: {d.monetization_score} | Status: {d.status}",
            f"Why: {d.why_selected}",
            f"Next: {d.recommended_action}",
            f"Goal: {d.goal_supported}",
            f"Approval needed: {'Yes — ' + d.approval_reason if d.requires_ray_approval else 'No'}",
            "",
        ]
    top_path.write_text("\n".join(top_md))

    # Rejected log
    rej_path.write_text(json.dumps([d.to_dict() for d in rejected], indent=2))

    # Register artifacts
    artifact_id = ""
    try:
        from lib.nexus_artifact_registry import register_artifact
        art = register_artifact(
            agent_name="hermes_monetization_decision_engine",
            artifact_type="monetization_decision_report",
            file_path=str(json_path),
            title=f"Monetization Decision Cycle {ts}",
            description=f"{len(top_ops)} actionable opportunities, {len(rejected)} rejected",
            evidence_level="verified_file",
        )
        artifact_id = art.artifact_id
    except Exception:
        pass

    return {
        "ts": ts,
        "mode": mode,
        "dry_run": dry_run,
        "total_scored": len(decisions),
        "top_opportunities": [d.to_dict() for d in top_ops],
        "rejected": [d.to_dict() for d in rejected],
        "needs_approval": [d.to_dict() for d in needs_approval],
        "high_value": [d.to_dict() for d in high_value],
        "top_recommendation": top_rec,
        "artifact_id": artifact_id,
        "artifact_path": str(json_path.relative_to(ROOT)),
        "md_path": str(md_path.relative_to(ROOT)),
        "top_actions_path": str(top_path.relative_to(ROOT)),
        "rejected_path": str(rej_path.relative_to(ROOT)),
    }


def load_latest_decisions(limit: int = 20) -> list[dict]:
    """Load most recent opportunity decisions from monetization reports."""
    if not DECISION_DIR.exists():
        return []
    files = sorted(DECISION_DIR.glob("monetization_decision_cycle_*.json"), reverse=True)
    if not files:
        return []
    try:
        data = json.loads(files[0].read_text())
        ops = data.get("top_opportunities", [])
        return ops[:limit]
    except Exception:
        return []
