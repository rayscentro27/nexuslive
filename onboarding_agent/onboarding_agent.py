"""
AI Onboarding Agent.

Guides new clients through the 4-step onboarding flow:
  welcome → credit → business → funding → complete

Listens for:
  - client_registered     → creates session, sends welcome message
  - onboarding_step_done  → advances to next step
  - lead_qualified        → starts onboarding for a converted lead

Each step sends a targeted message explaining what's needed and why.
On completion: emits credit_analysis_queued to hand off to credit_agent.

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m onboarding_agent.onboarding_agent
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger('OnboardingAgent')

# ─── Step messages ────────────────────────────────────────────────────────────

_STEP_MESSAGES = {
    'welcome': (
        "Welcome to Nexus! 🎉 I'm your onboarding assistant.\n\n"
        "Here's what we'll do together:\n"
        "📋 Step 1: Welcome (you're here!)\n"
        "💳 Step 2: Credit review\n"
        "🏢 Step 3: Business profile\n"
        "💰 Step 4: Funding assessment\n\n"
        "This takes about 10 minutes and puts you in position to access funding.\n\n"
        "When you're ready, reply 'next' to begin your credit review."
    ),
    'credit': (
        "Step 2: Credit Review 💳\n\n"
        "Your credit profile is one of the most important factors lenders use.\n\n"
        "I need the following:\n"
        "• Your personal credit score (approximate is fine)\n"
        "• Any known negative items (late payments, collections, etc.)\n"
        "• Business credit established? (yes/no)\n\n"
        "Don't worry if your credit isn't perfect — we work with scores from 550+.\n\n"
        "Reply with your info or type 'skip' to come back to this later."
    ),
    'business': (
        "Step 3: Business Profile 🏢\n\n"
        "Tell me about your business:\n"
        "• Business name\n"
        "• How long in operation?\n"
        "• Monthly revenue (approximate)\n"
        "• Industry/type of business\n"
        "• Registered as LLC, Corp, or Sole Prop?\n\n"
        "This helps us match you with the right funding products.\n\n"
        "Reply with your business details."
    ),
    'funding': (
        "Step 4: Funding Assessment 💰\n\n"
        "Almost done! Last questions:\n"
        "• How much funding are you looking for?\n"
        "• What will you use it for?\n"
        "• When do you need it by?\n"
        "• Have you applied for business funding before?\n\n"
        "Based on your answers, I'll match you with the best options available.\n\n"
        "Reply with your funding needs."
    ),
    'complete': (
        "✅ Onboarding Complete!\n\n"
        "You're all set, {name}. Here's what happens next:\n\n"
        "1️⃣ Our credit team will review your profile\n"
        "2️⃣ We'll identify the best funding matches\n"
        "3️⃣ We'll submit applications on your behalf\n\n"
        "Timeline: Most clients receive a decision within 3–7 business days.\n\n"
        "We only get paid (10% fee) when you receive funding. "
        "You'll hear from us soon! 🚀"
    ),
}


def _send_step_message(client_id: str, step: str, name: str = '') -> None:
    msg = _STEP_MESSAGES.get(step, '')
    if not msg:
        return
    msg = msg.replace('{name}', name.split()[0] if name else 'there')
    try:
        from autonomy.output_service import send_message
        send_message(message=msg, client_id=client_id, metadata={'step': step, 'agent': 'onboarding_agent'})
    except Exception as e:
        logger.warning(f"Output service failed for step {step}: {e}")


def _get_client_name(client_id: str) -> str:
    try:
        import urllib.request
        key = os.getenv('SUPABASE_KEY', '')
        url = f"{os.getenv('SUPABASE_URL', '')}/rest/v1/clients?id=eq.{client_id}&select=name&limit=1"
        req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
        with urllib.request.urlopen(req, timeout=6) as r:
            rows = json.loads(r.read())
            return rows[0].get('name', '') if rows else ''
    except Exception:
        return ''


# ─── Event handlers ───────────────────────────────────────────────────────────

def handle_client_registered(event_payload: dict) -> dict:
    """Start onboarding when a new client registers."""
    from onboarding_agent.onboarding_service import create_session
    from funnel_engine.funnel_service import record_funnel_event, update_funnel_stage

    client_id = event_payload.get('client_id', '')
    if not client_id:
        return {'success': False, 'error': 'client_id missing'}

    session = create_session(client_id)
    if not session:
        return {'success': False, 'error': 'Could not create onboarding session'}

    name = _get_client_name(client_id) or event_payload.get('name', '')
    _send_step_message(client_id, 'welcome', name)

    # Record funnel event
    try:
        record_funnel_event(client_id=client_id, stage='onboarding_started',
                            event_source='onboarding_agent')
        update_funnel_stage(client_id=client_id, new_stage='onboarding_started')
    except Exception:
        pass

    try:
        from autonomy.summary_service import write_summary
        write_summary(
            agent_name='onboarding_agent',
            summary_type='onboarding_started',
            summary_text=f"Onboarding started for client {client_id}",
            what_happened='New client registered, onboarding session created',
            what_changed='Session created, welcome message sent',
            recommended_next_action='Wait for client to proceed to credit step',
            priority='medium',
        )
    except Exception:
        pass

    logger.info(f"Onboarding started for client {client_id}")
    return {'success': True, 'session_id': session.get('id'), 'current_step': 'welcome'}


def handle_onboarding_step_done(event_payload: dict) -> dict:
    """Advance to next step when a client completes a step."""
    from onboarding_agent.onboarding_service import advance_step
    from funnel_engine.funnel_service import record_funnel_event

    client_id    = event_payload.get('client_id', '')
    completed_step = event_payload.get('step', '')

    if not client_id:
        return {'success': False, 'error': 'client_id missing'}

    next_step = advance_step(client_id)
    if not next_step:
        return {'success': False, 'error': 'Could not advance step'}

    name = _get_client_name(client_id)
    _send_step_message(client_id, next_step, name)

    if next_step == 'complete':
        # Emit credit_analysis_queued for the credit agent to pick up
        try:
            from autonomy.event_emitter import emit_event
            emit_event(
                event_type='client_registered',
                client_id=client_id,
                payload={'triggered_by': 'onboarding_complete', 'source': 'onboarding_agent'},
            )
        except Exception:
            pass
        try:
            record_funnel_event(client_id=client_id, stage='credit_improved',
                                event_source='onboarding_agent')
        except Exception:
            pass

    logger.info(f"Onboarding step advanced: client={client_id} next={next_step}")
    return {'success': True, 'next_step': next_step}


def get_stalled_sessions(hours: int = 48) -> list:
    """Return sessions that haven't progressed in N hours."""
    from onboarding_agent.onboarding_service import get_active_sessions
    import urllib.parse
    from datetime import timedelta, timezone as tz
    from datetime import datetime as dt

    sessions = get_active_sessions()
    cutoff   = dt.now(tz.utc) - timedelta(hours=hours)
    stalled  = []
    for s in sessions:
        started_raw = s.get('started_at', '')
        try:
            started = dt.fromisoformat(started_raw.replace('Z', '+00:00'))
            if started < cutoff:
                stalled.append(s)
        except Exception:
            pass
    return stalled
