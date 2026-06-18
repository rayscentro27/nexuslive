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


def _graph_get(path: str, params: dict) -> dict:
    """Read-only Graph GET. Returns parsed JSON (may contain an 'error' key)."""
    url = "https://graph.facebook.com/v19.0/" + path.lstrip("/") + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=20, context=_ctx()) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8", errors="ignore"))
        except Exception:
            return {"error": {"message": f"HTTP {exc.code}", "code": exc.code}}
    except Exception as exc:
        return {"error": {"message": str(exc)[:200]}}


def _redact(text: str, *secrets: str) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "<redacted>")
    return text


def _write_page_token(path: Path, token: str) -> bool:
    """Replace only the META_PAGE_ACCESS_TOKEN= line, preserving the rest. No printing."""
    if not path.exists():
        return False
    lines = path.read_text(errors="ignore").splitlines()
    found = False
    for i, l in enumerate(lines):
        if l.startswith("META_PAGE_ACCESS_TOKEN="):
            lines[i] = f"META_PAGE_ACCESS_TOKEN={token}"
            found = True
            break
    if not found:
        lines.append(f"META_PAGE_ACCESS_TOKEN={token}")
    path.write_text("\n".join(lines) + "\n")
    return True


def _token_meta(token: str, app_token: str) -> dict:
    """debug_token a token; return safe fields only (type/valid/expiry/scopes/profile_id)."""
    d = _graph_get("debug_token", {"input_token": token, "access_token": app_token}).get("data", {})
    exp = d.get("expires_at")
    return {
        "type": d.get("type"), "is_valid": d.get("is_valid"), "expires_at": exp,
        "scopes": d.get("scopes", []) or [], "profile_id": d.get("profile_id"),
        "long_lived": (exp in (0, None)) or (isinstance(exp, int) and (exp - datetime.now(timezone.utc).timestamp()) > 86400),
    }


def exchange(user_token: str, *, target_page_id: str = "", target_page_name: str = "",
             write_local: bool = False, write_worker: bool = False, dry_run: bool = False) -> dict:
    """Exchange a USER token → long-lived user token → Page token; optionally write to .env.
    Never returns or prints raw tokens."""
    env = _env()
    app_id, secret = env.get("META_APP_ID", ""), env.get("META_APP_SECRET", "")
    target_page_id = target_page_id or env.get("META_PAGE_ID", "")
    app_token = f"{app_id}|{secret}"
    out: dict = {
        "mode": "exchange", "checked_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run, "token_not_printed": True,
        "user_token_present": bool(user_token), "user_token_exchanged": False,
        "page_found": False, "page_id": None, "page_name": None,
        "page_token_written_local": False, "page_token_written_worker": False,
        "page_token_type": None, "expires_at": None, "long_lived_or_non_expiring": "unknown",
        "publish_scopes": None, "instagram_resolved": None, "blocker": None,
    }
    if not user_token:
        out["blocker"] = "no USER token provided (use --user-token-env or --user-token-stdin)"
        return out
    if not (app_id and secret):
        out["blocker"] = "META_APP_ID / META_APP_SECRET missing in .env"
        return out

    # 1) inspect input token type (best-effort)
    in_meta = _token_meta(user_token, app_token)
    if in_meta.get("type") == "PAGE":
        out["blocker"] = "input token is a PAGE token; --exchange requires a USER token"
        return out

    # 2) exchange for a long-lived user token (idempotent if already long-lived)
    ex = _graph_get("oauth/access_token", {
        "grant_type": "fb_exchange_token", "client_id": app_id,
        "client_secret": secret, "fb_exchange_token": user_token,
    })
    if ex.get("error"):
        out["blocker"] = "user-token exchange failed: " + _redact(str(ex["error"].get("message")), user_token, secret)
        return out
    ll_user = ex.get("access_token") or user_token
    out["user_token_exchanged"] = bool(ex.get("access_token"))

    # 3) /me/accounts → find target page
    accts = _graph_get("me/accounts", {"fields": "id,name,access_token,tasks", "access_token": ll_user})
    if accts.get("error"):
        out["blocker"] = "/me/accounts failed: " + _redact(str(accts["error"].get("message")), ll_user, user_token)
        return out
    pages = accts.get("data", []) or []
    page = None
    if target_page_id:
        page = next((p for p in pages if p.get("id") == target_page_id), None)
    if not page and target_page_name:
        page = next((p for p in pages if (p.get("name") or "").lower() == target_page_name.lower()), None)
    if not page:
        out["blocker"] = f"target page not found in /me/accounts (have {len(pages)} page(s)); pass --target-page-id/name"
        return out
    out["page_found"], out["page_id"], out["page_name"] = True, page.get("id"), page.get("name")
    page_token = page.get("access_token", "")
    if not page_token:
        out["blocker"] = "page found but no access_token returned (missing pages_show_list/manage scope on user token)"
        return out

    # 4) verify page token
    pmeta = _token_meta(page_token, app_token)
    scopes = pmeta.get("scopes", [])
    out["page_token_type"] = pmeta.get("type")
    out["expires_at"] = pmeta.get("expires_at")
    out["long_lived_or_non_expiring"] = "non-expiring" if pmeta.get("expires_at") in (0, None) else ("long-lived" if pmeta.get("long_lived") else "short-lived")
    out["publish_scopes"] = ("pages_manage_posts" in scopes) and ("pages_read_engagement" in scopes)
    ident = _graph_get(str(page.get("id")), {"fields": "id,name", "access_token": page_token})
    if ident.get("error"):
        out["blocker"] = "page identity verify failed: " + _redact(str(ident["error"].get("message")), page_token)
        return out
    ig_id = env.get("META_INSTAGRAM_ACCOUNT_ID", "")
    if ig_id:
        ig = _graph_get(ig_id, {"fields": "id,username", "access_token": page_token})
        out["instagram_resolved"] = not bool(ig.get("error"))

    # 5) write env (only if requested and not dry-run)
    if dry_run:
        out["note"] = "dry-run: env files NOT modified. Would write META_PAGE_ACCESS_TOKEN to: " + \
            ", ".join([p for p, w in [("~/nexus-ai/.env", write_local), ("~/nexus-ai-worker/.env", write_worker)] if w]) or "(no --write target)"
        return out
    if write_local:
        out["page_token_written_local"] = _write_page_token(Path.home() / "nexus-ai" / ".env", page_token)
    if write_worker:
        out["page_token_written_worker"] = _write_page_token(Path.home() / "nexus-ai-worker" / ".env", page_token)
    # never keep the token in memory longer than needed
    page_token = ""  # noqa: F841
    return out


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


def _read_user_token(args) -> str:
    """Get the USER token from an env var or hidden stdin. Never echoed."""
    if args.user_token_env:
        import os
        return (os.environ.get(args.user_token_env, "") or "").strip()
    if args.user_token_stdin:
        import getpass
        try:
            return getpass.getpass("Paste USER access token (hidden): ").strip()
        except Exception:
            return sys.stdin.readline().strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Report/exchange Meta token status safely (never prints the token).")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--exchange", action="store_true", help="exchange a USER token → long-lived Page token")
    ap.add_argument("--user-token-env", metavar="VARNAME", help="env var holding the USER token")
    ap.add_argument("--user-token-stdin", action="store_true", help="read USER token from hidden stdin prompt")
    ap.add_argument("--target-page-id", default="")
    ap.add_argument("--target-page-name", default="")
    ap.add_argument("--write-local-env", action="store_true", help="write Page token to ~/nexus-ai/.env")
    ap.add_argument("--write-worker-env", action="store_true", help="write Page token to ~/nexus-ai-worker/.env")
    ap.add_argument("--dry-run", action="store_true", help="exchange: do everything except write env files")
    args = ap.parse_args()

    if args.exchange:
        user_token = _read_user_token(args)
        ex = exchange(
            user_token,
            target_page_id=args.target_page_id, target_page_name=args.target_page_name,
            write_local=args.write_local_env, write_worker=args.write_worker_env,
            dry_run=args.dry_run,
        )
        if args.json:
            print(json.dumps(ex, indent=2))
        else:
            print(f"exchange dry_run={ex['dry_run']} user_token_present={ex['user_token_present']} "
                  f"exchanged={ex['user_token_exchanged']} page_found={ex['page_found']} "
                  f"page={ex['page_name']}({ex['page_id']}) type={ex['page_token_type']} "
                  f"expiry={ex['long_lived_or_non_expiring']} publish_scopes={ex['publish_scopes']} "
                  f"wrote_local={ex['page_token_written_local']} wrote_worker={ex['page_token_written_worker']}")
            if ex.get("blocker"):
                print(f"BLOCKER: {ex['blocker']}")
        return 0 if not ex.get("blocker") else 1

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
