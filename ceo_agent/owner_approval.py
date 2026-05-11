"""
Owner Approval Queue — Part 11.

Helpers for querying and actioning the owner_approval_queue table.
Used by telegram_bot.py for /approvals, /approve <id>, /reject <id> commands.
"""

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('OwnerApproval')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _sb(path: str, method: str = 'GET', body: Optional[dict] = None, prefer: str = '') -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }
    if prefer:
        headers['Prefer'] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return result if isinstance(result, list) else ([result] if result else [])
    except Exception as e:
        logger.warning(f"{method} {path}: {e}")
        return []


def get_pending(limit: int = 10) -> list:
    return _sb(
        f"owner_approval_queue?status=eq.pending"
        f"&order=priority.asc,created_at.asc&limit={limit}"
    )


def get_item(item_id: str) -> Optional[dict]:
    rows = _sb(f"owner_approval_queue?id=eq.{item_id}&limit=1")
    return rows[0] if rows else None


def find_item(short_id: str) -> Optional[dict]:
    """Find item by full or partial ID (first 8 chars)."""
    pending = _sb("owner_approval_queue?status=eq.pending&select=id,action_type,description&limit=100")
    for item in pending:
        if (item.get('id', '').startswith(short_id) or item.get('id') == short_id):
            return get_item(item['id'])
    return None


def approve(item_id: str, notes: str = '') -> bool:
    rows = _sb(f"owner_approval_queue?id=eq.{item_id}&status=eq.pending&limit=1")
    if not rows:
        return False
    _sb(f"owner_approval_queue?id=eq.{item_id}", 'PATCH', {
        'status': 'approved',
        'review_notes': notes or None,
        'reviewed_at': datetime.now(timezone.utc).isoformat(),
    }, prefer='return=minimal')
    return True


def reject(item_id: str, notes: str = '') -> bool:
    rows = _sb(f"owner_approval_queue?id=eq.{item_id}&status=eq.pending&limit=1")
    if not rows:
        return False
    _sb(f"owner_approval_queue?id=eq.{item_id}", 'PATCH', {
        'status': 'rejected',
        'review_notes': notes or None,
        'reviewed_at': datetime.now(timezone.utc).isoformat(),
    }, prefer='return=minimal')
    return True


def needs_edits(item_id: str, notes: str) -> bool:
    rows = _sb(f"owner_approval_queue?id=eq.{item_id}&status=eq.pending&limit=1")
    if not rows:
        return False
    _sb(f"owner_approval_queue?id=eq.{item_id}", 'PATCH', {
        'status': 'needs_edits',
        'review_notes': notes,
        'reviewed_at': datetime.now(timezone.utc).isoformat(),
    }, prefer='return=minimal')
    return True


# ─── Telegram Formatting ──────────────────────────────────────────────────────

def format_pending_list() -> str:
    items = get_pending(limit=15)
    if not items:
        return "No pending approvals. 🎉"

    priority_icon = {'urgent': '🔴', 'normal': '🟡', 'low': '🟢'}
    lines = [f'<b>Pending Approvals ({len(items)})</b>', '']
    for item in items:
        icon = priority_icon.get(item.get('priority', 'normal'), '•')
        short_id = item.get('id', '')[:8]
        desc = item.get('description', '')[:60]
        action_type = item.get('action_type', '?')
        requested_by = item.get('requested_by', '?')
        created = (item.get('created_at') or '')[:10]
        lines.append(f"{icon} <b>[{short_id}]</b> {action_type}")
        lines.append(f"   {desc}")
        lines.append(f"   By: {requested_by} | {created}")
        lines.append('')

    lines.append('Commands: /approve &lt;id&gt; | /reject &lt;id&gt; | /needs_edits &lt;id&gt; &lt;notes&gt;')
    return '\n'.join(lines)


def format_item_detail(item: dict) -> str:
    short_id = item.get('id', '')[:8]
    lines = [
        f'<b>Approval Request [{short_id}]</b>',
        f"Type: {item.get('action_type', '?')}",
        f"Priority: {item.get('priority', 'normal').upper()}",
        f"Requested by: {item.get('requested_by', '?')}",
        f"Description: {item.get('description', '')}",
        f"Created: {(item.get('created_at') or '')[:16].replace('T', ' ')} UTC",
        '',
        f"/approve {short_id} | /reject {short_id} | /needs_edits {short_id} &lt;note&gt;",
    ]
    payload = item.get('payload')
    if payload and isinstance(payload, dict):
        lines.insert(-2, f"\nPayload: {json.dumps(payload, indent=2)[:300]}")
    return '\n'.join(lines)
