"""
AI Support Agent.

Handles client questions about funding, credit, and process.
Escalates complex cases to human review.

Category detection:
  funding  — loan, money, apply, funds, approved, denied, status, lender
  credit   — credit, score, fico, bureau, dispute, negative
  general  — everything else

Escalation triggers:
  - 3+ unanswered follow-ups
  - keywords: refund, legal, lawsuit, fraud, complaint
  - priority=high set externally

Listens for: support_request system events
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger('SupportAgent')

# ─── Category detection ───────────────────────────────────────────────────────

_CATEGORY_KEYWORDS = {
    'funding': ['loan', 'money', 'apply', 'fund', 'approv', 'denied', 'status',
                'lender', 'credit line', 'capital', 'revenue', 'collateral'],
    'credit':  ['credit', 'score', 'fico', 'bureau', 'dispute', 'negative', 'collection',
                'inquiry', 'report', 'utilization', 'derogatory'],
}

_ESCALATION_KEYWORDS = ['refund', 'legal', 'lawsuit', 'fraud', 'complaint',
                        'attorney', 'scam', 'sue', 'money back', 'charge back']


def detect_category(message: str) -> str:
    low = message.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in low for kw in keywords):
            return category
    return 'general'


def needs_escalation(message: str) -> bool:
    low = message.lower()
    return any(kw in low for kw in _ESCALATION_KEYWORDS)


# ─── Response knowledge base ──────────────────────────────────────────────────

_FUNDING_FAQ: dict = {
    'status': (
        "Your application is being reviewed by our funding team. "
        "Most decisions come within 3–7 business days. "
        "You'll receive an update via Telegram as soon as there's news."
    ),
    'approved': (
        "Congratulations! Once approved, funds are typically disbursed within 1–3 business days. "
        "Your 10% service fee will be deducted from the funded amount. "
        "Our team will contact you to walk through the agreement."
    ),
    'denied': (
        "If one lender declined, we often have other options. "
        "A denial from one lender doesn't mean you can't be funded — "
        "we work with 50+ lending partners. Would you like us to try alternative sources?"
    ),
    'how long': (
        "The full funding process typically takes 5–14 business days depending on the product. "
        "Business lines of credit can be as fast as 48 hours after approval."
    ),
    'amount': (
        "Funding amounts range from $5,000 to $5,000,000+ depending on your business profile. "
        "Qualification is based on time in business, monthly revenue, and credit score."
    ),
}

_CREDIT_FAQ: dict = {
    'improve': (
        "To improve your credit score quickly:\n"
        "• Pay down revolving balances below 30% utilization\n"
        "• Dispute any inaccurate negative items\n"
        "• Avoid new hard inquiries for 90 days\n"
        "• Become an authorized user on a seasoned account\n"
        "Most clients see 20–50 point improvements within 90 days."
    ),
    'minimum': (
        "We work with personal scores as low as 550. "
        "However, a score of 680+ unlocks significantly better rates and higher amounts. "
        "If your score is below 600, we can help you build it up first."
    ),
    'dispute': (
        "To dispute items on your credit report:\n"
        "1. Get your free report at annualcreditreport.com\n"
        "2. Identify inaccurate or outdated items\n"
        "3. File disputes with each bureau (Experian, Equifax, TransUnion)\n"
        "Bureaus have 30 days to investigate and respond."
    ),
}

_GENERAL_RESPONSES = {
    'hello': "Hi! I'm the Nexus support assistant. How can I help you today?",
    'fee': (
        "Our fee is 10% of the funded amount, paid only when you successfully receive funding. "
        "There are no upfront costs or monthly fees."
    ),
    'process': (
        "Here's how our process works:\n"
        "1️⃣ Complete onboarding (credit + business info)\n"
        "2️⃣ We review your profile and match lenders\n"
        "3️⃣ We submit applications on your behalf\n"
        "4️⃣ You receive funding and we collect our 10% fee\n"
        "Questions? Just ask!"
    ),
}


def _match_faq(message: str, faq: dict) -> Optional[str]:
    low = message.lower()
    for keyword, answer in faq.items():
        if keyword in low:
            return answer
    return None


def build_response(message: str, category: str, thread_message_count: int = 0) -> str:
    # Check for FAQ match first
    if category == 'funding':
        match = _match_faq(message, _FUNDING_FAQ)
        if match:
            return match
        return (
            "I'm looking into your funding question. "
            "For the most accurate update on your application, "
            "our funding team is reviewing your file. "
            "Is there anything specific you'd like me to clarify about the process?"
        )

    if category == 'credit':
        match = _match_faq(message, _CREDIT_FAQ)
        if match:
            return match
        return (
            "Great question about credit. "
            "Your credit profile is a key part of the funding process. "
            "Could you share more details so I can give you specific guidance? "
            "(e.g., your approximate score, what you're trying to address)"
        )

    # General
    match = _match_faq(message, _GENERAL_RESPONSES)
    if match:
        return match

    if thread_message_count >= 2:
        return (
            "I want to make sure you get the best answer. "
            "Let me flag this for our human team to follow up — "
            "you'll hear back within 24 hours."
        )

    return (
        "Thanks for reaching out! I'm here to help with questions about "
        "funding, credit, and our process. "
        "Could you give me a bit more detail about what you need help with?"
    )


# ─── Main handler ─────────────────────────────────────────────────────────────

def handle_support_request(event_payload: dict) -> dict:
    """
    Process a support_request event.
    payload: client_id, lead_id, message, subject (optional)
    """
    from support_agent.support_service import (
        open_thread, add_message, resolve_thread, escalate_thread, get_thread_messages
    )

    client_id = event_payload.get('client_id')
    lead_id   = event_payload.get('lead_id')
    message   = event_payload.get('message', '')
    subject   = event_payload.get('subject', message[:80])

    if not message:
        return {'success': False, 'error': 'No message provided'}

    # Detect category and escalation need
    category   = detect_category(message)
    escalate   = needs_escalation(message)
    priority   = 'high' if escalate else 'normal'

    # Open thread
    thread = open_thread(subject=subject, category=category,
                         client_id=client_id, lead_id=lead_id, priority=priority)
    if not thread:
        return {'success': False, 'error': 'Could not create support thread'}

    thread_id = thread['id']

    # Record client message
    add_message(thread_id, 'client', message)

    if escalate:
        escalate_thread(thread_id)
        response = (
            "I've flagged your message for urgent review by our team. "
            "A human agent will contact you within 2 hours. "
            "We take all concerns seriously and will resolve this promptly."
        )
        add_message(thread_id, 'agent', response)
        # Notify human via Telegram
        try:
            from lib.hermes_gate import send as gate_send
            alert = f"🚨 Support Escalation\nClient: {client_id or lead_id}\nMessage: {message[:200]}"
            gate_send(alert, event_type='critical_alert', severity='critical')
        except Exception:
            pass
    else:
        # Get message count for this thread
        prior_messages = get_thread_messages(thread_id)
        response = build_response(message, category, len(prior_messages))
        add_message(thread_id, 'agent', response)

        # Auto-resolve simple FAQs
        if len(response) < 300 and category != 'general':
            resolve_thread(thread_id, f"FAQ answered: {category}", 'ai_agent')

    # Send via output_service
    try:
        from autonomy.output_service import send_message
        send_message(message=response, client_id=client_id,
                     metadata={'thread_id': thread_id, 'agent': 'support_agent'})
    except Exception as e:
        logger.warning(f"Output service failed: {e}")

    # Write summary on escalations
    if escalate:
        try:
            from autonomy.summary_service import write_summary
            write_summary(
                agent_name='support_agent',
                summary_type='support_escalation',
                summary_text=f"Support escalation: client={client_id} category={category}",
                what_happened=f"Client message triggered escalation: '{message[:100]}'",
                what_changed='Thread escalated, human notified via Telegram',
                recommended_next_action='Human agent must follow up within 2 hours',
                follow_up_needed=True,
                priority='high',
            )
        except Exception:
            pass

    logger.info(f"Support request handled: thread={thread_id} category={category} escalated={escalate}")
    return {
        'success':    True,
        'thread_id':  thread_id,
        'category':   category,
        'escalated':  escalate,
        'response':   response,
    }
