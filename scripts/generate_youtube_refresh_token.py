#!/usr/bin/env python3
"""
generate_youtube_refresh_token.py — local-only YouTube OAuth refresh-token helper.

Runs the OAuth **Desktop** consent flow once on Ray's machine and prints the
resulting refresh token so it can be pasted into local .env as YOUTUBE_REFRESH_TOKEN.

It does NOT upload, post, schedule, or call any YouTube content API. It only
performs the OAuth authorization step to mint a refresh token.

Scope requested (upload only):
    https://www.googleapis.com/auth/youtube.upload

SAFETY:
  * Reads YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET from local .env only.
  * Never prints the client secret (only whether it is present).
  * Prints the refresh token exactly once at the very end (Ray copies it).
  * Writes no token/cache files by default; if any are written they are gitignored.
  * No upload/post/schedule. Executor is untouched and stays disabled.

Requires: google-auth-oauthlib  (install into a LOCAL venv only, with approval:
    python3 -m venv .venv-yt && . .venv-yt/bin/activate && pip install google-auth-oauthlib)

Usage (on Ray's machine, in a browser-capable session):
    python3 scripts/generate_youtube_refresh_token.py
    # or headless/manual:
    python3 scripts/generate_youtube_refresh_token.py --console
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def load_env_value(name: str) -> str | None:
    """Read a single var from process env or local .env (value not returned to logs)."""
    if os.environ.get(name):
        return os.environ[name]
    envf = ROOT / ".env"
    if envf.exists():
        for line in envf.read_text(errors="ignore").splitlines():
            m = re.match(rf"^{re.escape(name)}=(.*)$", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a YouTube upload refresh token (local OAuth, no posting)")
    ap.add_argument("--console", action="store_true",
                    help="Use console/manual flow instead of opening a local browser server")
    ap.add_argument("--port", type=int, default=8765, help="Local redirect port for the browser flow")
    args = ap.parse_args()

    client_id = load_env_value("YOUTUBE_CLIENT_ID")
    client_secret = load_env_value("YOUTUBE_CLIENT_SECRET")

    print("=== YouTube refresh-token helper (local OAuth only — no upload/post) ===")
    print(f"YOUTUBE_CLIENT_ID present:     {'yes' if client_id else 'NO'}")
    print(f"YOUTUBE_CLIENT_SECRET present: {'yes' if client_secret else 'NO'}")  # never prints the secret itself
    if not (client_id and client_secret):
        print("\n! Missing client id/secret in .env. Add YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET first.")
        return 2

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except Exception:
        print("\n! google-auth-oauthlib is not installed.")
        print("  Install locally (with approval), e.g.:")
        print("    python3 -m venv .venv-yt && . .venv-yt/bin/activate && pip install google-auth-oauthlib")
        print("  Then re-run this script.")
        return 3

    # Desktop ("installed") client config built from env — no client_secret.json on disk.
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

    try:
        if args.console:
            # Manual flow: prints a URL, you paste the code back. Good for headless.
            creds = flow.run_console()  # available in older google-auth-oauthlib
        else:
            # Opens a local browser + temporary redirect server.
            creds = flow.run_local_server(port=args.port, prompt="consent", access_type="offline")
    except AttributeError:
        # Newer libs removed run_console; fall back to local server.
        creds = flow.run_local_server(port=args.port, prompt="consent", access_type="offline")
    except Exception as e:
        print(f"\n! OAuth flow failed: {str(e)[:200]}")
        print("  Tip: ensure this OAuth client is type 'Desktop app' and you're a test user on the consent screen.")
        return 4

    refresh = getattr(creds, "refresh_token", None)
    if not refresh:
        print("\n! No refresh token returned. Re-run and ensure you grant consent (try --console, "
              "or revoke prior access so Google issues a new refresh token).")
        return 5

    print("\n✅ Refresh token generated. Add this line to your LOCAL .env (do NOT commit it):\n")
    print(f"YOUTUBE_REFRESH_TOKEN={refresh}")
    print("\nNext: paste that into .env, then run the publisher dry-run to confirm 6/6 readiness.")
    print("Nothing was uploaded, posted, or scheduled. The executor remains disabled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
