"""
hermes_monetization_scout.py
============================
CFO / Monetization Scout layer. When Ray pastes a transcript, article, notes, or
any source content and asks a strategic/monetization question, Hermes must treat
that pasted content as PRIMARY evidence and return a practical Nexus-first revenue
plan — NOT an artifact/evidence dump and NOT a generic summary.

Routing (called from hermes_conversational_router BEFORE evidence/opportunities):
  exact command → user-provided source analysis (here) → CFO/scout → scout dispatch
  → evidence dump (only if explicitly requested).

Deterministic, local-only: no paid API, no network, no publishing, no secrets.
"""
from __future__ import annotations

import re

# ── Intent + source detection ───────────────────────────────────────────────
SCOUT_TRIGGERS = (
    "monetization scout", "monetize", "monetization", "revenue plan", "revenue",
    "business idea", "side hustle", "offer", "landing page angle", "fastest cash",
    "cash flow", "cash-flow", "what can nexus do with this", "what can we do with this",
    "turn this into", "make money", "income", "productize", "package this",
    "growth pack", "content service",
)

# Risky/unverified claim patterns to flag (inspiration only, not marketing facts).
RISK_PATTERNS = {
    "income claim": r"\$\s?\d[\d,]*\s*(?:/|per\s*|a\s+)?(?:k|month|mo|day|week|year|hour)|\d+\s*(?:k|figures)\s*(?:a|per)?\s*month|full[- ]?time income|replace your (?:job|income)|quit your job",
    "guarantee claim": r"guarantee|guaranteed|risk[- ]?free|can't lose|always works",
    "easy-money claim": r"easy money|passive income|get rich|overnight|effortless|no work|while you sleep",
    "platform/algorithm claim": r"the algorithm (?:loves|rewards|favors)|go viral|guaranteed views|beat the algorithm",
    "funding claim": r"guaranteed funding|approved funding|\$\d[\d,]*\s*(?:in )?funding|fund your business fast",
    "trading claim": r"guaranteed (?:profit|returns|trades)|win rate|double your money",
}


def has_user_provided_source(message: str) -> bool:
    """True if the message itself contains pasted source content (transcript/article/notes)."""
    if not message:
        return False
    t = message.strip()
    # explicit markers
    markers = ("transcript", "[music]", "[applause]", "—transcript", "here's the transcript",
               "video:", "pasted", "article:", "notes:", "```")
    low = t.lower()
    if any(m in low for m in markers):
        return True
    # substantial pasted block: long text and/or many lines (a strategic ask alone is short)
    if len(t) >= 600:
        return True
    if t.count("\n") >= 8 and len(t) >= 300:
        return True
    # timestamp lines like 0:12 / 00:01:23 typical of transcripts
    if len(re.findall(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", t)) >= 3:
        return True
    return False


def is_monetization_scout_request(message: str) -> bool:
    low = (message or "").lower()
    return any(trig in low for trig in SCOUT_TRIGGERS)


def should_handle(message: str) -> bool:
    """Route here when a source is provided AND a monetization/strategic ask is present."""
    return has_user_provided_source(message) and is_monetization_scout_request(message)


# ── Analysis ─────────────────────────────────────────────────────────────────
# Idea catalogue with Nexus-fit scoring. Each idea scored 1-10 on the dimensions
# Ray specified. Ideas that REUSE existing Nexus systems rank highest (speed to cash).
_IDEA_CATALOGUE = [
    dict(name="Done-for-you AI content service (newsletters + shorts + posts)",
         keywords=("content", "newsletter", "short", "post", "video", "script", "social", "marketing", "ai", "automation", "faceless"),
         nexus_fit=10, speed_to_cash=9, recurring=9, ease=9, risk=2,
         reuses=["content engine", "newsletters", "YouTube short scripts", "landing page drafts", "showroom", "feedback memory", "Postiz", "HyperFrames", "Supabase artifacts"]),
    dict(name="AI lead-magnet + landing page funnel build",
         keywords=("landing", "funnel", "lead", "offer", "opt-in", "email", "list", "magnet"),
         nexus_fit=8, speed_to_cash=8, recurring=5, ease=8, risk=3,
         reuses=["landing page drafts", "content engine", "showroom", "Postiz"]),
    dict(name="AI content strategy/audit retainer",
         keywords=("strategy", "audit", "consult", "coach", "calendar", "plan"),
         nexus_fit=7, speed_to_cash=6, recurring=8, ease=7, risk=3,
         reuses=["content engine", "feedback memory", "showroom"]),
    dict(name="Faceless YouTube/short-video channel-as-a-service",
         keywords=("youtube", "channel", "faceless", "video", "shorts", "views", "subscribers"),
         nexus_fit=6, speed_to_cash=4, recurring=6, ease=5, risk=5,
         reuses=["HyperFrames", "YouTube short scripts", "content engine"]),
    dict(name="Sell an AI course/info-product",
         keywords=("course", "info product", "teach", "audience", "community", "cohort"),
         nexus_fit=3, speed_to_cash=2, recurring=4, ease=3, risk=6,
         reuses=["content engine"]),
    dict(name="AI tool/SaaS build",
         keywords=("saas", "app", "tool", "software", "build a tool", "micro saas"),
         nexus_fit=3, speed_to_cash=2, recurring=8, ease=2, risk=6,
         reuses=["landing page drafts"]),
]


def _composite(idea: dict) -> float:
    # Nexus-first weighting: fit + speed + ease + recurring, minus risk.
    return round(
        idea["nexus_fit"] * 0.30 + idea["speed_to_cash"] * 0.25 + idea["ease"] * 0.20
        + idea["recurring"] * 0.15 + (10 - idea["risk"]) * 0.10, 2)


def extract_ideas(source: str) -> list[dict]:
    low = (source or "").lower()
    scored = []
    for idea in _IDEA_CATALOGUE:
        hits = sum(1 for k in idea["keywords"] if k in low)
        if hits == 0:
            continue
        scored.append({**idea, "evidence_hits": hits, "composite": _composite(idea)})
    # If nothing matched (sparse transcript), still offer the safest executable default.
    if not scored:
        d = _IDEA_CATALOGUE[0]
        scored = [{**d, "evidence_hits": 0, "composite": _composite(d)}]
    scored.sort(key=lambda x: (x["composite"], x["evidence_hits"]), reverse=True)
    return scored


def detect_risks(source: str) -> list[str]:
    low = (source or "").lower()
    found = []
    for label, pat in RISK_PATTERNS.items():
        if re.search(pat, low):
            found.append(label)
    return found


# ── Preferred offers (Nexus-first, executable now with existing systems) ──────
_CONTENT_PACK_OFFER = {
    "name": "30-Day AI Content Growth Pack",
    "target": "small business owners, coaches, consultants, funding/credit pros, local service businesses, and agencies that need consistent marketing content",
    "deliverables": [
        "4 newsletter drafts", "8 short-form video scripts", "4 social posts",
        "1 landing page draft", "1 lead magnet outline", "1 content strategy summary",
    ],
    "pricing": ["$197 beta", "or $297 setup + $497/month recurring after validation"],
    "why": "Reuses Nexus's existing content engine, landing page drafts, showroom, feedback memory, Postiz planning, and HyperFrames packet workflow — fastest path to cash with no new build.",
    "landing_angle": "\"Consistent, on-brand marketing content every month — without hiring a team or learning AI tools. We draft your newsletters, short-video scripts, and posts; you approve.\"",
    "lead_magnet": "\"The 30-Day AI Content Starter Kit\" — 1 sample newsletter + 2 short-video scripts + a 7-day posting calendar (free), delivered via the content engine to capture leads.",
    "showroom_asset": "1 sample 30-Day Pack (4 newsletters, 8 scripts, 4 posts, 1 landing draft, 1 lead-magnet outline, 1 strategy summary)",
    "next_action": "Create ONE sample 30-Day AI Content Growth Pack for GoClear/Nexus, add it to the showroom, notify Ray (Ray-only), and use Ray's feedback to improve v2. Do NOT publish publicly without Ray approval.",
    "next_command": "python3 scripts/run_monetization_scout.py --build-sample-pack --notify --dry-run",
}

# Ray's preferred FIRST money offer for the current 30-day goal (proof_credit exists).
_CREDIT_FUNDING_OFFER = {
    "name": "Credit/Funding Readiness Review",
    "target": "new and existing business owners, entrepreneurs, and credit-repair/funding clients who want to qualify for business funding",
    "deliverables": [
        "business credit + fundability assessment", "Paydex / vendor-tradeline readiness checklist",
        "lender-readiness report (gaps + next steps)", "30-day action plan to improve fundability",
    ],
    "pricing": ["$97 starter review", "or $197–$297 full readiness review + report"],
    "why": "Reuses Nexus's proof_credit package, showroom, and report/checklist workflows; high-intent buyers; education-only (no guarantees) — fastest cash for Ray's current 30-day goal with assets that already exist.",
    "landing_angle": "\"Find out if your business is fundable — and exactly what to fix first. A clear readiness review + 30-day action plan. Education only, no guarantees, no hard pull.\"",
    "lead_magnet": "\"The Business Funding Readiness Checklist\" — a free self-scoring checklist (Paydex, business credit file, fundability gaps) that captures leads into the review offer.",
    "showroom_asset": "1 sample Credit/Funding Readiness Review (assessment + checklist + lender-readiness report + 30-day plan)",
    "next_action": "Create ONE sample Credit/Funding Readiness Review from the proof_credit package, add it to the showroom (needs_review), notify Ray (Ray-only). Draft outreach + intake checklist + report outline as APPROVAL-GATED tasks. Do NOT contact customers or take payment without Ray approval.",
    "next_command": "python3 scripts/run_monetization_scout.py --build-sample-pack --notify --dry-run",
}

# Credit/Funding signals — when present, Ray's preferred money-now offer ranks first.
_CREDIT_FUNDING_SIGNALS = (
    "credit", "funding", "fundability", "paydex", "tradeline", "lender", "loan",
    "business credit", "llc", "capital", "underwriting", "net 30", "vendor credit",
    "proof_credit",
)


def _select_offer(source: str) -> dict:
    """Pick the Nexus-first offer. Credit/Funding Readiness ranks first for Ray's
    current 30-day money goal whenever the source signals credit/funding; otherwise
    the content pack. The content pack is never removed — only re-ranked."""
    s = (source or "").lower()
    if any(sig in s for sig in _CREDIT_FUNDING_SIGNALS):
        return _CREDIT_FUNDING_OFFER
    return _CONTENT_PACK_OFFER


def analyze_source(source: str) -> dict:
    ideas = extract_ideas(source)
    best = ideas[0]
    risks = detect_risks(source)
    offer = _select_offer(source)
    return {"ideas": ideas, "best_idea": best, "offer": offer, "risks": risks,
            "source_chars": len(source or "")}


# ── Response formatting (the required 12-part shape) ─────────────────────────
def format_scout_response(a: dict) -> str:
    best = a["best_idea"]
    offer = a["offer"]
    ideas = a["ideas"]
    risks = a["risks"]

    risk_block = ("\n".join(f"  - ⚠️ {r} — inspiration only; do NOT repeat as a marketing fact unless verified"
                            for r in risks)
                  if risks else "  - No high-risk claims detected; still avoid unverified income/guarantee language.")

    L = [
        "NEXUS MONETIZATION SCOUT",
        f"(analyzed your pasted source directly — {a['source_chars']} chars — as primary evidence)\n",

        "1) EXECUTIVE RECOMMENDATION",
        f"   Launch the **{offer['name']}** as a beta service. It's the idea Nexus can ship fastest "
        "using systems that already exist — not the flashiest idea in the transcript.\n",

        "2) TOP IDEAS EXTRACTED",
        *[f"   - {i['name']} (signal hits: {i['evidence_hits']})" for i in ideas[:5]],
        "",

        "3) RANKED NEXUS FIT (fit·speed·ease·recurring − risk)",
        *[f"   {n}. {i['name']} — score {i['composite']} "
          f"(fit {i['nexus_fit']}, speed {i['speed_to_cash']}, ease {i['ease']}, recurring {i['recurring']}, risk {i['risk']})"
          for n, i in enumerate(ideas[:5], 1)],
        "",

        "4) BEST FIRST OFFER",
        f"   {offer['name']}",
        f"   Target: {offer['target']}",
        "   Deliverables: " + "; ".join(offer["deliverables"]),
        "   Beta pricing: " + " · ".join(offer["pricing"]),
        f"   Why: {offer['why']}\n",

        "5) LANDING PAGE ANGLE",
        f"   {offer['landing_angle']}\n",

        "6) LEAD MAGNET IDEA",
        f"   {offer['lead_magnet']}\n",

        "7) CONTENT ANGLES",
        "   - \"What I'd post for 30 days if I ran your business\"",
        "   - \"3 newsletters that bring back old customers\"",
        "   - \"The boring content system that beats going viral\"",
        "   - Niche cuts for funding/credit pros, coaches, local services.\n",

        "8) SHOWROOM ASSETS TO CREATE",
        f"   - {offer['showroom_asset']}",
        "   - Each registered as a reviewable asset (needs_review) for Ray feedback.\n",

        "9) POSTIZ / HYPERFRAMES USE",
        "   - Postiz: schedule the approved posts/newsletter cadence (draft-only until Ray approves).",
        "   - HyperFrames: turn the top 2 video scripts into storyboard/video packets for demo.\n",

        "10) RISKS & WEAK CLAIMS (from the source)",
        risk_block, "",

        "11) NEXT SAFE ACTION",
        f"   {offer['next_action']}",
        f"   Command: {offer['next_command']}\n",

        "12) MEMORY LESSONS",
        "   - Pasted source = primary evidence; analyze it before any artifact/evidence lookup.",
        "   - Rank by Nexus fit + speed to cash + recurring + ease − risk; reuse existing systems.",
        "   - For AI side-hustle transcripts, favor a service Nexus can deliver now over audience-building.",
        "   - Never repeat unverified income/funding/trading/platform claims as marketing facts.",
        "   - Always end with one next safe action + what needs Ray approval.\n",

        "REQUIRES RAY APPROVAL: public posting, real emails, Stripe/pricing go-live, affiliate signup, paid ads.",
    ]
    return "\n".join(L)


def run_scout(message: str) -> str:
    """Entry point: analyze the pasted source and return the 12-part scout response."""
    return format_scout_response(analyze_source(message))
