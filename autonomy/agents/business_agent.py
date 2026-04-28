"""
Business Agent.

Optional agent — lowest priority. Handles general business opportunity
and operational tasks. Only fires when no higher-priority agents are active.

Subscriptions:
  task_completed         — check if new business analysis is needed
  funding_approved       — post-funding business planning
  credit_analysis_completed — business health context
"""

from autonomy.agents.base_agent import BaseAgent
from autonomy.output_service    import create_task, log_action


class BusinessAgent(BaseAgent):
    NAME             = 'business_agent'
    COOLDOWN_MINUTES = 240   # longer cooldown — runs infrequently
    SUBSCRIPTIONS    = [
        'task_completed',
        'funding_approved',
        'credit_analysis_completed',
    ]

    def _act(self, event: dict, context: dict) -> list:
        event_type = event.get('event_type', '')
        client_id  = event.get('client_id')
        event_id   = event.get('id')
        payload    = event.get('payload') or {}
        outputs    = []

        if event_type == 'funding_approved':
            amount  = payload.get('amount', 'N/A')
            task_id = create_task(
                title=f'Post-Funding Business Planning — ${amount}',
                client_id=client_id,
                agent_name=self.NAME,
                description=(
                    f'Funding of ${amount} approved. Review business plan, '
                    'set milestones, and identify growth opportunities.'
                ),
                priority='medium',
                task_category='business',
            )
            if task_id:
                outputs.append({'type': 'task', 'id': task_id})
                log_action(self.NAME, 'created_task', client_id, event_id,
                           event_type, task_id, 'post-funding business plan task')

        elif event_type == 'credit_analysis_completed':
            score = payload.get('score')
            if score and score < 600:
                task_id = create_task(
                    title='Business Health Assessment',
                    client_id=client_id,
                    agent_name=self.NAME,
                    description=(
                        f'Credit score {score} indicates possible business stress. '
                        'Run business health assessment and identify improvement areas.'
                    ),
                    priority='medium',
                    task_category='business',
                )
                if task_id:
                    outputs.append({'type': 'task', 'id': task_id})
                    log_action(self.NAME, 'created_task', client_id, event_id,
                               event_type, task_id, f'business health assessment, score={score}')

        elif event_type == 'task_completed':
            task_cat = payload.get('task_category', '')
            if task_cat == 'funding':
                task_id = create_task(
                    title='Follow-Up Business Review',
                    client_id=client_id,
                    agent_name=self.NAME,
                    description='Funding milestone completed. Schedule 30-day business review.',
                    priority='low',
                    task_category='business',
                )
                if task_id:
                    outputs.append({'type': 'task', 'id': task_id})
                    log_action(self.NAME, 'created_task', client_id, event_id,
                               event_type, task_id, 'post-funding follow-up task')

        return outputs
