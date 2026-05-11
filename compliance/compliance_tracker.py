"""
Compliance Tracker.

Records financial recommendations, disclaimers, and approvals
for legal safety and enterprise trust.

Three record types:
  financial_recommendation — any funding or investment advice given to a client
  disclaimer_shown         — legal disclaimer displayed to a user
  approval_given           — explicit confirmation/consent from a client

Every significant financial action should call record_financial_recommendation().
Every time a user sees risk/legal text, call record_disclaimer().
Every time a user agrees to terms, call record_approval().

Usage:
    from compliance.compliance_tracker import (
        record_financial_recommendation,
        record_disclaimer,
        record_approval,
    )
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('ComplianceTracker')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Standard disclaimer texts
DISCLAIMERS = {
    'funding_advice': (
        "DISCLAIMER: The funding options presented are based on the information provided and "
        "are for informational purposes only. This does not constitute financial advice. "
        "Nexus does not guarantee approval. All lending decisions are made by third-party lenders. "
        "A 10% success fee applies only on funded amounts."
    ),
    'credit_advice': (
        "DISCLAIMER: Credit improvement suggestions are general in nature and not personalized "
        "financial advice. Results vary based on individual credit history. "
        "Nexus is not a credit repair organization."
    ),
    'investment_advice': (
        "DISCLAIMER: Trading strategies and signals are for educational purposes only. "
        "Past performance does not guarantee future results. "
        "All trading involves risk of loss. Trade only what you can afford to lose."
    ),
    'data_processing': (
        "By proceeding, you consent to Nexus processing your business and financial information "
        "for the purpose of matching you with funding products. "
        "Your data is never sold to third parties."
    ),
    'fee_disclosure': (
        "Fee disclosure: Nexus charges a 10% success fee on funded amounts. "
        "This fee is deducted from the funded amount. No upfront fees. "
        "No funding = no fee."
    ),
}


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


# ─── Record types ─────────────────────────────────────────────────────────────

def record_financial_recommendation(
    client_id: str,
    content: str,
    actor_id: str        = 'system',
    org_id: Optional[str] = None,
) -> Optional[str]:
    """
    Record any financial recommendation made to a client.
    Called by funding_agent, credit_agent, capital_agent, and API services.
    """
    row: dict = {
        'record_type': 'financial_recommendation',
        'client_id':   client_id,
        'content':     content,
        'actor_id':    actor_id,
        'acknowledged': False,
    }
    if org_id:
        row['org_id'] = org_id
    result = _sb_post('compliance_records', row)
    if result:
        logger.debug(f"Financial rec recorded: client={client_id}")
    return result.get('id') if result else None


def record_disclaimer(
    disclaimer_key: str,
    client_id: Optional[str] = None,
    org_id: Optional[str]    = None,
    actor_id: str            = 'system',
) -> Optional[str]:
    """
    Record that a legal disclaimer was shown to a user.
    disclaimer_key maps to DISCLAIMERS dict.
    """
    content = DISCLAIMERS.get(disclaimer_key, disclaimer_key)
    row: dict = {
        'record_type':  'disclaimer_shown',
        'content':      content,
        'actor_id':     actor_id,
        'acknowledged': False,
    }
    if client_id:
        row['client_id'] = client_id
    if org_id:
        row['org_id'] = org_id
    result = _sb_post('compliance_records', row)
    return result.get('id') if result else None


def record_approval(
    client_id: str,
    approval_text: str,
    actor_id: str        = 'client',
    org_id: Optional[str] = None,
) -> Optional[str]:
    """
    Record explicit consent or approval from a client.
    Called when a client agrees to terms, fee disclosure, or data processing.
    """
    now = datetime.now(timezone.utc).isoformat()
    row: dict = {
        'record_type':      'approval_given',
        'client_id':        client_id,
        'content':          approval_text,
        'actor_id':         actor_id,
        'acknowledged':     True,
        'acknowledged_at':  now,
    }
    if org_id:
        row['org_id'] = org_id
    result = _sb_post('compliance_records', row)
    if result:
        # Also audit log
        try:
            from compliance.audit_logger import log_action
            log_action(
                action='client_approval_recorded',
                actor_id=actor_id,
                actor_type='user',
                entity_type='client',
                entity_id=client_id,
                details={'approval_text': approval_text[:200]},
            )
        except Exception:
            pass
    return result.get('id') if result else None


def mark_acknowledged(record_id: str) -> bool:
    """Mark a compliance record as acknowledged by the client."""
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"compliance_records?id=eq.{record_id}",
        {'acknowledged': True, 'acknowledged_at': now},
    )


def get_client_compliance_summary(client_id: str) -> dict:
    """Return a compliance summary for a client (for legal/audit use)."""
    rows = _sb_get(
        f"compliance_records?client_id=eq.{client_id}&order=created_at.desc&select=*"
    )
    by_type: dict = {}
    for r in rows:
        t = r.get('record_type', 'unknown')
        by_type[t] = by_type.get(t, 0) + 1

    unacknowledged = sum(1 for r in rows if not r.get('acknowledged', False))
    return {
        'client_id':       client_id,
        'total_records':   len(rows),
        'by_type':         by_type,
        'unacknowledged':  unacknowledged,
        'has_fee_disclosure': any(
            'fee' in (r.get('content') or '').lower() for r in rows
        ),
        'has_approval':    'approval_given' in by_type,
    }


def get_disclaimer_text(disclaimer_key: str) -> str:
    """Return the standard disclaimer text for a given key."""
    return DISCLAIMERS.get(disclaimer_key, '')
