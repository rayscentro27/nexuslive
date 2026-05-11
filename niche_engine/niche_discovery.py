"""
Niche Discovery Engine.

Scores niche candidates from research data and Hermes analysis.
Promotes validated niches to instance spawning.

Scoring approach:
  demand_score       — research article count + keyword frequency in titles
  competition_score  — estimated via keyword saturation (lower = less crowded)
  monetization_score — presence of funding/revenue/product keywords

Run as cron: python3 -m niche_engine.niche_discovery

Usage:
    from niche_engine.niche_discovery import run_niche_scan, validate_niche
"""

import os
import json
import logging
import urllib.request
from typing import Optional, List

from niche_engine.niche_registry import (
    upsert_niche, get_top_niches, update_status, list_niches,
)

logger = logging.getLogger('NicheDiscovery')

# ─── Niche seed list — topics worth exploring ──────────────────────────────────
NICHE_SEEDS = [
    'business funding',
    'credit repair',
    'real estate investing',
    'ecommerce automation',
    'ai consulting',
    'social media marketing',
    'trading signals',
    'dropshipping',
    'digital marketing agency',
    'financial coaching',
    'amazon fba',
    'saas tools',
    'bookkeeping services',
    'tax preparation',
    'insurance leads',
]

# Keywords that indicate monetization potential
MONETIZATION_KEYWORDS = [
    'revenue', 'profit', 'income', 'funding', 'investment', 'capital',
    'subscription', 'fee', 'commission', 'sale', 'deal', 'close',
    'product', 'service', 'client', 'customer', 'pay', 'earn',
]

# Keywords that indicate demand
DEMAND_KEYWORDS = [
    'how to', 'need', 'want', 'looking for', 'help', 'guide',
    'best', 'top', 'review', 'find', 'get', 'start', 'grow',
]

# High competition signals (many providers = saturated)
COMPETITION_KEYWORDS = [
    'guru', 'course', 'masterclass', 'agency', 'coach', 'consultant',
    'program', 'training', 'blueprint', 'system', 'formula',
]


def _score_text(text: str, keywords: List[str]) -> float:
    """Count keyword hits, normalize to 0–100."""
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    return min(hits / max(len(keywords), 1) * 200, 100.0)


def _fetch_research_summaries(keyword: str, limit: int = 20) -> List[dict]:
    """Pull recent research rows related to this niche keyword."""
    import urllib.parse
    key = os.getenv('SUPABASE_KEY', '')
    url = (
        f"{os.getenv('SUPABASE_URL', '')}/rest/v1/research"
        f"?title=ilike.{urllib.parse.quote('%' + keyword + '%')}"
        f"&select=title,summary,domain&limit={limit}"
    )
    req = urllib.request.Request(
        url, headers={'apikey': key, 'Authorization': f'Bearer {key}'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return []


def _hermes_score_niche(niche: str) -> Optional[dict]:
    """
    Ask Hermes to score a niche.
    Returns dict with demand, competition, monetization scores or None.
    """
    prompt = (
        f"Score this business niche for an autonomous AI business system: '{niche}'\n\n"
        "Return ONLY valid JSON with these keys (values 0-100):\n"
        "{\n"
        '  "demand_score": <how many people actively seek this>,\n'
        '  "competition_score": <market saturation level, 100=very crowded>,\n'
        '  "monetization_score": <revenue potential>,\n'
        '  "notes": "<one sentence summary>"\n'
        "}\n"
        "No other text."
    )
    try:
        token = os.getenv('HERMES_GATEWAY_TOKEN', '')
        url   = 'http://localhost:8642/v1/chat/completions'
        body  = json.dumps({
            'model': 'hermes',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 200,
        }).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type':  'application/json',
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            resp    = json.loads(r.read())
            content = resp['choices'][0]['message']['content'].strip()
            # Strip markdown fences if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            return json.loads(content)
    except Exception as e:
        logger.debug(f"Hermes niche score failed for {niche}: {e}")
        return None


def score_niche(niche: str) -> dict:
    """
    Score a niche using research data + optional Hermes enhancement.
    Returns score dict suitable for upsert_niche().
    """
    rows = _fetch_research_summaries(niche)
    combined_text = ' '.join(
        (r.get('title', '') + ' ' + r.get('summary', '')) for r in rows
    )

    # Heuristic scores from research text
    demand        = _score_text(combined_text, DEMAND_KEYWORDS)        if combined_text else 30.0
    competition   = _score_text(combined_text, COMPETITION_KEYWORDS)   if combined_text else 50.0
    monetization  = _score_text(combined_text, MONETIZATION_KEYWORDS)  if combined_text else 40.0

    # Boost demand if we have many research articles
    article_boost  = min(len(rows) * 3, 20)
    demand         = min(demand + article_boost, 100)

    sources = [r.get('title', '') for r in rows[:5]]

    # Try Hermes enhancement
    ai_scores = _hermes_score_niche(niche)
    if ai_scores:
        demand       = (demand + ai_scores.get('demand_score', demand)) / 2
        competition  = (competition + ai_scores.get('competition_score', competition)) / 2
        monetization = (monetization + ai_scores.get('monetization_score', monetization)) / 2
        notes        = ai_scores.get('notes', '')
    else:
        notes = f"Scored from {len(rows)} research articles."

    return {
        'demand_score':       round(demand, 1),
        'competition_score':  round(competition, 1),
        'monetization_score': round(monetization, 1),
        'research_sources':   sources,
        'notes':              notes,
    }


def run_niche_scan(seeds: Optional[List[str]] = None) -> List[dict]:
    """
    Score all seed niches and upsert to DB.
    Returns list of scored niche records.
    """
    targets = seeds or NICHE_SEEDS
    results = []
    for niche in targets:
        scores = score_niche(niche)
        record = upsert_niche(
            name=niche,
            demand_score=scores['demand_score'],
            competition_score=scores['competition_score'],
            monetization_score=scores['monetization_score'],
            research_sources=scores['research_sources'],
            notes=scores['notes'],
        )
        if record:
            results.append(record)
            logger.info(
                f"Scored niche={niche} total={record.get('total_score')}"
            )
    return results


def validate_niche(name: str, threshold: float = 55.0) -> bool:
    """
    Validate a candidate niche. If total_score >= threshold, mark validated.
    Returns True if validated.
    """
    scores = score_niche(name)
    record = upsert_niche(
        name=name,
        demand_score=scores['demand_score'],
        competition_score=scores['competition_score'],
        monetization_score=scores['monetization_score'],
        research_sources=scores['research_sources'],
        notes=scores['notes'],
    )
    if not record:
        return False

    total = record.get('total_score', 0)
    if total >= threshold:
        update_status(name, 'validated')
        logger.info(f"Niche validated: {name} score={total}")
        return True
    else:
        logger.info(f"Niche below threshold: {name} score={total} < {threshold}")
        return False


def get_validated_for_launch() -> List[dict]:
    """Return validated niches ready to spawn as instances."""
    return list_niches(status='validated', limit=10)


if __name__ == '__main__':
    import sys
    # Manual .env loading
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())

    logging.basicConfig(level=logging.INFO)
    results = run_niche_scan()
    print(f"Scanned {len(results)} niches")
    top = get_top_niches(5)
    for n in top:
        print(f"  {n['name']:35s}  score={n['total_score']}")
