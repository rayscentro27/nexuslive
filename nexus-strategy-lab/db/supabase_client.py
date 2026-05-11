"""
db/supabase_client.py — Thin Supabase REST wrapper.

Uses the service-role key so workers can bypass RLS.
All table operations go through here to keep credentials in one place.
"""
import json
import time
import logging
import requests
from typing import Any, Optional

from config import settings

logger = logging.getLogger(__name__)
REQUEST_TIMEOUT = float(__import__('os').getenv('STRATEGY_LAB_REQUEST_TIMEOUT', '15'))
MAX_ATTEMPTS = max(1, int(__import__('os').getenv('STRATEGY_LAB_DB_RETRIES', '2')))

# ── Default headers ───────────────────────────────────────────────────────────
def _headers(extra: Optional[dict] = None, service_role: bool = True) -> dict:
    key = settings.SUPABASE_SERVICE_ROLE_KEY if service_role else settings.SUPABASE_KEY
    h = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }
    if extra:
        h.update(extra)
    return h


def _url(table: str) -> str:
    return f"{settings.SUPABASE_URL}/rest/v1/{table}"


def _request(method: str, url: str, *, service_role: bool = True,
             extra_headers: Optional[dict] = None, **kwargs):
    headers = _headers(extra_headers, service_role)
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return requests.request(
                method,
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                **kwargs,
            )
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= MAX_ATTEMPTS:
                break
            logger.warning(
                "Supabase %s %s failed (%s/%s): %s",
                method,
                url,
                attempt,
                MAX_ATTEMPTS,
                exc,
            )
            time.sleep(min(2 * attempt, 5))
    raise last_error


# ── Core operations ───────────────────────────────────────────────────────────
def select(table: str, query: str = '', service_role: bool = True) -> list[dict]:
    """
    Fetch rows from a table.
    query examples:
        'status=eq.pending&order=created_at.asc'
        'id=eq.some-uuid'
    """
    url = _url(table)
    if query:
        url = f"{url}?{query}"
    r = _request('GET', url, service_role=service_role,
                 extra_headers={'Accept': 'application/json'})
    r.raise_for_status()
    return r.json()


def insert(table: str, row: dict, service_role: bool = True) -> dict:
    """Insert a single row; returns the inserted row."""
    r = _request(
        'POST',
        _url(table),
        service_role=service_role,
        extra_headers={'Prefer': 'return=representation'},
        json=row,
    )
    r.raise_for_status()
    result = r.json()
    return result[0] if isinstance(result, list) else result


def upsert(table: str, row: dict, on_conflict: str, service_role: bool = True) -> dict:
    """
    Upsert a single row by conflict column(s).
    on_conflict: comma-separated column name(s), e.g. 'candidate_id'
    """
    url = f"{_url(table)}?on_conflict={on_conflict}"
    r = _request(
        'POST',
        url,
        service_role=service_role,
        extra_headers={
            'Prefer': 'resolution=merge-duplicates,return=representation'
        },
        json=row,
    )
    r.raise_for_status()
    result = r.json()
    return result[0] if isinstance(result, list) else result


def update(table: str, row: dict, match: str, service_role: bool = True) -> dict:
    """
    Patch rows matching a filter.
    match example: 'id=eq.some-uuid'
    """
    url = f"{_url(table)}?{match}"
    r = _request(
        'PATCH',
        url,
        service_role=service_role,
        extra_headers={'Prefer': 'return=representation'},
        json=row,
    )
    r.raise_for_status()
    result = r.json()
    return result[0] if isinstance(result, list) and result else result


def delete(table: str, match: str, service_role: bool = True) -> None:
    """Delete rows matching a filter."""
    url = f"{_url(table)}?{match}"
    r = _request('DELETE', url, service_role=service_role)
    r.raise_for_status()


# ── Convenience helpers ───────────────────────────────────────────────────────
def get_by_id(table: str, id_value: str, id_col: str = 'id') -> Optional[dict]:
    rows = select(table, f'{id_col}=eq.{id_value}')
    return rows[0] if rows else None


def count(table: str, query: str = '') -> int:
    url = _url(table)
    if query:
        url = f"{url}?{query}"
    r = _request(
        'GET',
        url,
        extra_headers={'Accept': 'application/json', 'Prefer': 'count=exact'},
    )
    r.raise_for_status()
    content_range = r.headers.get('Content-Range', '0/0')
    # Format: "0-9/42" or "*/0"
    total = content_range.split('/')[-1]
    return int(total) if total.isdigit() else 0


# ── Health check ──────────────────────────────────────────────────────────────
def ping() -> bool:
    """Returns True if Supabase is reachable and credentials are valid."""
    try:
        r = requests.get(
            f"{settings.SUPABASE_URL}/rest/v1/",
            headers=_headers(),
            timeout=5,
        )
        return r.status_code in (200, 404)  # 404 = auth ok, table unknown
    except Exception as e:
        logger.warning(f"Supabase ping failed: {e}")
        return False


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    settings.validate()
    ok = ping()
    print(f"Supabase connection: {'OK' if ok else 'FAILED'}")
    sys.exit(0 if ok else 1)
