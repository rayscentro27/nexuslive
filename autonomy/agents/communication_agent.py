"""
Communication Agent.

Handles all client-facing notification tasks. Never acts first —
always reacts to handoffs or completed milestones.

Subscriptions:
  client_registered   — new paying client; send welcome email via Resend
  agent_handoff       — another agent requests a client communication
  funding_approved    — send approval notification
  task_completed      — notify client of milestone completion
  document_uploaded   — acknowledge receipt
"""

import os
import json
import urllib.request
from typing import List
from autonomy.agents.base_agent import BaseAgent
from autonomy.output_service    import create_task, send_message, log_action

RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')
FROM_EMAIL     = 'Nexus AI <noreply@goclearonline.cc>'


def _send_welcome_email(to_email: str, plan: str) -> bool:
    """Send a welcome email via the Resend API. Returns True on success."""
    if not RESEND_API_KEY or not to_email:
        return False
    plan_label = plan.capitalize()
    html = f"""
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#1a2244;">
  <h2 style="color:#5b7cfa;">Welcome to Nexus AI! 🚀</h2>
  <p>Your <strong>{plan_label}</strong> subscription is now active.</p>
  <p>Here's what you can do right now:</p>
  <ul>
    <li>Check your <strong>Dashboard</strong> for your personalized action plan</li>
    <li>Visit <strong>Funding Roadmap</strong> to see your funding path</li>
    <li>Submit a <strong>YouTube trading video</strong> to let our AI research and rank it for you</li>
    <li>Explore <strong>AI Bots</strong> for automated market insights</li>
  </ul>
  <p>Questions? Reply to this email — a real person will respond within 24 hours.</p>
  <p style="margin-top:32px;color:#6b7280;font-size:13px;">
    Nexus AI · goclearonline.cc<br>
    You're receiving this because you just subscribed.
  </p>
</div>
"""
    body = json.dumps({
        'from':    FROM_EMAIL,
        'to':      [to_email],
        'subject': f'Welcome to Nexus AI — {plan_label} plan activated',
        'html':    html,
    }).encode()
    req = urllib.request.Request(
        'https://api.resend.com/emails',
        data=body,
        headers={
            'Authorization': f'Bearer {RESEND_API_KEY}',
            'Content-Type':  'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return bool(result.get('id'))
    except Exception as e:
        import logging
        logging.getLogger('CommunicationAgent').warning(f'Resend error: {e}')
        return False


def _store_comm_memory(client_id: str, content: str, meta: dict = None,
                       importance: int = 60) -> None:
    """Write a communication_history memory for a client (fire-and-forget)."""
    try:
        from memory_engine.memory_store_service import store_memory
        store_memory(
            memory_type='communication_history',
            content=content,
            subject_id=client_id,
            subject_type='client',
            client_id=client_id,
            source_agent='communication_agent',
            importance_score=importance,
            meta=meta or {},
        )
    except Exception:
        pass


def _read_comm_memory(client_id: str) -> List[str]:
    """Return recent communication history (best-effort)."""
    try:
        from memory_engine.memory_retrieval_service import get_communication_history
        return get_communication_history(client_id, limit=3)
    except Exception:
        return []


class CommunicationAgent(BaseAgent):
    NAME             = 'communication_agent'
    COOLDOWN_MINUTES = 45
    SUBSCRIPTIONS    = [
        'client_registered',
        'agent_handoff',
        'funding_approved',
        'task_completed',
        'document_uploaded',
    ]

    def _act(self, event: dict, context: dict) -> list:
        event_type = event.get('event_type', '')
        client_id  = event.get('client_id')
        event_id   = event.get('id')
        payload    = event.get('payload') or {}
        outputs    = []

        # Read prior communication history before acting
        prior_comms = _read_comm_memory(client_id) if client_id else []
        if prior_comms:
            self.logger.info(f"Prior comms for {client_id}: {len(prior_comms)} entries")

        if event_type == 'client_registered':
            email = payload.get('email', '')
            plan  = payload.get('plan', 'pro')
            sent  = _send_welcome_email(email, plan)
            status = 'sent' if sent else 'resend_unavailable'
            msg_id = send_message(
                from_agent=self.NAME,
                content=f'Welcome email {status} to {email} (plan={plan})',
                client_id=client_id,
                message_type='welcome_email',
                payload={'email': email, 'plan': plan, 'status': status},
            )
            if msg_id:
                outputs.append({'type': 'message', 'id': msg_id})
            log_action(self.NAME, f'welcome_email_{status}', client_id, event_id,
                       event_type, msg_id, f'plan={plan} email={email}')
            _store_comm_memory(
                client_id,
                f'Welcome email {status}: plan={plan}, email={email}.',
                meta={'email': email, 'plan': plan, 'sent': sent},
                importance=90,
            )

        elif event_type == 'agent_handoff':
            to_agent = payload.get('to_agent')
            if to_agent != self.NAME:
                return []
            context_note = payload.get('context', '')
            task_id = create_task(
                title='Send Client Update',
                client_id=client_id,
                agent_name=self.NAME,
                description=f'Communication requested by {payload.get("from_agent", "?")}. Message: {context_note}',
                priority='medium',
                task_category='communication',
            )
            if task_id:
                outputs.append({'type': 'task', 'id': task_id})
                log_action(self.NAME, 'created_task', client_id, event_id,
                           event_type, task_id, f'comms task for handoff from {payload.get("from_agent")}')
                _store_comm_memory(
                    client_id,
                    f'Client update task created via handoff from {payload.get("from_agent","?")}. {context_note[:120]}',
                    meta={'from_agent': payload.get('from_agent'), 'task_id': task_id},
                )

        elif event_type == 'funding_approved':
            amount   = payload.get('amount', 'N/A')
            provider = payload.get('provider', 'N/A')
            task_id  = create_task(
                title=f'Notify Client — Funding Approved ${amount}',
                client_id=client_id,
                agent_name=self.NAME,
                description=(
                    f'Funding of ${amount} approved via {provider}. '
                    f'Contact client to confirm next steps and disbursement timeline.'
                ),
                priority='high',
                task_category='communication',
            )
            if task_id:
                outputs.append({'type': 'task', 'id': task_id})
                log_action(self.NAME, 'created_task', client_id, event_id,
                           event_type, task_id, f'funding approved notification task')
                _store_comm_memory(
                    client_id,
                    f'Funding approval notification sent: ${amount} via {provider}.',
                    meta={'amount': str(amount), 'provider': provider, 'task_id': task_id},
                    importance=80,
                )
                try:
                    from optimization_engine.recommendation_tracker import record_recommendation
                    record_recommendation(
                        agent_name=self.NAME,
                        client_id=client_id,
                        recommendation='funding_notification_task',
                        outcome='pending',
                        event_id=event_id,
                    )
                except Exception:
                    pass
                from autonomy.summary_service import write_summary
                write_summary(
                    agent_name=self.NAME,
                    summary_type='milestone_notification',
                    summary_text=f'Funding approval notification queued for client {client_id}: ${amount} via {provider}.',
                    what_happened=f'Client funding of ${amount} approved. Notification task created.',
                    what_changed='Task: "Notify Client — Funding Approved" created.',
                    recommended_next_action='Call client within 24h to confirm next steps.',
                    follow_up_needed=True,
                    client_id=client_id,
                    trigger_event_type='funding_approved',
                    priority='high',
                    extra_payload={'amount': str(amount), 'provider': provider},
                )

        elif event_type == 'task_completed':
            task_title = payload.get('task_title', 'a task')
            task_cat   = payload.get('task_category', '')
            if task_cat in ('funding', 'credit'):
                msg_id = send_message(
                    from_agent=self.NAME,
                    content=f'Milestone completed for client {client_id}: {task_title}. Sending update.',
                    client_id=client_id,
                    message_type='notification',
                    payload=payload,
                )
                if msg_id:
                    outputs.append({'type': 'message', 'id': msg_id})
                    log_action(self.NAME, 'sent_message', client_id, event_id,
                               event_type, msg_id, f'milestone notification: {task_title}')
                    _store_comm_memory(
                        client_id,
                        f'Milestone notification sent: {task_title} ({task_cat}).',
                        meta={'task_title': task_title, 'task_cat': task_cat},
                    )

        elif event_type == 'document_uploaded':
            doc_type = payload.get('document_type', 'document')
            task_id  = create_task(
                title=f'Acknowledge Document Receipt — {doc_type}',
                client_id=client_id,
                agent_name=self.NAME,
                description=f'Client uploaded {doc_type}. Confirm receipt and set expectations for review timeline.',
                priority='low',
                task_category='communication',
            )
            if task_id:
                outputs.append({'type': 'task', 'id': task_id})
                log_action(self.NAME, 'created_task', client_id, event_id,
                           event_type, task_id, 'document acknowledgement task')
                _store_comm_memory(
                    client_id,
                    f'Document receipt acknowledged: {doc_type}.',
                    meta={'doc_type': doc_type, 'task_id': task_id},
                    importance=50,
                )

        return outputs
