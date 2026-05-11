"""
Capital Agent.

Monitors signal-level market intelligence and translates approved trading
signals into capital deployment tasks for relevant clients.

Subscriptions:
  signal_approved — a trading signal passed the scoring pipeline
  funding_approved — client has capital; evaluate deployment options
"""

from autonomy.agents.base_agent import BaseAgent
from autonomy.output_service    import create_task, send_message, log_action


class CapitalAgent(BaseAgent):
    NAME             = 'capital_agent'
    COOLDOWN_MINUTES = 90
    SUBSCRIPTIONS    = [
        'signal_approved',
        'funding_approved',
    ]

    def _act(self, event: dict, context: dict) -> list:
        event_type = event.get('event_type', '')
        client_id  = event.get('client_id')
        event_id   = event.get('id')
        payload    = event.get('payload') or {}
        outputs    = []

        if event_type == 'signal_approved':
            symbol     = payload.get('symbol', '?')
            direction  = payload.get('direction', '?')
            confidence = payload.get('confidence_label', 'medium')
            score      = payload.get('score_total', 0)

            if score >= 70 or confidence == 'high':
                task_id = create_task(
                    title=f'Capital Opportunity — {symbol} {direction.upper()} ({confidence})',
                    client_id=client_id,
                    agent_name=self.NAME,
                    description=(
                        f'High-quality signal: {symbol} {direction}, '
                        f'score={score}, confidence={confidence}. '
                        f'Review position sizing and risk parameters before entry.'
                    ),
                    priority='high' if confidence == 'high' else 'medium',
                    task_category='capital',
                )
                if task_id:
                    outputs.append({'type': 'task', 'id': task_id})
                    log_action(self.NAME, 'created_task', client_id, event_id,
                               event_type, task_id,
                               f'signal opportunity: {symbol} score={score}')
                    from autonomy.summary_service import write_summary
                    write_summary(
                        agent_name=self.NAME,
                        summary_type='capital_opportunity',
                        summary_text=f'Capital opportunity: {symbol} {direction.upper()} score={score} confidence={confidence}.',
                        what_happened=f'High-quality signal received: {symbol} {direction}, score={score}.',
                        what_changed='Capital opportunity task created for review.',
                        recommended_next_action='Review position sizing and risk parameters before entry.',
                        follow_up_needed=True,
                        client_id=client_id,
                        trigger_event_type='signal_approved',
                        priority='high' if confidence == 'high' else 'medium',
                        extra_payload={'symbol': symbol, 'direction': direction,
                                       'score': score, 'confidence': confidence},
                    )

        elif event_type == 'funding_approved':
            amount  = payload.get('amount', 'N/A')
            task_id = create_task(
                title=f'Capital Deployment Plan — ${amount}',
                client_id=client_id,
                agent_name=self.NAME,
                description=(
                    f'${amount} in new capital available. '
                    'Develop allocation strategy: diversification, position limits, '
                    'and target instruments.'
                ),
                priority='high',
                task_category='capital',
            )
            if task_id:
                outputs.append({'type': 'task', 'id': task_id})
                log_action(self.NAME, 'created_task', client_id, event_id,
                           event_type, task_id, f'capital deployment plan, amount={amount}')
                from autonomy.summary_service import write_summary
                write_summary(
                    agent_name=self.NAME,
                    summary_type='capital_deployment',
                    summary_text=f'New capital ${amount} available for client {client_id}. Deployment plan created.',
                    what_happened=f'${amount} in new capital confirmed via funding_approved event.',
                    what_changed='Capital deployment plan task created.',
                    recommended_next_action='Develop allocation strategy before deploying capital.',
                    follow_up_needed=True,
                    client_id=client_id,
                    trigger_event_type='funding_approved',
                    priority='high',
                    extra_payload={'amount': str(amount)},
                )

        return outputs
