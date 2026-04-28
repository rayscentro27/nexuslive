"""
AI Closer Agent.

Handles inbound inquiries, qualifies leads, books appointments,
and closes deals via a structured conversation flow.

Flow:
  open → qualify → present_offer → handle_objection → close / follow_up

Channel: Telegram (text-based "call" flow — voice note support optional).
Each session maps to a call_session row with transcript turns logged.

Qualification criteria:
  ✓ Has a business (or starting one)
  ✓ Revenue > $0 (even pre-revenue counts for some products)
  ✓ Looking for funding/credit/grants
  ✗ Disqualifiers: purely personal loan, no business intent

Triggers:
  system_events: event_type = 'closer_session_requested'
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger('CloserAgent')

# ─── Qualification logic ──────────────────────────────────────────────────────

_QUALIFY_KEYWORDS  = ['business', 'company', 'llc', 'corp', 'revenue', 'funding',
                       'loan', 'grant', 'capital', 'employee', 'product', 'service']
_DISQUALIFY_KEYWORDS = ['personal', 'car loan', 'mortgage', 'student loan',
                         'credit card debt', 'no business']


def qualify_lead(message: str) -> str:
    """Return 'qualified', 'disqualified', or 'needs_info'."""
    low = message.lower()
    if any(kw in low for kw in _DISQUALIFY_KEYWORDS):
        return 'disqualified'
    if any(kw in low for kw in _QUALIFY_KEYWORDS):
        return 'qualified'
    return 'needs_info'


# ─── Script steps ─────────────────────────────────────────────────────────────

_SCRIPTS = {
    'open': (
        "Hey! Thanks for reaching out. I'm the Nexus AI closer — "
        "I help businesses get funded fast.\n\n"
        "Real quick: tell me about your business and what you're looking for. "
        "I'll let you know exactly what we can do for you."
    ),
    'qualify': (
        "Perfect. Based on what you've shared, you look like a strong candidate.\n\n"
        "Here's what we do:\n"
        "• We get businesses like yours funded — $10K to $500K+\n"
        "• We only charge a 10% fee when you receive funds\n"
        "• No upfront cost, no risk to you\n\n"
        "Does that sound like something worth exploring?"
    ),
    'needs_info': (
        "I want to make sure I'm pointing you in the right direction. "
        "Tell me:\n"
        "1. Do you have an existing business?\n"
        "2. What's your monthly revenue (approximate)?\n"
        "3. What would you use the funding for?\n\n"
        "Takes 30 seconds — and I can tell you right now if you qualify."
    ),
    'present_offer': (
        "Here's what I can put together for you:\n\n"
        "💰 Business Line of Credit — up to $150K, revolving\n"
        "📋 SBA Micro Loan — up to $50K, low rate\n"
        "⚡ Revenue-Based Advance — up to $500K, fast approval\n\n"
        "Our team will review your profile and match you with the best option.\n\n"
        "Ready to move forward? Just say 'yes' and I'll start your file now."
    ),
    'handle_objection_fee': (
        "I totally get it — fees always raise questions.\n\n"
        "Here's the reality: you pay NOTHING unless you get funded. "
        "Our 10% fee is taken out of the funded amount automatically — "
        "so if you get $50K, our fee is $5K. You walk away with $45K.\n\n"
        "No funding = no fee. Period.\n\n"
        "Does that make sense? Want to move forward?"
    ),
    'handle_objection_time': (
        "I hear you — timing matters.\n\n"
        "Here's the good news: our fastest products fund in 24–48 hours after approval. "
        "The application takes less than 10 minutes.\n\n"
        "Even if you don't need it right now, getting pre-approved means "
        "you have access when you do need it. Want me to lock in your spot?"
    ),
    'close': (
        "Awesome! Let's get this done.\n\n"
        "I'm starting your funding file now. Here's what happens next:\n"
        "1️⃣ Our credit team reviews your profile (today)\n"
        "2️⃣ We match you with the best lenders (24–48 hours)\n"
        "3️⃣ You receive an offer (3–7 business days)\n\n"
        "You'll hear from our team shortly. "
        "Welcome to Nexus — you made the right call. 🚀"
    ),
    'follow_up': (
        "No problem at all — I'll check back in. "
        "If anything changes or you have questions, just message me here anytime.\n\n"
        "One last thing: would it help if I sent you some info on what you'd qualify for? "
        "Zero commitment — just so you have the numbers."
    ),
    'disqualified': (
        "I appreciate you reaching out! Based on what you've shared, "
        "our current products are focused on business funding.\n\n"
        "If you're planning to start a business, I'd love to help you prepare. "
        "Or if you're looking for personal financial resources, "
        "I can point you toward some options.\n\n"
        "Which would be more helpful?"
    ),
}

_OBJECTION_KEYWORDS = {
    'fee':  ['fee', 'commission', 'percent', 'cost', 'expensive', 'charge', '10%'],
    'time': ['time', 'later', 'not now', 'busy', 'hurry', 'fast', 'how long'],
}


def detect_objection(message: str) -> Optional[str]:
    low = message.lower()
    for obj_type, keywords in _OBJECTION_KEYWORDS.items():
        if any(kw in low for kw in keywords):
            return obj_type
    return None


def _is_ready_to_close(message: str) -> bool:
    low = message.lower()
    return any(kw in low for kw in ['yes', 'ready', 'let\'s go', 'proceed',
                                     'sign me up', 'start', 'do it', 'move forward'])


def _try_hermes(system_prompt: str, user_message: str) -> Optional[str]:
    try:
        token = os.getenv('HERMES_GATEWAY_TOKEN', '')
        if not token:
            return None
        import urllib.request as _ur
        body = json.dumps({
            'model': 'hermes',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user',   'content': user_message},
            ],
            'max_tokens': 250,
        }).encode()
        req = _ur.Request(
            'http://localhost:8642/v1/chat/completions',
            data=body,
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
        )
        with _ur.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            return data.get('choices', [{}])[0].get('message', {}).get('content', '').strip() or None
    except Exception:
        return None


# ─── Main handler ─────────────────────────────────────────────────────────────

def handle_closer_session(event_payload: dict) -> dict:
    """
    Process a closer session event.
    payload: client_id, lead_id, message, session_id (optional — resumes existing)
    """
    from voice_agent.call_service import (
        open_session, close_session, add_transcript_turn,
        record_outcome, get_session_transcript,
    )
    from sales_agent.conversation_service import (
        record_conversion_event, update_lead_status,
    )

    client_id  = event_payload.get('client_id')
    lead_id    = event_payload.get('lead_id')
    message    = event_payload.get('message', '')
    session_id = event_payload.get('session_id')

    # Open or resume session
    if not session_id:
        session = open_session(call_type='inbound', channel='telegram',
                               client_id=client_id, lead_id=lead_id)
        if not session:
            return {'success': False, 'error': 'Could not open call session'}
        session_id = session['id']
        # First turn — send opener
        response = _SCRIPTS['open']
        add_transcript_turn(session_id, 'agent', response, turn_order=1)
    else:
        # Get current turn count
        transcript = get_session_transcript(session_id)
        turn_count = len(transcript)

        # Log client message
        add_transcript_turn(session_id, 'client', message, turn_order=turn_count + 1)

        # Determine next script step
        if _is_ready_to_close(message):
            response = _SCRIPTS['close']
            record_outcome(session_id, 'closed', notes='Closer agent closed the deal')
            close_session(session_id, outcome='closed')
            if lead_id:
                update_lead_status(lead_id, 'converted', notes='Closed by closer agent')
                record_conversion_event('deal_closed', lead_id=lead_id, client_id=client_id)
            try:
                from autonomy.event_emitter import emit_event
                emit_event('client_registered', client_id=client_id,
                           payload={'triggered_by': 'closer_agent', 'lead_id': lead_id or ''})
            except Exception:
                pass
        elif objection := detect_objection(message):
            response = _SCRIPTS.get(f'handle_objection_{objection}', _SCRIPTS['handle_objection_fee'])
            add_transcript_turn(session_id, 'agent', response, turn_order=turn_count + 2)
        else:
            qual = qualify_lead(message)
            if qual == 'qualified':
                # Try Hermes for a personalized offer, fallback to script
                sys_prompt = (
                    "You are a sharp, confident business funding closer for Nexus. "
                    "The lead is qualified. Present the offer enthusiastically and drive to a yes. "
                    "Be concise — max 120 words. Reference 10% success fee."
                )
                response = _try_hermes(sys_prompt, message) or _SCRIPTS['present_offer']
                record_outcome(session_id, 'qualified')
            elif qual == 'disqualified':
                response = _SCRIPTS['disqualified']
                close_session(session_id, outcome='not_qualified')
            else:
                response = _SCRIPTS['needs_info']

        add_transcript_turn(session_id, 'agent', response, turn_order=turn_count + 2)

    # Send response
    try:
        from autonomy.output_service import send_message
        send_message(message=response, client_id=client_id,
                     metadata={'session_id': session_id, 'agent': 'closer_agent'})
    except Exception as e:
        logger.warning(f"Output failed: {e}")

    logger.info(f"Closer session: {session_id} lead={lead_id}")
    return {'success': True, 'session_id': session_id, 'response': response}
