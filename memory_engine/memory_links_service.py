"""
Memory Links Service.

Links ai_memory rows to tasks, threads, stages, and events.
Used after storing a memory to record what context it belongs to.
"""

import os
import json
import logging
import urllib.request
from typing import Optional, List

logger = logging.getLogger('MemoryLinks')

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
    except Exception as e:
        logger.warning(f"POST {path} → {e}")
        return None


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def link_memory(
    memory_id: str,
    task_id: Optional[str]   = None,
    thread_id: Optional[str] = None,
    stage: Optional[str]     = None,
    event_id: Optional[str]  = None,
) -> Optional[str]:
    """
    Create a link between an ai_memory row and a task/thread/stage/event.
    Returns the link row id, or None on failure.
    """
    if not any([task_id, thread_id, stage, event_id]):
        return None

    row: dict = {'memory_id': memory_id}
    if task_id:
        row['related_task_id'] = task_id
    if thread_id:
        row['related_thread_id'] = thread_id
    if stage:
        row['related_stage'] = stage
    if event_id:
        row['related_event_id'] = event_id

    result = _sb_post('memory_links', row)
    if result:
        return result.get('id')
    return None


def get_memory_links(memory_id: str) -> List[dict]:
    """Return all links for a given memory_id."""
    return _sb_get(
        f"memory_links?memory_id=eq.{memory_id}&select=*&order=created_at.desc"
    )


def get_memories_for_task(task_id: str) -> List[str]:
    """Return memory_ids linked to a specific task_id."""
    rows = _sb_get(
        f"memory_links?related_task_id=eq.{task_id}&select=memory_id"
    )
    return [r['memory_id'] for r in rows]
