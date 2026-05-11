"""
Memory Retrieval Service.

Fetches relevant ai_memory rows and assembles context strings that can be
prepended to AI prompts before any OpenClaw call.

Retrieval functions are pure read — they never write.
"""

import os
import json
import logging
import urllib.request
from typing import Optional, List, Dict

logger = logging.getLogger('MemoryRetrieval')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
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


# ─── Core retrievers ─────────────────────────────────────────────────────────

def retrieve_memories(
    subject_id: Optional[str]   = None,
    subject_type: Optional[str] = None,
    memory_type: Optional[str]  = None,
    client_id: Optional[str]    = None,
    source_agent: Optional[str] = None,
    limit: int = 10,
) -> List[Dict]:
    """
    Return raw ai_memory rows matching the given filters.
    All filters are optional — omit to broaden the query.
    Only returns is_active=true rows ordered by importance DESC, then created_at DESC.
    """
    parts = [
        'is_active=eq.true',
        f'limit={limit}',
        'order=importance_score.desc,created_at.desc',
        'select=*',
    ]
    if subject_id:
        parts.append(f'subject_id=eq.{subject_id}')
    if subject_type:
        parts.append(f'subject_type=eq.{subject_type}')
    if memory_type:
        parts.append(f'memory_type=eq.{memory_type}')
    if client_id:
        parts.append(f'client_id=eq.{client_id}')
    if source_agent:
        parts.append(f'source_agent=eq.{source_agent}')

    qs = '&'.join(parts)
    return _sb_get(f'ai_memory?{qs}')


def get_client_state(subject_id: str) -> Optional[str]:
    """
    Return the most recent client_state memory content for a client id.
    Returns None if no memory exists.
    """
    rows = retrieve_memories(
        subject_id=subject_id,
        subject_type='client',
        memory_type='client_state',
        limit=1,
    )
    return rows[0]['content'] if rows else None


def get_strategy_history(strategy_type: Optional[str] = None, limit: int = 5) -> List[str]:
    """
    Return content strings from strategy_history memories.
    Optionally filter by strategy_type stored in meta.
    """
    rows = retrieve_memories(memory_type='strategy_history', limit=limit * 3)
    results = []
    for r in rows:
        if strategy_type:
            meta = r.get('meta') or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            if meta.get('strategy_type') != strategy_type:
                continue
        results.append(r['content'])
        if len(results) >= limit:
            break
    return results


def get_signal_history(symbol: Optional[str] = None, limit: int = 5) -> List[str]:
    """
    Return content strings from signal_history memories.
    Optionally filter by symbol stored in meta.
    """
    rows = retrieve_memories(memory_type='signal_history', limit=limit * 3)
    results = []
    for r in rows:
        if symbol:
            meta = r.get('meta') or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            if meta.get('symbol') != symbol:
                continue
        results.append(r['content'])
        if len(results) >= limit:
            break
    return results


def get_recent_summaries(limit: int = 3) -> List[str]:
    """Return the most recent conversation_summary memory contents."""
    rows = retrieve_memories(memory_type='conversation_summary', limit=limit)
    return [r['content'] for r in rows]


def get_funding_history(client_id: str, limit: int = 5) -> List[str]:
    """Return recent funding_history memories for a client."""
    rows = retrieve_memories(
        memory_type='funding_history',
        client_id=client_id,
        limit=limit,
    )
    return [r['content'] for r in rows]


def get_credit_history(client_id: str, limit: int = 5) -> List[str]:
    """Return recent credit_history memories for a client."""
    rows = retrieve_memories(
        memory_type='credit_history',
        client_id=client_id,
        limit=limit,
    )
    return [r['content'] for r in rows]


def get_communication_history(client_id: str, limit: int = 5) -> List[str]:
    """Return recent communication_history memories for a client."""
    rows = retrieve_memories(
        memory_type='communication_history',
        client_id=client_id,
        limit=limit,
    )
    return [r['content'] for r in rows]


def get_prior_advice(
    client_id: str,
    agent_name: str,
    limit: int = 3,
) -> List[str]:
    """
    Return recent memory entries written by a specific agent for this client.
    Used by agents to avoid repeating advice they've already given.
    """
    rows = retrieve_memories(
        client_id=client_id,
        source_agent=agent_name,
        limit=limit,
    )
    return [r['content'] for r in rows]


def has_recent_memory(
    client_id: str,
    memory_type: str,
    hours: int = 24,
) -> bool:
    """
    Return True if a memory of the given type exists for this client
    within the last N hours. Used to suppress redundant agent actions.
    """
    from datetime import timedelta
    from datetime import datetime, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows   = _sb_get(
        f"ai_memory"
        f"?is_active=eq.true"
        f"&client_id=eq.{client_id}"
        f"&memory_type=eq.{memory_type}"
        f"&created_at=gt.{cutoff}"
        f"&select=id&limit=1"
    )
    return len(rows) > 0


# ─── Context assemblers ───────────────────────────────────────────────────────

def build_signal_context(symbol: Optional[str] = None, limit: int = 3) -> str:
    """
    Assemble a prompt-ready context block from recent signal memories.
    Returns empty string if no memories exist.
    """
    items = get_signal_history(symbol=symbol, limit=limit)
    if not items:
        return ''
    lines = ['[SIGNAL MEMORY]']
    for i, content in enumerate(items, 1):
        lines.append(f'{i}. {content.strip()}')
    return '\n'.join(lines)


def build_strategy_context(strategy_type: Optional[str] = None, limit: int = 3) -> str:
    """
    Assemble a prompt-ready context block from recent strategy memories.
    Returns empty string if no memories exist.
    """
    items = get_strategy_history(strategy_type=strategy_type, limit=limit)
    if not items:
        return ''
    lines = ['[STRATEGY MEMORY]']
    for i, content in enumerate(items, 1):
        lines.append(f'{i}. {content.strip()}')
    return '\n'.join(lines)


def build_full_context(
    subject_id: Optional[str]   = None,
    subject_type: Optional[str] = None,
    signal_symbol: Optional[str]      = None,
    strategy_type: Optional[str]      = None,
    include_summaries: bool           = True,
) -> str:
    """
    Build a combined memory context block for prepending to any AI prompt.

    Usage in signal_reviewer.py:
        from memory_engine.memory_retrieval_service import build_full_context
        ctx = build_full_context(signal_symbol=signal['symbol'])
        prompt = ctx + '\\n\\n' + base_prompt if ctx else base_prompt
    """
    parts = []

    # Client state
    if subject_id:
        state = get_client_state(subject_id)
        if state:
            parts.append(f'[CLIENT STATE]\n{state.strip()}')

    # Session summaries
    if include_summaries:
        summaries = get_recent_summaries(limit=2)
        if summaries:
            block = '\n'.join(f'{i+1}. {s.strip()}' for i, s in enumerate(summaries))
            parts.append(f'[RECENT CONTEXT]\n{block}')

    # Signal history
    sig_ctx = build_signal_context(symbol=signal_symbol, limit=3)
    if sig_ctx:
        parts.append(sig_ctx)

    # Strategy history
    strat_ctx = build_strategy_context(strategy_type=strategy_type, limit=3)
    if strat_ctx:
        parts.append(strat_ctx)

    return '\n\n'.join(parts)


def build_client_context(client_id: str, agent_name: Optional[str] = None) -> str:
    """
    Build a compact memory context block for an agent acting on a specific client.
    Includes: client state, prior agent advice, funding/credit history snippets.
    Returns empty string if no memory exists.
    """
    parts = []

    state = get_client_state(client_id)
    if state:
        parts.append(f'[CLIENT STATE]\n{state.strip()}')

    if agent_name:
        prior = get_prior_advice(client_id, agent_name, limit=3)
        if prior:
            block = '\n'.join(f'{i+1}. {p.strip()}' for i, p in enumerate(prior))
            parts.append(f'[PRIOR ADVICE — {agent_name}]\n{block}')

    funding = get_funding_history(client_id, limit=2)
    if funding:
        block = '\n'.join(f'{i+1}. {f.strip()}' for i, f in enumerate(funding))
        parts.append(f'[FUNDING HISTORY]\n{block}')

    credit = get_credit_history(client_id, limit=2)
    if credit:
        block = '\n'.join(f'{i+1}. {c.strip()}' for i, c in enumerate(credit))
        parts.append(f'[CREDIT HISTORY]\n{block}')

    return '\n\n'.join(parts)
