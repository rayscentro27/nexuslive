"""
Funnel Deployer.

Deploys pre-built funnel templates to nexus instances.
Templates define step sequences for each funnel type.

Usage:
    from funnel_engine.funnel_deployer import (
        deploy_template, deploy_all_funnels_for_instance,
        get_active_funnels,
    )
"""

import logging
from typing import Optional, List

from funnel_engine.funnel_registry import (
    create_funnel, add_step, activate_funnel,
    list_funnels, get_step_count,
)

logger = logging.getLogger('FunnelDeployer')


# ─── Funnel templates ─────────────────────────────────────────────────────────
# Each template is a list of step dicts: name, type, content, order

FUNNEL_TEMPLATES = {
    'lead_gen': {
        'name':  'Lead Generation Funnel',
        'steps': [
            {
                'step_name':  'Awareness Hook',
                'step_order': 1,
                'step_type':  'message',
                'content':    (
                    "Struggling to get business funding? Our AI-powered system "
                    "matches you with the right lenders in minutes — no guesswork."
                ),
            },
            {
                'step_name':  'Lead Capture Form',
                'step_order': 2,
                'step_type':  'form',
                'content':    'Tell us about your business: name, monthly revenue, credit score.',
                'config':     {'fields': ['business_name', 'monthly_revenue', 'credit_score', 'phone']},
            },
            {
                'step_name':  'Qualification Delay',
                'step_order': 3,
                'step_type':  'delay',
                'config':     {'delay_minutes': 2},
            },
            {
                'step_name':  'Instant Match Offer',
                'step_order': 4,
                'step_type':  'offer',
                'content':    (
                    "Great news! Based on your profile, you qualify for up to $150,000 "
                    "in funding. Click below to see your matches."
                ),
            },
        ],
    },

    'sales': {
        'name':  'Sales Conversion Funnel',
        'steps': [
            {
                'step_name':  'Problem Statement',
                'step_order': 1,
                'step_type':  'message',
                'content':    (
                    "Most business owners leave $50,000+ on the table because they "
                    "don't know how to access the right capital. We fix that."
                ),
            },
            {
                'step_name':  'Social Proof',
                'step_order': 2,
                'step_type':  'message',
                'content':    (
                    "Our clients have secured over $2M in funding this quarter alone. "
                    "Zero upfront fees — we only win when you win."
                ),
            },
            {
                'step_name':  'Objection Handler',
                'step_order': 3,
                'step_type':  'message',
                'content':    (
                    "Worried about credit? We work with scores from 500+. "
                    "Been in business under 1 year? We have options for you too."
                ),
            },
            {
                'step_name':  'CTA — Book Call',
                'step_order': 4,
                'step_type':  'offer',
                'content':    "Book your free 15-minute funding strategy call now.",
                'config':     {'cta_type': 'calendar_link'},
            },
        ],
    },

    'onboarding': {
        'name':  'Client Onboarding Funnel',
        'steps': [
            {
                'step_name':  'Welcome Message',
                'step_order': 1,
                'step_type':  'message',
                'content':    (
                    "Welcome aboard! I'm your AI funding assistant. "
                    "Let's get you funded as fast as possible."
                ),
            },
            {
                'step_name':  'Credit Review Prompt',
                'step_order': 2,
                'step_type':  'form',
                'content':    "First, let's review your credit profile. Share your latest score.",
                'config':     {'fields': ['credit_score', 'derogatory_items', 'utilization_pct']},
            },
            {
                'step_name':  'Business Profile',
                'step_order': 3,
                'step_type':  'form',
                'content':    "Tell us about your business.",
                'config':     {'fields': ['business_name', 'industry', 'monthly_revenue', 'time_in_business_months']},
            },
            {
                'step_name':  'Funding Match',
                'step_order': 4,
                'step_type':  'offer',
                'content':    "Based on your profile, here are your top 3 funding options.",
                'config':     {'auto_match': True},
            },
        ],
    },

    'upsell': {
        'name':  'Upsell / Cross-Sell Funnel',
        'steps': [
            {
                'step_name':  'Congrats Message',
                'step_order': 1,
                'step_type':  'message',
                'content':    (
                    "Congratulations on securing your funding! "
                    "Here's how to make it work even harder for you."
                ),
            },
            {
                'step_name':  'Credit Building Offer',
                'step_order': 2,
                'step_type':  'offer',
                'content':    (
                    "Build your business credit to 700+ and unlock 10x more capital. "
                    "Our 90-day credit accelerator program starts at $297."
                ),
            },
            {
                'step_name':  'Trading Signal Access',
                'step_order': 3,
                'step_type':  'offer',
                'content':    (
                    "Deploy your capital smarter. Get access to our AI trading signals "
                    "— 78% win rate, $97/month."
                ),
            },
        ],
    },
}


def deploy_template(
    template_key: str,
    instance_id: Optional[str] = None,
    niche: Optional[str]       = None,
    auto_activate: bool        = True,
) -> Optional[dict]:
    """
    Deploy a funnel template to an instance.
    Creates funnel + all steps, optionally activates.
    Returns the funnel record.
    """
    template = FUNNEL_TEMPLATES.get(template_key)
    if not template:
        logger.warning(f"Unknown template: {template_key}")
        return None

    funnel_name = template['name']
    if niche:
        funnel_name = f"{niche.title()} — {template['name']}"

    funnel = create_funnel(
        funnel_name=funnel_name,
        funnel_type=template_key,
        instance_id=instance_id,
        niche=niche,
    )
    if not funnel:
        return None

    funnel_id = funnel['id']
    for step in template['steps']:
        add_step(
            funnel_id=funnel_id,
            step_name=step['step_name'],
            step_order=step['step_order'],
            step_type=step.get('step_type', 'message'),
            content=step.get('content'),
            config=step.get('config'),
        )

    if auto_activate:
        activate_funnel(funnel_id)
        funnel['status'] = 'active'

    logger.info(
        f"Deployed funnel '{funnel_name}' (type={template_key}) "
        f"instance={instance_id} steps={len(template['steps'])}"
    )
    return funnel


def deploy_all_funnels_for_instance(
    instance_id: str,
    niche: Optional[str] = None,
) -> List[dict]:
    """
    Deploy all 4 funnel types for a new instance.
    Called by replication_service when spawning.
    """
    deployed = []
    for key in FUNNEL_TEMPLATES:
        funnel = deploy_template(
            template_key=key,
            instance_id=instance_id,
            niche=niche,
            auto_activate=True,
        )
        if funnel:
            deployed.append(funnel)
    logger.info(f"Deployed {len(deployed)} funnels for instance {instance_id}")
    return deployed


def get_active_funnels(instance_id: Optional[str] = None) -> List[dict]:
    """Return all active funnels, optionally filtered by instance."""
    return list_funnels(instance_id=instance_id, status='active')
