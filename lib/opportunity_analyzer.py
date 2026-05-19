"""
Nexus Opportunity Intelligence Engine
--------------------------------------
Analyzes business ideas, URLs, tools, niches, and opportunities.
Returns structured scoring and execution roadmap.
Called by hermes_internal_first.py when Hermes detects an opportunity input.

Safety: No financial guarantees. Educational analysis only.
"""

import re
from typing import Optional


# ─── Trigger Detection ────────────────────────────────────────────────────────

OPPORTUNITY_TRIGGERS = [
    # Direct analysis requests
    r'\banalyze\b.*\bopportunity\b',
    r'\bscore\b.*\bbusiness\b',
    r'\bcan nexus monetize\b',
    r'\bcan (we|this) automate\b',
    r'\bcould this (make money|be automated|work)\b',
    r'\bwould this business work\b',
    r'\bhow quickly could this\b',
    r'\bwhat would the roadmap\b',
    r'\bresearch this (niche|saas|affiliate|tool|app|business|idea)\b',
    r'\bfaceless content business\b',
    r'\bmonetize this\b',
    r'\bopportunity analysis\b',
    r'\bscore (this|the) opportunity\b',
    r'\bwhat do you think about this\b',
    # URL detection
    r'https?://',
    r'www\.',
    # Opportunity nouns
    r'\b(saas|affiliate program|youtube channel|niche|newsletter business|digital product|course|app idea)\b',
]

OPPORTUNITY_TRIGGER_RE = re.compile(
    '|'.join(OPPORTUNITY_TRIGGERS), re.IGNORECASE
)


def is_opportunity_input(text: str) -> bool:
    """Return True if the input looks like an opportunity analysis request."""
    return bool(OPPORTUNITY_TRIGGER_RE.search(text))


# ─── Opportunity Scoring ──────────────────────────────────────────────────────

def score_opportunity(opportunity_text: str) -> dict:
    """
    Score an opportunity across 7 dimensions.
    Returns a scored report dict.
    """
    text = opportunity_text.lower()

    # Heuristic scoring — pattern-based, not AI inference
    scores = {
        'startup_cost':      _score_startup_cost(text),
        'time_to_revenue':   _score_time_to_revenue(text),
        'automation':        _score_automation(text),
        'scalability':       _score_scalability(text),
        'recurring_revenue': _score_recurring(text),
        'nexus_synergy':     _score_nexus_synergy(text),
        'operational_ease':  _score_ops_ease(text),
    }

    weights = {
        'startup_cost': 1.0,
        'time_to_revenue': 1.5,
        'automation': 2.0,
        'scalability': 1.5,
        'recurring_revenue': 1.5,
        'nexus_synergy': 2.0,
        'operational_ease': 1.0,
    }

    weighted_total = sum(scores[k] * weights[k] for k in scores)
    max_score = sum(10 * w for w in weights.values())
    final_score = round((weighted_total / max_score) * 100)

    category = _classify(final_score)

    return {
        'score': final_score,
        'category': category,
        'dimension_scores': scores,
        'weights': weights,
        'weighted_total': round(weighted_total, 1),
    }


def _score_startup_cost(text: str) -> int:
    if any(w in text for w in ['free', '$0', 'no cost', 'zero cost']):
        return 10
    if any(w in text for w in ['cheap', 'low cost', '$10', '$15', '$20', '$50']):
        return 8
    if any(w in text for w in ['$100', '$200', '$300', '$500']):
        return 5
    if any(w in text for w in ['$1000', '$2000', 'expensive', 'hardware']):
        return 2
    return 7  # default medium


def _score_time_to_revenue(text: str) -> int:
    if any(w in text for w in ['same day', 'within days', '3 days', '1 week', 'week 1']):
        return 9
    if any(w in text for w in ['2 weeks', 'month 1', 'first month']):
        return 7
    if any(w in text for w in ['6 weeks', '2 months', '3 months']):
        return 5
    if any(w in text for w in ['6 months', 'year', 'long-term']):
        return 2
    return 6


def _score_automation(text: str) -> int:
    if any(w in text for w in ['fully automated', 'full automation', 'runs itself']):
        return 10
    if any(w in text for w in ['ai', 'nexus', 'automated', 'workflow', 'content generation']):
        return 8
    if any(w in text for w in ['semi-automated', 'partly automated', 'some manual']):
        return 5
    if any(w in text for w in ['manual', 'hands-on', 'client calls', 'consulting']):
        return 3
    return 6


def _score_scalability(text: str) -> int:
    if any(w in text for w in ['unlimited', 'infinite scale', 'passive', 'content', 'saas']):
        return 9
    if any(w in text for w in ['youtube', 'newsletter', 'blog', 'affiliate', 'digital product']):
        return 8
    if any(w in text for w in ['service business', 'agency', 'freelance']):
        return 5
    if any(w in text for w in ['local', 'physical', 'in-person']):
        return 3
    return 6


def _score_recurring(text: str) -> int:
    if any(w in text for w in ['mrr', 'monthly recurring', 'subscription', 'saas', 'retainer']):
        return 10
    if any(w in text for w in ['recurring', 'monthly', 'newsletter', 'membership']):
        return 8
    if any(w in text for w in ['affiliate', 'commission']):
        return 6
    if any(w in text for w in ['one-time', 'single purchase', 'one time']):
        return 3
    return 5


def _score_nexus_synergy(text: str) -> int:
    if any(w in text for w in ['content generation', 'research', 'seo', 'affiliate', 'faceless', 'ai writing']):
        return 10
    if any(w in text for w in ['youtube', 'newsletter', 'blog', 'marketing', 'analysis']):
        return 9
    if any(w in text for w in ['saas', 'digital product', 'course', 'lead generation']):
        return 7
    if any(w in text for w in ['coaching', 'consulting', 'service', 'agency']):
        return 5
    return 6


def _score_ops_ease(text: str) -> int:
    if any(w in text for w in ['automated', 'passive', 'no staff', 'runs itself']):
        return 10
    if any(w in text for w in ['simple', 'low maintenance', 'minimal effort']):
        return 8
    if any(w in text for w in ['moderate', 'some effort', 'part-time']):
        return 5
    if any(w in text for w in ['full-time', 'team needed', 'high maintenance', 'client calls']):
        return 2
    return 6


def _classify(score: int) -> str:
    if score >= 88:
        return 'Quick Win'
    if score >= 78:
        return 'High Leverage'
    if score >= 65:
        return 'Scalable Asset'
    if score >= 50:
        return 'Experimental'
    return 'Avoid'


# ─── Report Generator ─────────────────────────────────────────────────────────

def generate_opportunity_report(opportunity_text: str, context: Optional[str] = None) -> str:
    """
    Generate a full structured opportunity analysis report.
    Returns formatted text suitable for Telegram or Hermes response.
    """
    scoring = score_opportunity(opportunity_text)

    # Extract a clean opportunity name (first ~50 chars or extracted URL)
    url_match = re.search(r'https?://[^\s]+', opportunity_text)
    if url_match:
        opp_name = url_match.group(0)[:60]
        opp_type = 'URL / Tool / Platform'
    else:
        opp_name = opportunity_text[:60] + ('…' if len(opportunity_text) > 60 else '')
        opp_type = _detect_type(opportunity_text)

    score = scoring['score']
    category = scoring['category']
    dims = scoring['dimension_scores']

    # Revenue + startup cost estimates
    rev_estimate = _estimate_revenue(score, opp_type)
    startup_cost = _estimate_startup_cost(dims['startup_cost'])

    # Roadmap
    roadmap_7d = _roadmap_7d(opp_type, category)
    roadmap_30d = _roadmap_30d(opp_type, category)
    roadmap_90d = _roadmap_90d(score, opp_type)

    # Workforce assignments
    assignments = _assign_workers(opp_type, category)

    competition = _competition_analysis(opp_type, score)

    report = f"""
╔══════════════════════════════════════════════╗
   NEXUS OPPORTUNITY REPORT
   Educational analysis only — no guarantees
╚══════════════════════════════════════════════╝

OPPORTUNITY: {opp_name}
TYPE: {opp_type}
CATEGORY: {category}  |  SCORE: {score}/100

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIMENSION SCORES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Startup Cost:        {dims['startup_cost']}/10 — {startup_cost}
Time to Revenue:     {dims['time_to_revenue']}/10
Automation:          {dims['automation']}/10
Scalability:         {dims['scalability']}/10
Recurring Revenue:   {dims['recurring_revenue']}/10
Nexus Synergy:       {dims['nexus_synergy']}/10
Operational Ease:    {dims['operational_ease']}/10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REVENUE POTENTIAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rev_estimate}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPETITION ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{competition}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7-DAY ROADMAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{roadmap_7d}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
30-DAY ROADMAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{roadmap_30d}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
90-DAY SCALING PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{roadmap_90d}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKFORCE ASSIGNMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{assignments}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTENT OPPORTUNITIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_content_potential(opp_type, score)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AFFILIATE POTENTIAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_affiliate_potential(opp_type, score)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RISKS + CONSIDERATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_risks(opp_type, score)}

RECOMMENDATION: {_recommendation(category, score)}

⚠️ Educational analysis only. No financial guarantees.
Results depend on execution, market conditions, and effort.
""".strip()

    # Auto-create a Supabase dispatch task so this opportunity is tracked
    create_dispatch_task(opp_name, score, category)

    return report


def _detect_type(text: str) -> str:
    text = text.lower()
    if re.search(r'https?://', text):
        return 'URL / Tool / Platform'
    if any(w in text for w in ['youtube', 'video', 'channel', 'faceless']):
        return 'Faceless YouTube Channel'
    if any(w in text for w in ['newsletter', 'email list', 'substack']):
        return 'Newsletter Business'
    if any(w in text for w in ['affiliate', 'referral program']):
        return 'Affiliate Opportunity'
    if any(w in text for w in ['saas', 'software', 'app', 'platform']):
        return 'SaaS / Software'
    if any(w in text for w in ['course', 'digital product', 'ebook', 'template']):
        return 'Digital Product'
    if any(w in text for w in ['agency', 'service', 'consulting', 'freelance']):
        return 'Service Business'
    if any(w in text for w in ['niche', 'blog', 'seo', 'content']):
        return 'Content / SEO Business'
    if any(w in text for w in ['local', 'brick and mortar', 'physical']):
        return 'Local Business'
    return 'Business Opportunity'


def _estimate_revenue(score: int, opp_type: str) -> str:
    if score >= 90:
        return "High: $2,000–$15,000/mo potential at scale\nMonth 1 target: $500–$2,000\nCeiling: $50,000+/mo with strong execution"
    if score >= 75:
        return "Moderate-High: $1,000–$8,000/mo potential at scale\nMonth 1 target: $200–$1,000\nCeiling: $20,000+/mo"
    if score >= 60:
        return "Moderate: $500–$3,000/mo potential at scale\nMonth 1 target: $100–$500\nCeiling: $10,000+/mo"
    return "Lower: $200–$1,500/mo potential\nMonth 1 target: $50–$200\nCeiling: $5,000/mo"


def _estimate_startup_cost(cost_score: int) -> str:
    if cost_score >= 9: return "$0 — free to start"
    if cost_score >= 7: return "$0–$50 — minimal tools"
    if cost_score >= 5: return "$50–$300 — some tool costs"
    return "$300–$1,000+ — meaningful upfront cost"


def _roadmap_7d(opp_type: str, category: str) -> str:
    if category in ('Quick Win', 'High Leverage'):
        return """Day 1: Research + validate the core opportunity
Day 2: Create offer or content plan
Day 3: Set up distribution (content, landing page, or outreach)
Day 4: Publish first piece / send first outreach
Day 5: Track response + iterate
Day 6: Identify affiliate or monetization hooks
Day 7: Create dispatch tasks for week 2 scale"""
    return """Day 1-2: Deep research phase — market, competition, margins
Day 3-4: Build minimal viable version or content
Day 5-6: Test with small audience or outreach batch
Day 7: Evaluate results, decide on next sprint"""


def _roadmap_30d(opp_type: str, category: str) -> str:
    return """Week 1: Launch + first iteration
Week 2: First revenue test or audience building
Week 3: Identify what's working, double down
Week 4: Scale the working channel, add affiliate layer
Month-end target: First paying customer or 100 engaged audience"""


def _roadmap_90d(score: int, opp_type: str) -> str:
    if score >= 85:
        return """Month 1: $500–$2K revenue, audience foundation
Month 2: $1.5K–$5K revenue, affiliate revenue layer active
Month 3: $3K–$10K revenue, recurring component live
By Day 90: Systematized and delegated to Nexus workers"""
    return """Month 1: Test and validate core mechanics
Month 2: Scale what works, cut what doesn't
Month 3: Build toward predictable revenue stream
By Day 90: Clear decision point — scale or pivot"""


def _assign_workers(opp_type: str, category: str) -> str:
    assignments = []
    text = opp_type.lower()
    if any(w in text for w in ['youtube', 'faceless', 'content', 'seo', 'newsletter']):
        assignments.append("→ content_worker: script writing, article drafts, repurposing")
        assignments.append("→ seo_worker: keyword research, article optimization")
    if any(w in text for w in ['affiliate', 'referral', 'commission']):
        assignments.append("→ affiliate_worker: program research, link management")
    if any(w in text for w in ['saas', 'software', 'app', 'landing page']):
        assignments.append("→ codex: implementation, code generation")
        assignments.append("→ nexus_launch_engine: product page, checkout flow")
    if any(w in text for w in ['research', 'niche', 'market', 'opportunity']):
        assignments.append("→ research_worker: niche validation, competition analysis")
    if any(w in text for w in ['service', 'agency', 'consulting']):
        assignments.append("→ comms_worker: outreach templates, pitch decks")
    assignments.append("→ Hermes: coordination, approval gates, CEO digest updates")
    return '\n'.join(assignments) if assignments else "→ research_worker: initial deep dive\n→ Hermes: coordination"


def _content_potential(opp_type: str, score: int) -> str:
    if score >= 80:
        return """HIGH — Multiple content angles available:
• YouTube long-form (educational, how-to, comparison)
• YouTube Shorts (quick tips, stats, explainers)
• SEO articles (how-to, comparison, ranked lists)
• Newsletter section (tool pick, opportunity spotlight)
• LinkedIn posts (business owner angle)"""
    return """MODERATE — Content angles:
• 1-2 article topics for SEO
• 1-2 social posts
• Newsletter mention"""


def _affiliate_potential(opp_type: str, score: int) -> str:
    text = opp_type.lower()
    if any(w in text for w in ['ai', 'tool', 'software', 'saas']):
        return "HIGH — Most SaaS tools have affiliate programs (20–45% recurring)\nCheck: PartnerStack, Impact.com, or direct"
    if any(w in text for w in ['business', 'funding', 'credit', 'financial']):
        return "HIGH — Financial niche affiliates pay $30–$500/conversion\nNav, Lendio, Bluevine, ZenBusiness"
    if score >= 75:
        return "MODERATE — Look for complementary tools or services with affiliate programs"
    return "LOW-MODERATE — Research affiliate angles before committing"


def _risks(opp_type: str, score: int) -> str:
    risks = []
    text = opp_type.lower()
    if 'youtube' in text or 'content' in text:
        risks.append("• YouTube algorithm dependency — build email list as backup")
        risks.append("• Time to AdSense threshold: 1,000 subscribers + 4,000 hours")
    if 'affiliate' in text:
        risks.append("• Program terms can change — diversify across 3+ programs")
        risks.append("• Cookie tracking limitations — use first-touch attribution")
    if 'saas' in text:
        risks.append("• Technical complexity — ensure Nexus can handle build")
        risks.append("• Churn risk — need strong onboarding and product quality")
    if score < 70:
        risks.append("• Lower score = higher execution risk — test before scaling")
    risks.append("• Market conditions always change — build multiple revenue streams")
    risks.append("• No financial guarantees — results vary by execution quality")
    return '\n'.join(risks) if risks else "• Standard business risk — validate before scaling"


def _recommendation(category: str, score: int) -> str:
    if category == 'Quick Win':
        return "LAUNCH THIS WEEK — high confidence, low risk, fast payback"
    if category == 'High Leverage':
        return "START WITHIN 2 WEEKS — strong fundamentals, build now"
    if category == 'Scalable Asset':
        return "START WITHIN MONTH 1 — good long-term play, start content/research"
    if category == 'Experimental':
        return "TEST FIRST — run a small validation experiment before committing"
    return "AVOID or RESEARCH MORE — score too low to recommend investment"


def _competition_analysis(opp_type: str, score: int) -> str:
    text = opp_type.lower()
    if 'youtube' in text or 'faceless' in text:
        return ("Competition: HIGH volume, but most content is low quality.\n"
                "Differentiation: Niche down to business credit/funding/AI tools.\n"
                "Moat: Consistency + Nexus proprietary data angle.\n"
                "Barrier to entry: Low — advantage goes to first movers who niche.")
    if 'saas' in text or 'software' in text:
        return ("Competition: MEDIUM-HIGH — crowded market, but niche SaaS can dominate.\n"
                "Differentiation: Solve a specific pain point better than existing tools.\n"
                "Moat: Integrations, data network effects, switching costs.\n"
                "Barrier to entry: Medium — technical build required.")
    if 'newsletter' in text or 'email' in text:
        return ("Competition: LOW-MEDIUM — newsletters have low discovery but high retention.\n"
                "Differentiation: Curated niche + exclusive Nexus analysis angle.\n"
                "Moat: Subscriber relationships — hard to migrate.\n"
                "Barrier to entry: Very low — advantage to consistent, valuable publishers.")
    if 'affiliate' in text:
        return ("Competition: HIGH — many affiliates in most niches.\n"
                "Differentiation: Authority content + first-touch SEO strategy.\n"
                "Moat: Domain authority, email list, trust with audience.\n"
                "Barrier to entry: Low — but SEO moat takes 6–12 months to build.")
    if 'grant' in text or 'funding' in text or 'credit' in text:
        return ("Competition: LOW — grant research and funding coaching is underserved.\n"
                "Differentiation: AI-powered research at fraction of consultant price.\n"
                "Moat: Data + reputation + client results.\n"
                "Barrier to entry: Low — trust is the primary differentiator.")
    if score >= 80:
        return ("Competition: MODERATE — validated opportunity attracts players.\n"
                "Differentiation: Move fast, niche down, build audience before competition scales.\n"
                "Moat: First-mover advantage + Nexus AI infrastructure.\n"
                "Barrier to entry: Low-Medium.")
    return ("Competition: VARIABLE — research existing players before committing.\n"
            "Recommended: Search top 10 YouTube videos and Google results for the niche.\n"
            "Assess: Can we create content or a product better than the top 3 results?")


def create_dispatch_task(opp_name: str, score: int, category: str) -> dict:
    """
    Create a Supabase dispatch task when an opportunity is analyzed.
    Returns the created task dict or empty dict on failure.
    """
    try:
        import os
        import requests as _req
        from datetime import datetime, timezone

        url = os.environ.get('SUPABASE_URL', '')
        key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
        if not url or not key:
            return {}

        task = {
            'source': 'lane4_opportunity',
            'original_prompt': f'Opportunity analyzed: {opp_name[:120]}',
            'normalized_goal': f'[{category}] Score {score}/100 — {opp_name[:80]}',
            'task_type': 'research',
            'risk_level': 'low',
            'status': 'received',
            'approval_required': False,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        r = _req.post(
            f'{url}/rest/v1/agent_dispatch_tasks',
            headers={
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation',
            },
            json=task,
            timeout=5,
        )
        if r.status_code in (200, 201):
            data = r.json()
            return data[0] if isinstance(data, list) else data
    except Exception:
        pass
    return {}
