"""
Nexus Proof Automation Engine — V1 core (JSON-backed, local, compliance-safe).

Tracks: credit readiness · funding readiness · online opportunity · trading lab ·
AI improvement. Produces projects, scout findings, asset drafts, simulator runs,
metrics, Hermes decisions, AI-improvement recommendations, and registers Showroom
packages — all test_only / draft_only. No publish, email, payment, live trading,
paid APIs, or guarantees. Reuses lib.showroom_assets for Showroom registration.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "logs" / "proof_automation" / "store.json"
ASSET_DIR = ROOT / "reports" / "content_engine" / "generated" / "proof_automation"

# ── Modes / flags ────────────────────────────────────────────────────────────
AUTOMATION_MODES = ["off", "draft_only", "test_only", "ray_owned_channels", "approved_live"]
FLAGS = {
    "AUTOMATION_GLOBAL_ENABLED": True,   # internal/test loops only
    "PUBLIC_PUBLISH_ENABLED": False,
    "COLD_OUTREACH_ENABLED": False,
    "PAYMENT_AUTOMATION_ENABLED": False,
    "LIVE_TRADING_ENABLED": False,
    "APPROVED_LIVE_MODE": False,
}

TRACKS = ["credit", "funding", "opportunity", "trading", "ai_improvement"]

# Claims that must never appear in generated assets.
PROHIBITED = [
    "guaranteed credit score", "guaranteed deletion", "guaranteed funding", "guaranteed approval",
    "guaranteed profit", "guaranteed income", "guaranteed clients", "instant credit repair",
    "secret loophole", "no-risk income", "get funded fast", "approval no matter what",
]

SCOUTS = {
    "credit": "Credit Scout", "funding": "Funding Scout", "opportunity": "Opportunity Scout",
    "trading": "Trading Scout", "marketing": "Marketing Scout", "metrics": "Metrics Scout",
    "ai_improvement": "AI Improvement Scout",
}

# Seeded scout missions (per scout).
SEED_MISSIONS = {
    "credit": [
        "Research best structure for a credit readiness assessment.",
        "Research best structure for a 30-day credit action plan.",
        "Research dispute-prep / document checklist format.",
        "Research how to explain credit improvement without promising results.",
    ],
    "funding": [
        "Research business funding readiness checklist.",
        "Research bankability factors.",
        "Research business credibility setup.",
        "Research funding document checklist.",
        "Research how to explain funding prep without promising approval.",
    ],
    "opportunity": [
        "Research online opportunity models suitable for beginners.",
        "Research affiliate/content/service paths.",
        "Research scam/noise filters.",
        "Research how to turn an interest into a testable campaign.",
    ],
    "trading": [
        "Research how to structure a trading strategy from a video/transcript.",
        "Research safe paper-trading workflow.",
        "Research metrics for judging demo strategy performance.",
        "Research strategy improvement loop.",
    ],
    "marketing": [
        "Research landing page structure for credit/funding audience.",
        "Research Facebook/IG post hooks.",
        "Research short video/Reel structure.",
        "Research lead magnet formats.",
        "Research CTA testing ideas.",
    ],
    "metrics": [
        "Define core metrics for Nexus proof projects.",
        "Define drop-off stages.",
        "Define improvement triggers.",
        "Define Hermes recommendation rules.",
    ],
    "ai_improvement": [
        "Evaluate Postiz for Nexus social scheduling and draft distribution.",
        "Evaluate Mautic for landing pages, forms, email, and marketing automation.",
        "Evaluate Typebot + n8n for intake automation.",
        "Evaluate Chatwoot for inbox/customer messaging.",
        "Evaluate Manus/OpenManus-style systems for autonomous task execution.",
        "Evaluate current Hermes features that can improve Nexus.",
        "Evaluate low-cost/local model options for research/scout work.",
        "Evaluate AI video/content tools for producing Nexus marketing assets.",
        "Evaluate AI SEO/content systems for turning research into campaigns.",
        "Evaluate browser automation agents for repeatable marketing/test tasks.",
    ],
}

# AI Improvement scoring catalogue (deterministic V1 — needs live verification flag).
AI_TOOLS = {
    "Postiz": dict(area="social scheduling / draft distribution", cost="self-host (free) or paid SaaS tier",
                   scores=dict(revenue=7, automation=8, user_benefit=6, speed=7, cost=8, risk=3, fit=8, urgency=7),
                   action="create_adapter_only"),
    "Mautic": dict(area="landing pages / forms / email automation", cost="self-host (free), infra/maintenance time",
                   scores=dict(revenue=7, automation=7, user_benefit=7, speed=4, cost=6, risk=5, fit=6, urgency=5),
                   action="defer"),
    "Typebot+n8n": dict(area="intake automation / workflow", cost="self-host (free) or low SaaS",
                        scores=dict(revenue=6, automation=8, user_benefit=7, speed=6, cost=7, risk=4, fit=7, urgency=6),
                        action="create_adapter_only"),
    "Chatwoot": dict(area="inbox / customer messaging", cost="self-host (free) or paid SaaS",
                     scores=dict(revenue=5, automation=6, user_benefit=7, speed=5, cost=6, risk=4, fit=5, urgency=4),
                     action="defer"),
    "Manus/OpenManus": dict(area="autonomous task execution pattern", cost="model inference cost varies",
                            scores=dict(revenue=5, automation=8, user_benefit=5, speed=3, cost=4, risk=6, fit=5, urgency=4),
                            action="monitor"),
    "Hermes features": dict(area="scout/decision/learning core", cost="internal dev time",
                            scores=dict(revenue=7, automation=8, user_benefit=7, speed=7, cost=8, risk=3, fit=9, urgency=7),
                            action="test_in_sandbox"),
    "Local/low-cost models": dict(area="scout/research inference cost", cost="local compute (Ollama already present)",
                                  scores=dict(revenue=6, automation=7, user_benefit=5, speed=7, cost=9, risk=3, fit=8, urgency=6),
                                  action="test_in_sandbox"),
    "AI video/content tools": dict(area="marketing asset production", cost="varies; some free/local (HyperFrames present)",
                                   scores=dict(revenue=7, automation=7, user_benefit=6, speed=5, cost=5, risk=4, fit=7, urgency=6),
                                   action="monitor"),
    "AI SEO/content systems": dict(area="research→campaign content", cost="varies",
                                   scores=dict(revenue=7, automation=6, user_benefit=6, speed=5, cost=5, risk=4, fit=6, urgency=5),
                                   action="monitor"),
    "Browser automation agents": dict(area="repeatable marketing/test tasks", cost="compute + maintenance",
                                      scores=dict(revenue=5, automation=7, user_benefit=4, speed=4, cost=6, risk=6, fit=5, urgency=4),
                                      action="defer"),
}

AI_ACTIONS = ["implement_now", "test_in_sandbox", "create_adapter_only", "monitor", "defer", "avoid"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, key: str) -> str:
    return f"{prefix}_{hashlib.sha1(key.encode()).hexdigest()[:8]}"


def _empty_store() -> dict:
    cols = ["projects", "scout_missions", "scout_findings", "assets", "leads", "conversations",
            "messages", "metrics", "recommendations", "feedback", "events", "outcomes",
            "ai_research_items", "ai_improvement_recommendations", "ai_tool_cost_estimates",
            "ai_implementation_plans", "ai_upgrade_tasks", "ai_research_sources", "ai_feature_watchlist"]
    return {"updated_at": _now(), **{c: [] for c in cols}}


def load() -> dict:
    if STORE.exists():
        try:
            return json.loads(STORE.read_text())
        except Exception:
            pass
    return _empty_store()


def save(s: dict) -> None:
    s["updated_at"] = _now()
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(s, indent=2))


def _append(col: str, rec: dict) -> dict:
    s = load()
    s.setdefault(col, [])
    # idempotent by id
    s[col] = [r for r in s[col] if r.get("id") != rec.get("id")]
    s[col].append(rec)
    save(s)
    return rec


def compliance_scrub(text: str) -> str:
    low = text.lower()
    for p in PROHIBITED:
        if p in low:
            # never emit a prohibited claim; replace with safe framing
            import re
            text = re.sub(re.escape(p), "[education only — no guarantee]", text, flags=re.I)
    return text


# ── Projects ─────────────────────────────────────────────────────────────────
def create_project(track: str, goal: str, audience: str = "", offer: str = "",
                   channel: str = "", mode: str = "draft_only", tenant_id: str = "default") -> dict:
    pid = _id("proj", f"{track}:{goal}")
    rec = {
        "id": pid, "project_id": pid, "track": track, "goal": goal, "audience": audience,
        "offer": offer, "channel": channel, "current_hypothesis": "", "ray_feedback": [],
        "automation_mode": mode if mode in AUTOMATION_MODES else "draft_only",
        "status": "new", "next_action": "run_scouts", "assigned_scouts": [],
        "generated_assets": [], "metrics": {}, "hermes_recommendation": None,
        "showroom_package_id": None, "tenant_id": tenant_id,
        "created_at": _now(), "updated_at": _now(),
    }
    _append("projects", rec)
    _append("events", {"id": _id("evt", pid + "create"), "project_id": pid, "type": "project_created", "at": _now()})
    return rec


def _scouts_for_track(track: str) -> list[str]:
    base = {"credit": ["credit", "marketing", "metrics"],
            "funding": ["funding", "marketing", "metrics"],
            "opportunity": ["opportunity", "marketing", "metrics"],
            "trading": ["trading", "metrics"],
            "ai_improvement": ["ai_improvement", "metrics"]}.get(track, ["metrics"])
    return base


def run_scouts(project_id: str) -> list[dict]:
    s = load()
    proj = next((p for p in s["projects"] if p["id"] == project_id), None)
    if not proj:
        return []
    findings = []
    for scout in _scouts_for_track(proj["track"]):
        missions = SEED_MISSIONS.get(scout, [])
        for m in missions:
            mid = _id("mission", f"{project_id}:{scout}:{m}")
            _append("scout_missions", {"id": mid, "mission_id": mid, "project_id": project_id,
                                       "scout": scout, "scout_name": SCOUTS[scout], "mission": m,
                                       "status": "researched", "at": _now()})
            fid = _id("finding", mid)
            finding = {
                "id": fid, "scout_id": scout, "scout_name": SCOUTS[scout], "mission_id": mid,
                "project_id": project_id, "findings": _seed_finding(scout, m, proj),
                "source_notes": "Internal templates + prior Nexus reports. NEEDS LIVE VERIFICATION (no live web call this run).",
                "opportunity_score": 7, "risk_flags": _risk_flags(proj["track"]),
                "recommended_angle": _angle(proj["track"]),
                "recommended_asset": _first_asset(proj["track"]),
                "recommended_next_step": "generate_assets", "confidence": 0.7, "timestamp": _now(),
            }
            findings.append(_append("scout_findings", finding))
    proj["assigned_scouts"] = _scouts_for_track(proj["track"])
    proj["status"] = "researched"; proj["next_action"] = "hermes_decision"; proj["updated_at"] = _now()
    _append("projects", proj)
    return findings


def _seed_finding(scout: str, mission: str, proj: dict) -> str:
    return (f"{SCOUTS[scout]} reviewed: '{mission}'. Recommendation: produce an educational, compliance-safe "
            f"deliverable for the {proj['track']} track that explains where the user stands and the concrete next "
            f"steps, with no guarantees. (Template-driven V1; flag for live verification.)")


def _risk_flags(track: str) -> list[str]:
    common = ["no guarantees", "educational only", "review-only drafts"]
    return common + {"credit": ["avoid credit-repair-results claims"],
                     "funding": ["avoid funding-approval claims"],
                     "trading": ["paper/demo only, no live trading, no investment advice"],
                     "opportunity": ["filter scams/noise; no income guarantees"],
                     "ai_improvement": ["no auto-install, no paid APIs, no auto-connect"]}.get(track, [])


def _first_asset(track: str) -> str:
    return {"credit": "credit readiness assessment", "funding": "funding readiness score",
            "opportunity": "landing page", "trading": "paper-test plan",
            "ai_improvement": "AI improvement report"}.get(track, "landing page")


def _angle(track: str) -> str:
    return {"credit": "Educate on credit readiness + a clear 30-day plan.",
            "funding": "Help owners see funding-readiness gaps before applying.",
            "opportunity": "Turn an interest into one testable, low-risk campaign.",
            "trading": "Structure an idea into a paper-test plan with risk rules.",
            "ai_improvement": "Score tools by Nexus-fit; adapter-first, no auto-install."}.get(track, "")


# ── Hermes decision ──────────────────────────────────────────────────────────
def hermes_decision(project_id: str) -> dict:
    s = load()
    proj = next((p for p in s["projects"] if p["id"] == project_id), None)
    if not proj:
        return {}
    track = proj["track"]
    prof = TRACK_PROFILE.get(track, TRACK_PROFILE["opportunity"])
    metric = prof["metric"]
    rec = {
        "id": _id("rec", project_id), "project_id": project_id,
        "what_understood": f"User is in the {track} track: {prof['audience']}. Goal: {proj.get('goal','')[:80]}.",
        "what_created": f"A {track} package: {', '.join(prof['deliverables'][:4])} + landing page, posts, and a proof report (all needs_review).",
        "decision_summary": f"Ship the {track} deliverables as review-only drafts, run the test campaign, and measure {metric}.",
        "recommended_action": "Review the landing page + lead magnet, then run the simulator/test and watch the metric.",
        "reason": "Fastest path to a concrete, track-specific proof artifact reusing Nexus content + showroom + feedback loop.",
        "evidence": [f"{f['scout_name']}: {f['recommended_angle']}" for f in s["scout_findings"] if f["project_id"] == project_id][:4],
        "risk_flags": _risk_flags(track),
        "asset_instructions": f"Produce {', '.join(prof['deliverables'][:5])} — specific, action-oriented, compliance-safe, no guarantees.",
        "metric_to_track": metric, "metric_that_matters": metric,
        "what_to_test_next": f"Run the {track} simulator scenario and review the top assets (landing page, lead magnet, posts).",
        "next_test": f"Simulate the {track} scenario; review assets.",
        "improve_if_weak": f"If the response is weak, sharpen '{prof['deliverables'][0]}' and the headline/CTA first; re-test one variable at a time.",
        "improvement_task": "Apply Ray feedback to v2 of the weakest asset.",
        "confidence": 0.74, "at": _now(),
    }
    _append("recommendations", rec)
    proj["hermes_recommendation"] = rec["id"]; proj["status"] = "decided"; proj["next_action"] = "generate_assets"
    proj["updated_at"] = _now(); _append("projects", proj)
    return rec


# ── Asset engine ─────────────────────────────────────────────────────────────
ASSET_TYPES = ["landing_page", "facebook_post", "instagram_post", "linkedin_post", "short_video_script",
               "lead_magnet", "dm_reply", "email_reply", "intake_questions", "follow_up_sequence",
               "metrics_plan", "proof_report", "improvement_recommendation"]


def _assets_for_track(track: str) -> list[str]:
    return ASSET_TYPES  # all tracks can produce all; templates vary by track


def _disclaimer(track: str) -> str:
    return ("Educational content only. No guarantee of " + {
        "credit": "credit-score change, deletion, or credit-repair results",
        "funding": "funding approval, amount, or terms",
        "opportunity": "income, clients, or results",
        "trading": "profit; paper/demo only, not investment advice",
        "ai_improvement": "outcomes; research only",
    }.get(track, "results") + ". No credit pull / no application / nothing published without approval.")


def generate_assets(project_id: str) -> list[dict]:
    s = load()
    proj = next((p for p in s["projects"] if p["id"] == project_id), None)
    if not proj:
        return []
    track = proj["track"]
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    try:
        from lib import showroom_assets as SA
    except Exception:
        SA = None
    for atype in ASSET_TYPES:
        body = compliance_scrub(_asset_body(track, atype, proj))
        fname = f"{project_id}_{atype}.md"
        fpath = ASSET_DIR / fname
        fpath.write_text(body)
        aid = _id("asset", f"{project_id}:{atype}")
        rec = {"id": aid, "project_id": project_id, "asset_type": atype, "track": track,
               "file_path": str(fpath.relative_to(ROOT)), "status": "needs_review", "at": _now()}
        _append("assets", rec)
        out.append(rec)
        if SA:
            SA.register(f"proof_{track}", f"Proof {track.title()} — {atype.replace('_',' ').title()}",
                        str(fpath.relative_to(ROOT)), showroom_path=str(fpath.relative_to(ROOT)),
                        key=fname, status="needs_review")
    proj["generated_assets"] = [a["id"] for a in out]; proj["status"] = "assets_generated"
    proj["next_action"] = "simulate"; proj["updated_at"] = _now(); _append("projects", proj)
    log_metric(project_id, "assets_created", len(out))
    return out


# Track-specific content profiles — drive impressive, specific, compliance-safe assets.
TRACK_PROFILE = {
    "credit": dict(
        audience="people who want to understand and improve their credit",
        headline="Know exactly where your credit stands — and the next 30 days of moves that actually matter.",
        sub="A clear credit readiness assessment, an issue checklist, a dispute/document-prep checklist, and a simple 30-day action plan. Education, not promises.",
        problem="Most people guess at credit: they don't know what's hurting them, which items to address first, or what documents to gather.",
        deliverables=["Credit readiness assessment", "Issue checklist", "Dispute/document-prep checklist",
                      "30-day action plan", "Educational explainer", "Progress tracker"],
        steps=["Assess where you stand (utilization, history, mix, recent activity)",
               "List the issues to review (errors, high balances, missing info)",
               "Prep documents + dispute letters the correct way (no shortcuts)",
               "Follow a 30-day plan and track each step"],
        hooks=["The 3 things hurting most credit profiles (and what to do first)",
               "What a dispute letter should actually say",
               "Your 30-day credit readiness plan, one step at a time"],
        lead_title="Credit Readiness Checklist", cta="Get your free credit readiness check",
        metric="intake completions"),
    "funding": dict(
        audience="business owners preparing to seek funding",
        headline="See exactly what's missing before you apply for business funding.",
        sub="A business funding readiness review, a business-foundation checklist, a document-gap list, and a lender-readiness action plan. Education, not approvals.",
        problem="Owners apply for funding before they're 'bankable' — inconsistent business info, missing docs, weak credibility — and get slowed down.",
        deliverables=["Funding readiness score", "Business foundation checklist", "Document gap list",
                      "Bankability / business-credibility review", "Lender-readiness action plan", "Funding pathway recommendation"],
        steps=["Score your funding readiness (entity, banking, docs, credibility)",
               "Fix the business foundation gaps (name/address/phone/EIN consistency)",
               "Close the document gaps lenders commonly expect",
               "Follow a next-step funding-prep plan and re-score"],
        hooks=["The inconsistency that quietly stalls funding applications",
               "The 'Funding Docs' folder every owner should have ready",
               "What 'bankable' actually means before you apply"],
        lead_title="Business Funding Readiness Checklist", cta="Get your free funding readiness review",
        metric="readiness plans created"),
    "opportunity": dict(
        audience="people turning an interest into a real, testable online income idea",
        headline="Turn your interest into one testable offer — and filter out the internet noise.",
        sub="Idea-to-offer research, a scam/noise filter, a monetization path, a landing page + posts, a test campaign with metrics, and an improvement loop.",
        problem="Beginners drown in hype and chase 10 ideas at once instead of testing one real offer with real metrics.",
        deliverables=["Opportunity research summary", "Scam/noise filter", "Monetization path + offer recommendation",
                      "Landing page + social posts", "Lead magnet", "Test campaign + metrics tracker", "Improvement loop"],
        steps=["Research the idea → a specific, legitimate offer",
               "Filter scams/noise (avoid 'guaranteed income' traps)",
               "Pick ONE testable monetization path",
               "Create landing page + posts → run a test campaign → track metrics → improve"],
        hooks=["Stop chasing 10 ideas — test ONE offer the right way",
               "How to spot an online 'opportunity' scam in 30 seconds",
               "From interest to offer to first test campaign"],
        lead_title="Idea-to-Offer Starter Kit", cta="Get your free idea-to-offer plan",
        metric="clicks → replies"),
    "trading": dict(
        audience="people who want to structure and paper-test a trading idea safely",
        headline="Turn a trading idea into a structured, paper-tested strategy — with real risk rules.",
        sub="Strategy rules extraction, a backtest + paper-test plan, explicit risk rules, a performance tracker, and an improvement recommendation. Paper/demo only.",
        problem="People copy a YouTube strategy with no rules, no risk plan, and no way to judge if it actually works.",
        deliverables=["Extracted strategy rules", "Strategy checklist", "Backtest plan", "Paper-test plan",
                      "Risk rules / notes", "Performance tracker", "Improvement recommendation"],
        steps=["Extract the exact rules from the idea/source (entry, exit, filters)",
               "Define risk rules (stop, size, R-multiple) — before any test",
               "Build a backtest + paper-test plan",
               "Track demo performance and recommend improvements"],
        hooks=["Don't trade a YouTube strategy until it has these rules",
               "The risk rules that come BEFORE any entry",
               "How to judge a demo strategy honestly"],
        lead_title="Strategy Structuring Checklist", cta="Get your free paper-test plan",
        metric="paper-test plans created"),
    "ai_improvement": dict(
        audience="Ray / Nexus, evaluating tools that could improve the system",
        headline="Should Nexus adopt this tool? A scored evaluation with cost, effort, benefit, and risk.",
        sub="Tool/repo/feature evaluation with a cost estimate, implementation effort, benefit/risk scores, a recommended action, and an upgrade backlog.",
        problem="It's easy to chase every shiny AI tool; Nexus needs scored, Nexus-fit decisions — adapter-first, no auto-install.",
        deliverables=["Tool/repo/feature evaluation", "Cost estimate", "Implementation effort estimate",
                      "Benefit + risk scores", "Recommended action", "Upgrade backlog entry"],
        steps=["Evaluate the tool/repo/feature against Nexus needs",
               "Estimate cost + implementation effort",
               "Score benefit vs risk and assign an action (implement/test/adapter/monitor/defer/avoid)",
               "Add to the AI upgrade backlog; build a disabled adapter first"],
        hooks=["Is this AI tool worth it for Nexus? Here's the score.",
               "Adapter-first: how Nexus evaluates new tools safely",
               "The Nexus AI upgrade backlog, ranked by benefit"],
        lead_title="AI Tool Evaluation Scorecard", cta="See the scored recommendation",
        metric="recommendations created"),
}


def _reply(track: str, proj: dict) -> str:
    """Track-specific, impressive, compliance-safe reply preview."""
    p = TRACK_PROFILE[track]
    deliv = ", ".join(p["deliverables"][:5])
    disc = _disclaimer(track)
    intros = {
        "credit": f"Here's how Nexus can help: a credit readiness assessment, an issue checklist, a dispute/document-prep checklist, and a 30-day action plan — all educational guidance, with no guaranteed score increase or deletion.",
        "funding": f"Here's how Nexus can help: a business funding readiness review, a business-foundation checklist, a document-gap list, a bankability/business-credibility review, and a next-step funding-prep plan — educational, with no approval guarantee.",
        "opportunity": f"Here's how Nexus can help: idea-to-offer research, a scam/noise filter, a clear monetization path, a landing page + posts, a test campaign with metrics, and an improvement loop.",
        "trading": f"Here's how Nexus can help: strategy rules extraction, a backtest/paper-test plan, explicit risk rules, a performance tracker, and an improvement recommendation — paper/demo only, no live trading or profit guarantee.",
        "ai_improvement": f"Here's how Nexus evaluates it: a tool/repo/feature evaluation with a cost estimate, implementation effort, benefit/risk scores, a recommended action, and an entry on the upgrade backlog.",
    }
    return f"{intros[track]} Want me to send the {p['lead_title']} and your plan?  ({disc})"


def _bullets(items):
    return "\n".join(f"- {x}" for x in items)


def _numbered(items):
    return "\n".join(f"{i}. {x}" for i, x in enumerate(items, 1))


def _asset_body(track: str, atype: str, proj: dict) -> str:
    p = TRACK_PROFILE.get(track, TRACK_PROFILE["opportunity"])
    goal = proj.get("goal", "")
    disc = _disclaimer(track)
    aud = p["audience"]
    head = f"# {atype.replace('_',' ').title()} — {track} track (DRAFT / needs_review)\n_Goal: {goal}_\n"
    bodies = {
        "landing_page":
            f"## Headline\n{p['headline']}\n\n## Subheadline\n{p['sub']}\n\n## Who it's for\n{aud.capitalize()}.\n\n"
            f"## The problem\n{p['problem']}\n\n## What you get\n{_bullets(p['deliverables'])}\n\n"
            f"## How it works\n{_numbered(p['steps'])}\n\n## CTA\n**{p['cta']}**\n\n"
            f"## FAQ\nQ: Is this guaranteed? A: No — it's education + a clear plan you act on.\n\n## Disclaimer\n{disc}",
        "facebook_post":
            f"{p['hooks'][0]}\n\n{p['problem']} Here's a clearer way:\n{_numbered(p['steps'])}\n\nComment 'PLAN' and I'll send the free {p['lead_title']}.\n\n_{disc}_",
        "instagram_post":
            f"{p['hooks'][1]} (save this 📌)\n\n{_numbered(p['steps'][:3])}\n\nFree {p['lead_title']} in bio.\n\n_{disc}_",
        "linkedin_post":
            f"{p['hooks'][2]}\n\nA practical, no-hype approach for {aud}:\n{_bullets(p['deliverables'][:5])}\n\nEducation first — you stay in control. DM 'PLAN' for the checklist.\n\n_{disc}_",
        "short_video_script":
            f"Hook (0-3s): \"{p['hooks'][0]}\"\nBody (3-35s): {p['problem']} Do this instead — {('; '.join(p['steps']))}.\n"
            f"CTA (35-45s): \"{p['cta']} — link in bio.\"\nCompliance note: {disc}",
        "lead_magnet":
            f"# {p['lead_title']}\n_{p['sub']}_\n\n## Steps\n{_numbered(p['steps'])}\n\n## What's included\n{_bullets(p['deliverables'])}\n\n_{disc}_",
        "dm_reply": _reply(track, proj),
        "email_reply":
            f"Subject: Your next steps — {p['lead_title']}\n\nHi [First Name],\n\n{p['problem']}\n\nHere's the plan Nexus put together for you:\n{_numbered(p['steps'])}\n\nYou'll get: {', '.join(p['deliverables'][:5])}. Reply 'YES' and I'll send the {p['lead_title']}.\n\n— Ray @ Nexus\n_{disc}_",
        "intake_questions": _intake_questions(track),
        "follow_up_sequence":
            f"Day 1: deliver the {p['lead_title']} + summarize their starting point.\nDay 3: 'Any questions on step 1?'\n"
            f"Day 5: share one relevant tip from the plan.\nDay 7: offer a free readiness review (educational).\n_{disc}_",
        "metrics_plan":
            f"Funnel: views → clicks → replies → intake starts → intake completions → {p['metric']} → proof reports.\n"
            f"Primary metric: **{p['metric']}**.\nImprovement triggers: low clicks → revise headline; low replies → revise CTA/hook; high intake drop-off → simplify questions; weak deliverable → revise the plan content.",
        "proof_report":
            f"# Proof Report — {track} (template)\n- Audience: {aud}\n- Starting point: [from intake]\n- Top blockers: [identified]\n"
            f"- Deliverables provided: {', '.join(p['deliverables'][:4])}\n- Plan steps completed: [tracked]\n- Outcome: education + clear next steps (no guarantees)\n\n_{disc}_",
        "improvement_recommendation":
            f"If results are weak, re-test ONE variable at a time in this order: 1) headline/hook 2) CTA 3) offer framing 4) audience 5) channel. "
            f"For the {track} track specifically, sharpen the first deliverable ('{p['deliverables'][0]}') to be more concrete before changing the offer.",
    }
    return head + "\n" + bodies.get(atype, "(draft)")


def _intake_questions(track: str) -> str:
    q = {
        "credit": ["What's your main credit concern?", "Do you have a recent report to review?", "What's blocking you now?", "Goal in 90 days?"],
        "funding": ["Business stage?", "Entity / EIN / business bank set up?", "Revenue / time in business?", "Funding goal?"],
        "opportunity": ["Your interest/skill?", "Audience?", "Time/budget?", "Preferred channels?"],
        "trading": ["Market & timeframe?", "Strategy idea/source?", "Indicators?", "Risk rules?"],
        "ai_improvement": ["Tool/repo to evaluate?", "Problem it should solve?", "Nexus area?", "Budget/constraints?"],
    }.get(track, ["What's your goal?"])
    return "\n".join(f"{i}. {x}" for i, x in enumerate(q, 1))


# ── Metrics + feedback ───────────────────────────────────────────────────────
def log_metric(project_id: str, name: str, value) -> dict:
    rec = {"id": _id("metric", f"{project_id}:{name}:{_now()}"), "project_id": project_id,
           "name": name, "value": value, "at": _now()}
    return _append("metrics", rec)


def record_feedback(project_id: str, feedback: str) -> dict:
    rec = {"id": _id("fb", f"{project_id}:{_now()}"), "project_id": project_id, "feedback": feedback,
           "lesson": f"Apply to v2: {feedback}", "next_action": "revise_weakest_asset", "at": _now()}
    _append("feedback", rec)
    s = load()
    proj = next((p for p in s["projects"] if p["id"] == project_id), None)
    if proj:
        proj.setdefault("ray_feedback", []).append(feedback); proj["updated_at"] = _now(); _append("projects", proj)
    return rec


# ── Inbound / simulator ──────────────────────────────────────────────────────
INTENTS = {
    # order matters: ai_improvement + funding + credit + trading checked before the opportunity default
    "ai_improvement": ["research ", "evaluate", "should nexus use", "postiz", "mautic", "typebot",
                        "chatwoot", "openmanus", "repo", "ai tool", "ai feature"],
    "funding": ["business funding", "funding", "loan", "fund my business", "lender", "bankability"],
    "credit": ["credit", "fix my credit", "credit repair", "credit score", "dispute"],
    "trading": ["trading strategy", "forex", "backtest", "paper trade", "strategy on youtube", "indicator"],
    "opportunity": ["make money online", "online opportunity", "side hustle", "cleaning products", "affiliate"],
}


def classify_intent(message: str) -> str:
    low = message.lower()
    for track in ("ai_improvement", "funding", "credit", "trading", "opportunity"):
        if any(k in low for k in INTENTS[track]):
            return track
    return "opportunity"


def simulate(message: str, identity: str = "simulator") -> dict:
    track = classify_intent(message)
    proj = create_project(track, goal=message, audience="(from simulator)", mode="test_only")
    lead = {"id": _id("lead", f"{proj['id']}:{identity}"), "project_id": proj["id"], "identity": identity,
            "intent": track, "status": "interested", "at": _now()}
    _append("leads", lead)
    conv = {"id": _id("conv", lead["id"]), "lead_id": lead["id"], "project_id": proj["id"], "at": _now()}
    _append("conversations", conv)
    _append("messages", {"id": _id("msg", f"{conv['id']}:in"), "conversation_id": conv["id"],
                         "direction": "inbound", "text": message, "at": _now()})
    findings = run_scouts(proj["id"])
    rec = hermes_decision(proj["id"])
    assets = generate_assets(proj["id"])
    if track == "ai_improvement":
        ai_rec = ai_improvement_scout(_extract_tool(message))
    else:
        ai_rec = None
    reply = compliance_scrub(_reply(track, proj))
    _append("messages", {"id": _id("msg", f"{conv['id']}:out"), "conversation_id": conv["id"],
                         "direction": "outbound", "text": reply, "mode": "test_only", "at": _now()})
    log_metric(proj["id"], "ideas_submitted", 1)
    log_metric(proj["id"], "intake_starts", 1)
    pkg = register_showroom_package(track, proj["id"])
    prof = TRACK_PROFILE.get(track, TRACK_PROFILE["opportunity"])
    # top 3 generated assets (landing page, lead magnet, and the lead-channel post)
    top_types = ["landing_page", "lead_magnet", "facebook_post"]
    top3 = [{"asset_type": a["asset_type"], "file_path": a["file_path"], "status": a["status"]}
            for a in assets if a["asset_type"] in top_types]
    return {"track": track, "project_id": proj["id"], "lead_id": lead["id"], "findings": len(findings),
            "reply_preview": reply, "next_recommended_action": rec.get("recommended_action"),
            "top_assets": top3, "showroom_package": pkg.get("package_id"),
            "hermes_recommendation": rec.get("id"),
            "hermes_recommendation_summary": rec.get("decision_summary"),
            "metric_to_watch": prof["metric"], "assets": len(assets),
            "ai_recommendation": ai_rec, "mode": "test_only"}


def _extract_tool(message: str) -> str:
    for tool in AI_TOOLS:
        if tool.split("/")[0].lower() in message.lower():
            return tool
    return "Postiz"


# ── AI Improvement Scout ─────────────────────────────────────────────────────
def ai_improvement_scout(tool: str) -> dict:
    spec = AI_TOOLS.get(tool, AI_TOOLS["Postiz"])
    sc = spec["scores"]
    benefit = round((sc["revenue"] + sc["automation"] + sc["user_benefit"]) / 3, 1)
    rec = {
        "id": _id("ai_rec", tool), "tool": tool, "area": spec["area"], "cost_estimate": spec["cost"],
        "scores": sc, "benefit_score": benefit, "risk_score": sc["risk"],
        "recommended_action": spec["action"],
        "report_path": f"reports/showroom/ai_improvement_{tool.split('/')[0].lower().replace('+','_')}.md",
        "ray_approval_status": "pending", "needs_live_verification": True, "at": _now(),
    }
    _append("ai_improvement_recommendations", rec)
    _append("ai_research_items", {"id": _id("ai_item", tool), "tool": tool, "area": spec["area"],
                                  "status": "researched", "at": _now()})
    _append("ai_feature_watchlist", {"id": _id("ai_watch", tool), "tool": tool, "action": spec["action"], "at": _now()})
    # write the AI improvement report
    _write_ai_report(tool, spec, benefit)
    return rec


def _write_ai_report(tool: str, spec: dict, benefit: float) -> None:
    sc = spec["scores"]
    p = ROOT / spec.get("report_path", f"reports/showroom/ai_improvement_{tool.split('/')[0].lower()}.md") if False else \
        ROOT / "reports" / "showroom" / f"ai_improvement_{tool.split('/')[0].lower().replace('+','_')}.md"
    p.write_text(
        f"# AI Improvement Recommendation — {tool}\n_V1 · template scoring · NEEDS LIVE VERIFICATION_\n\n"
        f"1. Summary: Evaluate {tool} for {spec['area']}. Recommended action: **{spec['action']}**.\n"
        f"2. What it is: {tool} ({spec['area']}).\n3. Why it matters: improves Nexus {spec['area']}.\n"
        f"4. Nexus area improved: {spec['area']}.\n5. Cost estimate: {spec['cost']}.\n"
        f"6. Implementation estimate: adapter-first, sandbox before any install.\n"
        f"7. Benefits: revenue {sc['revenue']}/10, automation {sc['automation']}/10, user {sc['user_benefit']}/10 (benefit avg {benefit}).\n"
        f"8. Risks: risk {sc['risk']}/10 — no auto-install, no auto-connect, no paid APIs.\n"
        f"9. Required safeguards: disabled adapter, sandbox test, Ray approval before activation.\n"
        f"10. Recommended action: **{spec['action']}**.\n11. Build plan: create disabled adapter + interface.\n"
        f"12. Test plan: sandbox-only smoke test.\n13. Decision needed from Ray: approve sandbox/adapter? \n")


# ── Showroom package registration ────────────────────────────────────────────
PACKAGE_NAMES = {
    "credit": "Proof Automation — Credit Comeback Demo",
    "funding": "Proof Automation — Business Funding Readiness Demo",
    "opportunity": "Proof Automation — Online Opportunity Builder Demo",
    "trading": "Proof Automation — Trading Strategy Lab Demo",
    "ai_improvement": "Proof Automation — AI Improvement Scout Demo",
}


def register_showroom_package(track: str, project_id: str) -> dict:
    pkg_id = _id("pkg", f"{track}:{project_id}")
    s = load()
    proj = next((p for p in s["projects"] if p["id"] == project_id), None)
    if proj:
        proj["showroom_package_id"] = pkg_id; proj["updated_at"] = _now(); _append("projects", proj)
    pkg = {"id": pkg_id, "package_id": pkg_id, "name": PACKAGE_NAMES.get(track, f"Proof Automation — {track}"),
           "track": track, "project_id": project_id, "status": "needs_review", "at": _now()}
    _append("outcomes", pkg)
    return pkg


# ── Seed ─────────────────────────────────────────────────────────────────────
SEED_PROJECTS = [
    ("credit", "Help a person understand what to do next to improve credit readiness."),
    ("funding", "Help a business owner see what is missing before seeking funding."),
    ("opportunity", "Turn an interest (e.g. cleaning products) into a testable online income campaign."),
    ("trading", "Turn a strategy idea into a paper-test plan."),
    ("ai_improvement", "Evaluate Postiz, Mautic, Typebot/n8n, Chatwoot, Manus/OpenManus, Hermes features, local models for Nexus."),
]


def seed_all() -> dict:
    results = []
    for track, goal in SEED_PROJECTS:
        proj = create_project(track, goal, mode="test_only")
        run_scouts(proj["id"])
        hermes_decision(proj["id"])
        generate_assets(proj["id"])
        register_showroom_package(track, proj["id"])
        log_metric(proj["id"], "proof_reports_created", 1)
        results.append(proj["id"])
    # AI improvement scout over the full catalogue
    for tool in AI_TOOLS:
        ai_improvement_scout(tool)
    return {"seeded_projects": results, "ai_recommendations": len(AI_TOOLS)}


def summary() -> dict:
    s = load()
    return {c: len(s.get(c, [])) for c in
            ["projects", "scout_findings", "assets", "leads", "messages", "metrics",
             "recommendations", "feedback", "outcomes", "ai_improvement_recommendations", "ai_feature_watchlist"]}
