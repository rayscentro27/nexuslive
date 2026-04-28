"""
Onboarding Service.

Manages onboarding_sessions and onboarding_steps in Supabase.

Steps (in order):
  1. welcome    — greet + explain what happens
  2. credit     — collect credit info / upload docs
  3. business   — collect business details
  4. funding    — assess funding readiness + match products
  5. complete   — handoff to funding agent
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('OnboardingService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

STEPS = [
    ('welcome',  1),
    ('credit',   2),
    ('business', 3),
    ('funding',  4),
]
STEP_NAMES = [s[0] for s in STEPS]


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
    }


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def _sb_post(path: str, body: dict) -> Optional[dict]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return None
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


def _sb_patch(path: str, body: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    h    = _headers()
    h['Prefer'] = 'return=minimal'
    req  = urllib.request.Request(url, data=data, headers=h, method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"PATCH {path} → {e}")
        return False


# ─── Sessions ─────────────────────────────────────────────────────────────────

def get_session(client_id: str) -> Optional[dict]:
    rows = _sb_get(
        f"onboarding_sessions?client_id=eq.{client_id}&select=*&limit=1"
    )
    return rows[0] if rows else None


def create_session(client_id: str) -> Optional[dict]:
    """Create a new onboarding session and seed all steps as pending."""
    # Prevent duplicate session
    existing = get_session(client_id)
    if existing:
        return existing

    result = _sb_post('onboarding_sessions', {
        'client_id':    client_id,
        'current_step': 'welcome',
        'status':       'active',
    })
    if not result:
        return None

    session_id = result['id']
    # Seed steps
    for step_name, order in STEPS:
        _sb_post('onboarding_steps', {
            'session_id': session_id,
            'step_name':  step_name,
            'step_order': order,
            'status':     'pending',
        })

    # Mark welcome as in_progress immediately
    _sb_patch(
        f"onboarding_steps?session_id=eq.{session_id}&step_name=eq.welcome",
        {'status': 'in_progress'},
    )
    logger.info(f"Onboarding session created for client {client_id}")
    return result


def advance_step(client_id: str) -> Optional[str]:
    """
    Mark current step as complete and advance to next.
    Returns new step name, or 'complete' if all done.
    """
    session = get_session(client_id)
    if not session:
        return None
    session_id    = session['id']
    current_step  = session.get('current_step', 'welcome')
    now           = datetime.now(timezone.utc).isoformat()

    # Mark current step complete
    _sb_patch(
        f"onboarding_steps?session_id=eq.{session_id}&step_name=eq.{current_step}",
        {'status': 'complete', 'completed_at': now},
    )

    # Find next step
    try:
        current_idx = STEP_NAMES.index(current_step)
        next_idx    = current_idx + 1
    except ValueError:
        next_idx = len(STEP_NAMES)

    if next_idx >= len(STEP_NAMES):
        # All steps complete
        _sb_patch(f"onboarding_sessions?id=eq.{session_id}",
                  {'status': 'complete', 'current_step': 'complete', 'completed_at': now})
        logger.info(f"Onboarding complete for client {client_id}")
        return 'complete'

    next_step = STEP_NAMES[next_idx]
    _sb_patch(f"onboarding_sessions?id=eq.{session_id}", {'current_step': next_step})
    _sb_patch(
        f"onboarding_steps?session_id=eq.{session_id}&step_name=eq.{next_step}",
        {'status': 'in_progress'},
    )
    logger.info(f"Onboarding advanced: client={client_id} step={next_step}")
    return next_step


def get_step_status(client_id: str) -> List[dict]:
    """Return all steps with their status for a client."""
    session = get_session(client_id)
    if not session:
        return []
    return _sb_get(
        f"onboarding_steps?session_id=eq.{session['id']}&order=step_order.asc&select=*"
    )


def get_active_sessions(limit: int = 100) -> List[dict]:
    return _sb_get(
        f"onboarding_sessions?status=eq.active&order=started_at.asc&limit={limit}&select=*"
    )
