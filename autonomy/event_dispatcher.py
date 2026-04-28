"""
Event Dispatcher.

Polls system_events for pending events, routes each to all subscribed
agents in priority order, and marks the event processed or failed.

Priority order:
  1. credit_agent      — blockers first
  2. funding_agent     — core pipeline
  3. capital_agent     — capital deployment
  4. communication_agent — notifications
  5. business_agent    — optional/low-priority
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger('EventDispatcher')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

BATCH_SIZE = int(os.getenv('AUTONOMY_BATCH_SIZE', '20'))


def _headers(prefer: str = '') -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    h   = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    if prefer:
        h['Prefer'] = prefer
    return h


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def _sb_patch(path: str, body: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers('return=minimal'), method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.warning(f"PATCH {path} → {e}")
        return False


def _build_registry():
    """Instantiate agents in priority order."""
    from autonomy.agents.credit_agent        import CreditAgent
    from autonomy.agents.funding_agent       import FundingAgent
    from autonomy.agents.capital_agent       import CapitalAgent
    from autonomy.agents.communication_agent import CommunicationAgent
    from autonomy.agents.business_agent      import BusinessAgent
    from autonomy.agents.strategy_agent      import StrategyAgent

    return [
        StrategyAgent(),       # research pipeline → paper trading (runs first — no client dependency)
        CreditAgent(),
        FundingAgent(),
        CapitalAgent(),
        CommunicationAgent(),
        BusinessAgent(),
    ]


def fetch_pending_events(limit: int = BATCH_SIZE) -> list:
    return _sb_get(
        f"system_events?status=eq.pending"
        f"&order=created_at.asc"
        f"&limit={limit}"
        f"&select=*"
    )


def mark_processing(event_id: str) -> bool:
    return _sb_patch(
        f"system_events?id=eq.{event_id}",
        {'status': 'processing'},
    )


def mark_processed(event_id: str, processed_by: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"system_events?id=eq.{event_id}",
        {'status': 'processed', 'processed_by': processed_by, 'processed_at': now},
    )


def mark_failed(event_id: str, error_msg: str) -> bool:
    return _sb_patch(
        f"system_events?id=eq.{event_id}",
        {'status': 'failed', 'error_msg': error_msg[:500]},
    )


def mark_ignored(event_id: str) -> bool:
    return _sb_patch(
        f"system_events?id=eq.{event_id}",
        {'status': 'ignored'},
    )


def dispatch_event(event: dict, agents: list, context: Optional[dict] = None) -> dict:
    """
    Route one event to all subscribed agents.
    Returns summary dict.
    """
    event_type = event.get('event_type', '')
    event_id   = event.get('id', '')
    result     = {'event_id': event_id, 'event_type': event_type, 'acted': [], 'skipped': []}

    mark_processing(event_id)

    acted_by = []
    for agent in agents:
        if not agent.can_handle(event_type):
            continue
        outcome = agent.process(event, context or {})
        if outcome['acted']:
            acted_by.append(agent.NAME)
            result['acted'].append({'agent': agent.NAME, 'outputs': len(outcome['outputs'])})
        else:
            result['skipped'].append({'agent': agent.NAME, 'reason': outcome['reason']})

    if acted_by:
        mark_processed(event_id, ','.join(acted_by))
    else:
        mark_ignored(event_id)

    return result


def run_dispatch_cycle(context_loader=None) -> dict:
    """
    Fetch and dispatch one batch of pending events.
    Returns summary dict.
    """
    agents = _build_registry()
    events = fetch_pending_events()

    if not events:
        return {'processed': 0, 'total': 0}

    processed = acted = ignored = 0
    for event in events:
        ctx = context_loader(event.get('client_id')) if context_loader else {}
        try:
            result = dispatch_event(event, agents, ctx)
            if result['acted']:
                acted += 1
            else:
                ignored += 1
            processed += 1
        except Exception as exc:
            logger.exception(f"Dispatch error for event {event.get('id')}")
            mark_failed(event.get('id', ''), str(exc))
            processed += 1

    return {'processed': processed, 'acted': acted, 'ignored': ignored, 'total': len(events)}
