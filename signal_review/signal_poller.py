#!/usr/bin/env python3
"""
Signal Poller — main loop for the signal review workflow.

Polls tv_normalized_signals for status='new' every POLL_INTERVAL seconds.
For each new signal:
  1. Calls signal_reviewer → OpenClaw AI review
  2. If AI approves → calls risk_gate → risk check + Telegram alert
  3. If AI rejects → sends Telegram reject alert
  4. Updates signal status in Supabase

Run:
  python3 ~/nexus-ai/signal_review/signal_poller.py
"""

import os
import sys
import json
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime

# Load .env from nexus-ai root
_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())

from signal_reviewer import review_signal
from risk_gate import run_risk_gate, reject_signal
from signal_candidate_ingest_service import ingest_signal_candidate
from signal_scoring_service import score_signal_candidate
from signal_approval_service import approve_signal_candidate, expire_stale_candidates
from approved_signal_publish_service import publish_approved_signal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '..', 'logs', 'signal_review.log')),
    ]
)
logger = logging.getLogger('SignalPoller')

SUPABASE_URL   = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY   = os.getenv('SUPABASE_KEY', '')
POLL_INTERVAL  = int(os.getenv('SIGNAL_POLL_INTERVAL', '30'))   # seconds
MAX_PER_POLL   = int(os.getenv('SIGNAL_MAX_PER_POLL', '5'))     # max signals per cycle


def fetch_new_signals() -> list:
    url = (
        f"{SUPABASE_URL}/rest/v1/tv_normalized_signals"
        f"?status=eq.new&order=created_at.asc&limit={MAX_PER_POLL}&select=*"
    )
    req = urllib.request.Request(url, headers={
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def mark_processing(signal_id: str) -> bool:
    """Attempt to claim a signal by flipping status new → processing.

    Returns True only if this worker successfully claimed the row.
    This prevents duplicate processing when multiple pollers fetch the same
    signal before either has updated its status.
    """
    import urllib.parse

    encoded_id = urllib.parse.quote(str(signal_id), safe='')
    url = (
        f"{SUPABASE_URL}/rest/v1/tv_normalized_signals"
        f"?id=eq.{encoded_id}&status=eq.new&select=id,status"
    )
    body = json.dumps({'status': 'processing'}).encode()
    req = urllib.request.Request(
        url, data=body, method='PATCH',
        headers={
            'apikey':        SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type':  'application/json',
            'Prefer':        'return=representation',
        }
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        rows = json.loads(r.read())
    return bool(rows)


def _run_scoring_pipeline(signal: dict, ai_review: dict):
    """
    Ingest → Score → Approve → Publish.
    Non-fatal: failures are logged but do not affect the existing Telegram alert flow.
    """
    signal_id = signal.get('id', 'unknown')
    try:
        candidate_id = ingest_signal_candidate(signal, ai_review)
        if not candidate_id:
            logger.warning(f"Scoring pipeline: ingest returned no candidate_id for {signal_id}")
            return

        # Fetch candidate back to get normalised fields for scorer
        import urllib.parse
        url = (
            f"{SUPABASE_URL}/rest/v1/signal_candidates"
            f"?id=eq.{urllib.parse.quote(candidate_id)}&select=*&limit=1"
        )
        req = urllib.request.Request(url, headers={
            'apikey':        SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
        if not rows:
            logger.error(f"Scoring pipeline: candidate {candidate_id} not found after insert")
            return
        candidate = rows[0]

        score = score_signal_candidate(candidate_id, candidate, ai_review)
        if not score:
            logger.warning(f"Scoring pipeline: scoring returned None for candidate {candidate_id}")
            return

        approval = approve_signal_candidate(candidate_id, score)
        if not approval.get('approved'):
            logger.info(
                f"Scoring pipeline: candidate {candidate_id} not approved for portal: "
                f"{approval.get('reason')}"
            )
            return

        pub_id = publish_approved_signal(candidate_id, candidate, score, ai_review)
        if pub_id:
            logger.info(f"Scoring pipeline complete: approved_signal {pub_id} published")

    except Exception as e:
        logger.error(f"Scoring pipeline error for signal {signal_id}: {e}")


def process_signal(signal: dict):
    signal_id = signal['id']
    symbol    = signal.get('symbol', 'UNKNOWN')
    side      = signal.get('side', '').upper()

    logger.info(f"Processing signal {signal_id} — {symbol} {side}")

    # Step 1: claim signal (only one worker should succeed)
    try:
        claimed = mark_processing(signal_id)
        if not claimed:
            logger.info(f"Signal {signal_id} already claimed by another worker — skipping")
            return
    except Exception as e:
        logger.error(f"Could not claim signal {signal_id}: {e}")
        return

    # Step 2: AI review
    try:
        review = review_signal(signal)
    except Exception as e:
        logger.error(f"AI review failed for {signal_id}: {e}")
        reject_signal(signal, f"AI review error: {e}")
        return

    action = review.get('action', 'reject')
    logger.info(f"AI decision: {action} | {symbol} {side} | reasoning: {review.get('reasoning', '')}")

    # Step 3: route based on AI decision
    if action == 'approve':
        try:
            gate_result = run_risk_gate(signal, review)
        except Exception as e:
            logger.error(f"Risk gate failed for {signal_id}: {e}")
            reject_signal(signal, f"Risk gate error: {e}")
            return

        # Step 4: scoring pipeline — only runs if risk gate passed
        if gate_result.get('approved'):
            _run_scoring_pipeline(signal, review)

    elif action == 'hold':
        # Put back to 'new' so it gets re-evaluated next cycle
        try:
            url  = f"{SUPABASE_URL}/rest/v1/tv_normalized_signals?id=eq.{signal_id}"
            body = json.dumps({'status': 'new'}).encode()
            req  = urllib.request.Request(
                url, data=body, method='PATCH',
                headers={
                    'apikey': SUPABASE_KEY,
                    'Authorization': f'Bearer {SUPABASE_KEY}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=minimal',
                }
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
            logger.info(f"Signal {signal_id} held — will re-evaluate next cycle")
        except Exception as e:
            logger.error(f"Could not reset signal to new: {e}")

    else:  # reject
        reason = review.get('reasoning', 'AI rejected signal')
        reject_signal(signal, reason)


def run():
    logger.info(f"Signal Poller started — polling every {POLL_INTERVAL}s | max {MAX_PER_POLL} per cycle")
    logger.info(f"Supabase: {SUPABASE_URL[:40]}...")

    consecutive_errors = 0
    poll_count = 0

    while True:
        try:
            signals = fetch_new_signals()
            if signals:
                logger.info(f"Found {len(signals)} new signal(s)")
                for signal in signals:
                    process_signal(signal)
            else:
                logger.debug("No new signals")

            # Sweep stale candidates every 10 poll cycles (~5 min at 30s interval)
            poll_count += 1
            if poll_count % 10 == 0:
                try:
                    expire_stale_candidates(max_age_hours=24)
                except Exception as e:
                    logger.warning(f"Stale candidate sweep failed: {e}")

            consecutive_errors = 0

        except urllib.error.URLError as e:
            consecutive_errors += 1
            logger.error(f"Supabase fetch failed (attempt {consecutive_errors}): {e}")
            if consecutive_errors >= 5:
                logger.critical("5 consecutive Supabase errors — check connectivity")

        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Unexpected error in poll loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    run()
