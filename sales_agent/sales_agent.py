"""
AI Sales Agent.

Listens for lead_inquiry events and guides leads toward becoming clients.

Flow:
  lead_inquiry event → detect interest → send tailored response →
  handle objections → push toward signup → record conversion event

Intent detection (rule-based + keyword):
  interested   — mentions funding, loan, capital, credit, money, apply
  objecting    — mentions cost, expensive, fee, not sure, maybe, later
  ready        — mentions yes, sign up, agree, ready, let's go, start
  cold         — no relevant keywords

Commission model: 10% of funded amount (disclosed early)

Triggers:
  system_events: event_type = 'lead_inquiry'

Run standalone for testing:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m sales_agent.sales_agent
"""

import os
import json
import logging
import re
from typing import Optional

logger = logging.getLogger('SalesAgent')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# ─── Intent detection ─────────────────────────────────────────────────────────

_INTEREST_KEYWORDS = {
    'interested': [
        'funding', 'loan', 'capital', 'credit', 'money', 'apply',
        'business', 'finance', 'how does', 'tell me', 'interested',
        'help me', 'need', 'looking for', 'information', 'what is',
    ],
    'objecting': [
        'cost', 'expensive', 'fee', 'charge', 'not sure', 'maybe',
        'later', 'think about', 'concerned', 'worry', 'risky', 'scam',
        'too much', 'percent', 'commission',
    ],
    'ready': [
        'yes', 'sign up', 'agree', 'ready', "let's go", 'start',
        'proceed', 'sign me up', 'how do i', 'next step', 'enroll',
        'register', 'join',
    ],
}


def detect_intent(message: str) -> str:
    low = message.lower()
    scores = {intent: 0 for intent in _INTEREST_KEYWORDS}
    for intent, keywords in _INTEREST_KEYWORDS.items():
        for kw in keywords:
            if kw in low:
                scores[intent] += 1
    best = max(scores, key=lambda i: scores[i])
    return best if scores[best] > 0 else 'cold'


# ─── Response templates ───────────────────────────────────────────────────────

def _build_response(intent: str, lead_name: str = '', message_count: int = 0) -> str:
    name = lead_name.split()[0] if lead_name else 'there'

    if intent == 'ready':
        return (
            f"That's great, {name}! Let's get you started.\n\n"
            f"Here's what happens next:\n"
            f"1️⃣ We'll do a quick funding readiness check\n"
            f"2️⃣ Review your credit profile\n"
            f"3️⃣ Match you with the best funding options\n\n"
            f"Our fee is only 10% of what you receive — you pay nothing upfront.\n\n"
            f"Reply with your full name and best contact email to begin."
        )

    if intent == 'objecting':
        return (
            f"I completely understand, {name} — it's smart to ask questions.\n\n"
            f"Here's how our model works:\n"
            f"• Zero upfront cost — we only get paid when you get funded\n"
            f"• Our fee is 10% of the funded amount (industry standard)\n"
            f"• If you don't get funded, you owe nothing\n\n"
            f"We've helped businesses access $10K–$500K+ in funding. "
            f"Would you like to see what you might qualify for? No commitment."
        )

    if intent == 'interested':
        if message_count == 0:
            return (
                f"Hi {name}! 👋 Welcome to Nexus Funding.\n\n"
                f"We help businesses access working capital, SBA loans, "
                f"business lines of credit, and equipment financing.\n\n"
                f"Our process is simple:\n"
                f"✅ Free funding assessment\n"
                f"✅ Credit optimization guidance\n"
                f"✅ Matched with best lenders\n"
                f"✅ We handle the application\n\n"
                f"We work on a 10% success fee — paid only when you're funded.\n\n"
                f"What type of funding are you looking for?"
            )
        return (
            f"Great question, {name}. We work with businesses at all stages — "
            f"even if your credit needs work, we have options.\n\n"
            f"The fastest way to find out what you qualify for is our free assessment. "
            f"It takes 5 minutes and there's no obligation.\n\n"
            f"Want me to start one for you now?"
        )

    # cold / unknown
    return (
        f"Hi {name}! I'm the Nexus AI assistant. I help businesses find funding, "
        f"improve credit, and access capital.\n\n"
        f"Are you looking for:\n"
        f"• 💰 Business funding / loans\n"
        f"• 📈 Credit improvement\n"
        f"• 🏛 Government grants\n\n"
        f"Just reply with what you're looking for and I'll point you in the right direction."
    )


def _try_hermes_response(system_prompt: str, user_message: str) -> Optional[str]:
    """Try to get a richer response from Hermes. Returns None if unavailable."""
    try:
        token = os.getenv('HERMES_GATEWAY_TOKEN', '')
        if not token:
            return None
        url  = 'http://localhost:8642/v1/chat/completions'
        body = json.dumps({
            'model': 'hermes',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user',   'content': user_message},
            ],
            'max_tokens': 300,
        }).encode()
        req = urllib.request.Request(
            url, data=body,
            headers={
                'Content-Type':  'application/json',
                'Authorization': f'Bearer {token}',
            },
        )
        import urllib.request
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            return data.get('choices', [{}])[0].get('message', {}).get('content', '').strip() or None
    except Exception:
        return None


def _send_response(
    response_text: str,
    lead_id: Optional[str]   = None,
    client_id: Optional[str] = None,
) -> None:
    """Send response via output_service → Telegram."""
    try:
        from autonomy.output_service import send_message
        send_message(
            message=response_text,
            client_id=client_id,
            metadata={'lead_id': lead_id, 'agent': 'sales_agent'},
        )
    except Exception as e:
        logger.warning(f"Output service unavailable, falling back to direct Telegram: {e}")
        try:
            from lib.hermes_gate import send_direct_response
            send_direct_response(response_text, event_type='conversational_reply', parse_mode='HTML')
        except Exception as te:
            logger.error(f"Telegram fallback failed: {te}")


# ─── Main handler ─────────────────────────────────────────────────────────────

def handle_lead_inquiry(event_payload: dict) -> dict:
    """
    Process a lead_inquiry event.
    payload keys: external_id, channel, name, message, lead_id (optional), client_id (optional)
    """
    from sales_agent.conversation_service import (
        get_or_create_lead, get_or_create_conversation,
        update_conversation_intent, increment_message_count,
        close_conversation, record_conversion_event, update_lead_status,
    )

    external_id = event_payload.get('external_id', '')
    channel     = event_payload.get('channel', 'telegram')
    name        = event_payload.get('name', '')
    message     = event_payload.get('message', '')
    client_id   = event_payload.get('client_id')

    # Get or create lead
    lead = get_or_create_lead(external_id, channel, name)
    lead_id = lead.get('id')

    # Get or open conversation
    conv = get_or_create_conversation(lead_id=lead_id, client_id=client_id)
    conv_id  = conv.get('id')
    msg_count = conv.get('message_count', 0)

    # Detect intent
    intent = detect_intent(message)
    logger.info(f"Lead inquiry: lead={lead_id} intent={intent} msg={msg_count}")

    # Update conversation
    update_conversation_intent(conv_id, intent)
    increment_message_count(conv_id)

    # Build response using Nexus Super Prompt for company-aligned tone
    try:
        from autonomy.nexus_super_prompt import build_nexus_prompt
        system_prompt = build_nexus_prompt(
            role_name="funding_strategist",
            task_description=f"Respond to a lead inquiry: {message[:300]}",
            user_stage="awareness",
            current_goal="Schedule a funding assessment and understand lead's funding needs",
            user_data=f"intent={intent}, message_count={msg_count}",
            known_issues="none",
        )
    except Exception:
        system_prompt = (
            "You are a professional business funding consultant for Nexus Funding. "
            "Be warm, helpful, and concise. Our fee is 10% of funded amount, paid only on success. "
            "Guide the lead toward scheduling a funding assessment. Keep replies under 150 words."
        )
    response = _try_hermes_response(system_prompt, message) or _build_response(
        intent, lead.get('name', name), msg_count
    )

    # Send response
    _send_response(response, lead_id=lead_id, client_id=client_id)

    # Record conversion event
    if intent == 'ready':
        record_conversion_event('assessment_requested', lead_id=lead_id)
        close_conversation(conv_id, status='converted')
        update_lead_status(lead_id, 'qualified', notes='Ready to proceed via sales agent')

        # Emit onboarding event
        try:
            from autonomy.event_emitter import emit_event
            emit_event(
                event_type='lead_qualified',
                client_id=client_id,
                payload={'lead_id': lead_id, 'external_id': external_id, 'channel': channel},
            )
        except Exception:
            pass

    # Write summary
    try:
        from autonomy.summary_service import write_summary
        write_summary(
            agent_name='sales_agent',
            summary_type='sales_interaction',
            summary_text=f"Lead {lead_id} intent={intent}, response sent (msg #{msg_count+1})",
            what_happened=f"Handled lead inquiry: '{message[:80]}'",
            what_changed=f"Intent={intent}, conversation progressed",
            recommended_next_action='Monitor for follow-up' if intent != 'ready' else 'Begin onboarding',
            follow_up_needed=(intent == 'cold'),
            priority='high' if intent == 'ready' else 'low',
        )
    except Exception:
        pass

    return {'success': True, 'intent': intent, 'lead_id': lead_id, 'conversation_id': conv_id}


def process_pending_leads(limit: int = 20) -> int:
    """Re-engage cold leads that haven't heard back. Returns count processed."""
    import urllib.request
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url = (
        f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/"
        f"lead_profiles?status=eq.new&order=created_at.asc&limit={limit}&select=*"
    )
    req = urllib.request.Request(url, headers={
        'apikey': key, 'Authorization': f'Bearer {key}'
    })
    try:
        import json as _j
        with urllib.request.urlopen(req, timeout=10) as r:
            leads = _j.loads(r.read())
    except Exception:
        return 0

    count = 0
    for lead in leads:
        response = _build_response('cold', lead.get('name', ''), message_count=0)
        _send_response(response, lead_id=lead.get('id'))
        count += 1

    return count
