#!/usr/bin/env python3
"""
Syncs new nexuslive signups from Supabase into the lead scoring engine.
Runs as part of the daily lead check — pulls users who signed up in the last 24h
and adds them as leads if not already tracked.
"""
import os
import json
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger("SupabaseLeadSync")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ygqglfbhxiumqdisauar.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SEEN_FILE = Path(__file__).parent / "synced_user_ids.json"


def _load_seen() -> set:
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text()))
        except Exception:
            pass
    return set()


def _save_seen(seen: set):
    SEEN_FILE.write_text(json.dumps(list(seen), indent=2))


def sync_new_signups(hours_back: int = 24) -> list:
    """Pull new Supabase auth users from the last N hours and add them as leads."""
    if not SUPABASE_SERVICE_KEY:
        logger.warning("SUPABASE_SERVICE_ROLE_KEY not set — skipping signup sync")
        return []

    since = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Query auth.users via Supabase admin API
    cmd = [
        "curl", "-s",
        f"{SUPABASE_URL}/auth/v1/admin/users",
        "-H", f"apikey: {SUPABASE_SERVICE_KEY}",
        "-H", f"Authorization: Bearer {SUPABASE_SERVICE_KEY}",
        "-G", "--data-urlencode", f"created_after={since}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        logger.error(f"Supabase query failed: {result.stderr[:200]}")
        return []

    try:
        data = json.loads(result.stdout)
    except Exception as e:
        logger.error(f"Failed to parse Supabase response: {e}")
        return []

    users = data.get("users", [])
    seen = _load_seen()
    new_leads = []

    from lead_intelligence.lead_scoring_engine import add_lead

    for user in users:
        uid = user.get("id", "")
        if uid in seen:
            continue

        email = user.get("email", "")
        meta = user.get("user_metadata", {})
        name = meta.get("full_name") or meta.get("name") or email.split("@")[0] or "Unknown"
        created = user.get("created_at", "")[:10]

        # Determine source from app_metadata if available
        source = meta.get("source", "nexuslive_signup")

        lead = add_lead(
            name=name,
            email=email,
            source=source,
            interest="business funding",
            message=f"Signed up on nexuslive.netlify.app on {created}",
        )
        seen.add(uid)
        new_leads.append(lead)
        logger.info(f"Added lead from signup: {name} ({email}) score={lead['score']}")

    _save_seen(seen)
    return new_leads
