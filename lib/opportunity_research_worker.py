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
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
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
    category: str           # grant | loan | credit | sba | microloan
    name: str
    description: str
    min_credit: int
    max_credit: int         # 0 = no upper limit
    requires_ein: bool
    requires_business_bank: bool
    min_months_in_business: int
    max_amount: int
    typical_approval_days: int
    url_hint: str           # category slug, not a full URL

OPPORTUNITY_CATALOG: list[OpportunityTemplate] = [
    OpportunityTemplate(
        id='sba_microloan',
        category='sba',
        name='SBA Microloan Program',
        description='Up to $50,000 for small businesses and nonprofits.',
        min_credit=575, max_credit=0,
        requires_ein=True, requires_business_bank=True,
        min_months_in_business=0,
        max_amount=50_000, typical_approval_days=30,
        url_hint='funding',
    ),
    OpportunityTemplate(
        id='sba_7a',
        category='sba',
        name='SBA 7(a) Loan',
        description='Up to $5M for established businesses.',
        min_credit=640, max_credit=0,
        requires_ein=True, requires_business_bank=True,
        min_months_in_business=24,
        max_amount=5_000_000, typical_approval_days=60,
        url_hint='funding',
    ),
    OpportunityTemplate(
        id='nav_credit_builder',
        category='credit',
        name='Nav Business Credit Builder',
        description='Net-30 vendor accounts to establish business tradelines.',
        min_credit=0, max_credit=0,
        requires_ein=True, requires_business_bank=False,
        min_months_in_business=0,
        max_amount=0, typical_approval_days=7,
        url_hint='credit',
    ),
    OpportunityTemplate(
        id='kabbage_loc',
        category='loan',
        name='American Express Business Line of Credit',
        description='Revolving LOC up to $250K for established businesses.',
        min_credit=640, max_credit=0,
        requires_ein=True, requires_business_bank=True,
        min_months_in_business=12,
        max_amount=250_000, typical_approval_days=3,
        url_hint='funding',
    ),
    OpportunityTemplate(
        id='cdfi_microloan',
        category='microloan',
        name='CDFI Microloan',
        description='Community development microloans, flexible credit requirements.',
        min_credit=500, max_credit=0,
        requires_ein=False, requires_business_bank=False,
        min_months_in_business=0,
        max_amount=25_000, typical_approval_days=21,
        url_hint='funding',
    ),
    OpportunityTemplate(
        id='hello_alice_grant',
        category='grant',
        name='Hello Alice Small Business Grant',
        description='Rolling grant program for underserved entrepreneurs.',
        min_credit=0, max_credit=0,
        requires_ein=False, requires_business_bank=False,
        min_months_in_business=0,
        max_amount=10_000, typical_approval_days=90,
        url_hint='grants',
    ),
    OpportunityTemplate(
        id='nav_business_checking',
        category='credit',
        name='Business Checking Account',
        description='Dedicated business bank account — key fundability signal.',
        min_credit=0, max_credit=0,
        requires_ein=False, requires_business_bank=False,
        min_months_in_business=0,
        max_amount=0, typical_approval_days=1,
        url_hint='funding',
    ),
]


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _feasibility_score(opp: OpportunityTemplate, profile: dict, intelligence: Optional[dict]) -> int:
    """0–100 feasibility for a user × opportunity pair."""
    score = 50  # base

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

    # Credit gate
    if opp.min_credit > 0:
        if credit == 0:
            score -= 20  # unknown credit, penalty
        elif credit >= opp.min_credit:
            score += 20
        else:
            gap = opp.min_credit - credit
            score -= min(40, gap // 10)

    # EIN gate
    if opp.requires_ein:
        score += 15 if has_ein else -25

    # Bank gate
    if opp.requires_business_bank:
        score += 10 if has_bank else -20

    # Business age
    if opp.min_months_in_business > 0:
        if months_active >= opp.min_months_in_business:
            score += 10
        else:
            deficit = opp.min_months_in_business - months_active
            score -= min(30, deficit * 3)

    # Boost from intelligence score
    if intelligence:
        intel_score = intelligence.get('user_intelligence_score', 50)
        score += round((intel_score - 50) * 0.15)

    return max(0, min(100, score))


@dataclass
class UserOpportunity:
    user_id: str
    opportunity_id: str
    opportunity_name: str
    category: str
    feasibility_score: int
    max_amount: int
    url_hint: str
    reasons: list = field(default_factory=list)
    scored_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def score_user_opportunities(profile: dict, intelligence: Optional[dict]) -> list[UserOpportunity]:
    user_id = profile.get('id') or profile.get('user_id')
    if not user_id:
        return []

    results = []
    for opp in OPPORTUNITY_CATALOG:
        fs = _feasibility_score(opp, profile, intelligence)
        if fs < 20:
            continue  # skip clearly unqualified
        reasons = []
        credit = profile.get('personal_credit_score') or 0
        if credit >= opp.min_credit and opp.min_credit > 0:
            reasons.append(f"Credit {credit} meets minimum {opp.min_credit}")
        if opp.requires_ein and profile.get('ein'):
            reasons.append("EIN on file")
        if opp.requires_business_bank and profile.get('business_bank_account'):
            reasons.append("Business bank account confirmed")
        if fs >= 70:
            reasons.append("Strong overall profile match")

        results.append(UserOpportunity(
            user_id=user_id,
            opportunity_id=opp.id,
            opportunity_name=opp.name,
            category=opp.category,
            feasibility_score=fs,
            max_amount=opp.max_amount,
            url_hint=opp.url_hint,
            reasons=reasons,
        ))

    return sorted(results, key=lambda o: o.feasibility_score, reverse=True)


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

        for opp in opps[:5]:  # top 5 per user
            row = {
                'user_id':            opp.user_id,
                'opportunity_id':     opp.opportunity_id,
                'opportunity_name':   opp.opportunity_name,
                'category':           opp.category,
                'feasibility_score':  opp.feasibility_score,
                'max_amount':         opp.max_amount,
                'url_hint':           opp.url_hint,
                'reasons':            json.dumps(opp.reasons),
                'scored_at':          opp.scored_at,
            }

            if PERSIST:
                _sb_upsert('user_opportunities', row, on_conflict='user_id,opportunity_id')
            else:
                logger.info(
                    "[LOG_ONLY] %s → %s: feasibility=%d (set OPPORTUNITY_RESEARCH_WRITES_ENABLED=true to persist)",
                    user_id[:8], opp.opportunity_name, opp.feasibility_score,
                )

    summary = {
        'mode':            'live (writes enabled)' if PERSIST else 'log_only (set OPPORTUNITY_RESEARCH_WRITES_ENABLED=true)',
        'profiles_scanned': len(profiles),
        'opportunities_scored': total_opps,
        'high_feasibility': high_feasibility,
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
