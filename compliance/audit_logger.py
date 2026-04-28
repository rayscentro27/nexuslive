"""
Audit Logger.

Append-only log of every significant action in the system.
Call log_action() from any agent, service, or API handler.

This module is intentionally simple and fire-and-forget — audit logging
must NEVER block the main operation. All failures are silently swallowed.

Usage:
    from compliance.audit_logger import log_action

    log_action(
        action='funding_recommendation_sent',
        actor_id='funding_agent',
        actor_type='agent',
        entity_type='client',
        entity_id=client_id,
        details={'amount': 50000, 'product': 'SBA Loan'},
    )
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('AuditLogger')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Actions that always require audit logging
ALWAYS_LOG = {
    # Agent actions
    'funding_recommendation_sent',
    'credit_analysis_completed',
    'capital_deployed',
    'strategy_approved',
    'signal_approved',
    # Admin actions
    'command_executed',
    'command_approved',
    'command_rejected',
    'source_added',
    'source_disabled',
    # API actions
    'api_key_created',
    'api_key_revoked',
    'api_service_called',
    # Auth/access
    'user_added_to_org',
    'role_changed',
    'module_disabled',
    # Compliance
    'disclaimer_shown',
    'financial_advice_given',
    'client_data_accessed',
}


def log_action(
    action: str,
    actor_id: str            = 'system',
    actor_type: str          = 'system',
    entity_type: Optional[str] = None,
    entity_id: Optional[str]   = None,
    org_id: Optional[str]      = None,
    details: Optional[dict]    = None,
    ip_address: Optional[str]  = None,
) -> None:
    """
    Fire-and-forget audit log entry.
    Never raises — always silently handles errors.
    """
    try:
        key  = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
        url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/audit_logs"
        row: dict = {
            'actor_id':   actor_id,
            'actor_type': actor_type,
            'action':     action,
            'details':    details or {},
        }
        if entity_type:
            row['entity_type'] = entity_type
        if entity_id:
            row['entity_id'] = str(entity_id)
        if org_id:
            row['org_id'] = org_id
        if ip_address:
            row['ip_address'] = ip_address

        body = json.dumps(row).encode()
        h    = {
            'apikey': key, 'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json', 'Prefer': 'return=minimal',
        }
        req = urllib.request.Request(url, data=body, headers=h, method='POST')
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # Audit logging must never block or raise


def log_agent_action(
    agent_name: str,
    action: str,
    client_id: Optional[str] = None,
    details: Optional[dict]  = None,
) -> None:
    """Convenience wrapper for agent audit events."""
    log_action(
        action=action,
        actor_id=agent_name,
        actor_type='agent',
        entity_type='client' if client_id else None,
        entity_id=client_id,
        details=details,
    )


def log_api_action(
    api_key_id: str,
    action: str,
    org_id: Optional[str]   = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Convenience wrapper for API audit events."""
    log_action(
        action=action,
        actor_id=api_key_id,
        actor_type='api',
        org_id=org_id,
        details=details,
        ip_address=ip_address,
    )


def log_admin_action(
    admin_id: str,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str]   = None,
    details: Optional[dict]    = None,
) -> None:
    """Convenience wrapper for admin command audit events."""
    log_action(
        action=action,
        actor_id=admin_id,
        actor_type='user',
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )


def get_audit_trail(
    entity_type: Optional[str] = None,
    entity_id: Optional[str]   = None,
    actor_id: Optional[str]    = None,
    limit: int                 = 100,
) -> list:
    """Query the audit log."""
    parts = [f"order=created_at.desc&limit={limit}&select=*"]
    if entity_type:
        parts.append(f"entity_type=eq.{entity_type}")
    if entity_id:
        parts.append(f"entity_id=eq.{entity_id}")
    if actor_id:
        parts.append(f"actor_id=eq.{actor_id}")

    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/audit_logs?{'&'.join(parts)}"
    req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return []
