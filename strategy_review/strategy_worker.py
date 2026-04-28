"""
Strategy Worker.

Polls the research table for unprocessed entries and runs the full
strategy approval pipeline:

  research → strategy_candidates → strategy_scores → strategy_reviews
           → (if approved) approved_strategies

Mirrors signal_poller.py architecture:
  - Reads from shared Supabase data layer
  - Idempotent on every step (safe to re-run)
  - Stale expiry sweep on every Nth run
  - Logs pipeline outcome per candidate

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m strategy_review.strategy_worker

Or via cron (every 30 minutes):
  */30 * * * * cd /Users/raymonddavis/nexus-ai && source .env && \
      python3 -m strategy_review.strategy_worker >> logs/strategy_worker.log 2>&1
"""

import os
import sys
import json
import logging
import urllib.request
from datetime import datetime, timezone

# Load .env if present
_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ',
)
logger = logging.getLogger('StrategyWorker')

from strategy_candidate_ingest_service  import ingest_strategy_candidate
from strategy_scoring_service           import score_strategy_candidate
from strategy_approval_service          import approve_strategy_candidate, expire_stale_strategy_candidates
from approved_strategy_publish_service  import publish_approved_strategy

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

BATCH_SIZE      = int(os.getenv('STRATEGY_BATCH_SIZE', '20'))
EXPIRE_EVERY_N  = int(os.getenv('STRATEGY_EXPIRE_EVERY_N', '5'))

_run_count = 0


# ─── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


# ─── Fetch unprocessed research rows ─────────────────────────────────────────

def _fetch_unprocessed_research(limit: int) -> list:
    """
    Return research rows that don't yet have a strategy_candidates entry.
    Uses a NOT IN approach via the strategy_candidates source_research_id.
    """
    # Get all already-ingested source_research_ids
    try:
        ingested = _sb_get(
            "strategy_candidates?select=source_research_id&limit=10000"
        )
        ingested_ids = {str(row['source_research_id']) for row in ingested if row.get('source_research_id')}
    except Exception as e:
        logger.warning(f"Could not fetch ingested ids: {e}")
        ingested_ids = set()

    # Fetch recent research rows
    try:
        research_rows = _sb_get(
            f"research?select=id,title,content,source,created_at"
            f"&order=created_at.desc"
            f"&limit={limit * 3}"   # over-fetch to allow filtering
        )
    except Exception as e:
        logger.error(f"Failed to fetch research rows: {e}")
        return []

    # Filter out already-ingested
    unprocessed = [
        r for r in research_rows
        if str(r.get('id', '')) not in ingested_ids
           and r.get('title')
           and r.get('content')
    ]
    return unprocessed[:limit]


# ─── Per-candidate pipeline ───────────────────────────────────────────────────

def _run_pipeline(research_row: dict) -> str:
    """
    Run ingest → score → approve → publish for one research row.
    Returns: 'approved' | 'rejected' | 'error'
    """
    title = research_row.get('title', '')[:60]

    # 1. Ingest
    candidate_id = ingest_strategy_candidate(research_row)
    if not candidate_id:
        logger.error(f"Ingest failed for research {research_row.get('id')} ({title})")
        return 'error'

    # 2. Fetch candidate dict (need raw_content for scoring)
    try:
        rows = _sb_get(f"strategy_candidates?id=eq.{candidate_id}&select=*&limit=1")
        candidate = rows[0] if rows else {}
    except Exception as e:
        logger.error(f"Could not fetch candidate {candidate_id}: {e}")
        return 'error'

    # 3. Score
    score = score_strategy_candidate(candidate_id, candidate)
    if not score:
        logger.error(f"Scoring failed for candidate {candidate_id} ({title})")
        return 'error'

    # 4. Approve / reject
    approval = approve_strategy_candidate(candidate_id, score, candidate)

    if not approval.get('approved'):
        logger.warning(
            f"REJECTED strategy candidate {candidate_id} ({title}) "
            f"| {approval.get('reason', '')}"
        )
        return 'rejected'

    # 5. Publish
    strategy_id = publish_approved_strategy(candidate_id, candidate, score)
    if strategy_id:
        logger.info(
            f"APPROVED & PUBLISHED strategy {strategy_id} ← {candidate_id} ({title}) "
            f"| score={score.get('score_total')} conf={score.get('confidence_label')} "
            f"diff={score.get('difficulty_level')}"
        )
        return 'approved'
    else:
        logger.error(f"Publish failed for candidate {candidate_id} ({title})")
        return 'error'


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    global _run_count
    _run_count += 1

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    logger.info(f"Strategy worker starting (run #{_run_count}, batch={BATCH_SIZE})")

    research_rows = _fetch_unprocessed_research(BATCH_SIZE)

    if not research_rows:
        logger.info("No unprocessed research rows found.")
    else:
        logger.info(f"Processing {len(research_rows)} research row(s)...")
        approved = rejected = errors = 0
        for row in research_rows:
            outcome = _run_pipeline(row)
            if outcome == 'approved':   approved += 1
            elif outcome == 'rejected': rejected += 1
            else:                       errors   += 1

        logger.info(
            f"Pipeline complete — approved={approved} rejected={rejected} errors={errors}"
        )

    # Stale expiry sweep every N runs
    if _run_count % EXPIRE_EVERY_N == 0:
        logger.info("Running stale candidate expiry sweep...")
        expire_stale_strategy_candidates(max_age_hours=168)  # 7 days

    logger.info("Strategy worker done.")


if __name__ == '__main__':
    main()
