"""
run_pipeline.py — Full strategy lab pipeline runner.

Stages:
  1. Ingest   — research table + local .summary files → sources/transcripts/candidates
  2. Score    — candidates (draft) → strategy_scores
  3. Queue    — scored+approved candidates → hermes_review_queue (Prompt 3)
  4. Report   — summary + Telegram notification

Usage:
  cd ~/nexus-ai/nexus-strategy-lab
  python3 run_pipeline.py
  python3 run_pipeline.py --ingest-only
  python3 run_pipeline.py --score-only
  python3 run_pipeline.py --batch-size 10
  python3 run_pipeline.py --no-files
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

_LAB_ROOT   = Path(__file__).resolve().parent
_NEXUS_ROOT = _LAB_ROOT.parent
for _p in (_LAB_ROOT, _NEXUS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config import settings
settings.validate()

from ingestion.ingest       import run_ingest
from scoring.scorer         import run_scoring, score_candidate
from review.hermes_reviewer import run_review_cycle, send_review_digest
from trading.engine         import run_demo_trades
from db import supabase_client as db

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ',
)
logger = logging.getLogger('StrategyLab')


# ── Telegram notification ─────────────────────────────────────────────────────

def _notify(text: str):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return
    try:
        import requests
        requests.post(
            f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage',
            json={'chat_id': settings.TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'},
            timeout=10,
        )
    except Exception:
        pass


# ── Queue approved candidates for Hermes review ───────────────────────────────

def _queue_for_hermes(batch_size: int = 20) -> int:
    """
    Find scored candidates with recommendation='approve' not yet in hermes_review_queue.
    Adds them to hermes_review_queue for Prompt 3 processing.
    """
    try:
        # Candidates with approve recommendation not yet queued
        # Queue both 'approve' and 'review' recommendations for AI evaluation
        scores_approve = db.select('strategy_scores',
            f'recommendation=eq.approve&select=strategy_uuid,id&limit={batch_size}')
        scores_review  = db.select('strategy_scores',
            f'recommendation=eq.review&select=strategy_uuid,id&limit={batch_size}')
        scores = scores_approve + scores_review
        if not scores:
            return 0

        # Get already-queued entity_ids
        queued_existing = db.select('hermes_review_queue',
                           "domain=eq.strategy&entity_type=eq.strategy_library"
                           "&select=entity_id&limit=10000")
        queued = queued_existing
        queued_ids = {r['entity_id'] for r in queued if r.get('entity_id')}

        queued_count = 0
        for s in scores:
            cid = str(s['strategy_uuid'])
            if cid in queued_ids:
                continue
            try:
                db.insert('hermes_review_queue', {
                    'domain':       'strategy',
                    'entity_type':  'strategy_library',
                    'entity_id':    cid,
                    'status':       'pending',
                    'attempt_count': 0,
                })
                queued_count += 1
            except Exception as e:
                logger.warning(f"Could not queue candidate {cid}: {e}")

        if queued_count:
            logger.info(f"Queued {queued_count} candidates for Hermes review")
        return queued_count

    except Exception as e:
        logger.error(f"Hermes queue step failed: {e}")
        return 0


# ── Stats ─────────────────────────────────────────────────────────────────────

def _stats() -> dict:
    try:
        return {
            'library':    db.count('strategy_library'),
            'scored':     db.count('strategy_library', 'status=eq.scored'),
            'queued':     db.count('hermes_review_queue',
                                   'domain=eq.strategy&status=eq.pending'),
            'reviewed':   db.count('hermes_reviews', 'domain=eq.strategy'),
        }
    except Exception:
        return {}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Nexus Strategy Lab pipeline')
    parser.add_argument('--ingest-only', action='store_true')
    parser.add_argument('--score-only',  action='store_true')
    parser.add_argument('--batch-size',  type=int, default=20)
    parser.add_argument('--no-files',    action='store_true', help='Skip local .summary files')
    args = parser.parse_args()

    start  = datetime.now(timezone.utc)
    totals = {'ingested': 0, 'scored': 0, 'queued': 0, 'reviewed': 0, 'traded': 0, 'errors': 0}

    logger.info(f"=== Strategy Lab pipeline start (batch={args.batch_size}) ===")

    # Stage 1: Ingest
    if not args.score_only:
        logger.info("Stage 1: Ingest")
        r = run_ingest(batch_size=args.batch_size, include_files=not args.no_files)
        totals['ingested'] = r['ingested']
        totals['errors']  += r['errors']

    if args.ingest_only:
        logger.info(f"Ingest-only — done. ingested={totals['ingested']}")
        return

    # Stage 2: Score
    if not args.ingest_only:
        logger.info("Stage 2: Score")
        r = run_scoring(batch_size=args.batch_size)
        totals['scored'] = r['scored']
        totals['errors'] += r['errors']

    if args.score_only:
        logger.info(f"Score-only — done. scored={totals['scored']}")
        return

    # Stage 3: Queue approved/review recommendations for Hermes
    logger.info("Stage 3: Queue for Hermes review")
    totals['queued'] = _queue_for_hermes(args.batch_size)

    # Stage 4: Run Hermes review cycle
    logger.info("Stage 4: Hermes review cycle")
    r = run_review_cycle(batch_size=args.batch_size)
    totals['reviewed'] = r['reviewed']
    totals['errors']  += r['errors']

    # Stage 5: Demo trading
    logger.info("Stage 5: Demo trading engine")
    r = run_demo_trades(trades_per_strategy=2, strategy_limit=args.batch_size)
    totals['traded'] = r['trades']
    totals['errors'] += r['errors']

    if totals['reviewed'] > 0:
        # Fetch recent reviews for digest
        try:
            recent = db.select('hermes_reviews',
                               'domain=eq.strategy&select=entity_id,review_score,recommendations_json'
                               '&order=created_at.desc&limit=10')
            for rev in recent:
                rec_json = rev.get('recommendations_json') or {}
                rev['strategy_name'] = rec_json.get('enhanced_summary', '')[:40]
                rev['recommendation'] = rec_json.get('recommendation', '?')
            send_review_digest(recent)
        except Exception:
            pass

    # Summary
    elapsed = (datetime.now(timezone.utc) - start).seconds
    stats   = _stats()

    logger.info(
        f"=== Pipeline complete ({elapsed}s) | "
        f"ingested={totals['ingested']} scored={totals['scored']} "
        f"queued={totals['queued']} reviewed={totals['reviewed']} "
        f"traded={totals['traded']} errors={totals['errors']} ==="
    )
    if stats:
        logger.info(
            f"Supabase totals: library={stats.get('library','-')} "
            f"scored={stats.get('scored','-')} "
            f"hermes_queue={stats.get('queued','-')} reviewed={stats.get('reviewed','-')}"
        )

    if totals['ingested'] > 0 or totals['scored'] > 0:
        _notify(
            f"*Strategy Lab* run complete\n"
            f"Ingested: {totals['ingested']} | Scored: {totals['scored']} | "
            f"Queued for Hermes: {totals['queued']}\n"
            f"Total in library: {stats.get('library','?')} | "
            f"Pending review: {stats.get('queued','?')}"
        )


if __name__ == '__main__':
    main()
