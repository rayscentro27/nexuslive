"""
review/hermes_reviewer.py — AI-powered strategy review worker.

Polls hermes_review_queue for pending strategy items, sends each to
the AI gateway (OpenClaw → Hermes fallback), parses the structured
JSON response, and persists to hermes_reviews.

Flow:
  hermes_review_queue (pending)
    → fetch strategy_library + strategy_scores
    → AI review prompt → structured JSON response
    → hermes_reviews (insert)
    → strategy_library.confidence update
    → hermes_review_queue.status = 'processed'

Run:
  cd ~/nexus-ai/nexus-strategy-lab
  python3 -m review.hermes_reviewer
"""

import sys
import json
import re
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

VERSION = "1.0"

_LAB_ROOT   = Path(__file__).resolve().parent.parent
_NEXUS_ROOT = _LAB_ROOT.parent
for _p in (_LAB_ROOT, _NEXUS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config import settings
settings.validate()

from db import supabase_client as db
from db.ai_client import complete
from review.prompts import build_review_prompt, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BATCH_SIZE   = int(__import__('os').getenv('REVIEW_BATCH_SIZE', '5'))
RATE_LIMIT_COOLDOWN_MINUTES = int(__import__('os').getenv('REVIEW_RATE_LIMIT_COOLDOWN_MINUTES', '10'))


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    """Extract the first JSON object from AI response text."""
    # Strip markdown fences if present
    text = re.sub(r'```(?:json)?\s*', '', text, flags=re.IGNORECASE).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find first {...} block
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return None


def _validate_review(parsed: dict) -> dict:
    """Normalise and validate the AI response. Returns a clean dict."""
    score = int(parsed.get('review_score', 0))
    score = max(0, min(100, score))

    rec = str(parsed.get('recommendation', 'reject')).lower()
    if rec not in ('approve', 'review', 'reject'):
        rec = 'reject' if score < 45 else ('review' if score < 70 else 'approve')

    return {
        'review_score':         score,
        'recommendation':       rec,
        'review_text':          str(parsed.get('review_text', ''))[:2000],
        'strengths':            parsed.get('strengths') or [],
        'weaknesses':           parsed.get('weaknesses') or [],
        'missing_elements':     parsed.get('missing_elements') or [],
        'risk_assessment':      str(parsed.get('risk_assessment', ''))[:500],
        'enhanced_summary':     str(parsed.get('enhanced_summary', ''))[:600],
        'when_it_works':        str(parsed.get('when_it_works', ''))[:400],
        'when_it_fails':        str(parsed.get('when_it_fails', ''))[:400],
        'recommendations':      parsed.get('recommendations') or [],
    }


def _is_rate_limited_text(text: str) -> bool:
    t = (text or '').lower()
    return any(p in t for p in (
        'rate limit',
        'too many requests',
        'capacity',
        'try again later',
    ))


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:
        return None


def _rate_limit_cooldown_active(item: dict) -> bool:
    if not str(item.get('last_error') or '').startswith('rate_limited'):
        return False
    processed_at = _parse_ts(item.get('processed_at'))
    if not processed_at:
        return False
    return (datetime.now(timezone.utc) - processed_at) < timedelta(minutes=RATE_LIMIT_COOLDOWN_MINUTES)


def _fallback_review(strategy: dict, scores: dict, reason: str = '') -> dict:
    """
    Build a deterministic fallback review when the AI gateway is unavailable
    or returns a non-JSON/rate-limited response.
    """
    total = float(scores.get('total_score') or scores.get('overall_score') or 0)
    recommendation = 'reject'
    if total >= 70:
        recommendation = 'approve'
    elif total >= 45:
        recommendation = 'review'

    strengths = []
    weaknesses = []
    missing = []

    if (scores.get('clarity_score') or 0) >= 6:
        strengths.append('Strategy framing is reasonably clear.')
    else:
        weaknesses.append('Strategy framing is vague and needs clearer rules.')

    if (scores.get('risk_definition_score') or 0) >= 6:
        strengths.append('Risk management concepts are present.')
    else:
        missing.append('Add explicit stop loss, invalidation, and position sizing rules.')

    if (scores.get('testability_score') or 0) >= 6:
        strengths.append('Rules look testable enough for paper trading.')
    else:
        weaknesses.append('Entry and exit conditions need to be more testable.')

    summary = strategy.get('summary') or strategy.get('description') or ''
    summary = summary[:220] if summary else 'Deterministic fallback review generated from pre-score data.'

    note = 'AI fallback used'
    if reason:
        note = f"AI fallback used after gateway issue: {reason[:120]}"

    return {
        'review_score': int(max(0, min(100, round(total)))),
        'recommendation': recommendation,
        'review_text': f"{note}. Deterministic pre-score was {total:.2f}, so this item is marked {recommendation}.",
        'strengths': strengths or ['Deterministic score data was available for evaluation.'],
        'weaknesses': weaknesses or ['AI qualitative review was unavailable for this pass.'],
        'missing_elements': missing or ['Retry AI review later for a richer qualitative assessment.'],
        'risk_assessment': 'Risk assessment is based on deterministic scoring because the AI gateway was unavailable.',
        'enhanced_summary': summary,
        'when_it_works': 'Best treated as provisional until a full AI review succeeds.',
        'when_it_fails': 'Confidence is limited when gateway capacity is constrained.',
        'recommendations': [
            'Keep the strategy in the review pipeline for a later AI retry.',
            'Use paper-trading outcomes to validate the deterministic recommendation.',
        ],
        'fallback_reason': reason[:200],
    }


# ── Core review function ──────────────────────────────────────────────────────

def review_strategy(lib_id: str, attempts: int = 0) -> dict | None:
    """
    Fetch a strategy_library entry, run AI review, persist to hermes_reviews.
    Returns the review dict or None on failure.
    """
    # Fetch strategy
    try:
        strategies = db.select('strategy_library', f'id=eq.{lib_id}&select=*&limit=1')
        if not strategies:
            logger.error(f"strategy_library {lib_id} not found")
            return None
        strategy = strategies[0]
    except Exception as e:
        logger.error(f"Could not fetch strategy {lib_id}: {e}")
        return None

    # Fetch latest score
    try:
        scores_rows = db.select('strategy_scores',
                                f'strategy_uuid=eq.{lib_id}&select=*&order=created_at.desc&limit=1')
        scores = scores_rows[0] if scores_rows else {}
    except Exception:
        scores = {}

    # Check if already reviewed
    try:
        existing = db.select('hermes_reviews',
                             f"domain=eq.strategy&entity_id=eq.{lib_id}&select=id&limit=1")
        if existing:
            logger.info(f"Already reviewed: {lib_id[:8]}")
            return {'already_reviewed': True, 'id': existing[0]['id']}
    except Exception:
        pass

    # Build prompt and call AI
    prompt = build_review_prompt(strategy, scores)

    logger.info(f"Reviewing: {strategy.get('strategy_name', strategy.get('title','?'))[:60]} [{lib_id[:8]}]")

    try:
        raw_response = complete(
            prompt,
            system=SYSTEM_PROMPT,
            max_tokens=1024,
            temperature=0.2,
        )
    except RuntimeError as e:
        logger.error(f"AI call failed for {lib_id}: {e}")
        return None

    # Parse response
    parsed = _extract_json(raw_response)
    if not parsed:
        if _is_rate_limited_text(raw_response) and attempts + 1 < MAX_ATTEMPTS:
            logger.warning(f"Rate limited reviewing {lib_id[:8]} — deferring retry")
            return {
                'deferred': True,
                'reason': 'rate_limited',
                'detail': raw_response[:200],
            }
        logger.warning(f"Could not parse AI response for {lib_id}: {raw_response[:200]}")
        review = _fallback_review(strategy, scores, raw_response[:200])
        created_by = 'hermes_review_fallback'
    else:
        review = _validate_review(parsed)
        created_by = 'hermes_review_worker'

    # Persist to hermes_reviews
    review_row = {
        'domain':              'strategy',
        'entity_type':         'strategy_library',
        'entity_id':           lib_id,
        'review_type':         'strategy_evaluation',
        'review_score':        review['review_score'],
        'review_text':         review['review_text'] or 'No review text generated.',
        'recommendations_json': {
            'recommendation':   review['recommendation'],
            'strengths':        review['strengths'],
            'weaknesses':       review['weaknesses'],
            'missing_elements': review['missing_elements'],
            'risk_assessment':  review['risk_assessment'],
            'enhanced_summary': review['enhanced_summary'],
            'when_it_works':    review['when_it_works'],
            'when_it_fails':    review['when_it_fails'],
            'recommendations':  review['recommendations'],
        },
        'created_by': created_by,
    }

    try:
        inserted = db.insert('hermes_reviews', review_row)
        review_id = inserted.get('id')
        logger.info(
            f"Review stored: {lib_id[:8]} score={review['review_score']} "
            f"rec={review['recommendation']} → {review_id}"
        )
    except Exception as e:
        logger.error(f"hermes_reviews insert failed for {lib_id}: {e}")
        return None

    # Update strategy_library confidence (normalise score to 0–1)
    try:
        db.update('strategy_library',
                  {'confidence': round(review['review_score'] / 100.0, 4),
                   'status': review['recommendation']},
                  f'id=eq.{lib_id}')
    except Exception as ue:
        logger.warning(f"Could not update strategy_library confidence: {ue}")

    # Update strategy_library with enhanced content if better
    if review.get('enhanced_summary'):
        try:
            db.update('strategy_library',
                      {'summary': review['enhanced_summary']},
                      f'id=eq.{lib_id}')
        except Exception:
            pass

    return {**review, 'id': review_id, 'lib_id': lib_id}


# ── Queue poller ──────────────────────────────────────────────────────────────

def _mark_queue_item(item_id: str, status: str, error: str = None, **extra):
    try:
        patch = {'status': status,
                 'processed_at': datetime.now(timezone.utc).isoformat()}
        if error:
            patch['last_error'] = error[:500]
        elif status == 'processed':
            patch['last_error'] = None
        patch.update(extra)
        db.update('hermes_review_queue', patch, f'id=eq.{item_id}')
    except Exception as e:
        logger.warning(f"Could not update queue item {item_id}: {e}")


def run_review_cycle(batch_size: int = BATCH_SIZE) -> dict:
    """
    Process one batch of pending hermes_review_queue items.
    Returns { reviewed: int, skipped: int, errors: int }
    """
    try:
        pending = db.select('hermes_review_queue',
                            f'domain=eq.strategy&status=eq.pending'
                            f'&select=*&order=created_at.asc&limit={batch_size}')
    except Exception as e:
        logger.error(f"Could not fetch review queue: {e}")
        return {'reviewed': 0, 'skipped': 0, 'errors': 1}

    if not pending:
        logger.info("No pending strategy reviews in queue.")
        return {'reviewed': 0, 'skipped': 0, 'errors': 0}

    reviewed = skipped = errors = 0

    for item in pending:
        item_id   = item['id']
        lib_id    = item['entity_id']
        attempts  = item.get('attempt_count') or 0

        if _rate_limit_cooldown_active(item):
            logger.info(f"Cooldown active for queue item {item_id} — skipping retry this cycle")
            skipped += 1
            continue

        if attempts >= MAX_ATTEMPTS:
            logger.warning(f"Max attempts reached for queue item {item_id} — marking dead")
            _mark_queue_item(item_id, 'dead', 'max_attempts_exceeded')
            skipped += 1
            continue

        # Mark as processing
        try:
            db.update('hermes_review_queue',
                      {'status': 'processing'},
                      f'id=eq.{item_id}')
        except Exception:
            pass

        result = review_strategy(lib_id, attempts=attempts)

        if result:
            if result.get('deferred') and result.get('reason') == 'rate_limited':
                _mark_queue_item(
                    item_id,
                    'pending',
                    f"rate_limited: {result.get('detail', 'retry later')}",
                    attempt_count=attempts,
                )
                skipped += 1
            elif result.get('already_reviewed'):
                _mark_queue_item(item_id, 'processed', attempt_count=attempts + 1)
                skipped += 1
            else:
                _mark_queue_item(item_id, 'processed', attempt_count=attempts + 1)
                reviewed += 1
        else:
            _mark_queue_item(item_id, 'pending',
                             f'review failed on attempt {attempts + 1}',
                             attempt_count=attempts + 1)
            errors += 1

    logger.info(f"Review cycle: reviewed={reviewed} skipped={skipped} errors={errors}")
    return {'reviewed': reviewed, 'skipped': skipped, 'errors': errors}


# ── Telegram digest ───────────────────────────────────────────────────────────

def send_review_digest(reviews: list[dict]):
    """Send a Telegram summary of recent reviews."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return
    if not reviews:
        return

    try:
        from review.prompts import build_batch_summary_prompt
        prompt  = build_batch_summary_prompt(reviews)
        raw     = complete(prompt, max_tokens=300, temperature=0.2)
        parsed  = _extract_json(raw)
        digest  = parsed.get('digest', '') if parsed else ''
        top     = parsed.get('top_strategy') if parsed else None
        action  = parsed.get('action_required') == 'yes' if parsed else False
        note    = parsed.get('action_note') if parsed else None
    except Exception as e:
        logger.warning(f"Digest generation failed: {e}")
        digest = f"Completed {len(reviews)} strategy reviews."
        top = action = note = None

    lines = [f"*Hermes Strategy Review Digest*", f"Reviews: {len(reviews)}", ""]
    if digest:
        lines.append(digest)
    if top:
        lines.append(f"\n*Top strategy:* {top}")
    if action and note:
        lines.append(f"\n⚠️ *Action required:* {note}")

    try:
        import requests
        requests.post(
            f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage',
            json={'chat_id': settings.TELEGRAM_CHAT_ID,
                  'text': '\n'.join(lines), 'parse_mode': 'Markdown'},
            timeout=10,
        )
    except Exception:
        pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s %(message)s')
    stats = run_review_cycle()
    print(f"\nReview cycle complete: {stats}")
