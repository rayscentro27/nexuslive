"""
Opportunity Research Worker.

Scans user profiles for funding opportunities they qualify for based on
credit score, business setup, and engagement signals. Scores each
opportunity for feasibility and writes a prioritized opportunity queue.

Run:
  python3 -m lib.opportunity_research_worker

Cron (every 6 hours):
  0 */6 * * * cd ~/nexus-ai && source .env && python3 -m lib.opportunity_research_worker >> logs/opportunity_research.log 2>&1
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("OpportunityResearchWorker")

# ── env loading ───────────────────────────────────────────────────────────────

_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
DRY_RUN = os.getenv('NEXUS_DRY_RUN', 'true').lower() == 'true'
WRITES_ENABLED = os.getenv('OPPORTUNITY_RESEARCH_WRITES_ENABLED', 'false').lower() == 'true'
PERSIST = WRITES_ENABLED


# ── Opportunity catalog ───────────────────────────────────────────────────────

@dataclass
class OpportunityTemplate:
    id: str
    category: str
    name: str
    description: str
    min_credit: int
    max_credit: int
    requires_ein: bool
    requires_business_bank: bool
    min_months_in_business: int
    max_amount: int
    startup_cost: int
    risk_level: str             # low | medium | high
    monetization_type: str
    nexus_status: str           # pending | researching | reviewing | tested | validated
    tested_by_nexus: bool
    typical_approval_days: int
    typical_timeline_days: int
    url_hint: str
    educational_summary: str
    failure_points: str
    action_steps: list          # [{step, description}]


OPPORTUNITY_CATALOG: list[OpportunityTemplate] = [
    OpportunityTemplate(
        id='sba_microloan',
        category='sba',
        name='SBA Microloan Program',
        description='Up to $50,000 for small businesses and nonprofits. Offered through SBA intermediary lenders.',
        min_credit=575, max_credit=0,
        requires_ein=True, requires_business_bank=True,
        min_months_in_business=0,
        max_amount=50_000, startup_cost=0,
        risk_level='low', monetization_type='loan',
        nexus_status='validated', tested_by_nexus=True,
        typical_approval_days=30, typical_timeline_days=45,
        url_hint='funding',
        educational_summary=(
            'SBA Microloans are government-backed loans up to $50K distributed by nonprofit '
            'intermediary lenders. They typically require less paperwork than commercial loans '
            'and are designed for businesses that can\'t qualify for traditional bank financing. '
            'Credit requirements are flexible — some lenders approve scores as low as 575. '
            'An EIN and business bank account are required. Interest rates range 8–13%.'
        ),
        failure_points='No EIN, no business bank account, or credit below 575. Most rejections are from missing documentation.',
        action_steps=[
            {'step': '1', 'description': 'Obtain your EIN from IRS.gov (free, takes 10 minutes)'},
            {'step': '2', 'description': 'Open a dedicated business checking account'},
            {'step': '3', 'description': 'Find your local SBA intermediary lender at sba.gov/microloans'},
            {'step': '4', 'description': 'Prepare 2 years of tax returns, bank statements, and business plan'},
        ],
    ),
    OpportunityTemplate(
        id='sba_7a',
        category='sba',
        name='SBA 7(a) Loan',
        description='Up to $5M for established businesses with 2+ years of operation.',
        min_credit=640, max_credit=0,
        requires_ein=True, requires_business_bank=True,
        min_months_in_business=24,
        max_amount=5_000_000, startup_cost=0,
        risk_level='low', monetization_type='loan',
        nexus_status='validated', tested_by_nexus=True,
        typical_approval_days=60, typical_timeline_days=90,
        url_hint='funding',
        educational_summary=(
            'SBA 7(a) is the most popular SBA loan — it covers working capital, equipment, '
            'real estate, and refinancing. Requires 2+ years in business and a 640+ credit score. '
            'Banks like Live Oak and Huntington are SBA-preferred lenders and move faster. '
            'Rates are typically prime + 2.75%. Collateral may be required for loans over $25K.'
        ),
        failure_points='Business under 2 years old, credit below 640, or insufficient revenue to service debt.',
        action_steps=[
            {'step': '1', 'description': 'Verify your business has 2+ years of tax filings'},
            {'step': '2', 'description': 'Pull your business credit report (Dun & Bradstreet or Experian Business)'},
            {'step': '3', 'description': 'Prepare P&L, balance sheet, and 12 months of bank statements'},
            {'step': '4', 'description': 'Apply through an SBA-preferred lender for faster turnaround'},
        ],
    ),
    OpportunityTemplate(
        id='nav_credit_builder',
        category='credit',
        name='Net-30 Vendor Accounts (Business Credit Building)',
        description='Establish business tradelines through net-30 vendors that report to Dun & Bradstreet.',
        min_credit=0, max_credit=0,
        requires_ein=True, requires_business_bank=False,
        min_months_in_business=0,
        max_amount=0, startup_cost=0,
        risk_level='low', monetization_type='credit',
        nexus_status='validated', tested_by_nexus=True,
        typical_approval_days=7, typical_timeline_days=90,
        url_hint='credit',
        educational_summary=(
            'Business credit is separate from personal credit and requires deliberate building. '
            'Net-30 vendors (like Uline, Quill, Grainger) extend 30-day payment terms and report '
            'on-time payments to business credit bureaus. 3 active tradelines with 90-day history '
            'typically produces a Paydex score of 80+, which lenders use for business funding. '
            'Cost: $0 to get started. This is the foundation of the Nexus funding path.'
        ),
        failure_points='No EIN, not registering with Dun & Bradstreet (DUNS number required), or paying invoices late.',
        action_steps=[
            {'step': '1', 'description': 'Register for a free DUNS number at dnb.com'},
            {'step': '2', 'description': 'Open accounts with 3 net-30 vendors (Uline, Quill, Grainger recommended)'},
            {'step': '3', 'description': 'Make small purchases and pay in full within 30 days'},
            {'step': '4', 'description': 'Monitor your Paydex score at Nav.com after 90 days'},
        ],
    ),
    OpportunityTemplate(
        id='amex_business_loc',
        category='loan',
        name='American Express Business Line of Credit',
        description='Revolving LOC up to $250K for established businesses. Fast approval (1–3 days).',
        min_credit=640, max_credit=0,
        requires_ein=True, requires_business_bank=True,
        min_months_in_business=12,
        max_amount=250_000, startup_cost=0,
        risk_level='medium', monetization_type='loan',
        nexus_status='validated', tested_by_nexus=True,
        typical_approval_days=3, typical_timeline_days=3,
        url_hint='funding',
        educational_summary=(
            'American Express Business Line of Credit offers revolving credit up to $250K. '
            'Unlike term loans, you draw funds as needed and only pay interest on what you use. '
            'Requires 12+ months in business, 640+ personal credit, and $36K+ annual revenue. '
            'Approval is typically 1–3 business days. Rates vary 3–27% depending on draw amount '
            'and repayment period. This is a strong option after establishing basic business credit.'
        ),
        failure_points='Under 12 months in business, revenue below $36K annually, or personal credit under 640.',
        action_steps=[
            {'step': '1', 'description': 'Verify you have 12+ months of business bank statements showing $3K+/month'},
            {'step': '2', 'description': 'Check personal credit score is 640+'},
            {'step': '3', 'description': 'Apply through American Express Business — pre-qualification available without hard pull'},
        ],
    ),
    OpportunityTemplate(
        id='cdfi_microloan',
        category='microloan',
        name='CDFI Microloan',
        description='Community development microloans with flexible credit requirements, up to $25K.',
        min_credit=500, max_credit=0,
        requires_ein=False, requires_business_bank=False,
        min_months_in_business=0,
        max_amount=25_000, startup_cost=0,
        risk_level='low', monetization_type='loan',
        nexus_status='validated', tested_by_nexus=True,
        typical_approval_days=21, typical_timeline_days=30,
        url_hint='funding',
        educational_summary=(
            'CDFIs (Community Development Financial Institutions) are mission-driven lenders focused '
            'on underserved communities. They offer more flexible credit standards than banks — some '
            'approve credit scores as low as 500. Loans typically range $1K–$25K. Many CDFIs also '
            'provide free business coaching, which improves approval odds. This is the most accessible '
            'formal loan product for early-stage business owners.'
        ),
        failure_points='No business plan, no clear revenue model, or applying without the free coaching session.',
        action_steps=[
            {'step': '1', 'description': 'Find your local CDFI at cdfifund.gov'},
            {'step': '2', 'description': 'Schedule a free intake appointment — this is often required'},
            {'step': '3', 'description': 'Prepare a simple business plan and 3-month cash flow projection'},
        ],
    ),
    OpportunityTemplate(
        id='hello_alice_grant',
        category='grant',
        name='Hello Alice Small Business Grant',
        description='Rolling grant program for underserved entrepreneurs, $500–$10K.',
        min_credit=0, max_credit=0,
        requires_ein=False, requires_business_bank=False,
        min_months_in_business=0,
        max_amount=10_000, startup_cost=0,
        risk_level='low', monetization_type='grant',
        nexus_status='validated', tested_by_nexus=True,
        typical_approval_days=90, typical_timeline_days=120,
        url_hint='grants',
        educational_summary=(
            'Hello Alice runs rolling grant competitions for small business owners, especially women, '
            'minorities, and veteran entrepreneurs. Grants range $500–$10,000 and do not need to be '
            'repaid. Application is free. Competition is high — thousands apply per cycle. '
            'Nexus recommends applying to 5–10 grant programs simultaneously, not relying on one. '
            'Strong applications include a clear business impact statement and community focus.'
        ),
        failure_points='Incomplete application, generic impact statement, or applying to only one grant.',
        action_steps=[
            {'step': '1', 'description': 'Create a free profile at helloalice.com'},
            {'step': '2', 'description': 'Complete your business profile — this unlocks more matches'},
            {'step': '3', 'description': 'Browse active grants and apply to all you qualify for'},
            {'step': '4', 'description': 'Write a specific impact statement — generic answers are rejected'},
        ],
    ),
    OpportunityTemplate(
        id='business_checking',
        category='credit',
        name='Dedicated Business Checking Account',
        description='Foundation step: separate business finances to build fundability signals.',
        min_credit=0, max_credit=0,
        requires_ein=False, requires_business_bank=False,
        min_months_in_business=0,
        max_amount=0, startup_cost=0,
        risk_level='low', monetization_type='credit',
        nexus_status='validated', tested_by_nexus=True,
        typical_approval_days=1, typical_timeline_days=1,
        url_hint='funding',
        educational_summary=(
            'A dedicated business checking account is the single most important step for '
            'building fundability. Lenders look for 3–12 months of business banking history. '
            'Mixing personal and business finances is the #1 reason for loan denials. '
            'Recommended: Relay, Mercury, or your local bank. All are free or low-cost. '
            'Open this first — everything else builds on it.'
        ),
        failure_points='Using personal account for business transactions, or not maintaining minimum balance.',
        action_steps=[
            {'step': '1', 'description': 'Choose a business bank (Mercury or Relay recommended for ease)'},
            {'step': '2', 'description': 'Apply online — takes 10–15 minutes, usually approved same day'},
            {'step': '3', 'description': 'Move all business income and expenses to this account immediately'},
        ],
    ),
]


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _feasibility_score(opp: OpportunityTemplate, profile: dict, intelligence: Optional[dict]) -> int:
    score = 50

    credit = profile.get('personal_credit_score') or 0
    has_ein = bool(profile.get('ein'))
    has_bank = bool(profile.get('business_bank_account'))
    months_active = 0
    created = profile.get('created_at') or ''
    if created:
        try:
            ts = datetime.fromisoformat(created.replace('Z', '+00:00'))
            months_active = max(0, (datetime.now(timezone.utc) - ts).days // 30)
        except Exception:
            pass

    if opp.min_credit > 0:
        if credit == 0:
            score -= 20
        elif credit >= opp.min_credit:
            score += 20
        else:
            gap = opp.min_credit - credit
            score -= min(40, gap // 10)

    if opp.requires_ein:
        score += 15 if has_ein else -25

    if opp.requires_business_bank:
        score += 10 if has_bank else -20

    if opp.min_months_in_business > 0:
        if months_active >= opp.min_months_in_business:
            score += 10
        else:
            deficit = opp.min_months_in_business - months_active
            score -= min(30, deficit * 3)

    if intelligence:
        intel_score = intelligence.get('user_intelligence_score', 50)
        score += round((intel_score - 50) * 0.15)

    return max(0, min(100, score))


def _opportunity_score(opp: OpportunityTemplate, feasibility: int) -> int:
    """Overall opportunity quality score (risk-adjusted value for this user)."""
    base = feasibility
    if opp.risk_level == 'low':
        base += 10
    elif opp.risk_level == 'high':
        base -= 15
    if opp.tested_by_nexus:
        base += 5
    if opp.max_amount >= 50_000:
        base += 5
    if opp.startup_cost == 0:
        base += 5
    return max(0, min(100, base))


@dataclass
class UserOpportunity:
    user_id: str
    opportunity_id: str
    opportunity_name: str
    category: str
    feasibility_score: int
    opportunity_score: int
    startup_cost: int
    risk_level: str
    monetization_type: str
    nexus_status: str
    tested_by_nexus: bool
    max_amount: int
    educational_summary: str
    action_steps: list
    failure_points: str
    typical_timeline_days: int
    source: str
    source_url_hint: str
    reasons: list = field(default_factory=list)
    scored_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def score_user_opportunities(profile: dict, intelligence: Optional[dict]) -> list[UserOpportunity]:
    user_id = profile.get('id') or profile.get('user_id')
    if not user_id:
        return []

    results = []
    credit = profile.get('personal_credit_score') or 0

    for opp in OPPORTUNITY_CATALOG:
        fs = _feasibility_score(opp, profile, intelligence)
        if fs < 20:
            continue

        reasons = []
        if credit >= opp.min_credit and opp.min_credit > 0:
            reasons.append(f"Credit score {credit} meets minimum {opp.min_credit}")
        if opp.requires_ein and profile.get('ein'):
            reasons.append("EIN on file")
        if opp.requires_business_bank and profile.get('business_bank_account'):
            reasons.append("Business bank account confirmed")
        if opp.startup_cost == 0:
            reasons.append("No startup cost required")
        if fs >= 70:
            reasons.append("Strong overall profile match")

        opp_score = _opportunity_score(opp, fs)

        results.append(UserOpportunity(
            user_id=user_id,
            opportunity_id=opp.id,
            opportunity_name=opp.name,
            category=opp.category,
            feasibility_score=fs,
            opportunity_score=opp_score,
            startup_cost=opp.startup_cost,
            risk_level=opp.risk_level,
            monetization_type=opp.monetization_type,
            nexus_status=opp.nexus_status,
            tested_by_nexus=opp.tested_by_nexus,
            max_amount=opp.max_amount,
            educational_summary=opp.educational_summary,
            action_steps=opp.action_steps,
            failure_points=opp.failure_points,
            typical_timeline_days=opp.typical_timeline_days,
            source='nexus_catalog',
            source_url_hint=opp.url_hint,
            reasons=reasons,
        ))

    return sorted(results, key=lambda o: o.opportunity_score, reverse=True)


# ── Supabase helpers ──────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation,resolution=merge-duplicates',
    }


def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        logger.error("GET %s → HTTP %s: %s", path, e.code, e.read().decode()[:200])
        return []
    except Exception as e:
        logger.error("GET %s → %s", path, e)
        return []


def _sb_upsert(table: str, row: dict, on_conflict: str) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    data = json.dumps(row).encode()
    req = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
            return True
    except urllib.error.HTTPError as e:
        logger.error("UPSERT %s → HTTP %s: %s", table, e.code, e.read().decode()[:200])
        return False
    except Exception as e:
        logger.error("UPSERT %s → %s", table, e)
        return False


# ── Main runner ───────────────────────────────────────────────────────────────

def run_research(limit: int = 100) -> dict:
    """Score opportunities for all users. Returns summary."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL / SUPABASE_KEY not set")
        return {'error': 'missing credentials'}

    profiles = _sb_get(f'user_profiles?select=*&limit={limit}&order=updated_at.desc')
    if not profiles:
        logger.warning("No profiles returned")
        return {'scored': 0, 'warnings': ['no profiles found']}

    intelligence_rows = _sb_get('user_intelligence?select=user_id,user_intelligence_score&limit=500')
    intel_by_user = {r['user_id']: r for r in intelligence_rows}

    total_opps = 0
    high_feasibility = 0

    for profile in profiles:
        user_id = profile.get('id') or profile.get('user_id')
        if not user_id:
            continue

        opps = score_user_opportunities(profile, intel_by_user.get(user_id))
        total_opps += len(opps)
        high_feasibility += sum(1 for o in opps if o.feasibility_score >= 70)

        for opp in opps[:7]:
            row = {
                'user_id':               opp.user_id,
                'opportunity_id':        opp.opportunity_id,
                'opportunity_name':      opp.opportunity_name,
                'category':              opp.category,
                'feasibility_score':     opp.feasibility_score,
                'opportunity_score':     opp.opportunity_score,
                'startup_cost':          opp.startup_cost,
                'risk_level':            opp.risk_level,
                'monetization_type':     opp.monetization_type,
                'nexus_status':          opp.nexus_status,
                'tested_by_nexus':       opp.tested_by_nexus,
                'max_amount':            opp.max_amount or None,
                'educational_summary':   opp.educational_summary,
                'action_steps':          json.dumps(opp.action_steps),
                'failure_points':        opp.failure_points,
                'typical_timeline_days': opp.typical_timeline_days,
                'source':                opp.source,
                'source_url_hint':       opp.source_url_hint,
                'reasons':               json.dumps(opp.reasons),
                'scored_at':             opp.scored_at,
            }

            if PERSIST:
                _sb_upsert('user_opportunities', row, on_conflict='user_id,opportunity_id')
            else:
                logger.info(
                    "[LOG_ONLY] %s → %s: feasibility=%d opp_score=%d (set OPPORTUNITY_RESEARCH_WRITES_ENABLED=true to persist)",
                    user_id[:8], opp.opportunity_name, opp.feasibility_score, opp.opportunity_score,
                )

    summary = {
        'mode':               'live (writes enabled)' if PERSIST else 'log_only (set OPPORTUNITY_RESEARCH_WRITES_ENABLED=true)',
        'profiles_scanned':   len(profiles),
        'opportunities_scored': total_opps,
        'high_feasibility':   high_feasibility,
    }
    logger.info("Research complete: %s", summary)
    return summary


if __name__ == '__main__':
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ',
    )
    result = run_research()
    print(json.dumps(result, indent=2, default=str))
