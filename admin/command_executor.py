"""
Admin Command Executor.

Receives a parsed command dict (from command_parser.parse()) and executes it.
Writes the command to admin_commands in Supabase, then routes to the appropriate
handler.

High-risk commands (requires_confirmation) are stored but NOT executed
until explicitly confirmed.

Usage:
    from admin.command_parser import parse
    from admin.command_executor import execute

    parsed = parse("add youtube channel https://youtube.com/c/example")
    result = execute(parsed)
    print(result)  # {'success': True, 'command_id': '...', 'result': {...}}
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('CommandExecutor')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
    }


def _sb_post(path: str, body: dict) -> Optional[dict]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except urllib.error.HTTPError as e:
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


def _store_command(parsed: dict) -> Optional[str]:
    """Persist the command to admin_commands. Returns the row id."""
    row = {
        'raw_input':         parsed.get('raw_input', ''),
        'parsed_intent':     parsed.get('parsed_intent'),
        'command_type':      parsed.get('command_type'),
        'target_agent':      parsed.get('target_agent'),
        'payload':           parsed.get('payload', {}),
        'validation_status': parsed.get('validation_status', 'pending'),
        'queue_status':      parsed.get('queue_status', 'queued'),
        'created_by':        parsed.get('created_by', 'admin'),
    }
    result = _sb_post('admin_commands', row)
    return result.get('id') if result else None


def _mark_processed(command_id: str, queue_status: str = 'completed') -> None:
    now = datetime.now(timezone.utc).isoformat()
    _sb_patch(
        f"admin_commands?id=eq.{command_id}",
        {'queue_status': queue_status, 'processed_at': now},
    )


# ─── Handlers ─────────────────────────────────────────────────────────────────

def _handle_add_research_source(payload: dict, command_id: str) -> dict:
    from research_sources.source_registry import add_source
    source_type = payload.get('source_type', 'website')
    source_url  = payload.get('source_url', '')
    domain      = payload.get('domain', '')

    if not source_url:
        return {'success': False, 'error': 'source_url missing from payload'}

    source_id, msg = add_source(
        source_type=source_type,
        source_url=source_url,
        domain=domain,
        added_by='admin_command',
        command_id=command_id,
    )
    if source_id:
        return {'success': True, 'source_id': source_id, 'message': msg}
    return {'success': False, 'error': msg}


def _handle_rescan_source(payload: dict, command_id: str) -> dict:
    from research_sources.source_registry import queue_rescan
    label_or_url = payload.get('label_or_url', '')
    if not label_or_url:
        return {'success': False, 'error': 'No source label or URL provided'}
    ok, msg = queue_rescan(label_or_url)
    return {'success': ok, 'message': msg}


def _handle_rerun_funding(payload: dict, command_id: str) -> dict:
    client_ref = payload.get('client_ref', '')
    if not client_ref:
        return {'success': False, 'error': 'No client reference provided'}
    try:
        from autonomy.event_emitter import emit_event
        event_id = emit_event(
            event_type='credit_analysis_completed',
            client_id=client_ref,
            payload={'rerun': True, 'triggered_by': command_id, 'score': None},
        )
        return {'success': bool(event_id), 'event_id': event_id, 'client': client_ref}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _handle_rerun_credit(payload: dict, command_id: str) -> dict:
    client_ref = payload.get('client_ref', '')
    if not client_ref:
        return {'success': False, 'error': 'No client reference provided'}
    try:
        from autonomy.event_emitter import emit_event
        event_id = emit_event(
            event_type='client_registered',
            client_id=client_ref,
            payload={'rerun': True, 'triggered_by': command_id},
        )
        return {'success': bool(event_id), 'event_id': event_id, 'client': client_ref}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _handle_refresh_strategy_scores(payload: dict, command_id: str) -> dict:
    try:
        from autonomy.event_emitter import emit_event
        event_id = emit_event(
            event_type='refresh_strategy_scores',
            client_id=None,
            payload={'triggered_by': command_id},
        )
        return {'success': True, 'event_id': event_id}
    except Exception as e:
        return {'success': False, 'error': str(e)}


_HANDLERS = {
    'add_research_source':    _handle_add_research_source,
    'rescan_source':          _handle_rescan_source,
    'rerun_funding_analysis': _handle_rerun_funding,
    'rerun_credit_analysis':  _handle_rerun_credit,
    'refresh_strategy_scores': _handle_refresh_strategy_scores,
}


# ─── Public API ───────────────────────────────────────────────────────────────

def execute(parsed: dict) -> dict:
    """
    Store, gate on approval, then execute a parsed command.

    Returns:
      {'success': bool, 'command_id': str, 'result': dict, 'skipped': bool}
    """
    # Always persist the command first
    command_id = _store_command(parsed)
    if not command_id:
        return {'success': False, 'command_id': None, 'result': {'error': 'Failed to store command'}}

    validation   = parsed.get('validation_status', 'pending')
    safety_level = parsed.get('safety_level', 'medium')
    cmd_type     = parsed.get('command_type')

    # Create approval record for every stored command
    try:
        from admin.approval_service import create_approval_record
        create_approval_record(
            command_id=command_id,
            command_type=cmd_type,
            safety_level=safety_level,
        )
    except Exception as e:
        logger.warning(f"Approval record creation failed: {e}")

    # Invalid or unrecognized
    if validation == 'invalid':
        return {
            'success':    False,
            'command_id': command_id,
            'skipped':    True,
            'result':     {'error': parsed.get('error', 'Invalid command')},
        }

    # High-risk — store only, wait for confirmation
    if validation == 'requires_confirmation' or safety_level == 'high':
        logger.info(f"Command {command_id} [{cmd_type}] stored — approval required (high risk)")
        return {
            'success':    False,
            'command_id': command_id,
            'skipped':    True,
            'result':     {'message': 'Stored — awaiting explicit approval (high risk)'},
        }

    # Medium-risk — store but do NOT execute until approved
    if safety_level == 'medium':
        logger.info(f"Command {command_id} [{cmd_type}] stored — approval required (medium risk)")
        return {
            'success':    False,
            'command_id': command_id,
            'skipped':    True,
            'result':     {'message': 'Stored — awaiting approval. Use approve_command() to release.'},
        }

    # Low-risk — execute immediately (approval record already marked not_required)
    handler = _HANDLERS.get(cmd_type)
    if not handler:
        _mark_processed(command_id, 'failed')
        return {
            'success':    False,
            'command_id': command_id,
            'result':     {'error': f'No handler for command type: {cmd_type}'},
        }

    try:
        result = handler(parsed.get('payload', {}), command_id)
        status = 'completed' if result.get('success') else 'failed'
        _mark_processed(command_id, status)
        logger.info(f"Command {command_id} [{cmd_type}] → {status}")
        return {
            'success':    result.get('success', False),
            'command_id': command_id,
            'result':     result,
        }
    except Exception as e:
        _mark_processed(command_id, 'failed')
        logger.exception(f"Command {command_id} [{cmd_type}] crashed")
        return {
            'success':    False,
            'command_id': command_id,
            'result':     {'error': str(e)},
        }


def execute_approved_command(command_id: str) -> dict:
    """
    Execute a previously stored command that has now been approved.
    Called after approve_command() grants approval for a medium/high-risk command.

    Fetches the stored command from admin_commands, then routes to the handler.
    """
    import urllib.request as _ur, json as _j
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/admin_commands?id=eq.{command_id}&select=*&limit=1"
    req = _ur.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
    try:
        with _ur.urlopen(req, timeout=10) as r:
            rows = _j.loads(r.read())
    except Exception as e:
        return {'success': False, 'command_id': command_id, 'result': {'error': str(e)}}

    if not rows:
        return {'success': False, 'command_id': command_id, 'result': {'error': 'Command not found'}}

    row       = rows[0]
    cmd_type  = row.get('command_type')
    payload   = row.get('payload') or {}

    # Verify approval
    from admin.approval_service import is_approved
    if not is_approved(command_id):
        return {
            'success':    False,
            'command_id': command_id,
            'result':     {'error': 'Command not approved'},
        }

    handler = _HANDLERS.get(cmd_type)
    if not handler:
        _mark_processed(command_id, 'failed')
        return {'success': False, 'command_id': command_id,
                'result': {'error': f'No handler for: {cmd_type}'}}

    try:
        result = handler(payload, command_id)
        status = 'completed' if result.get('success') else 'failed'
        _mark_processed(command_id, status)
        logger.info(f"Approved command executed: {command_id} [{cmd_type}] → {status}")
        return {'success': result.get('success', False), 'command_id': command_id, 'result': result}
    except Exception as e:
        _mark_processed(command_id, 'failed')
        return {'success': False, 'command_id': command_id, 'result': {'error': str(e)}}


def run_command(raw_input: str, created_by: str = 'admin') -> dict:
    """One-liner: parse + execute. Convenience wrapper."""
    from admin.command_parser import parse
    parsed = parse(raw_input, created_by=created_by)
    return execute(parsed)
