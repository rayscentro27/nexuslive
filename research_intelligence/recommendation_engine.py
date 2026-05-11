"""
Source Recommendation Engine.

Reads coverage gaps and low health scores → generates source_recommendations.
Also writes an agent_run_summary of type='source_recommendation' so the
CEO briefing layer picks it up.

Logic:
  1. For each coverage gap (score < GAP_THRESHOLD):
       → recommend adding a source of the dominant type for that domain
  2. For each critically low health source (score < HEALTH_THRESHOLD):
       → recommend reviewing or replacing the source
  3. For each flagged duplicate pair:
       → recommend resolving the duplicate

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m research_intelligence.recommendation_engine
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger('RecommendationEngine')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

GAP_THRESHOLD    = float(os.getenv('COVERAGE_GAP_THRESHOLD', '40'))
HEALTH_THRESHOLD = float(os.getenv('HEALTH_LOW_THRESHOLD',  '35'))

# Suggested source types per domain
_DOMAIN_SOURCE_SUGGESTIONS = {
    'trading':  ('youtube_channel', 'YouTube trading channels (e.g., technical analysis, price action)'),
    'funding':  ('website',         'Funding-focused websites (e.g., SBA, alternative lenders)'),
    'grants':   ('rss_feed',        'Government grant RSS feeds (grants.gov, SAM.gov)'),
    'business': ('youtube_channel', 'Business strategy YouTube channels or podcasts'),
    'credit':   ('website',         'Credit repair / scoring authority websites'),
    'general':  ('website',         'General finance or business news website'),
}

# Source type priority for subdomain gaps
_SUBDOMAIN_PRIORITY = {
    'youtube_channel': 'high',
    'rss_feed':        'medium',
    'website':         'medium',
    'generic':         'low',
}


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
    }


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def _sb_post(path: str, body: dict) -> Optional[dict]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return None
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


def _store_recommendation(
    rec_type: str,
    domain: Optional[str],
    reason: str,
    priority: str = 'medium',
    suggested_url: Optional[str] = None,
) -> bool:
    row = {
        'recommended_source_type': rec_type,
        'suggested_domain':        domain,
        'suggested_url':           suggested_url,
        'reason':                  reason,
        'priority':                priority,
        'status':                  'pending',
    }
    result = _sb_post('source_recommendations', row)
    return result is not None


def _write_summary(
    what_happened: str,
    recommended_next_action: str,
    priority: str = 'medium',
) -> None:
    try:
        from autonomy.summary_service import write_summary
        write_summary(
            agent_name='recommendation_engine',
            summary_type='source_recommendation',
            summary_text=what_happened,
            what_happened=what_happened,
            what_changed='New source recommendations generated',
            recommended_next_action=recommended_next_action,
            follow_up_needed=True,
            priority=priority,
        )
    except Exception as e:
        logger.warning(f"Summary write failed: {e}")


# ─── Recommendation generators ────────────────────────────────────────────────

def _recommend_for_coverage_gaps(gaps: List[dict]) -> int:
    count = 0
    for gap in gaps:
        domain    = gap.get('domain', 'general')
        subdomain = gap.get('subdomain', 'website')
        score     = gap.get('coverage_score', 0)
        src_count = gap.get('source_count', 0)

        suggested_type, description = _DOMAIN_SOURCE_SUGGESTIONS.get(
            domain, _DOMAIN_SOURCE_SUGGESTIONS['general']
        )
        priority = 'high' if score < 20 else 'medium'
        reason   = (
            f"Coverage gap in {domain}/{subdomain}: "
            f"score={score}, only {src_count} source(s). "
            f"Suggestion: {description}"
        )
        ok = _store_recommendation(
            rec_type=suggested_type,
            domain=domain,
            reason=reason,
            priority=priority,
        )
        if ok:
            count += 1
            logger.info(f"Coverage recommendation: {domain}/{subdomain} → {suggested_type}")
    return count


def _recommend_for_low_health(low_sources: List[dict]) -> int:
    """Generate review/replace recommendations for critically low health sources."""
    count = 0
    for hs in low_sources:
        source_id = hs.get('source_id', '')
        score     = hs.get('score_total', 0)
        # Look up source details
        details = _sb_get(
            f"research_sources?id=eq.{source_id}&select=label,source_type,domain&limit=1"
        )
        detail  = details[0] if details else {}
        label   = detail.get('label', source_id[:12])
        stype   = detail.get('source_type', 'unknown')
        domain  = detail.get('domain', 'unknown')

        reason = (
            f"Source '{label}' has low health score ({score}/100). "
            f"Consider reviewing scan errors, replacing, or finding a higher-quality "
            f"{stype} for the {domain} domain."
        )
        ok = _store_recommendation(
            rec_type=stype,
            domain=domain,
            reason=reason,
            priority='high' if score < 20 else 'medium',
        )
        if ok:
            count += 1
            logger.info(f"Low-health recommendation: {label} score={score}")
    return count


def _recommend_for_duplicates(duplicates: List[dict]) -> int:
    """Recommend resolving flagged duplicate source pairs."""
    count = 0
    for dup in duplicates:
        sid   = dup.get('source_id', '')
        other = dup.get('duplicate_of_source_id', '')
        sim   = dup.get('similarity_score', 0)
        rsn   = dup.get('reason', '')

        reason = (
            f"Duplicate sources detected (similarity={sim}): "
            f"source {sid[:8]} ↔ {other[:8]}. Reason: {rsn}. "
            f"Review and consolidate to avoid redundant scanning."
        )
        ok = _store_recommendation(
            rec_type='review_duplicate',
            domain=None,
            reason=reason,
            priority='medium' if sim < 0.95 else 'high',
        )
        if ok:
            count += 1
    return count


# ─── Public API ───────────────────────────────────────────────────────────────

def run_recommendations() -> dict:
    """
    Generate source recommendations from coverage gaps, low health, and duplicates.
    Returns counts dict.
    """
    from research_intelligence.coverage_engine import get_coverage_gaps
    from source_health.health_scorer import get_low_health_sources
    from source_health.duplicate_detector import get_flagged_duplicates

    gaps       = get_coverage_gaps(threshold=GAP_THRESHOLD)
    low_health = get_low_health_sources(threshold=HEALTH_THRESHOLD)
    duplicates = get_flagged_duplicates(limit=20)

    cov_recs  = _recommend_for_coverage_gaps(gaps)
    hlth_recs = _recommend_for_low_health(low_health)
    dup_recs  = _recommend_for_duplicates(duplicates)

    total = cov_recs + hlth_recs + dup_recs

    if total > 0:
        summary = (
            f"Recommendation engine generated {total} new source recommendation(s): "
            f"{cov_recs} coverage gap(s), {hlth_recs} low-health source(s), "
            f"{dup_recs} duplicate pair(s)."
        )
        action = (
            "Review source_recommendations table. Add suggested sources via admin command: "
            "'add [type] source [url]'. Resolve duplicates via duplicate_detector.resolve_duplicate()."
        )
        _write_summary(summary, action, priority='high' if hlth_recs > 0 else 'medium')
        logger.info(summary)
    else:
        logger.info("No new recommendations generated — coverage and health look good")

    return {
        'coverage_recommendations': cov_recs,
        'health_recommendations':   hlth_recs,
        'duplicate_recommendations': dup_recs,
        'total':                    total,
    }


def get_pending_recommendations(limit: int = 50) -> List[dict]:
    return _sb_get(
        f"source_recommendations?status=eq.pending"
        f"&order=priority.asc,created_at.desc&limit={limit}&select=*"
    )


if __name__ == '__main__':
    _env = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(_env):
        with open(_env) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s %(message)s')
    result = run_recommendations()
    print(f"Recommendations: {result}")
