"""
Handoff Service.

Manages structured agent-to-agent handoffs. A handoff:
  1. Emits an agent_handoff system_event (picked up by autonomy_worker)
  2. Updates the client's active_stage in agent_context
  3. Records the handoff in agent_action_history

Stage progression on handoff:
  credit_agent    → funding_agent      : credit_review → funding
  funding_agent   → communication_agent: funding → communication
  any             → business_agent     : no stage change (supplementary)
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('HandoffService')

# Stage map: from_agent → to_agent → new active_stage
STAGE_MAP = {
    ('credit_agent',       'funding_agent'):       'funding',
    ('funding_agent',      'communication_agent'): 'communication',
    ('credit_agent',       'communication_agent'): 'communication',
}


def handoff(
    from_agent: str,
    to_agent: str,
    client_id: str,
    context: str             = '',
    payload: Optional[dict]  = None,
    trigger_event: Optional[str] = None,
) -> Optional[str]:
    """
    Emit a handoff event and update shared context.
    Returns the emitted event_id or None.
    """
    from autonomy.event_emitter      import emit_event
    from coordination.shared_context import advance_stage, record_agent_action

    p = {
        'from_agent': from_agent,
        'to_agent':   to_agent,
        'context':    context,
        'trigger':    trigger_event or '',
        **(payload or {}),
    }

    event_id = emit_event(
        event_type='agent_handoff',
        client_id=client_id,
        payload=p,
    )

    if event_id:
        logger.info(f"Handoff: {from_agent} → {to_agent} for client {client_id}")

        # Advance client stage if this is a known stage transition
        new_stage = STAGE_MAP.get((from_agent, to_agent))
        if new_stage:
            advance_stage(client_id, new_stage)

        # Record outgoing action
        record_agent_action(client_id, from_agent, f'handoff→{to_agent}')

    return event_id


def handoff_chain(
    steps: list,
    client_id: str,
    initial_context: str = '',
) -> list:
    """
    Execute a sequence of handoffs.
    steps = [('credit_agent', 'funding_agent'), ('funding_agent', 'communication_agent')]
    Returns list of emitted event_ids.
    """
    event_ids = []
    ctx       = initial_context
    for from_agent, to_agent in steps:
        eid = handoff(
            from_agent=from_agent,
            to_agent=to_agent,
            client_id=client_id,
            context=ctx,
        )
        if eid:
            event_ids.append(eid)
            ctx = f'Chained from {from_agent}'
    return event_ids
