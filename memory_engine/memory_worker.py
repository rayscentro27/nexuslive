"""
Memory Worker.

Runs periodically to:
  1. Consolidate recent signal and strategy pipeline results into ai_memory
     (signal_history, strategy_history types).
  2. Write a conversation_summary of the last N pipeline events.
  3. Expire old memory rows.

This is the only writer of 'signal_history' and 'strategy_history' entries —
the pipeline services themselves are kept free of memory side-effects.

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m memory_engine.memory_worker

Or via cron (every 2 hours):
  0 */2 * * * cd /Users/raymonddavis/nexus-ai && source .env && \\
      python3 -m memory_engine.memory_worker >> logs/memory_worker.log 2>&1
"""

import os
import sys
import json
import logging
import urllib.request
from datetime import datetime, timezone

# Load .env
_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ',
)
logger = logging.getLogger('MemoryWorker')

from memory_store_service import store_memory, expire_old_memories

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# How many hours back to look for new pipeline events
LOOKBACK_HOURS = int(os.getenv('MEMORY_LOOKBACK_HOURS', '6'))
# Memory TTL in hours (default 30 days)
MEMORY_TTL_HOURS = int(os.getenv('MEMORY_TTL_HOURS', '720'))


def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


# ─── Signal history consolidation ─────────────────────────────────────────────

def _fetch_recent_approved_signals(hours: int) -> list:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return _sb_get(
        f"approved_signals"
        f"?created_at=gt.{cutoff}"
        f"&select=id,symbol,direction,timeframe,setup_type,market_type,"
        f"headline,confidence_label,risk_label,score_total,created_at"
        f"&order=created_at.desc&limit=50"
    )


def _fetch_recent_rejected_signals(hours: int) -> list:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    # Rejected candidates have review_status='rejected' in signal_reviews
    return _sb_get(
        f"signal_reviews"
        f"?created_at=gt.{cutoff}"
        f"&review_action=eq.reject"
        f"&select=candidate_id,review_action,notes,score_total,confidence_label,created_at"
        f"&order=created_at.desc&limit=50"
    )


def consolidate_signal_history(hours: int) -> int:
    """Write signal_history memory entries for recent approved signals."""
    approved = _fetch_recent_approved_signals(hours)
    stored   = 0
    for sig in approved:
        content = (
            f"APPROVED SIGNAL: {sig.get('symbol','?')} {sig.get('direction','?')} "
            f"[{sig.get('timeframe','?')}] score={sig.get('score_total','?')} "
            f"conf={sig.get('confidence_label','?')} risk={sig.get('risk_label','?')}. "
            f"Setup: {sig.get('setup_type','?')}. {sig.get('headline','')}"
        ).strip()
        meta = {
            'symbol':    sig.get('symbol'),
            'direction': sig.get('direction'),
            'timeframe': sig.get('timeframe'),
            'source_id': sig.get('id'),
        }
        result = store_memory(
            memory_type='signal_history',
            content=content,
            subject_id=sig.get('symbol'),
            subject_type='signal',
            meta=meta,
            expires_hours=MEMORY_TTL_HOURS,
        )
        if result:
            stored += 1
    return stored


# ─── Strategy history consolidation ───────────────────────────────────────────

def _fetch_recent_approved_strategies(hours: int) -> list:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return _sb_get(
        f"approved_strategies"
        f"?created_at=gt.{cutoff}"
        f"&select=id,title,strategy_type,summary,difficulty_level,"
        f"confidence_label,score_total,when_it_works,when_it_fails,created_at"
        f"&order=created_at.desc&limit=30"
    )


def _fetch_recent_rejected_strategies(hours: int) -> list:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return _sb_get(
        f"strategy_reviews"
        f"?created_at=gt.{cutoff}"
        f"&review_action=eq.reject"
        f"&select=candidate_id,notes,score_total,confidence_label,created_at"
        f"&order=created_at.desc&limit=30"
    )


def consolidate_strategy_history(hours: int) -> int:
    """Write strategy_history memory entries for recent approved strategies."""
    approved = _fetch_recent_approved_strategies(hours)
    stored   = 0
    for strat in approved:
        content = (
            f"APPROVED STRATEGY: {strat.get('title','?')} "
            f"[{strat.get('strategy_type','?')}] score={strat.get('score_total','?')} "
            f"diff={strat.get('difficulty_level','?')} conf={strat.get('confidence_label','?')}. "
            f"{strat.get('summary','')[:200]}"
        ).strip()
        meta = {
            'strategy_type': strat.get('strategy_type'),
            'source_id':     strat.get('id'),
        }
        result = store_memory(
            memory_type='strategy_history',
            content=content,
            subject_id=strat.get('id'),
            subject_type='strategy',
            meta=meta,
            expires_hours=MEMORY_TTL_HOURS,
        )
        if result:
            stored += 1
    return stored


# ─── Conversation summary ──────────────────────────────────────────────────────

def write_pipeline_summary(signal_count: int, strategy_count: int, hours: int) -> None:
    """Write a brief pipeline summary as a conversation_summary memory."""
    if signal_count == 0 and strategy_count == 0:
        return
    now     = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    content = (
        f"Pipeline run at {now}: "
        f"stored {signal_count} signal memories and "
        f"{strategy_count} strategy memories from the last {hours}h."
    )
    store_memory(
        memory_type='conversation_summary',
        content=content,
        expires_hours=168,   # 7 days
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    logger.info(f"Memory worker starting (lookback={LOOKBACK_HOURS}h, ttl={MEMORY_TTL_HOURS}h)")

    # 1. Consolidate recent pipeline results
    sig_stored   = consolidate_signal_history(LOOKBACK_HOURS)
    strat_stored = consolidate_strategy_history(LOOKBACK_HOURS)
    logger.info(f"Stored signal_history={sig_stored} strategy_history={strat_stored}")

    # 2. Write pipeline summary
    write_pipeline_summary(sig_stored, strat_stored, LOOKBACK_HOURS)

    # 3. Expire old memories
    expired = expire_old_memories(max_age_hours=MEMORY_TTL_HOURS)
    if expired:
        logger.info(f"Expired {expired} old memory rows")

    logger.info("Memory worker done.")


if __name__ == '__main__':
    main()
