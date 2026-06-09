#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import ssl
import sys
from pathlib import Path
from urllib import error
from urllib import parse, request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.trading_safety_gate import seed_safe_trading_env_from_launch_agent


REQUIRED_ENV = ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY")
OUTPUT_JSON = ROOT / "logs" / "supabase_connectivity_latest.json"


def _env_presence() -> dict[str, bool]:
    return {name: bool(os.getenv(name)) for name in REQUIRED_ENV}


def _host_from_url(url: str) -> str:
    try:
        return parse.urlparse(url).hostname or ""
    except Exception:
        return ""


def _dns_check(host: str) -> tuple[bool, str | None]:
    if not host:
        return False, "missing_host"
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return True, None
    except Exception as exc:
        return False, str(exc)


def _ssl_context():
    cert_file = os.getenv("SSL_CERT_FILE", "")
    if not cert_file:
        try:
            import certifi
            cert_file = certifi.where()
        except Exception:
            cert_file = ""
    if cert_file:
        return ssl.create_default_context(cafile=cert_file)
    return None


def _https_check(url: str, key: str) -> tuple[bool, str | None]:
    if not url or not key:
        return False, "missing_url_or_key"
    try:
        req = request.Request(
            f"{url.rstrip('/')}/rest/v1/",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with request.urlopen(req, timeout=10, context=_ssl_context()) as resp:
            resp.read(256)
        return True, None
    except error.HTTPError as exc:
        if exc.code in {200, 401, 403}:
            return True, f"HTTP {exc.code}"
        return False, str(exc)
    except Exception as exc:
        return False, str(exc)


def _table_query_check(url: str, key: str) -> tuple[bool, str | None]:
    if not url or not key:
        return False, "missing_url_or_key"
    try:
        req = request.Request(
            f"{url.rstrip('/')}/rest/v1/reviewed_signal_proposals?select=id&limit=1",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with request.urlopen(req, timeout=10, context=_ssl_context()) as resp:
            resp.read(256)
        return True, None
    except Exception as exc:
        return False, str(exc)


def _client_import() -> tuple[bool, str | None]:
    try:
        import supabase  # type: ignore  # noqa: F401
        return True, None
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    seed_safe_trading_env_from_launch_agent()
    presence = _env_presence()
    url = os.getenv("SUPABASE_URL", "")
    host = _host_from_url(url)
    dns_ok, dns_error = _dns_check(host)
    https_ok, https_error = _https_check(url, os.getenv("SUPABASE_KEY", ""))
    query_ok, query_error = _table_query_check(url, os.getenv("SUPABASE_KEY", ""))
    client_ok, client_error = _client_import()
    env_ok = all(presence.values())
    blocker = None
    if not env_ok:
        blocker = "missing_env"
    elif not url.startswith("https://"):
        blocker = "invalid_url_format"
    elif not dns_ok:
        blocker = "dns_resolution_failed"
    elif not https_ok:
        blocker = "https_reachability_failed"
    elif not query_ok:
        blocker = "table_query_failed"
    payload = {
        "env_names_present": presence,
        "url_host": host or None,
        "dns_resolution_ok": dns_ok,
        "https_reachable": https_ok,
        "supabase_client_import_ok": client_ok,
        "table_query_dry_run_ok": query_ok,
        "blocker_category": blocker,
        "details": {
            "dns_error": dns_error,
            "https_error": https_error,
            "client_import_error": client_error,
            "table_query_error": query_error,
        },
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0 if blocker is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
