"""
Funding Agent.

Subscribes to events that indicate a client is ready for or progressing
through the funding pipeline.

Subscriptions:
  credit_analysis_completed — credit score is in; create funding tasks
  agent_handoff             — another agent (credit_agent) triggered us
  funding_approved          — funding came through; hand off to communication_agent
  document_uploaded         — new document may unblock funding review
"""

from typing import Optional, List
from autonomy.agents.base_agent import BaseAgent
from autonomy.output_service    import create_task, send_message, log_action
from autonomy.event_emitter     import emit_event


def _store_funding_memory(client_id: str, content: str, meta: Optional[dict] = None,
                          importance: int = 70) -> None:
    """Write a funding_history memory for a client (fire-and-forget)."""
    try:
        from memory_engine.memory_store_service import store_memory
        store_memory(
            memory_type='funding_history',
            content=content,
            subject_id=client_id,
            subject_type='client',
            client_id=client_id,
            source_agent='funding_agent',
            importance_score=importance,
            meta=meta or {},
        )
    except Exception:
        pass


def _read_funding_memory(client_id: str) -> List[str]:
    """Return prior funding_history snippets for context (best-effort)."""
    try:
        from memory_engine.memory_retrieval_service import get_funding_history
        return get_funding_history(client_id, limit=3)
    except Exception:
        return []


class FundingAgent(BaseAgent):
    NAME              = 'funding_agent'
    COOLDOWN_MINUTES  = 60
    SUBSCRIPTIONS     = [
        'credit_analysis_completed',
        'agent_handoff',
        'funding_approved',
        'document_uploaded',
    ]

    def _act(self, event: dict, context: dict) -> list:
        event_type = event.get('event_type', '')
        client_id  = event.get('client_id')
        event_id   = event.get('id')
        payload    = event.get('payload') or {}
        outputs    = []

        if event_type == 'credit_analysis_completed':
            outputs += self._handle_credit_completed(client_id, event_id, payload)

        elif event_type == 'agent_handoff':
            target = payload.get('to_agent')
            if target == self.NAME:
                outputs += self._handle_handoff(client_id, event_id, payload)

        elif event_type == 'funding_approved':
            outputs += self._handle_funding_approved(client_id, event_id, payload)

        elif event_type == 'document_uploaded':
            outputs += self._handle_document(client_id, event_id, payload)

        return outputs

    def _handle_credit_completed(self, client_id, event_id, payload) -> list:
        score = payload.get('score')
        tier  = payload.get('tier', 'unknown')
        outputs = []

        # Read memory: has this client been reviewed before?
        prior = _read_funding_memory(client_id)
        if prior:
            self.logger.info(f"Prior funding history for {client_id}: {len(prior)} entries")

        if score and score >= 600:
            task_id = create_task(
                title=f'Review Funding Application — Credit {tier} ({score})',
                client_id=client_id,
                agent_name=self.NAME,
                description=(
                    f'Credit analysis completed. Score: {score}, Tier: {tier}. '
                    f'Client is eligible for funding review. Initiate application.'
                ),
                priority='high',
                task_category='funding',
            )
            if task_id:
                outputs.append({'type': 'task', 'id': task_id})
                log_action(self.NAME, 'created_task', client_id, event_id,
                           'credit_analysis_completed', task_id,
                           f'score={score} tier={tier} → funding task created')
                # Write memory + track recommendation
                _store_funding_memory(
                    client_id,
                    f'Funding review task created. Score={score}, Tier={tier}.',
                    meta={'score': score, 'tier': tier, 'task_id': task_id},
                    importance=75,
                )
                try:
                    from optimization_engine.recommendation_tracker import record_recommendation
                    record_recommendation(
                        agent_name=self.NAME,
                        client_id=client_id,
                        recommendation='created_funding_task',
                        event_id=event_id,
                        score_at_time=score,
                    )
                except Exception:
                    pass
                # Write summary
                from autonomy.summary_service import write_summary
                write_summary(
                    agent_name=self.NAME,
                    summary_type='funding_recommendation',
                    summary_text=f'Funding review task created for client {client_id}. Score={score}, Tier={tier}.',
                    what_happened=f'Credit score {score} ({tier}) meets funding threshold.',
                    what_changed=f'Task created: "Review Funding Application — Credit {tier} ({score})"',
                    recommended_next_action='Assign task to advisor and initiate application.',
                    follow_up_needed=True,
                    client_id=client_id,
                    trigger_event_type='credit_analysis_completed',
                    priority='high',
                    extra_payload={'score': score, 'tier': tier, 'task_id': task_id},
                )
        else:
            score_str = str(score) if score else 'unavailable'
            msg_id = send_message(
                from_agent=self.NAME,
                content=(
                    f'Credit score {score_str} below funding threshold for client {client_id}. '
                    f'Flagging for credit_agent review.'
                ),
                client_id=client_id,
                to_agent='credit_agent',
                message_type='coordination',
                payload=payload,
            )
            if msg_id:
                outputs.append({'type': 'message', 'id': msg_id})
                log_action(self.NAME, 'sent_message', client_id, event_id,
                           'credit_analysis_completed', msg_id,
                           f'score below threshold, flagged credit_agent')
                _store_funding_memory(
                    client_id,
                    f'Score {score_str} below threshold — flagged for credit review.',
                    meta={'score': score},
                    importance=60,
                )
                from autonomy.summary_service import write_summary
                write_summary(
                    agent_name=self.NAME,
                    summary_type='blocker_detected',
                    summary_text=f'Credit score {score_str} below funding threshold for client {client_id}.',
                    what_happened=f'Credit score {score_str} received — below 600 threshold.',
                    blockers=[f'Credit score {score_str} insufficient for funding review'],
                    recommended_next_action='Credit agent to review remediation options.',
                    follow_up_needed=True,
                    client_id=client_id,
                    trigger_event_type='credit_analysis_completed',
                    priority='medium',
                    extra_payload={'score': score},
                )

        return outputs

    def _handle_handoff(self, client_id, event_id, payload) -> list:
        context_note = payload.get('context', '')
        task_id = create_task(
            title='Funding Review — Agent Handoff',
            client_id=client_id,
            agent_name=self.NAME,
            description=f'Handed off from {payload.get("from_agent", "?")}. Context: {context_note}',
            priority='high',
            task_category='funding',
        )
        outputs = []
        if task_id:
            outputs.append({'type': 'task', 'id': task_id})
            log_action(self.NAME, 'created_task', client_id, event_id,
                       'agent_handoff', task_id, 'handoff task created')
        return outputs

    def _handle_funding_approved(self, client_id, event_id, payload) -> list:
        amount   = payload.get('amount', 'N/A')
        provider = payload.get('provider', 'N/A')
        outputs  = []

        task_id = create_task(
            title=f'Funding Approved — ${amount} via {provider}',
            client_id=client_id,
            agent_name=self.NAME,
            description='Funding has been approved. Prepare onboarding and disbursement steps.',
            priority='high',
            task_category='funding',
        )
        if task_id:
            outputs.append({'type': 'task', 'id': task_id})
            log_action(self.NAME, 'created_task', client_id, event_id,
                       'funding_approved', task_id, 'funding approved task')
            # Write high-importance memory
            _store_funding_memory(
                client_id,
                f'Funding APPROVED: ${amount} via {provider}. Onboarding initiated.',
                meta={'amount': str(amount), 'provider': provider, 'task_id': task_id},
                importance=90,
            )
            try:
                from optimization_engine.recommendation_tracker import record_recommendation
                record_recommendation(
                    agent_name=self.NAME,
                    client_id=client_id,
                    recommendation='funding_approved_task',
                    outcome='accepted',
                    event_id=event_id,
                    notes=f'${amount} via {provider}',
                )
            except Exception:
                pass
            from autonomy.summary_service import write_summary
            write_summary(
                agent_name=self.NAME,
                summary_type='funding_approved',
                summary_text=f'Funding APPROVED for client {client_id}: ${amount} via {provider}.',
                what_happened=f'Funding of ${amount} approved via {provider}.',
                what_changed='Onboarding task created. Handoff sent to communication_agent.',
                recommended_next_action='Confirm disbursement timeline with client.',
                follow_up_needed=True,
                client_id=client_id,
                trigger_event_type='funding_approved',
                priority='high',
                extra_payload={'amount': str(amount), 'provider': provider},
            )

        # Hand off to communication_agent
        event_id_new = emit_event(
            event_type='agent_handoff',
            client_id=client_id,
            payload={
                'from_agent': self.NAME,
                'to_agent':   'communication_agent',
                'context':    f'Funding approved ${amount} via {provider}. Notify client.',
                'trigger':    'funding_approved',
            },
        )
        if event_id_new:
            outputs.append({'type': 'event', 'id': event_id_new})
            log_action(self.NAME, 'emitted_event', client_id, event_id,
                       'funding_approved', event_id_new, 'handoff → communication_agent')

        return outputs

    def _handle_document(self, client_id, event_id, payload) -> list:
        doc_type = payload.get('document_type', 'document')
        task_id  = create_task(
            title=f'Review Uploaded Document — {doc_type}',
            client_id=client_id,
            agent_name=self.NAME,
            description=f'New {doc_type} uploaded. Review for funding eligibility impact.',
            priority='medium',
            task_category='funding',
        )
        outputs = []
        if task_id:
            outputs.append({'type': 'task', 'id': task_id})
            log_action(self.NAME, 'created_task', client_id, event_id,
                       'document_uploaded', task_id, f'doc review task: {doc_type}')
        return outputs
