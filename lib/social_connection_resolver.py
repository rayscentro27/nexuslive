"""social_connection_resolver.py — resolve existing Facebook/Instagram connection metadata.

The Nexus social automation queue/publisher originally only checked the env var
names FACEBOOK_PAGE_ID / INSTAGRAM_BUSINESS_ID / POSTIZ_*. The real, already-working
Meta connection (also used by content_employee/publisher.py) is stored in the
repo-root .env under different names:

    META_PAGE_ID
    META_PAGE_ACCESS_TOKEN
    META_INSTAGRAM_ACCOUNT_ID
    META_APP_ID / META_APP_SECRET

This resolver maps all known aliases to a single normalized view so the automation
can see the existing connection. It NEVER returns or logs raw token values — only
presence / length / a redacted preview.

Safe by default: resolve() does no network I/O. Pass check_network=True to perform a
read-only Graph API GET (page/account identity only — no mutations, no publishing).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# Alias groups — first present, non-empty, non-placeholder value wins.
# Project-native META_* names are listed first.
_PAGE_ID_ALIASES = ("META_PAGE_ID", "FACEBOOK_PAGE_ID", "FB_PAGE_ID")
_IG_ID_ALIASES = (
    "META_INSTAGRAM_ACCOUNT_ID",
    "INSTAGRAM_BUSINESS_ID",
    "INSTAGRAM_ACCOUNT_ID",
    "IG_BUSINESS_ID",
    "IG_USER_ID",
)
_PAGE_TOKEN_ALIASES = (
    "META_PAGE_ACCESS_TOKEN",
    "FACEBOOK_PAGE_ACCESS_TOKEN",
    "FB_PAGE_ACCESS_TOKEN",
    "FACEBOOK_ACCESS_TOKEN",
    "META_ACCESS_TOKEN",
)
_IG_TOKEN_ALIASES = ("INSTAGRAM_ACCESS_TOKEN",) + _PAGE_TOKEN_ALIASES
_POSTIZ_URL_ALIASES = ("POSTIZ_URL",)
_POSTIZ_KEY_ALIASES = ("POSTIZ_API_KEY",)

_PLACEHOLDERS = {"changeme", "placeholder", "todo", "replace_me", "none", "null"}

_dotenv_cache: dict[str, str] | None = None


def _load_dotenv() -> dict[str, str]:
    global _dotenv_cache
    if _dotenv_cache is not None:
        return _dotenv_cache
    data: dict[str, str] = {}
    for path in (ROOT / ".env", ROOT / ".env.example"):
        if not path.exists():
            continue
        try:
            for line in path.read_text(errors="ignore").splitlines():
                text = line.strip()
                if not text or text.startswith("#") or "=" not in text:
                    continue
                key, value = text.split("=", 1)
                key = key.replace("export ", "").strip()
                value = value.strip().strip('"').strip("'")
                # process env wins over .env; .env wins over .env.example
                data.setdefault(key, value)
        except Exception:
            continue
    _dotenv_cache = data
    return data


def _raw(name: str) -> tuple[str | None, str]:
    """Return (value, source) for a single env name. Process env wins over .env."""
    val = os.getenv(name)
    if val is not None:
        return val, "env"
    dotenv = _load_dotenv()
    if name in dotenv:
        return dotenv[name], ".env"
    return None, "not_found"


def _is_placeholder(value: str) -> bool:
    low = value.strip().lower()
    return low in _PLACEHOLDERS or "your_" in low or low.startswith("<")


def _resolve_alias(aliases: tuple[str, ...]) -> dict[str, Any]:
    """Find the first usable alias. Never returns the raw value."""
    for name in aliases:
        value, source = _raw(name)
        if value is None:
            continue
        text = value.strip()
        if not text or _is_placeholder(text):
            continue
        return {
            "present": True,
            "matched_alias": name,
            "source": source,
            "length": len(text),
            "preview": (text[:2] + "…") if len(text) > 4 else "…",
            "_value": text,  # internal only; callers must not surface this
        }
    return {"present": False, "matched_alias": None, "source": "not_found", "length": 0, "preview": None}


def _public(field: dict[str, Any]) -> dict[str, Any]:
    """Strip the internal raw value from a resolved field."""
    return {k: v for k, v in field.items() if k != "_value"}


def resolve(platform: str, *, check_network: bool = False) -> dict[str, Any]:
    """Resolve connection metadata for 'facebook' or 'instagram'.

    Never includes raw tokens. Returns the shape required by the social automation:
    platform, connection_source, account_connected, publishing_ready,
    page_id_present, ig_business_id_present, token_present, missing_fields,
    safe_status_summary (+ permission_check details when check_network=True).
    """
    platform = platform.lower().strip()
    page = _resolve_alias(_PAGE_ID_ALIASES)
    ig = _resolve_alias(_IG_ID_ALIASES)
    fb_token = _resolve_alias(_PAGE_TOKEN_ALIASES)
    ig_token = _resolve_alias(_IG_TOKEN_ALIASES)
    postiz_url = _resolve_alias(_POSTIZ_URL_ALIASES)
    postiz_key = _resolve_alias(_POSTIZ_KEY_ALIASES)

    if platform == "facebook":
        token = fb_token
        id_field = page
        id_label = "page_id"
    elif platform == "instagram":
        token = ig_token
        id_field = ig
        id_label = "instagram_business_id"
    else:
        raise ValueError(f"unsupported platform: {platform!r}")

    # Determine connection source.
    if id_field["present"] and token["present"]:
        connection_source = "env"  # repo-root .env / process env (META_* native or aliases)
    elif postiz_url["present"] and postiz_key["present"]:
        connection_source = "postiz"
    else:
        connection_source = "unknown"

    account_connected = "yes" if (id_field["present"] and token["present"]) else (
        "yes" if (platform == "instagram" and ig["present"] and fb_token["present"]) else "no"
    )

    missing_fields: list[str] = []
    if not id_field["present"]:
        missing_fields.append(id_label)
    if not token["present"]:
        missing_fields.append("access_token")

    publishing_ready = "yes" if not missing_fields else "no"

    permission_check: dict[str, Any] = {"done": "no", "ok": None, "detail": None, "identity": None}
    if check_network and id_field["present"] and token["present"]:
        permission_check = _network_identity_check(id_field["_value"], token["_value"], platform)
        if permission_check.get("ok") is False:
            publishing_ready = "no"
            account_connected = "unknown"
            gerr = permission_check.get("graph_error") or {}
            if gerr.get("code") == 190:
                # Token is structurally present but rejected by Meta (expired / invalid).
                missing_fields.append("valid_access_token (current token expired or invalid — re-auth needed)")
            else:
                missing_fields.append(f"network_check_failed ({permission_check.get('detail')})")

    summary = (
        f"{platform}: account_connected={account_connected}, publishing_ready={publishing_ready}, "
        f"source={connection_source}, {id_label}_present={'yes' if id_field['present'] else 'no'} "
        f"(alias={id_field['matched_alias']}), token_present={'yes' if token['present'] else 'no'} "
        f"(alias={token['matched_alias']}). Tokens not printed."
    )

    return {
        "platform": platform,
        "connection_source": connection_source,
        "account_connected": account_connected,
        "publishing_ready": publishing_ready,
        "page_id_present": "yes" if page["present"] else "no",
        "ig_business_id_present": "yes" if ig["present"] else "no",
        "id_present": "yes" if id_field["present"] else "no",
        "id_matched_alias": id_field["matched_alias"],
        "token_present": "yes" if token["present"] else "no",
        "token_matched_alias": token["matched_alias"],
        "token_not_printed": True,
        "missing_fields": missing_fields,
        "permission_check_done": permission_check["done"],
        "permission_check": permission_check,
        "blocker": ", ".join(f"{m} missing" for m in missing_fields) or None,
        "safe_status_summary": summary,
        "fields": {
            "page_id": _public(page),
            "instagram_business_id": _public(ig),
            "page_access_token": _public(fb_token),
            "instagram_access_token": _public(ig_token),
            "postiz_url": _public(postiz_url),
            "postiz_api_key": _public(postiz_key),
        },
    }


def resolve_all(*, check_network: bool = False) -> dict[str, Any]:
    return {
        "facebook": resolve("facebook", check_network=check_network),
        "instagram": resolve("instagram", check_network=check_network),
        "postiz_present": _resolve_alias(_POSTIZ_URL_ALIASES)["present"]
        and _resolve_alias(_POSTIZ_KEY_ALIASES)["present"],
    }


def _network_identity_check(node_id: str, token: str, platform: str) -> dict[str, Any]:
    """Read-only Graph API identity check. No mutations, no publishing.

    Performs a single GET on the page/IG node to confirm the token can read it.
    Never returns the token. On any error, returns ok=False with a redacted detail.
    """
    import json
    import ssl
    import urllib.parse
    import urllib.request

    # Use certifi's CA bundle if available — this Mac's default Python trust store is
    # incomplete (same reason the Telegram senders were patched to use certifi).
    try:
        import certifi

        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()

    fields = "id,name" if platform == "facebook" else "id,username"
    url = (
        f"https://graph.facebook.com/v19.0/{urllib.parse.quote(str(node_id))}"
        f"?fields={fields}&access_token={urllib.parse.quote(str(token))}"
    )
    def _redact(text: str) -> str:
        return (text or "").replace(token, "<redacted-token>")[:400]

    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "nexus-connector-status"})
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        identity = {k: payload.get(k) for k in ("id", "name", "username") if k in payload}
        return {"done": "yes", "ok": True, "detail": "read-only identity GET succeeded", "identity": identity}
    except urllib.error.HTTPError as exc:  # Graph API returned a structured error body
        graph_error: dict[str, Any] = {}
        try:
            body = json.loads(exc.read().decode("utf-8", errors="ignore"))
            err = body.get("error", {}) if isinstance(body, dict) else {}
            # Only surface non-secret diagnostic fields.
            graph_error = {
                "message": _redact(str(err.get("message", ""))),
                "type": err.get("type"),
                "code": err.get("code"),
                "error_subcode": err.get("error_subcode"),
            }
        except Exception:
            pass
        return {
            "done": "yes",
            "ok": False,
            "detail": _redact(f"HTTP {exc.code}: {exc.reason}"),
            "graph_error": graph_error,
            "identity": None,
        }
    except Exception as exc:  # network/SSL errors
        return {"done": "yes", "ok": False, "detail": _redact(str(exc)), "identity": None}
