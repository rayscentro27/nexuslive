"""
Admin Command Parser.

Converts plain-language super-admin instructions into structured commands.
Uses regex pattern matching — no LLM required.

Supported command types:
  add_research_source      — add a YouTube channel, website, or RSS feed
  rescan_source            — re-run a source that was already added
  pause_pipeline           — pause a named worker or pipeline
  resume_pipeline          — resume a paused worker
  rerun_funding_analysis   — re-trigger funding review for a client
  rerun_credit_analysis    — re-trigger credit analysis for a client
  refresh_strategy_scores  — recompute strategy scoring weights

Safety levels:
  low     — auto-queue immediately
  medium  — queue with review flag
  high    — require explicit confirmation before execution

Usage:
    from admin.command_parser import parse
    result = parse("add youtube channel https://youtube.com/c/example")
    # {'command_type': 'add_research_source', 'payload': {...},
    #   'parsed_intent': '...', 'safety_level': 'low', 'valid': True}
"""

import re
import urllib.parse
from typing import Optional, Tuple
from datetime import datetime, timezone


# ─── Pattern registry ─────────────────────────────────────────────────────────

# Each entry: (regex, command_type, safety_level, payload_builder_key)
_PATTERNS = [
    # YouTube channel
    (
        r'(?:add|track|monitor|scan)\s+(?:youtube|yt)\s+(?:channel\s+)?(?:at\s+)?(https?://\S+)',
        'add_research_source', 'low', 'youtube_url',
    ),
    # Website
    (
        r'(?:add|review|track|monitor|scan)\s+(?:website|site|web|url)\s+(?:at\s+)?(https?://\S+)',
        'add_research_source', 'low', 'website_url',
    ),
    # RSS feed
    (
        r'(?:add|track)\s+(?:rss|feed)\s+(?:at\s+)?(https?://\S+)',
        'add_research_source', 'low', 'rss_url',
    ),
    # Plain URL — auto-detect source type
    (
        r'^(https?://\S+)$',
        'add_research_source', 'low', 'auto_url',
    ),
    # Rescan by label or url
    (
        r'(?:rescan|re-scan|re scan)\s+(?:source\s+)?(.+)',
        'rescan_source', 'low', 'label_or_url',
    ),
    # Pause pipeline/worker
    (
        r'pause\s+(?:the\s+)?(?:pipeline\s+|worker\s+)?(.+)',
        'pause_pipeline', 'medium', 'target_name',
    ),
    # Resume pipeline/worker
    (
        r'resume\s+(?:the\s+)?(?:pipeline\s+|worker\s+)?(.+)',
        'resume_pipeline', 'medium', 'target_name',
    ),
    # Rerun funding for client
    (
        r'rerun\s+funding\s+(?:analysis\s+)?(?:for\s+)?(.+)',
        'rerun_funding_analysis', 'medium', 'client_ref',
    ),
    # Rerun credit for client
    (
        r'rerun\s+credit\s+(?:analysis\s+)?(?:for\s+)?(.+)',
        'rerun_credit_analysis', 'medium', 'client_ref',
    ),
    # Refresh strategy scores
    (
        r'refresh\s+strategy\s+scores?',
        'refresh_strategy_scores', 'medium', None,
    ),
    # Disable a source — high risk
    (
        r'(?:disable|remove|delete)\s+(?:source\s+)?(.+)',
        'disable_source', 'high', 'label_or_url',
    ),
]


# ─── URL utilities ─────────────────────────────────────────────────────────────

def _detect_source_type(url: str) -> str:
    """Infer source type from URL."""
    lower = url.lower()
    if 'youtube.com' in lower or 'youtu.be' in lower:
        return 'youtube_channel'
    if lower.endswith('.xml') or lower.endswith('.rss') or '/feed' in lower:
        return 'rss_feed'
    return 'website'


def _extract_domain(url: str) -> str:
    """Extract bare domain from URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.lstrip('www.') or url[:50]
    except Exception:
        return url[:50]


def _validate_url(url: str) -> Tuple[bool, str]:
    """Return (valid, error_message)."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False, 'URL must start with http:// or https://'
        if not parsed.netloc:
            return False, 'URL missing domain'
        return True, ''
    except Exception as e:
        return False, str(e)


# ─── Payload builders ─────────────────────────────────────────────────────────

def _build_payload(builder_key: Optional[str], match_group: Optional[str]) -> dict:
    if not builder_key or not match_group:
        return {}

    val = match_group.strip().rstrip('.,;')

    if builder_key == 'youtube_url':
        url_valid, err = _validate_url(val)
        return {
            'source_type': 'youtube_channel',
            'source_url':  val,
            'domain':      _extract_domain(val),
            'valid_url':   url_valid,
            'url_error':   err,
        }

    if builder_key == 'website_url':
        url_valid, err = _validate_url(val)
        return {
            'source_type': 'website',
            'source_url':  val,
            'domain':      _extract_domain(val),
            'valid_url':   url_valid,
            'url_error':   err,
        }

    if builder_key == 'rss_url':
        url_valid, err = _validate_url(val)
        return {
            'source_type': 'rss_feed',
            'source_url':  val,
            'domain':      _extract_domain(val),
            'valid_url':   url_valid,
            'url_error':   err,
        }

    if builder_key == 'auto_url':
        url_valid, err = _validate_url(val)
        return {
            'source_type': _detect_source_type(val),
            'source_url':  val,
            'domain':      _extract_domain(val),
            'valid_url':   url_valid,
            'url_error':   err,
        }

    if builder_key in ('label_or_url', 'target_name', 'client_ref'):
        return {builder_key: val}

    return {}


# ─── Public API ───────────────────────────────────────────────────────────────

def parse(raw_input: str, created_by: str = 'admin') -> dict:
    """
    Parse a plain-language admin command.

    Returns a dict with:
      command_type, parsed_intent, payload, safety_level,
      validation_status, queue_status, raw_input, created_by, created_at
    """
    text = raw_input.strip()
    now  = datetime.now(timezone.utc).isoformat()

    for pattern, cmd_type, safety, builder_key in _PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            continue

        group = m.group(1) if m.lastindex and m.lastindex >= 1 else None
        payload = _build_payload(builder_key, group)

        # URL validation — fail fast for add_research_source with bad URL
        if cmd_type == 'add_research_source':
            if not payload.get('valid_url', True):
                return {
                    'raw_input':         raw_input,
                    'command_type':      cmd_type,
                    'parsed_intent':     f'Add {payload.get("source_type","source")}: {group}',
                    'payload':           payload,
                    'safety_level':      safety,
                    'validation_status': 'invalid',
                    'queue_status':      'rejected',
                    'created_by':        created_by,
                    'created_at':        now,
                    'error':             payload.get('url_error', 'Invalid URL'),
                }

        validation_status = _determine_validation_status(safety, payload)
        queue_status      = 'queued' if validation_status == 'valid' else 'pending_review'
        target_agent      = _target_agent(cmd_type)
        intent            = _build_intent(cmd_type, payload, group)

        return {
            'raw_input':         raw_input,
            'command_type':      cmd_type,
            'parsed_intent':     intent,
            'target_agent':      target_agent,
            'payload':           payload,
            'safety_level':      safety,
            'validation_status': validation_status,
            'queue_status':      queue_status,
            'created_by':        created_by,
            'created_at':        now,
        }

    # No pattern matched
    return {
        'raw_input':         raw_input,
        'command_type':      None,
        'parsed_intent':     None,
        'payload':           {},
        'safety_level':      None,
        'validation_status': 'invalid',
        'queue_status':      'rejected',
        'created_by':        created_by,
        'created_at':        now,
        'error':             'Unrecognized command. Try: "add youtube channel <url>" or "rerun funding for <client>".',
    }


def _determine_validation_status(safety: str, payload: dict) -> str:
    if safety == 'high':
        return 'requires_confirmation'
    if safety == 'medium':
        return 'valid'      # queue with review flag set via queue_status
    return 'valid'          # low = auto-queue


def _target_agent(cmd_type: str) -> Optional[str]:
    mapping = {
        'add_research_source':    'research_agent',
        'rescan_source':          'research_agent',
        'rerun_funding_analysis': 'funding_agent',
        'rerun_credit_analysis':  'credit_agent',
        'refresh_strategy_scores': 'capital_agent',
        'pause_pipeline':         'system',
        'resume_pipeline':        'system',
        'disable_source':         'research_agent',
    }
    return mapping.get(cmd_type)


def _build_intent(cmd_type: str, payload: dict, raw_group: Optional[str]) -> str:
    if cmd_type == 'add_research_source':
        st  = payload.get('source_type', 'source')
        url = payload.get('source_url', raw_group or '')
        return f"Add {st}: {url}"
    if cmd_type == 'rescan_source':
        return f"Rescan source: {payload.get('label_or_url', raw_group or '')}"
    if cmd_type == 'pause_pipeline':
        return f"Pause pipeline/worker: {payload.get('target_name', raw_group or '')}"
    if cmd_type == 'resume_pipeline':
        return f"Resume pipeline/worker: {payload.get('target_name', raw_group or '')}"
    if cmd_type == 'rerun_funding_analysis':
        return f"Rerun funding analysis for: {payload.get('client_ref', raw_group or '')}"
    if cmd_type == 'rerun_credit_analysis':
        return f"Rerun credit analysis for: {payload.get('client_ref', raw_group or '')}"
    if cmd_type == 'refresh_strategy_scores':
        return "Refresh all strategy scoring weights"
    if cmd_type == 'disable_source':
        return f"Disable source: {payload.get('label_or_url', raw_group or '')}"
    return cmd_type
