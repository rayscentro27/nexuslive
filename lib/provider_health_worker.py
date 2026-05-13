"""
Provider Health Polling Worker.

Checks connectivity and latency for all 7 AI providers, then updates
the provider_health table in Supabase.

Run:
  python3 -m lib.provider_health_worker

Cron (every 15 minutes):
  */15 * * * * cd ~/nexus-ai && source .env && python3 -m lib.provider_health_worker >> logs/provider_health.log 2>&1
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("ProviderHealthWorker")

# ── env loading ───────────────────────────────────────────────────────────────

_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
DRY_RUN = os.getenv('NEXUS_DRY_RUN', 'true').lower() == 'true'

GROQ_API_KEY       = os.getenv('GROQ_API_KEY', '')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OLLAMA_BASE_URL    = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11555')

TIMEOUT = 8  # seconds per check


# ── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_headers() -> dict:
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation,resolution=merge-duplicates',
    }


def _sb_upsert(table: str, row: dict, on_conflict: str = 'provider_name') -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(row).encode()
    req = urllib.request.Request(url, data=data, headers=_sb_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
            return True
    except urllib.error.HTTPError as e:
        logger.error("UPSERT %s → HTTP %s: %s", table, e.code, e.read().decode()[:200])
        return False
    except Exception as e:
        logger.error("UPSERT %s → %s", table, e)
        return False


# ── Provider check functions ──────────────────────────────────────────────────

def _check_url(url: str, headers: Optional[dict] = None, expected_status: int = 200) -> tuple[str, int]:
    """Returns (status, latency_ms). Status: online | offline | degraded."""
    t0 = time.time()
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            r.read()
            latency = round((time.time() - t0) * 1000)
            status = r.status if hasattr(r, 'status') else 200
            if status >= 500:
                return 'degraded', latency
            return 'online', latency
    except urllib.error.HTTPError as e:
        latency = round((time.time() - t0) * 1000)
        if e.code in (401, 403):
            return 'online', latency  # auth error = server is up
        if e.code >= 500:
            return 'degraded', latency
        return 'online', latency
    except Exception:
        latency = round((time.time() - t0) * 1000)
        return 'offline', latency


def check_ollama() -> tuple[str, int, Optional[str]]:
    url = f"{OLLAMA_BASE_URL}/api/tags"
    status, latency = _check_url(url)
    error = None if status != 'offline' else f"Cannot reach {OLLAMA_BASE_URL}"
    return status, latency, error


def check_groq() -> tuple[str, int, Optional[str]]:
    if not GROQ_API_KEY:
        return 'offline', 0, 'GROQ_API_KEY not set'
    url = 'https://api.groq.com/openai/v1/models'
    status, latency = _check_url(url, headers={'Authorization': f'Bearer {GROQ_API_KEY}'})
    return status, latency, None if status != 'offline' else 'Groq API unreachable'


def check_openrouter() -> tuple[str, int, Optional[str]]:
    if not OPENROUTER_API_KEY:
        return 'offline', 0, 'OPENROUTER_API_KEY not set'
    url = 'https://openrouter.ai/api/v1/models'
    status, latency = _check_url(url, headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'})
    return status, latency, None if status != 'offline' else 'OpenRouter API unreachable'


def check_claude_cli() -> tuple[str, int, Optional[str]]:
    """Check if claude CLI binary is available."""
    import shutil
    t0 = time.time()
    path = shutil.which('claude')
    latency = round((time.time() - t0) * 1000)
    if path:
        return 'online', latency, None
    return 'offline', latency, 'claude binary not found in PATH'


def check_codex() -> tuple[str, int, Optional[str]]:
    """Check if codex CLI binary is available."""
    import shutil
    t0 = time.time()
    path = shutil.which('codex')
    latency = round((time.time() - t0) * 1000)
    if path:
        return 'online', latency, None
    return 'offline', latency, 'codex binary not found in PATH'


def check_opencode() -> tuple[str, int, Optional[str]]:
    """Check if opencode CLI binary is available."""
    import shutil
    t0 = time.time()
    path = shutil.which('opencode')
    latency = round((time.time() - t0) * 1000)
    if path:
        return 'online', latency, None
    return 'offline', latency, 'opencode binary not found in PATH'


def check_notebooklm() -> tuple[str, int, Optional[str]]:
    """NotebookLM is browser-based — just verify the domain is reachable."""
    status, latency = _check_url('https://notebooklm.google.com')
    return status, latency, None if status != 'offline' else 'notebooklm.google.com unreachable'


# ── Registry ──────────────────────────────────────────────────────────────────

PROVIDER_CHECKS = {
    'ollama':       check_ollama,
    'groq':         check_groq,
    'openrouter':   check_openrouter,
    'claude_cli':   check_claude_cli,
    'codex':        check_codex,
    'opencode':     check_opencode,
    'notebooklm':   check_notebooklm,
}


# ── Main runner ───────────────────────────────────────────────────────────────

def run_poll() -> dict:
    """Poll all providers and upsert health records. Returns summary."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL / SUPABASE_KEY not set")
        return {'error': 'missing credentials'}

    now = datetime.now(timezone.utc).isoformat()
    results = {}

    for name, check_fn in PROVIDER_CHECKS.items():
        try:
            status, latency, error = check_fn()
        except Exception as e:
            status, latency, error = 'offline', 0, str(e)

        results[name] = {'status': status, 'latency_ms': latency, 'error': error}
        icon = '🟢' if status == 'online' else ('🟡' if status == 'degraded' else '🔴')
        logger.info("%s %s: %s (%dms)%s", icon, name, status, latency,
                    f" — {error}" if error else "")

        row = {
            'provider_name': name,
            'status': status,
            'latency_ms': latency,
            'last_checked_at': now,
            'error_detail': error,
            'updated_at': now,
        }

        if DRY_RUN:
            logger.info("[DRY_RUN] would upsert provider_health: %s → %s", name, status)
        else:
            _sb_upsert('provider_health', row, on_conflict='provider_name')

    online  = sum(1 for r in results.values() if r['status'] == 'online')
    offline = sum(1 for r in results.values() if r['status'] == 'offline')
    degraded = sum(1 for r in results.values() if r['status'] == 'degraded')

    summary = {
        'mode':     'dry_run' if DRY_RUN else 'live',
        'polled':   len(results),
        'online':   online,
        'offline':  offline,
        'degraded': degraded,
        'results':  results,
    }
    logger.info("Poll complete: %d online, %d offline, %d degraded", online, offline, degraded)
    return summary


if __name__ == '__main__':
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ',
    )
    result = run_poll()
    print(json.dumps(result, indent=2, default=str))
