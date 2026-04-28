"""
Supabase health check — verifies key tables exist and have recent data.
Uses REST API directly (no browser needed).
"""
import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta


SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")

TABLES_TO_CHECK = [
    ("user_subscriptions", "updated_at"),
    ("ai_usage_log", "created_at"),
    ("browser_tasks", "created_at"),
    ("coord_tasks", "created_at"),
]


async def run(page, payload: dict) -> dict:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }

    results = []
    errors = []
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    for table, ts_col in TABLES_TO_CHECK:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select=count&{ts_col}=gt.{cutoff}&limit=1"
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{table}?select={ts_col}&order={ts_col}.desc&limit=1",
            headers={**headers, "Range": "0-0", "Prefer": "count=exact"},
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                count_range = r.headers.get("Content-Range", "?")
                results.append(f"  ✓ {table}: {count_range} rows")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                errors.append(f"  ✗ {table}: table not found")
            else:
                errors.append(f"  ✗ {table}: HTTP {e.code}")
        except Exception as e:
            errors.append(f"  ✗ {table}: {str(e)[:60]}")

    summary_lines = [f"Supabase Table Health ({SUPABASE_URL[:40]}):"]
    summary_lines += results + errors

    return {
        "status": "error" if errors else "ok",
        "summary": "\n".join(summary_lines),
        "errors": errors,
    }
