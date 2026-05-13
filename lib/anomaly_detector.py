"""
Operational Anomaly Detector.

Reads user_profiles, analytics_events, user_intelligence, and provider_health
tables to detect 6 categories of operational anomalies.

Run:
  python3 -m lib.anomaly_detector

Or import:
  from lib.anomaly_detector import run_detection, AnomalyResult
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("AnomalyDetector")

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

# ── Anomaly thresholds ────────────────────────────────────────────────────────

# Onboarding: user created > N days ago with onboarding_complete=false and no recent activity
ONBOARDING_ABANDONMENT_DAYS = 3
ONBOARDING_INACTIVITY_HOURS = 48

# Provider: mark unknown/offline providers that haven't been checked recently
PROVIDER_STALE_HOURS = 6

# Engagement: % of users with red health exceeding this triggers a platform alert
RED_HEALTH_ALERT_PCT = 60

# Error spike: > N error events in the last hour
ERROR_SPIKE_THRESHOLD = 10

# Low activity: platform has < N analytics events in last 24h (after launch)
LOW_ACTIVITY_THRESHOLD = 0  # 0 = disabled until we have real users

# ── Supabase helpers ──────────────────────────────────────────────────────────

import urllib.request
import urllib.error


def _headers() -> dict:
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }


def _sb_get(path: str) -> list:
    import urllib.parse
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


# ── Anomaly model ─────────────────────────────────────────────────────────────

@dataclass
class AnomalyResult:
    category: str          # onboarding_abandonment | provider_outage | error_spike |
                           # engagement_drop | red_health_spike | stale_intelligence
    severity: str          # critical | high | medium | low
    title: str
    detail: str
    affected_count: int = 0
    affected_ids: list = field(default_factory=list)
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ── Detection functions ───────────────────────────────────────────────────────

def detect_onboarding_abandonment(profiles: list) -> Optional[AnomalyResult]:
    """Users who started onboarding N+ days ago but never finished, with no recent activity."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=ONBOARDING_ABANDONMENT_DAYS)
    cutoff_activity = datetime.now(timezone.utc) - timedelta(hours=ONBOARDING_INACTIVITY_HOURS)

    abandoned = []
    for p in profiles:
        if p.get('onboarding_complete'):
            continue
        created = p.get('created_at') or ''
        updated = p.get('updated_at') or p.get('created_at') or ''
        try:
            created_ts = datetime.fromisoformat(created.replace('Z', '+00:00'))
            updated_ts = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            if created_ts < cutoff and updated_ts < cutoff_activity:
                abandoned.append(p.get('id') or p.get('user_id') or 'unknown')
        except Exception:
            continue

    if not abandoned:
        return None

    return AnomalyResult(
        category='onboarding_abandonment',
        severity='high' if len(abandoned) >= 3 else 'medium',
        title=f'{len(abandoned)} user(s) abandoned onboarding',
        detail=(
            f'{len(abandoned)} user(s) created their account {ONBOARDING_ABANDONMENT_DAYS}+ days ago, '
            f'have not completed onboarding, and have been inactive for {ONBOARDING_INACTIVITY_HOURS}+ hours. '
            f'Consider sending a re-engagement nudge.'
        ),
        affected_count=len(abandoned),
        affected_ids=[uid[:8] for uid in abandoned],
    )


def detect_provider_outage(providers: list) -> list[AnomalyResult]:
    """Provider health entries that are offline or have never been checked."""
    anomalies = []
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=PROVIDER_STALE_HOURS)

    offline = []
    stale = []
    for p in providers:
        name = p.get('provider_name') or p.get('name') or 'unknown'
        status = p.get('status') or 'unknown'
        checked = p.get('last_checked_at') or p.get('updated_at') or ''

        if status == 'offline':
            offline.append(name)
        elif status == 'unknown' or not checked:
            stale.append(name)
        elif checked:
            try:
                ts = datetime.fromisoformat(checked.replace('Z', '+00:00'))
                if ts < stale_cutoff:
                    stale.append(name)
            except Exception:
                stale.append(name)

    if offline:
        anomalies.append(AnomalyResult(
            category='provider_outage',
            severity='critical',
            title=f'{len(offline)} provider(s) offline',
            detail=f'Providers reported OFFLINE: {", ".join(offline)}. Check connectivity and restart.',
            affected_count=len(offline),
            affected_ids=offline,
        ))

    if stale:
        anomalies.append(AnomalyResult(
            category='provider_stale',
            severity='medium',
            title=f'{len(stale)} provider(s) not health-checked',
            detail=(
                f'Providers with unknown/stale health: {", ".join(stale)}. '
                f'Run provider health polling worker to update status.'
            ),
            affected_count=len(stale),
            affected_ids=stale,
        ))

    return anomalies


def detect_error_spike(analytics: list) -> Optional[AnomalyResult]:
    """More than ERROR_SPIKE_THRESHOLD error events in the last hour."""
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    errors = []
    for ev in analytics:
        if ev.get('event_type') != 'error':
            continue
        ts_str = ev.get('created_at') or ''
        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            if ts >= one_hour_ago:
                errors.append(ev)
        except Exception:
            continue

    if len(errors) < ERROR_SPIKE_THRESHOLD:
        return None

    pages = {}
    for ev in errors:
        page = ev.get('page') or 'unknown'
        pages[page] = pages.get(page, 0) + 1
    top_page = max(pages, key=lambda k: pages[k]) if pages else 'unknown'

    return AnomalyResult(
        category='error_spike',
        severity='critical' if len(errors) >= ERROR_SPIKE_THRESHOLD * 2 else 'high',
        title=f'{len(errors)} frontend errors in the last hour',
        detail=(
            f'{len(errors)} error events logged in the last 60 minutes. '
            f'Most affected page: {top_page} ({pages.get(top_page, 0)} errors). '
            f'Check browser console and Supabase logs.'
        ),
        affected_count=len(errors),
    )


def detect_red_health_spike(intelligence_rows: list, profiles: list) -> Optional[AnomalyResult]:
    """Alerts if the % of red-health users exceeds RED_HEALTH_ALERT_PCT."""
    if not intelligence_rows and not profiles:
        return None

    total = len(intelligence_rows) if intelligence_rows else len(profiles)
    if total == 0:
        return None

    red = sum(1 for r in intelligence_rows if r.get('operational_health') == 'red')
    pct = round(red / total * 100)

    if pct < RED_HEALTH_ALERT_PCT:
        return None

    return AnomalyResult(
        category='red_health_spike',
        severity='high',
        title=f'{pct}% of users have red operational health',
        detail=(
            f'{red}/{total} users scored below 50 composite. '
            f'Low scores typically indicate incomplete onboarding or zero engagement. '
            f'Run user_intelligence_worker and review next_best_action queue.'
        ),
        affected_count=red,
    )


def detect_stale_intelligence(intelligence_rows: list, profiles: list) -> Optional[AnomalyResult]:
    """Users with profiles but no user_intelligence row, or rows older than 24h."""
    profile_ids = {p.get('id') or p.get('user_id') for p in profiles if p.get('id') or p.get('user_id')}
    intel_ids = {r.get('user_id') for r in intelligence_rows if r.get('user_id')}
    unscored = profile_ids - intel_ids

    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    stale = []
    for r in intelligence_rows:
        scored_at = r.get('scored_at') or r.get('updated_at') or ''
        try:
            ts = datetime.fromisoformat(scored_at.replace('Z', '+00:00'))
            if ts < stale_cutoff:
                stale.append(r.get('user_id', 'unknown'))
        except Exception:
            stale.append(r.get('user_id', 'unknown'))

    total_stale = len(unscored) + len(stale)
    if total_stale == 0:
        return None

    detail_parts = []
    if unscored:
        detail_parts.append(f'{len(unscored)} user(s) have never been scored')
    if stale:
        detail_parts.append(f'{len(stale)} score(s) are older than 24 hours')

    return AnomalyResult(
        category='stale_intelligence',
        severity='medium',
        title=f'{total_stale} user intelligence record(s) stale or missing',
        detail='. '.join(detail_parts) + '. Set NEXUS_DRY_RUN=false and run user_intelligence_worker.',
        affected_count=total_stale,
        affected_ids=[uid[:8] for uid in list(unscored)[:10]],
    )


def detect_zero_analytics(analytics: list, profiles: list) -> Optional[AnomalyResult]:
    """If we have users but zero analytics events, instrumentation may be broken."""
    if not profiles:
        return None  # no users yet, expected
    if LOW_ACTIVITY_THRESHOLD <= 0:
        return None  # disabled

    one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = [
        ev for ev in analytics
        if ev.get('created_at') and _ts_after(ev['created_at'], one_day_ago)
    ]

    if len(recent) > LOW_ACTIVITY_THRESHOLD:
        return None

    return AnomalyResult(
        category='zero_analytics',
        severity='high',
        title='No frontend analytics events in last 24h',
        detail=(
            f'Platform has {len(profiles)} user(s) but recorded only {len(recent)} analytics event(s) '
            f'in the last 24 hours. Verify useAnalytics hook is wired and Supabase RLS allows inserts.'
        ),
        affected_count=0,
    )


def _ts_after(ts_str: str, cutoff: datetime) -> bool:
    try:
        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return ts >= cutoff
    except Exception:
        return False


# ── Main runner ───────────────────────────────────────────────────────────────

def run_detection() -> dict:
    """Run all anomaly checks. Returns summary with list of AnomalyResult dicts."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL / SUPABASE_KEY not set")
        return {'error': 'missing credentials', 'anomalies': []}

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')

    logger.info("Fetching data for anomaly detection...")
    profiles          = _sb_get('user_profiles?select=id,created_at,updated_at,onboarding_complete&limit=500')
    providers         = _sb_get('provider_health?select=*')
    analytics         = _sb_get(f'analytics_events?select=event_type,page,created_at,user_id&created_at=gt.{cutoff}&limit=5000')
    intelligence_rows = _sb_get(f'user_intelligence?select=user_id,operational_health,scored_at&limit=500')

    anomalies: list[AnomalyResult] = []

    # 1. Onboarding abandonment
    a = detect_onboarding_abandonment(profiles)
    if a:
        anomalies.append(a)

    # 2. Provider outage / stale
    anomalies.extend(detect_provider_outage(providers))

    # 3. Error spike
    a = detect_error_spike(analytics)
    if a:
        anomalies.append(a)

    # 4. Red health spike
    a = detect_red_health_spike(intelligence_rows, profiles)
    if a:
        anomalies.append(a)

    # 5. Stale intelligence
    a = detect_stale_intelligence(intelligence_rows, profiles)
    if a:
        anomalies.append(a)

    # 6. Zero analytics
    a = detect_zero_analytics(analytics, profiles)
    if a:
        anomalies.append(a)

    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    anomalies.sort(key=lambda x: severity_order.get(x.severity, 9))

    mode = 'dry_run' if DRY_RUN else 'live'
    summary = {
        'mode': mode,
        'detected_at': datetime.now(timezone.utc).isoformat(),
        'total_anomalies': len(anomalies),
        'critical': sum(1 for a in anomalies if a.severity == 'critical'),
        'high': sum(1 for a in anomalies if a.severity == 'high'),
        'medium': sum(1 for a in anomalies if a.severity == 'medium'),
        'anomalies': [a.to_dict() for a in anomalies],
    }

    for a in anomalies:
        logger.warning("[%s] %s — %s: %s", a.severity.upper(), a.category, a.title, a.detail[:80])

    if not anomalies:
        logger.info("No anomalies detected.")

    logger.info("Detection complete: %d anomalies (%d critical, %d high, %d medium)",
                len(anomalies), summary['critical'], summary['high'], summary['medium'])
    return summary


if __name__ == '__main__':
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ',
    )
    result = run_detection()
    print(json.dumps(result, indent=2))
