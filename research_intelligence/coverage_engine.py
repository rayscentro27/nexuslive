"""
Research Coverage Engine.

Classifies research sources and artifacts by domain, then computes a
coverage_score (0-100) per domain/subdomain combination.

Domains: trading, funding, grants, business, credit, general
Subdomain: derived from source_type (youtube_channel, website, rss_feed, etc.)

coverage_score formula:
  source_count  → up to 40 pts  (40 = saturated at 10+ sources)
  artifact_count → up to 30 pts (30 = saturated at 50+ artifacts)
  signal_count   → up to 20 pts (20 = saturated at 20+ signals)
  strategy_count → up to 10 pts (10 = saturated at 10+ strategies)

Upserts into research_coverage (UNIQUE on domain, subdomain).

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m research_intelligence.coverage_engine
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('CoverageEngine')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Domain keyword classifiers
_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    'trading':  ['trading', 'trade', 'forex', 'stock', 'crypto', 'option', 'futures',
                 'market', 'technical analysis', 'price action', 'oanda', 'chart'],
    'funding':  ['funding', 'finance', 'loan', 'lend', 'capital', 'investment', 'investor',
                 'pitch', 'raise', 'revenue', 'cashflow', 'debt', 'equity'],
    'grants':   ['grant', 'sba', 'government', 'federal', 'sbir', 'sttr', 'nonprofit',
                 'award', 'application', 'rfp', 'funder'],
    'business': ['business', 'entrepreneur', 'startup', 'strategy', 'growth', 'marketing',
                 'sales', 'crm', 'operations', 'management', 'leadership'],
    'credit':   ['credit', 'score', 'fico', 'bureau', 'report', 'dispute', 'debt',
                 'repair', 'utilization', 'inquiry'],
}


def _classify_domain(text: str) -> str:
    """Return the best-matching domain for a label/URL/domain string."""
    low = (text or '').lower()
    scores: Dict[str, int] = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in low)
        if hits:
            scores[domain] = hits
    if not scores:
        return 'general'
    return max(scores, key=lambda d: scores[d])


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


def _upsert_coverage(row: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/research_coverage"
    data = json.dumps(row).encode()
    h    = _headers()
    h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
    req  = urllib.request.Request(url, data=data, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"Upsert coverage → {e}")
        return False


def _compute_score(
    source_count: int,
    artifact_count: int,
    signal_count: int,
    strategy_count: int,
) -> float:
    src_pts  = min(source_count   / 10, 1.0) * 40
    art_pts  = min(artifact_count / 50, 1.0) * 30
    sig_pts  = min(signal_count   / 20, 1.0) * 20
    strat_pts = min(strategy_count / 10, 1.0) * 10
    return round(src_pts + art_pts + sig_pts + strat_pts, 2)


# ─── Public API ───────────────────────────────────────────────────────────────

def build_coverage_map(limit: int = 500) -> int:
    """
    Classify all active sources, aggregate counts by domain+subdomain,
    compute coverage scores, and upsert results.
    Returns number of domain rows upserted.
    """
    sources = _sb_get(
        f"research_sources?status=in.(active,pending_scan)&select=*&limit={limit}"
    )

    # Aggregate: {(domain, subdomain): {source_count, artifact_count, signal_count, strategy_count}}
    buckets: Dict[Tuple[str, str], Dict[str, int]] = {}

    for src in sources:
        domain    = _classify_domain(
            (src.get('domain') or '') + ' ' + (src.get('label') or '')
        )
        subdomain = src.get('source_type', 'generic')
        key       = (domain, subdomain)

        if key not in buckets:
            buckets[key] = {'source_count': 0, 'artifact_count': 0,
                            'signal_count': 0, 'strategy_count': 0}

        buckets[key]['source_count'] += 1

        # Pull artifact counts for this source
        arts = _sb_get(
            f"research?source_id=eq.{src['id']}&select=id&limit=200"
        )
        buckets[key]['artifact_count'] += len(arts)

        # Signals (research_artifacts type=signal)
        sigs = _sb_get(
            f"research_artifacts?source_id=eq.{src['id']}&artifact_type=eq.signal&select=id&limit=100"
        )
        buckets[key]['signal_count'] += len(sigs)

        # Strategies
        strats = _sb_get(
            f"research_artifacts?source_id=eq.{src['id']}&artifact_type=eq.strategy&select=id&limit=100"
        )
        buckets[key]['strategy_count'] += len(strats)

    now = datetime.now(timezone.utc).isoformat()
    upserted = 0

    for (domain, subdomain), counts in buckets.items():
        score = _compute_score(
            counts['source_count'],
            counts['artifact_count'],
            counts['signal_count'],
            counts['strategy_count'],
        )
        row = {
            'domain':         domain,
            'subdomain':      subdomain,
            'coverage_score': score,
            'source_count':   counts['source_count'],
            'artifact_count': counts['artifact_count'],
            'signal_count':   counts['signal_count'],
            'strategy_count': counts['strategy_count'],
            'last_updated':   now,
        }
        if _upsert_coverage(row):
            upserted += 1
            logger.info(f"Coverage: {domain}/{subdomain} score={score} "
                        f"sources={counts['source_count']} artifacts={counts['artifact_count']}")

    return upserted


def get_coverage_report(limit: int = 50) -> List[dict]:
    """Return coverage rows sorted by score ascending (gaps first)."""
    return _sb_get(
        f"research_coverage?order=coverage_score.asc&limit={limit}&select=*"
    )


def get_coverage_gaps(threshold: float = 40, limit: int = 20) -> List[dict]:
    """Return domain/subdomain pairs with coverage below threshold."""
    return _sb_get(
        f"research_coverage?coverage_score=lt.{threshold}"
        f"&order=coverage_score.asc&limit={limit}&select=*"
    )


def classify_domain(text: str) -> str:
    """Expose domain classifier for use by other modules."""
    return _classify_domain(text)


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
    n = build_coverage_map()
    print(f"Coverage map built: {n} domain(s) upserted")
    gaps = get_coverage_gaps()
    if gaps:
        print(f"\nCoverage gaps ({len(gaps)}):")
        for g in gaps:
            print(f"  {g['domain']}/{g['subdomain']} score={g['coverage_score']} "
                  f"sources={g['source_count']}")
