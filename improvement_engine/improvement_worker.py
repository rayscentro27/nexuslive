"""
Improvement Worker.

Cron job that generates candidate improvement experiments from observed outcomes.

Sources:
  - optimization_engine outcomes (low-performing recommendations)
  - signal scoring patterns (consistently low scores)
  - funding match rates (low conversion domains)
  - communication response patterns (low open/response rates)

Generates:
  - improvement_experiments with proposed variants
  - Sends Telegram alert when variants are ready for review

All generation is safe — nothing is promoted without human approval.

Cron: 0 3 * * *  (daily at 3am — after optimization_worker at 2am)

Run: python3 -m improvement_engine.improvement_worker
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
import lib.ssl_fix  # noqa — fixes HTTPS on macOS Python 3.14

logger = logging.getLogger('ImprovementWorker')


def _load_env() -> None:
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())


def _send_telegram(message: str) -> None:
    token   = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        return
    try:
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        body = json.dumps({'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}).encode()
        req  = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


def _sb_get(path: str) -> list:
    key = os.getenv('SUPABASE_KEY', '')
    url = f"{os.getenv('SUPABASE_URL', '')}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return []


def _generate_signal_experiments() -> int:
    """
    Check for signals with consistently low scores.
    Propose a scoring weight adjustment experiment.
    """
    from improvement_engine.improvement_service import propose_experiment, add_variant

    # Find low-scoring signal patterns
    rows = _sb_get(
        "tv_normalized_signals?review_score=lt.0.5&select=symbol,direction&limit=100"
    )
    if len(rows) < 10:
        return 0

    # Aggregate by symbol
    symbols: dict = {}
    for r in rows:
        s = r.get('symbol', 'UNKNOWN')
        symbols[s] = symbols.get(s, 0) + 1

    low_sym = sorted(symbols.items(), key=lambda x: x[1], reverse=True)[:3]
    if not low_sym:
        return 0

    exp = propose_experiment(
        domain='signal',
        title=f"Signal score adjustment — {', '.join(s for s, _ in low_sym)}",
        hypothesis=(
            f"Symbols {[s for s, _ in low_sym]} have {len(rows)} low-scored signals. "
            "Adjusting confidence thresholds may improve signal quality."
        ),
        baseline_config={'low_symbols': [s for s, _ in low_sym], 'sample_size': len(rows)},
        proposed_by='improvement_worker',
    )
    if not exp:
        return 0

    # Propose a variant with tighter entry criteria
    add_variant(
        experiment_id=exp['id'],
        variant_name='tighter_entry_criteria',
        variant_config={
            'min_rr_ratio':        2.5,
            'min_signal_strength': 0.65,
            'excluded_symbols':    [s for s, _ in low_sym],
        },
        rationale='Exclude consistently low-scoring symbols and raise RR requirement.',
        generated_by='improvement_worker',
    )
    logger.info(f"Signal experiment proposed for {[s for s, _ in low_sym]}")
    return 1


def _generate_communication_experiments() -> int:
    """
    Check funnel stall patterns.
    Propose a communication timing experiment.
    """
    from improvement_engine.improvement_service import propose_experiment, add_variant

    stalled = _sb_get(
        "funnel_stage_tracking?status=eq.stalled&select=stage&limit=200"
    )
    if len(stalled) < 5:
        return 0

    # Find most stalled stage
    stages: dict = {}
    for r in stalled:
        s = r.get('stage', 'unknown')
        stages[s] = stages.get(s, 0) + 1

    top_stall = max(stages, key=lambda x: stages[x]) if stages else None
    if not top_stall:
        return 0

    exp = propose_experiment(
        domain='communication',
        title=f"Reduce stall rate at stage: {top_stall}",
        hypothesis=(
            f"Stage '{top_stall}' has {stages[top_stall]} stalled clients. "
            "Reducing nudge delay and adding a secondary touchpoint may reduce stall rate."
        ),
        baseline_config={'target_stage': top_stall, 'stall_count': stages[top_stall]},
        proposed_by='improvement_worker',
    )
    if not exp:
        return 0

    add_variant(
        experiment_id=exp['id'],
        variant_name='earlier_nudge',
        variant_config={'nudge_delay_hours': 24, 'secondary_touchpoint': True},
        rationale='Send first nudge at 24h instead of 48h, add SMS/email followup.',
        generated_by='improvement_worker',
    )
    add_variant(
        experiment_id=exp['id'],
        variant_name='incentive_nudge',
        variant_config={'nudge_delay_hours': 36, 'include_incentive': True, 'incentive': 'free_credit_review'},
        rationale='Offer a free credit review to reactivate stalled clients.',
        generated_by='improvement_worker',
    )
    logger.info(f"Communication experiment proposed for stage={top_stall}")
    return 1


def _generate_source_experiments() -> int:
    """
    Check source health scores.
    Propose scheduling policy changes for low-health sources.
    """
    from improvement_engine.improvement_service import propose_experiment, add_variant
    from source_health.health_scorer import get_low_health_sources

    low_health = get_low_health_sources(threshold=35)
    if len(low_health) < 3:
        return 0

    exp = propose_experiment(
        domain='source',
        title=f"Reschedule {len(low_health)} low-health sources",
        hypothesis=(
            f"{len(low_health)} sources below health threshold 35. "
            "Reducing scan frequency or pausing may improve overall signal quality."
        ),
        baseline_config={'source_count': len(low_health), 'threshold': 35},
        proposed_by='improvement_worker',
    )
    if not exp:
        return 0

    add_variant(
        experiment_id=exp['id'],
        variant_name='reduce_low_health_frequency',
        variant_config={
            'action': 'reduce_frequency',
            'target_health_threshold': 35,
            'new_interval_days': 7,
        },
        rationale='Scan low-health sources weekly instead of daily to reduce noise.',
        generated_by='improvement_worker',
    )
    logger.info(f"Source experiment proposed for {len(low_health)} low-health sources")
    return 1


def run_improvement_cycle() -> dict:
    from improvement_engine.improvement_service import get_pending_review
    from improvement_engine.promotion_rules import apply_approved_variants

    # Generate new experiments
    new_signal  = _generate_signal_experiments()
    new_comms   = _generate_communication_experiments()
    new_source  = _generate_source_experiments()
    total_new   = new_signal + new_comms + new_source

    # Apply any approved variants
    promoted = apply_approved_variants(limit=5)

    # Count items awaiting review
    pending = get_pending_review()

    if total_new > 0 or len(pending) > 0:
        pending_lines = '\n'.join(
            f"  • [{v.get('experiment_id','')[:6]}] {v.get('variant_name','')} "
            f"score={v.get('sim_score') or 'unscored'}"
            for v in pending[:5]
        ) or '  (none)'

        message = (
            f"<b>🔬 Improvement Engine</b>\n"
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
            f"New experiments: {total_new}  "
            f"(signal={new_signal} comms={new_comms} source={new_source})\n"
            f"Variants awaiting review: <b>{len(pending)}</b>\n"
            f"Promoted this cycle: {len(promoted)}\n\n"
            f"<b>Pending review:</b>\n{pending_lines}\n\n"
            f"Approve variants in admin panel before they go live."
        )
        _send_telegram(message)

    logger.info(
        f"Improvement cycle: {total_new} new experiments, "
        f"{len(pending)} pending review, {len(promoted)} promoted"
    )
    return {
        'new_experiments': total_new,
        'pending_review':  len(pending),
        'promoted':        len(promoted),
    }


if __name__ == '__main__':
    _load_env()
    logging.basicConfig(level=logging.INFO)
    result = run_improvement_cycle()
    print(f"New experiments: {result['new_experiments']}")
    print(f"Pending review:  {result['pending_review']}")
    print(f"Promoted:        {result['promoted']}")
