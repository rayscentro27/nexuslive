#!/usr/bin/env python3
"""
Shared helpers for Nexus prelaunch testing/admin scripts.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from lib.env_loader import load_nexus_env

load_nexus_env()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_truthy(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def default_test_mode() -> bool:
    return is_truthy(os.getenv("TEST_MODE"), default=True)


@dataclass
class SupabaseConfig:
    url: str
    key: str

    @property
    def rest_base(self) -> str:
        return f"{self.url.rstrip('/')}/rest/v1"

    @property
    def auth_admin_base(self) -> str:
        return f"{self.url.rstrip('/')}/auth/v1/admin"


def get_supabase_config() -> SupabaseConfig:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()
    if not url or not key:
        raise RuntimeError("Supabase not configured")
    return SupabaseConfig(url=url, key=key)


def supabase_request(
    path: str,
    *,
    method: str = "GET",
    body: Optional[dict] = None,
    prefer: Optional[str] = None,
    timeout: int = 10,
    auth_admin: bool = False,
) -> tuple[Any, dict]:
    cfg = get_supabase_config()
    base = cfg.auth_admin_base if auth_admin else cfg.rest_base
    headers = {
        "apikey": cfg.key,
        "Authorization": f"Bearer {cfg.key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{base}/{path.lstrip('/')}", data=data, headers=headers, method=method.upper())
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode()
        payload = json.loads(raw) if raw else None
        return payload, dict(response.headers.items())


def rest_select(path: str, *, timeout: int = 10) -> Any:
    payload, _ = supabase_request(path, timeout=timeout)
    return payload


def table_exists(table: str) -> bool:
    try:
        supabase_request(f"{table}?select=*&limit=0", timeout=8)
        return True
    except Exception:
        return False


def auth_users(email: str = "", per_page: int = 200) -> list[dict]:
    query = f"users?per_page={per_page}"
    payload, _ = supabase_request(query, auth_admin=True, timeout=10)
    users = (payload or {}).get("users", [])
    if email:
        email_l = email.strip().lower()
        users = [user for user in users if (user.get("email") or "").lower() == email_l]
    return users


def user_profiles(limit: int = 20) -> list[dict]:
    rows = rest_select(f"user_profiles?select=*&order=created_at.desc&limit={limit}", timeout=10) or []
    return rows


def combined_users(limit: int = 20, email: str = "") -> list[dict]:
    profiles = user_profiles(limit=max(limit, 50))
    profile_by_id = {row.get("id"): row for row in profiles if row.get("id")}
    users = auth_users(email=email, per_page=max(limit, 200))
    combined = []
    for user in users:
        user_id = user.get("id")
        profile = profile_by_id.get(user_id, {})
        combined.append({
            "id": user_id,
            "email": user.get("email"),
            "full_name": profile.get("full_name") or user.get("user_metadata", {}).get("full_name") or "",
            "role": profile.get("role"),
            "subscription_plan": profile.get("subscription_plan"),
            "onboarding_complete": profile.get("onboarding_complete"),
            "profile_exists": bool(profile),
            "created_at": user.get("created_at"),
        })
    combined.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return combined[:limit]


def latest_row(table: str, filter_query: str = "", select: str = "*") -> Optional[dict]:
    glue = "&" if filter_query else ""
    rows = rest_select(f"{table}?select={select}{glue}{filter_query}&order=created_at.desc&limit=1", timeout=10) or []
    return rows[0] if rows else None


def count_rows(table: str, filter_query: str = "") -> int:
    glue = "&" if filter_query else ""
    _, headers = supabase_request(
        f"{table}?select=*{glue}{filter_query}&limit=1",
        prefer="count=exact",
        timeout=10,
    )
    content_range = headers.get("Content-Range", "")
    if "/" in content_range:
        try:
            return int(content_range.split("/")[-1])
        except ValueError:
            return 0
    return 0


def count_by(table: str, column: str, limit: int = 500) -> dict[str, int]:
    rows = rest_select(f"{table}?select={urllib.parse.quote(column)}&limit={limit}", timeout=10) or []
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(column)
        key = str(value if value is not None else "null")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def probe_port(host: str, port: int, timeout: float = 1.5) -> bool:
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def run_command(command: list[str] | str, timeout: int = 10) -> tuple[int, str, str]:
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=isinstance(command, str),
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def list_launchd(pattern: str = "nexus|hermes|email|telegram|scheduler|orchestrator") -> list[str]:
    code, out, _ = run_command(["bash", "-lc", f"launchctl list | rg '{pattern}'"], timeout=10)
    if code != 0 or not out:
        return []
    return [line for line in out.splitlines() if line.strip()]


def pgrep_lines(pattern: str) -> list[str]:
    code, out, _ = run_command(["bash", "-lc", f"pgrep -a -f \"{pattern}\""], timeout=10)
    if code != 0 or not out:
        return []
    return [line for line in out.splitlines() if line.strip()]


def build_tester_email(name: str, login_link: str, membership_level: str, note: str = "") -> dict[str, str]:
    from lib.compliance_disclaimers import long_compliance_disclaimer

    friendly_name = name or "Tester"
    membership = membership_level or "admin_test"
    website_url = os.getenv("NEXUS_WEBSITE_URL", "https://nexus.goclearonline.com").strip()
    disclaimer = long_compliance_disclaimer()
    body_lines = [
        "Welcome to Nexus,",
        "",
        "You’ve been invited to join the Nexus Beta Program.",
        "",
        "Nexus is an AI-powered business readiness and operational platform designed to help entrepreneurs organize and improve:",
        "",
        "• Business funding readiness",
        "• Credit and business profile setup",
        "• Funding roadmaps and recommendations",
        "• Grants and opportunities",
        "• AI-guided operational support",
        "• Business growth organization and insights",
        "",
        "As a beta tester, you will receive early access to the platform and help shape future improvements before public launch.",
        "",
        "━━━━━━━━━━━━━━━",
        "WHAT YOU’LL NEED TO SIGN UP",
        "━━━━━━━━━━━━━━━",
        "",
        "• Your email address",
        "• A secure password",
        "• Basic business information, optional but recommended",
        "",
        "Depending on the features you test, Nexus may also later allow you to add:",
        "",
        "• Business details",
        "• Funding readiness information",
        "• Credit-related insights",
        "• Goals and operational priorities",
        "",
        "━━━━━━━━━━━━━━━",
        "GET STARTED",
        "━━━━━━━━━━━━━━━",
        "",
        f"Create your account here:\n\n{login_link}",
        "",
        "Once your account is created, you’ll be able to log in to the Nexus Dashboard and begin exploring the platform.",
        "",
        "━━━━━━━━━━━━━━━",
        "MOBILE ACCESS",
        "━━━━━━━━━━━━━━━",
        "",
        "• Install the Nexus app on your iPhone or Android device",
        "• Add Nexus to your home screen for quick access",
        "• Receive future mobile-ready updates and improvements",
        "",
        "━━━━━━━━━━━━━━━",
        "BETA ACCESS DETAILS",
        "━━━━━━━━━━━━━━━",
        "",
        f"Your beta access has been enabled with a waived subscription during the testing period ({membership}).",
        "",
        "━━━━━━━━━━━━━━━",
        "IMPORTANT DISCLAIMER",
        "━━━━━━━━━━━━━━━",
        "",
        disclaimer,
        "",
        "━━━━━━━━━━━━━━━",
        "QUESTIONS OR SUPPORT?",
        "━━━━━━━━━━━━━━━",
        "",
        "If you have any questions during onboarding or testing, simply reply to this email.",
        "",
        "Welcome to Nexus.",
        "— The Nexus Team",
        website_url,
    ]
    if note:
        body_lines.extend(["", f"Admin note: {note}"])
    return {
        "subject": "You’ve Been Invited to Join Nexus Beta",
        "body": "\n".join(body_lines),
    }
