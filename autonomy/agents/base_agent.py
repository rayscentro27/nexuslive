"""
Base Agent.

All agents inherit from BaseAgent. Subclasses define:
  NAME          — unique agent identifier
  SUBSCRIPTIONS — list of event_type strings this agent handles
  COOLDOWN_MINUTES — per-client cooldown (override if needed)
  _act()        — business logic; returns list of output dicts

Agents NEVER write to Supabase directly.
All writes go through output_service.
"""

import logging
from typing import Optional, List
from autonomy.decision_layer import should_act
from autonomy.output_service import log_action


class BaseAgent:
    NAME: str              = 'base_agent'
    SUBSCRIPTIONS: List[str] = []
    COOLDOWN_MINUTES: int  = 30

    def __init__(self):
        self.logger = logging.getLogger(f'Agent.{self.NAME}')

    def can_handle(self, event_type: str) -> bool:
        return event_type in self.SUBSCRIPTIONS

    def _load_memory_context(self, client_id: Optional[str]) -> dict:
        """
        Load relevant memory for this agent+client before acting.
        Returns a dict merged into ctx passed to _act().
        Failures are silenced — memory is advisory, not required.
        """
        if not client_id:
            return {}
        try:
            from memory_engine.memory_retrieval_service import (
                get_prior_advice, has_recent_memory
            )
            prior  = get_prior_advice(client_id, self.NAME, limit=3)
            recent = has_recent_memory(client_id, f'{self.NAME}_action', hours=24)
            return {'prior_advice': prior, 'has_recent_memory': recent}
        except Exception as e:
            self.logger.debug(f"Memory load skipped: {e}")
            return {}

    def process(self, event: dict, context: Optional[dict] = None) -> dict:
        """
        Entry point called by event_dispatcher.
        Runs decision layer, then _act() if approved.
        Returns {'acted': bool, 'reason': str, 'outputs': list}
        """
        event_type = event.get('event_type', '')
        client_id  = event.get('client_id')
        event_id   = event.get('id')
        payload    = event.get('payload') or {}
        ctx        = context or {}

        act, reason = should_act(
            agent_name=self.NAME,
            agent_subscriptions=self.SUBSCRIPTIONS,
            event_type=event_type,
            client_id=client_id,
            payload=payload,
            cooldown_minutes=self.COOLDOWN_MINUTES,
        )

        if not act:
            self.logger.debug(f"Skipping {event_type} for {client_id}: {reason}")
            log_action(
                agent_name=self.NAME,
                action_taken='skipped',
                client_id=client_id,
                event_id=event_id,
                event_type=event_type,
                decision_reason=reason,
            )
            return {'acted': False, 'reason': reason, 'outputs': []}

        # Enrich context with memory before calling _act
        memory_ctx = self._load_memory_context(client_id)
        ctx        = {**ctx, **memory_ctx}

        try:
            outputs = self._act(event, ctx)
        except Exception as exc:
            self.logger.exception(f"_act() failed for {self.NAME} on {event_type}")
            log_action(
                agent_name=self.NAME,
                action_taken='failed',
                client_id=client_id,
                event_id=event_id,
                event_type=event_type,
                decision_reason=str(exc),
            )
            return {'acted': False, 'reason': str(exc), 'outputs': []}

        self.logger.info(
            f"Acted on {event_type} for client={client_id}: {len(outputs)} output(s)"
        )
        return {'acted': True, 'reason': reason, 'outputs': outputs}

    def _act(self, event: dict, context: dict) -> list:
        """
        Override in subclasses.
        Return list of output dicts produced (task_ids, message_ids, event_ids).
        """
        raise NotImplementedError
