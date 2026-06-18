#!/usr/bin/env python3
"""facebook_token_status.py — safely report the Meta token's type, validity, expiry,
and scopes via the read-only Graph debug_token endpoint. NEVER prints the token.

Why this exists: tokens created in the Graph API Explorer look fine in Meta's UI but are
often SHORT-LIVED (expire in ~1-2 hours). This tool shows the real expiry + type so token
problems are obvious before a publish fails. For durable publishing you want a LONG-LIVED
*Page* token (type=PAGE, expires_at=0) with pages_manage_posts + pages_read_engagement.

Usage:
    python3 scripts/facebook_token_status.py            # human summary
    python3 scripts/facebook_token_status.py --json     # machine-readable (no token)
    python3 scripts/facebook_token_status.py --report   # also write safe readiness report
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _ctx():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _env() -> dict[str, str]:
    env: dict[str, str] = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(errors="ignore").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def status() -> dict:
    env = _env()
    tok = env.get("META_PAGE_ACCESS_TOKEN", "")
    app_id = env.get("META_APP_ID", "")
    secret = env.get("META_APP_SECRET", "")
    out: dict = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "token_present": bool(tok),
        "token_not_printed": True,
        "type": None, "is_valid": None, "expires_at": None, "expires_human": None,
        "hours_remaining": None, "is_long_lived": None,
        "profile_id": None, "has_publish_scopes": None, "scopes_present": [], "blocker": None,
    }
    if not tok:
        out["blocker"] = "META_PAGE_ACCESS_TOKEN not set in .env"
        return out
    if not (app_id and secret):
        out["blocker"] = "META_APP_ID / META_APP_SECRET missing — cannot call debug_token"
        return out
    app_token = f"{app_id}|{secret}"
    url = (
        "https://graph.facebook.com/v19.0/debug_token?input_token="
        + urllib.parse.quote(tok) + "&access_token=" + urllib.parse.quote(app_token)
    )
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=15, context=_ctx()) as r:
            d = json.loads(r.read()).get("data", {})
    except Exception as exc:
        msg = str(exc)
        for s in (tok, secret):
            if s:
                msg = msg.replace(s, "<redacted>")
        out["blocker"] = f"debug_token failed: {msg[:200]}"
        return out

    exp = d.get("expires_at")
    scopes = d.get("scopes", []) or []
    out["type"] = d.get("type")
    out["is_valid"] = d.get("is_valid")
    out["expires_at"] = exp
    out["profile_id"] = d.get("profile_id")
    out["scopes_present"] = [s for s in ("pages_manage_posts", "pages_read_engagement", "instagram_content_publish") if s in scopes]
    out["has_publish_scopes"] = "pages_manage_posts" in scopes and "pages_read_engagement" in scopes
    if exp in (0, None):
        out["expires_human"] = "never (long-lived)"
        out["is_long_lived"] = True
        out["hours_remaining"] = None
    else:
        dt = datetime.fromtimestamp(exp, timezone.utc)
        out["expires_human"] = dt.isoformat()
        hrs = (dt - datetime.now(timezone.utc)).total_seconds() / 3600
        out["hours_remaining"] = round(hrs, 2)
        out["is_long_lived"] = hrs > 24
        if hrs < 24:
            out["blocker"] = f"token is SHORT-LIVED (~{round(hrs,1)}h left) — exchange for a long-lived Page token"
    if d.get("is_valid") is False:
        out["blocker"] = "token invalid/expired"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Report Meta token status safely (never prints the token).")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    st = status()
    if args.report:
        rd = ROOT / "reports" / "social"
        rd.mkdir(parents=True, exist_ok=True)
        (rd / "facebook_token_readiness_latest.json").write_text(json.dumps(st, indent=2) + "\n")
    if args.json:
        print(json.dumps(st, indent=2))
    else:
        print(f"token_present={st['token_present']} type={st['type']} valid={st['is_valid']} "
              f"long_lived={st['is_long_lived']} expires={st['expires_human']} "
              f"publish_scopes={st['has_publish_scopes']} page={st['profile_id']}")
        if st["blocker"]:
            print(f"BLOCKER: {st['blocker']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
