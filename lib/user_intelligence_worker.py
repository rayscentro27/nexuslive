"""
User Intelligence Scoring Worker.

Reads user profiles from Supabase, computes 7-dimension intelligence scores,
and upserts results into user_intelligence table.

Run:
  python3 -m lib.user_intelligence_worker

Or as a cron:
  0 */2 * * * cd /Users/raymonddavis/nexus-ai && source .env && python3 -m lib.user_intelligence_worker >> logs/user_intelligence.log 2>&1
"""
from __future__ import annotations

import json
import logging
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("UserIntelligenceWorker")

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

SCORING_VERSION = 'v1'
DRY_RUN = os.getenv('NEXUS_DRY_RUN', 'true').lower() == 'true'


# ── Supabase helpers ──────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }


def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        logger.error(f"GET {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return []
    except Exception as e:
        logger.error(f"GET {path} → {e}")
        return []


def _sb_upsert(table: str, row: dict, on_conflict: str = 'user_id') -> Optional[dict]:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = _headers()
    headers['Prefer'] = f'return=representation,resolution=merge-duplicates'
    data = json.dumps(row).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    req.add_header('Prefer', f'return=representation,resolution=merge-duplicates')
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        logger.error(f"UPSERT {table} → HTTP {e.code}: {body}")
        return None
    except Exception as e:
        logger.error(f"UPSERT {table} → {e}")
        return None


# ── Scoring logic ─────────────────────────────────────────────────────────────

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> int:
    return int(max(lo, min(hi, value)))


def compute_onboarding_score(profile: dict) -> int:
    """0–100: fraction of onboarding steps completed."""
    if profile.get('onboarding_complete'):
        return 100
    step = profile.get('onboarding_step') or ''
    step_map = {
        'profile':       20,
        'business':      40,
        'credit':        60,
        'funding':       80,
        'trading':       90,
        'complete':      100,
    }
    for key, score in step_map.items():
        if key in step.lower():
            return score
    has_name = bool(profile.get('full_name'))
    has_business = bool(profile.get('business_name'))
    partial = (has_name * 10) + (has_business * 10)
    return partial


def compute_engagement_score(profile: dict, analytics: list) -> int:
    """0–100: activity depth and recency."""
    score = 0

    # Recency: was user active in last 7 days?
    updated = profile.get('updated_at') or profile.get('created_at') or ''
    if updated:
        try:
            ts = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            days_ago = (datetime.now(timezone.utc) - ts).days
            if days_ago <= 1:
                score += 40
            elif days_ago <= 7:
                score += 25
            elif days_ago <= 30:
                score += 10
        except Exception:
            pass

    # Analytics event diversity
    features_seen = {e.get('feature') for e in analytics if e.get('feature')}
    score += min(len(features_seen) * 10, 40)

    # Session count proxy from analytics
    sessions = {e.get('session_id') for e in analytics if e.get('session_id')}
    score += min(len(sessions) * 5, 20)

    return _clamp(score)


def compute_business_setup_score(profile: dict) -> int:
    """0–100: business foundation completeness."""
    score = 0
    if profile.get('business_name'):     score += 25
    if profile.get('business_type'):     score += 15
    if profile.get('ein'):               score += 25
    if profile.get('business_address'):  score += 15
    if profile.get('industry'):          score += 10
    if profile.get('revenue'):           score += 10
    return _clamp(score)


def compute_funding_readiness_score(profile: dict) -> int:
    """0–100: proxy from profile fields (real score lives in FundingReadiness)."""
    score = 0
    credit = profile.get('personal_credit_score') or 0
    if credit >= 720:   score += 40
    elif credit >= 680: score += 30
    elif credit >= 620: score += 20
    elif credit >= 550: score += 10

    if profile.get('business_bank_account'): score += 20
    if profile.get('ein'):                   score += 15
    if profile.get('business_name'):         score += 10
    if profile.get('business_tradelines', 0) >= 3: score += 15
    return _clamp(score)


def compute_grant_engagement(analytics: list) -> int:
    """0–100: grant interaction depth."""
    grant_events = [e for e in analytics if e.get('feature') == 'grants' or 'grant' in (e.get('event_name') or '')]
    return _clamp(len(grant_events) * 20)


def compute_trading_activation(analytics: list) -> int:
    """0–100: paper trading engagement."""
    trading_events = [e for e in analytics if e.get('feature') == 'trading' or 'trad' in (e.get('event_name') or '')]
    if not trading_events:
        return 0
    return _clamp(20 + len(trading_events) * 15)


def determine_next_best_action(
    onboarding: int,
    business: int,
    funding: int,
    credit: int,
    trading: int,
    grants: int,
) -> tuple[str, str, str]:
    """Return (action_text, priority, category) for the most impactful next step."""
    if onboarding < 60:
        return "Complete your onboarding steps to unlock all features", "high", "onboarding"
    if business < 40:
        return "Set up your LLC and EIN — required for business funding", "high", "business"
    if funding < 30:
        return "Start building business credit with net-30 vendor accounts", "high", "credit"
    if funding < 50:
        return "Open a dedicated business bank account to improve fundability", "high", "funding"
    if funding < 70:
        return "Apply for entry-level business credit cards to build tradelines", "medium", "credit"
    if grants < 20:
        return "Explore the 20 grant programs in your catalog — 3 may match your profile", "medium", "grants"
    if trading < 20:
        return "Try the paper trading demo — explore strategies with zero risk", "low", "trading"
    if funding >= 70:
        return "Apply for SBA microloan or business line of credit — you qualify", "high", "funding"
    return "Review your dashboard for today's top recommended actions", "low", "dashboard"


def determine_user_state(
    onboarding: int,
    engagement: int,
    funding: int,
) -> str:
    """Classify user into an operational state."""
    if onboarding < 40:
        return "onboarding_stalled" if engagement < 20 else "onboarding_in_progress"
    if engagement < 10:
        return "inactive"
    if funding >= 70 and engagement >= 50:
        return "funding_ready"
    if engagement >= 60:
        return "highly_engaged"
    return "active"


def determine_health(composite: int) -> str:
    if composite >= 75:
        return "green"
    if composite >= 50:
        return "yellow"
    return "red"


def score_user(profile: dict, analytics: list) -> dict:
    """Compute all intelligence scores for one user profile."""
    user_id = profile.get('id') or profile.get('user_id')
    if not user_id:
        raise ValueError("profile missing id/user_id")

    created_at = profile.get('created_at') or ''
    days_since_signup = 0
    if created_at:
        try:
            ts = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            days_since_signup = (datetime.now(timezone.utc) - ts).days
        except Exception:
            pass

    onboarding   = compute_onboarding_score(profile)
    engagement   = compute_engagement_score(profile, analytics)
    business     = compute_business_setup_score(profile)
    funding      = compute_funding_readiness_score(profile)
    grants       = compute_grant_engagement(analytics)
    trading      = compute_trading_activation(analytics)

    # Weighted composite (see user_intelligence_profile.md for weights)
    composite = _clamp(
        onboarding   * 0.20
        + funding    * 0.25
        + engagement * 0.15
        + business   * 0.10
        + grants     * 0.05
        + trading    * 0.05
        # credit_health defaults to funding proxy for now
        + funding    * 0.20
    )

    next_action, priority, category = determine_next_best_action(
        onboarding, business, funding, 0, trading, grants
    )

    features_activated = list({
        e.get('feature') for e in analytics
        if e.get('feature') and e.get('event_type') != 'page_view'
    } - {None})

    return {
        'user_id':                   user_id,
        'user_intelligence_score':   composite,
        'engagement_score':          engagement,
        'readiness_score':           funding,
        'operational_health':        determine_health(composite),
        'onboarding_score':          onboarding,
        'funding_readiness_score':   funding,
        'trading_activation_score':  trading,
        'credit_health_score':       0,
        'grant_engagement_score':    grants,
        'business_setup_score':      business,
        'onboarding_complete':       bool(profile.get('onboarding_complete')),
        'onboarding_step':           profile.get('onboarding_step') or '',
        'features_activated':        features_activated,
        'days_since_signup':         days_since_signup,
        'next_best_action':          next_action,
        'next_best_action_priority': priority,
        'next_best_action_category': category,
        'scoring_version':           SCORING_VERSION,
        'scored_at':                 datetime.now(timezone.utc).isoformat(),
        'raw_signals': {
            'analytics_event_count': len(analytics),
            'has_business_name':     bool(profile.get('business_name')),
            'has_ein':               bool(profile.get('ein')),
        },
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }


# ── Main runner ───────────────────────────────────────────────────────────────

def run_scoring(limit: int = 100) -> dict:
    """Score up to `limit` users. Returns summary stats."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL / SUPABASE_KEY not set")
        return {'error': 'missing Supabase credentials', 'scored': 0}

    logger.info("Fetching user_profiles (limit=%d)...", limit)
    profiles = _sb_get(f'user_profiles?select=*&limit={limit}&order=updated_at.desc')
    if not profiles:
        logger.warning("No profiles returned")
        return {'scored': 0, 'warnings': ['no profiles found']}

    logger.info("Fetching analytics events...")
    # Fetch recent events (last 30 days) in one bulk query
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
    raw_analytics = _sb_get(
        f'analytics_events?select=user_id,event_type,event_name,feature,session_id'
        f'&created_at=gt.{cutoff}&limit=5000'
    )

    # Group analytics by user_id
    analytics_by_user: dict[str, list] = {}
    for ev in raw_analytics:
        uid = ev.get('user_id')
        if uid:
            analytics_by_user.setdefault(uid, []).append(ev)

    scored = 0
    errors = 0
    health_counts = {'green': 0, 'yellow': 0, 'red': 0, 'unknown': 0}

    for profile in profiles:
        user_id = profile.get('id') or profile.get('user_id')
        if not user_id:
            continue
        try:
            row = score_user(profile, analytics_by_user.get(user_id, []))
            health_counts[row.get('operational_health', 'unknown')] = \
                health_counts.get(row.get('operational_health', 'unknown'), 0) + 1

            if DRY_RUN:
                logger.info(
                    "[DRY_RUN] user=%s score=%d health=%s next=%s",
                    user_id[:8],
                    row['user_intelligence_score'],
                    row['operational_health'],
                    row['next_best_action'][:50],
                )
            else:
                result = _sb_upsert('user_intelligence', row)
                if result:
                    scored += 1
                    logger.info("Scored user=%s → %d (%s)", user_id[:8], row['user_intelligence_score'], row['operational_health'])
                else:
                    errors += 1
        except Exception as e:
            logger.error("Failed to score user=%s: %s", (user_id or '?')[:8], e)
            errors += 1

    if DRY_RUN:
        scored = len(profiles)

    summary = {
        'mode':         'dry_run' if DRY_RUN else 'live',
        'total_profiles': len(profiles),
        'scored':       scored,
        'errors':       errors,
        'health':       health_counts,
    }
    logger.info("Scoring complete: %s", summary)
    return summary


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ',
    )
    result = run_scoring()
    print(json.dumps(result, indent=2))
