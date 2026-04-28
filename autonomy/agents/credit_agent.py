"""
Credit Agent.

Handles credit-related events. Primary trigger: new client data arrives
that needs credit analysis, or a credit issue needs remediation.

Subscriptions:
  client_registered         — new client; initiate credit check
  credit_analysis_completed — review result; flag issues or hand off
  task_completed            — if a credit task completes, re-evaluate
"""

from autonomy.agents.base_agent import BaseAgent
from autonomy.output_service    import create_task, send_message, log_action
from autonomy.event_emitter     import emit_event


class CreditAgent(BaseAgent):
    NAME             = 'credit_agent'
    COOLDOWN_MINUTES = 120
    SUBSCRIPTIONS    = [
        'client_registered',
        'credit_analysis_completed',
        'task_completed',
    ]

    def _act(self, event: dict, context: dict) -> list:
        event_type = event.get('event_type', '')
        client_id  = event.get('client_id')
        event_id   = event.get('id')
        payload    = event.get('payload') or {}
        outputs    = []

        if event_type == 'client_registered':
            task_id = create_task(
                title='Initiate Credit Analysis',
                client_id=client_id,
                agent_name=self.NAME,
                description=(
                    'New client registered. Run credit profile analysis: '
                    'credit score, utilization, derogatory marks, length of history.'
                ),
                priority='high',
                task_category='credit',
            )
            if task_id:
                outputs.append({'type': 'task', 'id': task_id})
                log_action(self.NAME, 'created_task', client_id, event_id,
                           event_type, task_id, 'new client → credit analysis task')

        elif event_type == 'credit_analysis_completed':
            score   = payload.get('score')
            issues  = payload.get('issues', [])

            if issues:
                issue_list = ', '.join(issues[:3])
                task_id = create_task(
                    title=f'Credit Issues Identified — {len(issues)} item(s)',
                    client_id=client_id,
                    agent_name=self.NAME,
                    description=f'Issues found: {issue_list}. Review and create remediation plan.',
                    priority='high',
                    task_category='credit',
                )
                if task_id:
                    outputs.append({'type': 'task', 'id': task_id})
                    log_action(self.NAME, 'created_task', client_id, event_id,
                               event_type, task_id, f'{len(issues)} credit issues flagged')
                    from autonomy.summary_service import write_summary
                    write_summary(
                        agent_name=self.NAME,
                        summary_type='credit_issues_detected',
                        summary_text=f'{len(issues)} credit issue(s) found for client {client_id}: {issue_list}.',
                        what_happened=f'Credit analysis returned {len(issues)} derogatory item(s).',
                        what_changed=f'Remediation task created.',
                        blockers=[f'Credit issues blocking funding: {issue_list}'],
                        recommended_next_action='Review issues and build remediation plan.',
                        follow_up_needed=True,
                        client_id=client_id,
                        trigger_event_type='credit_analysis_completed',
                        priority='high',
                        extra_payload={'issues': issues, 'score': score},
                    )

            if score and score >= 600:
                # Hand off to funding_agent
                eid = emit_event(
                    event_type='agent_handoff',
                    client_id=client_id,
                    payload={
                        'from_agent': self.NAME,
                        'to_agent':   'funding_agent',
                        'context':    f'Credit score {score} qualifies for funding review.',
                        'trigger':    'credit_analysis_completed',
                    },
                )
                if eid:
                    outputs.append({'type': 'event', 'id': eid})
                    log_action(self.NAME, 'emitted_event', client_id, event_id,
                               event_type, eid, f'score={score} → handoff funding_agent')
                    from autonomy.summary_service import write_summary
                    write_summary(
                        agent_name=self.NAME,
                        summary_type='credit_analysis_completed',
                        summary_text=f'Credit score {score} received for client {client_id}. Handoff to funding_agent.',
                        what_happened=f'Credit analysis complete. Score={score} meets 600 threshold.',
                        what_changed='Handoff event emitted to funding_agent.',
                        recommended_next_action='Funding agent to initiate application review.',
                        follow_up_needed=False,
                        client_id=client_id,
                        trigger_event_type='credit_analysis_completed',
                        priority='high',
                        extra_payload={'score': score, 'issues': issues},
                    )

        elif event_type == 'task_completed':
            task_cat = payload.get('task_category', '')
            if task_cat == 'credit':
                msg_id = send_message(
                    from_agent=self.NAME,
                    content=f'Credit task completed for client {client_id}. Ready for next step.',
                    client_id=client_id,
                    to_agent='funding_agent',
                    message_type='coordination',
                    payload=payload,
                )
                if msg_id:
                    outputs.append({'type': 'message', 'id': msg_id})
                    log_action(self.NAME, 'sent_message', client_id, event_id,
                               event_type, msg_id, 'credit task done → notify funding_agent')

        return outputs
