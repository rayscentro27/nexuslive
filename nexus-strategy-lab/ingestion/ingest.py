"""
ingestion/ingest.py — Strategy ingestion pipeline.

Flow per research row:
  research (id, title, content)
    → strategy_library  (full structured strategy record)

strategy_library is the FK anchor for strategy_scores and portal display.
strategy_candidates (from Windows migration) is the structured drafting table —
created in parallel for portal editing workflows.

Idempotent on title — safe to re-run.
"""

import sys
import json
import re
import logging
from pathlib import Path
from datetime import datetime, timezone

_LAB_ROOT   = Path(__file__).resolve().parent.parent
_NEXUS_ROOT = _LAB_ROOT.parent
for _p in (_LAB_ROOT, _NEXUS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config import settings
settings.validate()

import os
TENANT_ID = os.getenv('NEXUS_TENANT_ID', '')

from db import supabase_client as db

logger = logging.getLogger(__name__)


# ── Content analysis helpers ──────────────────────────────────────────────────

def _infer_market(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ['forex', 'eurusd', 'gbpusd', 'currency pair', 'fx ']):
        return 'forex'
    if any(k in t for k in ['bitcoin', 'crypto', 'ethereum', 'defi', 'altcoin']):
        return 'crypto'
    if any(k in t for k in ['stock', 'equity', 'nasdaq', 's&p', 'earnings', 'shares']):
        return 'equities'
    if any(k in t for k in ['futures', 'es contract', 'nq contract', 'commodity']):
        return 'futures'
    if any(k in t for k in ['option', 'calls', 'puts', 'straddle', 'premium']):
        return 'options'
    return 'multi'


def _infer_setup_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ['scalp', '1-minute', '1m chart', 'micro trade']): return 'scalping'
    if any(k in t for k in ['mean reversion', 'revert', 'oversold', 'overbought']): return 'mean_reversion'
    if any(k in t for k in ['breakout', 'break out', 'range break']): return 'breakout'
    if any(k in t for k in ['momentum', 'rsi divergence', 'volume surge']): return 'momentum'
    if any(k in t for k in ['trend following', 'moving average', 'ema cross', 'sma cross']): return 'trend_following'
    if any(k in t for k in ['pullback', 'pull back', 'retracement', 'fibonacci']): return 'pullback'
    if any(k in t for k in ['reversal', 'pin bar', 'engulfing', 'double top', 'double bottom']): return 'reversal'
    if any(k in t for k in ['range trading', 'support and resistance', 'channel']): return 'range'
    if any(k in t for k in ['swing trade', 'multi-day', 'overnight hold']): return 'swing'
    return 'general'


def _infer_timeframe(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ['1-minute', '1m chart', 'scalp']): return 'M1'
    if any(k in t for k in ['5-minute', '5m chart', '15-minute']): return 'M5'
    if any(k in t for k in ['1-hour', '1h chart', 'hourly', 'h1']): return 'H1'
    if any(k in t for k in ['4-hour', '4h', 'h4']): return 'H4'
    if any(k in t for k in ['daily', 'day chart', 'd1']): return 'D1'
    if any(k in t for k in ['weekly', 'w1']): return 'W1'
    return None


def _extract_indicators(text: str) -> list:
    known = ['rsi', 'macd', 'ema', 'sma', 'bollinger bands', 'atr', 'stochastic', 'adx',
             'ichimoku', 'vwap', 'fibonacci', 'volume', 'parabolic sar', 'cci', 'williams %r']
    t = text.lower()
    return [ind for ind in known if ind in t]


def _extract_rule_sentences(text: str, keywords: list, max_count: int = 3) -> list:
    sentences = re.split(r'[.!?\n]+', text)
    matched = [s.strip() for s in sentences
               if any(k in s.lower() for k in keywords) and 15 < len(s.strip()) < 300]
    return matched[:max_count]


def _extract_channel(title: str) -> str:
    return title.split(' - ', 1)[0].strip() if ' - ' in title else ''


def _first_paragraph(text: str, max_len: int = 500) -> str:
    paras = [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if len(p.strip()) > 40]
    if paras:
        p = paras[0]
        return (p[:max_len].rsplit(' ', 1)[0] + '…') if len(p) > max_len else p
    return text[:max_len]


# ── Idempotency ───────────────────────────────────────────────────────────────

def _library_exists(title: str) -> str | None:
    try:
        # URL-encode for query param
        from urllib.parse import quote
        rows = db.select('strategy_library',
                         f'title=eq.{quote(title)}&select=id&limit=1')
        return rows[0]['id'] if rows else None
    except Exception:
        return None


# ── Core ingest ───────────────────────────────────────────────────────────────

def ingest_one(research_row: dict) -> str | None:
    """
    Ingest a single research row into strategy_library.
    Returns strategy_library UUID or None on failure.
    """
    title   = (research_row.get('title') or '').strip()
    content = (research_row.get('content') or '').strip()
    res_id  = research_row.get('id')

    if not title or not content:
        return None

    # Idempotency
    existing = _library_exists(title)
    if existing:
        logger.info(f"Already in library: {title[:60]}")
        return existing

    market    = _infer_market(title + ' ' + content)
    setup     = _infer_setup_type(content)
    timeframe = _infer_timeframe(content)
    channel   = _extract_channel(title)
    indicators = _extract_indicators(content)
    strategy_name = title.split(' - ', 1)[-1].strip() if ' - ' in title else title

    entry_sentences = _extract_rule_sentences(content,
        ['entry', 'enter', 'buy when', 'sell when', 'long when', 'short when', 'trigger'])
    exit_sentences  = _extract_rule_sentences(content,
        ['exit', 'close', 'take profit', 'target', 'profit level'])
    risk_sentences  = _extract_rule_sentences(content,
        ['stop loss', 'stop-loss', 'invalidation', 'risk', 'position size', 'max loss'])
    inv_sentences   = _extract_rule_sentences(content,
        ['invalidation', 'avoid', 'does not work', 'when to exit', 'cut loss'])
    pitfall_sentences = _extract_rule_sentences(content,
        ['avoid', 'pitfall', 'mistake', 'common error', 'fails in', 'choppy'])

    import re as _re
    slug = _re.sub(r'[^a-z0-9]+', '-', strategy_name.lower())[:80].strip('-')

    row = {
        'title':              title[:500],
        'channel_name':       channel or None,
        'strategy_name':      strategy_name[:300],
        'strategy_id':        slug,
        'summary':            _first_paragraph(content),
        'setup_type':         setup,
        'market':             market,
        'entry_rules':        {'conditions': entry_sentences},
        'exit_rules':         {'conditions': exit_sentences},
        'risk_rules':         {'conditions': risk_sentences},
        'invalidation_rules': {'conditions': inv_sentences},
        'indicators':         indicators,
        'pitfalls':           {'notes': pitfall_sentences},
        'confidence':         0.5,   # 0.0–1.0; updated by scoring
        'status':             'draft',
        'version':            1,
        'created_by':         'ingest_worker',
    }
    if timeframe:
        row['timeframes'] = [timeframe]
    if research_row.get('source'):
        row['source_url'] = str(research_row['source'])[:1000]

    # ── Step 1: research_artifacts (FK anchor for strategy_library) ──────────
    import hashlib
    trace_id = hashlib.md5(title.encode()).hexdigest()[:16]
    artifact_row = {
        'title':          title[:500],
        'source_type':    'youtube_summary',
        'source_url':     str(research_row.get('source') or '')[:1000] or None,
        'channel_name':   channel or None,
        'summary':        _first_paragraph(content, max_len=300),
        'strategy_built': False,
        'trace_id':       trace_id,
    }
    try:
        artifact = db.insert('research_artifacts', artifact_row)
        artifact_id = artifact.get('id')
        if not artifact_id:
            logger.error(f"research_artifacts insert returned no id for '{title[:60]}'")
            return None
    except Exception as e:
        logger.error(f"research_artifacts insert failed for '{title[:60]}': {e}")
        return None

    # ── Step 2: strategy_library ──────────────────────────────────────────
    row['artifact_id'] = artifact_id
    row['trace_id']    = trace_id

    try:
        inserted = db.insert('strategy_library', row)
        lib_id = inserted.get('id')
        if not lib_id:
            logger.error(f"strategy_library insert returned no id for '{title[:60]}'")
            return None
        logger.info(
            f"Ingested: {title[:60]} | market={market} setup={setup} "
            f"indicators={indicators[:3]} → lib={lib_id[:8]}"
        )
        return lib_id
    except Exception as e:
        logger.error(f"strategy_library insert failed for '{title[:60]}': {e}")
        return None


# ── Batch runners ─────────────────────────────────────────────────────────────

def ingest_from_research_table(batch_size: int = 20) -> dict:
    """Pull unprocessed rows from research table → strategy_library."""
    try:
        existing = db.select('strategy_library', 'select=title&limit=10000')
        existing_titles = {r['title'] for r in existing if r.get('title')}
    except Exception as e:
        logger.warning(f"Could not fetch existing library entries: {e}")
        existing_titles = set()

    try:
        research = db.select('research',
                             f'select=id,title,content,source,created_at'
                             f'&order=created_at.desc&limit={batch_size * 3}')
    except Exception as e:
        logger.error(f"Could not fetch research rows: {e}")
        return {'ingested': 0, 'skipped': 0, 'errors': 1}

    unprocessed = [
        r for r in research
        if r.get('title') and r.get('content')
        and r['title'] not in existing_titles
    ][:batch_size]

    ingested = errors = 0
    for row in unprocessed:
        result = ingest_one(row)
        if result:
            ingested += 1
        else:
            errors += 1

    logger.info(
        f"research table ingest: ingested={ingested} "
        f"already_in_library={len(existing_titles)} errors={errors}"
    )
    return {'ingested': ingested, 'skipped': len(existing_titles), 'errors': errors}


def ingest_from_summary_files(limit: int = 50) -> dict:
    """Read local .summary files → strategy_library."""
    summary_dir = settings.RESEARCH_OUTPUT_DIR
    if not summary_dir.exists():
        return {'ingested': 0, 'skipped': 0, 'errors': 0}

    files = list(summary_dir.glob('*.summary'))
    if not files:
        return {'ingested': 0, 'skipped': 0, 'errors': 0}

    try:
        existing = db.select('strategy_library', 'select=title&limit=10000')
        existing_titles = {r['title'] for r in existing if r.get('title')}
    except Exception:
        existing_titles = set()

    ingested = skipped = errors = 0
    for fp in files[:limit]:
        try:
            text  = fp.read_text(encoding='utf-8', errors='replace').strip()
            title = fp.stem.replace('.en.vtt', '').strip()
            if not text or title in existing_titles:
                skipped += 1
                continue
            row = {'id': f'file:{fp.name}', 'title': title, 'content': text,
                   'source': f'local:{fp.name}', 'created_at': None}
            result = ingest_one(row)
            if result:
                ingested += 1
                existing_titles.add(title)
            else:
                errors += 1
        except Exception as e:
            logger.error(f"Error ingesting {fp.name}: {e}")
            errors += 1

    logger.info(f"file ingest: ingested={ingested} skipped={skipped} errors={errors}")
    return {'ingested': ingested, 'skipped': skipped, 'errors': errors}


def run_ingest(batch_size: int = 20, include_files: bool = True) -> dict:
    r1 = ingest_from_research_table(batch_size)
    r2 = ingest_from_summary_files(batch_size) if include_files else {}
    return {
        'ingested': r1['ingested'] + r2.get('ingested', 0),
        'skipped':  r1['skipped']  + r2.get('skipped',  0),
        'errors':   r1['errors']   + r2.get('errors',   0),
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s %(message)s')
    stats = run_ingest()
    print(f"\nIngest complete: {stats}")
