"""
Nexus One Command Interpreter.

Interprets plain-language operator commands from Telegram or other surfaces.
Extends the existing admin/command_parser with:
  - Hermes-enhanced intent classification
  - Nexus One voice acknowledgment
  - Routing into existing admin_commands / queue structures
  - Risk classification and approval routing

Supported command intents:
  source_add        — add YouTube channel / website / RSS for research
  source_pause      — pause a source or all source scans
  source_resume     — resume source scanning
  analysis_run      — rerun funding/credit/strategy analysis
  pipeline_control  — pause/resume pipeline stages
  review_now        — force a review cycle
  schedule          — schedule a task for later
  status_query      — what is blocked / what needs attention
  approve           — approve a pending decision/variant
  override          — override a decision
  niche_explore     — explore/validate a new niche
  unknown           — cannot classify

Risk levels:
  low    — source adds, status queries, schedule requests
  medium — analysis reruns, pipeline pauses, niche exploration
  high   — pipeline stops, bulk overrides, system resets

Usage:
    from nexus_one.command_interpreter import interpret_command, route_command
"""

import os
import re
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('NexusOneInterpreter')

# ─── Intent patterns ──────────────────────────────────────────────────────────

_INTENT_PATTERNS = [
    # Source management
    ('source_add',      r'add\s+(youtube|channel|website|site|rss|source|url)'),
    ('source_add',      r'(subscribe|track|monitor)\s+.*(channel|site|source)'),
    ('source_pause',    r'(pause|stop|halt)\s+.*(scan|source|research)'),
    ('source_resume',   r'(resume|restart|continue|unpause)\s+.*(scan|source|research)'),

    # Analysis
    ('analysis_run',    r'(rerun|run|redo|retry)\s+.*(funding|credit|analysis|strategy)'),
    ('analysis_run',    r'(analyze|analyse)\s+(this|the)?\s*(client|lead|business)'),

    # Pipeline
    ('pipeline_control', r'(pause|stop|halt)\s+.*(pipeline|strategy|signal|engine)'),
    ('pipeline_control', r'(resume|restart)\s+.*(pipeline|strategy|signal)'),

    # Review
    ('review_now',      r'(review|check|run)\s+(now|immediately|asap)'),
    ('review_now',      r'force\s+(review|scan|cycle)'),

    # Schedule
    ('schedule',        r'(schedule|remind|later|tomorrow|at\s+\d)'),

    # Status
    ('status_query',    r'what\s+(is|are|needs|changed|blocked)'),
    ('status_query',    r'(status|health|update|briefing|summary)\??'),
    ('status_query',    r"what.*(attention|review|approve|decide)"),

    # Approvals
    ('approve',         r'approve\s+([a-f0-9\-]{6,})'),
    ('approve',         r'(approve|confirm|go ahead|execute)\s+(decision|variant|command)'),
    ('override',        r'(override|cancel|reject|deny)\s+([a-f0-9\-]{6,})'),

    # Niche
    ('niche_explore',   r'(explore|validate|test|research)\s+.*(niche|market|idea)'),
    ('niche_explore',   r'(what about|try)\s+.*(business|market|niche)'),
]

_RISK_MAP = {
    'source_add':       'low',
    'source_pause':     'medium',
    'source_resume':    'low',
    'analysis_run':     'medium',
    'pipeline_control': 'high',
    'review_now':       'low',
    'schedule':         'low',
    'status_query':     'low',
    'approve':          'medium',
    'override':         'high',
    'niche_explore':    'medium',
    'unknown':          'medium',
}

_APPROVAL_REQUIRED = {'pipeline_control', 'override'}


def _classify_intent(text: str) -> str:
    text_lower = text.lower()
    for intent, pattern in _INTENT_PATTERNS:
        if re.search(pattern, text_lower):
            return intent
    return 'unknown'


def _try_hermes_interpret(command: str, state_context: str = '') -> Optional[dict]:
    """
    Use Hermes to parse ambiguous commands.
    Returns dict with intent, action, notes — or None on failure.
    """
    from nexus_one.identity import build_context_prompt
    prompt = build_context_prompt(
        state_summary=state_context,
        command=command,
    ) + (
        "\n\nClassify this command. Return ONLY valid JSON:\n"
        '{\n'
        '  "intent": "<one of: source_add|source_pause|source_resume|analysis_run|'
        'pipeline_control|review_now|schedule|status_query|approve|override|niche_explore|unknown>",\n'
        '  "action": "<what should happen in one sentence>",\n'
        '  "target": "<what entity/resource is affected>",\n'
        '  "risk_level": "<low|medium|high>",\n'
        '  "notes": "<anything else relevant>"\n'
        '}'
    )
    try:
        token = os.getenv('HERMES_GATEWAY_TOKEN', '')
        url   = 'http://localhost:8642/v1/chat/completions'
        body  = json.dumps({
            'model':    'hermes',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 300,
        }).encode()
        req = urllib.request.Request(
            url, data=body,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            resp    = json.loads(r.read())
            content = resp['choices'][0]['message']['content'].strip()
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            return json.loads(content)
    except Exception as e:
        logger.debug(f"Hermes interpret failed: {e}")
        return None


def interpret_command(raw_command: str, use_hermes: bool = True) -> dict:
    """
    Parse a plain-language command into a structured intent object.

    Returns:
        intent        — classified intent
        risk_level    — low | medium | high
        requires_approval — bool
        action        — what should happen
        target        — entity/resource affected
        understood    — Nexus One's plain-language confirmation
        raw_command   — original text
        parsed_at     — timestamp
    """
    # Fast regex classification
    intent     = _classify_intent(raw_command)
    risk_level = _RISK_MAP.get(intent, 'medium')
    action     = _build_action_description(intent, raw_command)
    target     = _extract_target(intent, raw_command)

    # Try Hermes for unknown or ambiguous intents
    if intent == 'unknown' and use_hermes:
        ai = _try_hermes_interpret(raw_command)
        if ai:
            intent     = ai.get('intent', intent)
            risk_level = ai.get('risk_level', risk_level)
            action     = ai.get('action', action)
            target     = ai.get('target', target)

    requires_approval = (
        intent in _APPROVAL_REQUIRED or risk_level == 'high'
    )

    understood = _build_understood_text(intent, raw_command, action, target)

    return {
        'intent':             intent,
        'risk_level':         risk_level,
        'requires_approval':  requires_approval,
        'action':             action,
        'target':             target or 'system',
        'understood':         understood,
        'raw_command':        raw_command,
        'parsed_at':          datetime.now(timezone.utc).isoformat(),
    }


def _build_action_description(intent: str, text: str) -> str:
    _actions = {
        'source_add':        'Add new research source to source registry and schedule scans',
        'source_pause':      'Pause source scan schedule (no new scrapes until resumed)',
        'source_resume':     'Resume source scan schedule',
        'analysis_run':      'Queue funding/credit/strategy analysis run',
        'pipeline_control':  'Modify pipeline run state (pause or resume)',
        'review_now':        'Force immediate review cycle',
        'schedule':          'Schedule task for specified time',
        'status_query':      'Return current system status summary',
        'approve':           'Approve pending decision or variant',
        'override':          'Override and cancel pending decision',
        'niche_explore':     'Queue niche discovery validation scan',
        'unknown':           'Manual review required — intent unclear',
    }
    return _actions.get(intent, 'Route to admin queue for review')


def _extract_target(intent: str, text: str) -> str:
    """Extract the target entity from the command text."""
    # URL extraction
    url_match = re.search(r'https?://\S+', text)
    if url_match:
        return url_match.group(0)

    # YouTube channel
    yt_match = re.search(r'youtube\.com/(@[\w]+|channel/[\w]+)', text, re.I)
    if yt_match:
        return yt_match.group(0)

    # UUID (for approve/override)
    uuid_match = re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', text, re.I)
    if uuid_match:
        return uuid_match.group(0)

    # Short ID
    short_id = re.search(r'\b[a-f0-9]{6,12}\b', text)
    if short_id and intent in ('approve', 'override'):
        return short_id.group(0)

    return ''


def _build_understood_text(intent: str, raw: str, action: str, target: str) -> str:
    target_str = f" → target: {target}" if target else ''
    return f"{intent.replace('_', ' ').title()}{target_str}. {action}."


def route_command(parsed: dict, operator_id: str = 'super_admin') -> Optional[dict]:
    """
    Store the parsed command in admin_commands table for approval/execution.
    Returns the stored command record or None.
    """
    key = os.getenv('SUPABASE_KEY', '')
    url = f"{os.getenv('SUPABASE_URL', '')}/rest/v1/admin_commands"
    row = {
        'raw_command':   parsed['raw_command'],
        'command_type':  parsed['intent'],
        'risk_level':    parsed['risk_level'],
        'status':        'pending_approval' if parsed['requires_approval'] else 'queued',
        'payload': {
            'action':   parsed['action'],
            'target':   parsed['target'],
            'parsed_at': parsed['parsed_at'],
        },
        'submitted_by':  operator_id,
    }
    data = json.dumps(row).encode()
    h    = {
        'apikey': key, 'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json', 'Prefer': 'return=representation',
    }
    req = urllib.request.Request(url, data=data, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except Exception as e:
        logger.error(f"route_command store failed: {e}")
        return None


def handle_telegram_command(
    message_text: str,
    operator_id: str = 'super_admin',
) -> str:
    """
    Full pipeline: parse → route → format acknowledgment.
    Returns Telegram-formatted response string.
    """
    from nexus_one.output_formatter import format_command_ack

    parsed  = interpret_command(message_text)
    stored  = route_command(parsed, operator_id=operator_id)
    cmd_id  = stored.get('id') if stored else None

    expected = (
        'Awaiting your approval before execution.'
        if parsed['requires_approval']
        else 'Will execute in next worker cycle (usually within 5 minutes).'
    )

    return format_command_ack(
        raw_command=message_text,
        understood=parsed['understood'],
        action=parsed['action'],
        requires_approval=parsed['requires_approval'],
        risk_level=parsed['risk_level'],
        expected_result=expected,
        command_id=cmd_id,
    )
