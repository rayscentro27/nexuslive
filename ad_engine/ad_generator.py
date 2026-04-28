"""
Ad Generation Engine.

Generates hooks, scripts, headlines, and CTAs for:
  TikTok, Instagram, YouTube

Uses Hermes when available for AI-generated copy.
Falls back to high-performing templates for each platform.

Usage:
    from ad_engine.ad_generator import generate_campaign

    campaign_id = generate_campaign(
        platform='tiktok',
        objective='leads',
        campaign_name='Nexus Funding Q1',
        business_type='funding',
        target_audience='small business owners',
    )
"""

import os
import json
import logging
from typing import Optional, List

logger = logging.getLogger('AdGenerator')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# ─── Templates ────────────────────────────────────────────────────────────────

_TEMPLATES = {
    'tiktok': {
        'hook': [
            "POV: You just got $50,000 for your business in 48 hours 💰",
            "Banks said no. We said yes. Here's how we got this business owner funded 👇",
            "Stop leaving money on the table — here's the funding hack most business owners don't know",
            "I helped 3 businesses get funded this week. Here's exactly how. 🧵",
        ],
        'script': [
            (
                "If you own a business and you're not using this, you're missing out.\n\n"
                "Most banks only approve 20% of business loan applications.\n"
                "But alternative lenders? 70%+.\n\n"
                "At Nexus, we match you with the right lender — and we only "
                "get paid when YOU get funded.\n\n"
                "Link in bio. Free assessment. Takes 5 minutes."
            ),
        ],
        'cta': [
            "Click the link in bio — free funding check in 5 minutes",
            "DM us 'FUND' to see what you qualify for",
            "Comment 'MONEY' and we'll send you the funding guide",
        ],
    },
    'instagram': {
        'hook': [
            "Your business qualifies for more funding than you think. Here's proof. 👇",
            "We funded 47 businesses last month. This is what they all had in common.",
            "Credit score 550? You can still get funded. Here's how.",
        ],
        'headline': [
            "Get Your Business Funded in 72 Hours — No Upfront Cost",
            "$10K–$500K for Your Business. We Only Charge When You Win.",
            "Bad Credit? We Work With Scores from 550+",
        ],
        'cta': [
            "Tap the link in bio — free business funding assessment",
            "DM 'FUND ME' to get started",
            "Save this post. You'll need it when you're ready to grow.",
        ],
    },
    'youtube': {
        'hook': [
            "In this video I'm going to show you exactly how small businesses are getting "
            "funded even with bad credit — and the one platform that makes it happen.",
            "Most business owners don't know this funding strategy exists. "
            "By the end of this video, you will.",
        ],
        'script': [
            (
                "INTRO: What's up everyone — if you own a business or you're "
                "thinking about starting one, this video is for you.\n\n"
                "PROBLEM: Getting business funding is hard. Banks reject 80% of applications. "
                "Interest rates are high. The process takes forever.\n\n"
                "SOLUTION: That's why we built Nexus. We connect business owners with "
                "alternative lenders who actually want to fund you — even if your credit isn't perfect.\n\n"
                "OFFER: We do all the work. You just fill out a 5-minute assessment. "
                "And here's the best part — we only charge a 10% fee when you get funded. "
                "Zero risk to you.\n\n"
                "CTA: Link in the description. Free assessment. No commitment."
            ),
        ],
        'cta': [
            "Link in the description — get your free funding assessment today",
            "Subscribe and hit the bell — I drop funding strategies every week",
            "Comment below: how much funding does your business need?",
        ],
    },
}


def _try_hermes(prompt: str) -> Optional[str]:
    try:
        token = os.getenv('HERMES_GATEWAY_TOKEN', '')
        if not token:
            return None
        import urllib.request as _ur
        try:
            from autonomy.nexus_super_prompt import build_nexus_prompt
            system_prompt = build_nexus_prompt(
                role_name="ad_copy_agent",
                task_description=prompt[:400],
                user_stage="awareness",
                current_goal="Create high-converting ad copy for Nexus platform",
            )
        except Exception:
            system_prompt = "You are a direct-response copywriter for Nexus, a business funding platform."
        body = json.dumps({
            'model': 'hermes',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ],
            'max_tokens': 400,
        }).encode()
        req = _ur.Request(
            'http://localhost:8642/v1/chat/completions',
            data=body,
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
        )
        with _ur.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
            return data.get('choices', [{}])[0].get('message', {}).get('content', '').strip() or None
    except Exception:
        return None


def _sb_post(path: str, body: dict) -> Optional[dict]:
    key  = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    h    = {
        'apikey': key, 'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json', 'Prefer': 'return=representation',
    }
    req  = urllib.request.Request(url, data=data, headers=h, method='POST')
    try:
        import urllib.request
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


def _store_creative(
    campaign_id: str,
    creative_type: str,
    platform: str,
    content: str,
) -> Optional[str]:
    import urllib.request
    key  = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/ad_creatives"
    body = json.dumps({
        'campaign_id':   campaign_id,
        'creative_type': creative_type,
        'platform':      platform,
        'content':       content,
        'status':        'draft',
    }).encode()
    h = {
        'apikey': key, 'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json', 'Prefer': 'return=representation',
    }
    req = urllib.request.Request(url, data=body, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0].get('id') if rows else None
    except Exception as e:
        logger.error(f"Store creative → {e}")
        return None


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_campaign(
    platform: str,
    campaign_name: str,
    objective: str         = 'leads',
    business_type: str     = 'funding',
    target_audience: str   = 'small business owners',
    org_id: Optional[str]  = None,
    use_ai: bool           = True,
) -> Optional[str]:
    """
    Create a campaign and generate draft creatives for it.
    Returns campaign_id or None on failure.
    """
    import urllib.request
    key  = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/ad_campaigns"
    row: dict = {
        'campaign_name':   campaign_name,
        'platform':        platform.lower(),
        'objective':       objective,
        'status':          'draft',
        'target_audience': target_audience,
    }
    if org_id:
        row['org_id'] = org_id
    h = {
        'apikey': key, 'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json', 'Prefer': 'return=representation',
    }
    body = json.dumps(row).encode()
    req  = urllib.request.Request(url, data=body, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows  = json.loads(r.read())
            camp  = rows[0] if rows else None
    except Exception as e:
        logger.error(f"Create campaign → {e}")
        return None

    if not camp:
        return None

    campaign_id = camp['id']
    templates   = _TEMPLATES.get(platform.lower(), _TEMPLATES['instagram'])
    created     = 0

    for creative_type, items in templates.items():
        for i, template in enumerate(items[:2]):  # max 2 per type
            # Try AI enhancement
            if use_ai and i == 0:
                ai_prompt = (
                    f"Write a high-converting {creative_type} for a {platform} ad.\n"
                    f"Business: {business_type} company\n"
                    f"Audience: {target_audience}\n"
                    f"Objective: {objective}\n"
                    f"Tone: bold, direct, action-oriented\n"
                    f"Max 150 words. No hashtags.\n"
                    f"Base template for reference: {template[:200]}"
                )
                content = _try_hermes(ai_prompt) or template
            else:
                content = template

            if _store_creative(campaign_id, creative_type, platform, content):
                created += 1

    logger.info(f"Campaign created: {campaign_name} platform={platform} creatives={created}")
    return campaign_id


def get_creatives(campaign_id: str) -> List[dict]:
    import urllib.request
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url = (
        f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/"
        f"ad_creatives?campaign_id=eq.{campaign_id}&order=creative_type.asc&select=*"
    )
    req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return []


def generate_quick_ad(
    platform: str,
    creative_type: str = 'hook',
    business_type: str = 'funding',
    target_audience: str = 'small business owners',
) -> str:
    """Generate a single creative piece without creating a campaign."""
    templates = _TEMPLATES.get(platform.lower(), _TEMPLATES['instagram'])
    items     = templates.get(creative_type, [])
    if not items:
        return ''

    ai_prompt = (
        f"Write one {creative_type} for a {platform} ad for a {business_type} company. "
        f"Target: {target_audience}. Bold, direct, max 80 words."
    )
    return _try_hermes(ai_prompt) or items[0]
