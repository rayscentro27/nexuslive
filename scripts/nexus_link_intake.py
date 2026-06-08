#!/usr/bin/env python3
"""
nexus_link_intake.py — paste-a-link intake router (internal/free, draft-only).

Lets Ray drop any link and have Nexus file it on the right record:
  affiliate link  -> Revenue Hub campaign (affiliate_link, disclosure/review flagged)
  YouTube / source -> hand off to scripts/nexus_source_intake_router.py
  repo / tool link -> proposed knowledge_item (Tool Registry / Knowledge Graph review)
  landing page     -> campaign metadata (landing link, review flagged)
  unknown          -> proposed knowledge_item (review queue)

SAFETY: dry-run by default; --apply required for writes. Idempotent. Creates/updates
INTERNAL records only. Never publishes, sends, posts, activates links publicly, or
changes credentials. Affiliate links are stored but marked disclosure/review-required.

Usage:
  python3 scripts/nexus_link_intake.py --url "https://meetava.sjv.io/c/.../21836" --type affiliate --campaign Nav --apply
  python3 scripts/nexus_link_intake.py --url "https://youtube.com/watch?v=..." --type youtube_video --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DISCLOSURE = ("This content may include affiliate links. If you use a link, "
              "Nexus/GoClearOnline may earn a commission at no extra cost to you.")

CAMPAIGN_ALIASES = {
    "nav": "Nav", "business credit builder": "Business Credit Builder",
    "paydex": "Paydex Education", "legalzoom": "LegalZoom",
    "newsletter": "Newsletter Platform (Beehiiv TBD)", "beehiiv": "Newsletter Platform (Beehiiv TBD)",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sb_creds():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not (url and key):
        envf = ROOT / ".env"
        if envf.exists():
            for line in envf.read_text(errors="ignore").splitlines():
                if line.startswith("SUPABASE_URL=") and not url:
                    url = line.split("=", 1)[1].strip().strip('"')
                if line.startswith("SUPABASE_SERVICE_ROLE_KEY=") and not key:
                    key = line.split("=", 1)[1].strip().strip('"')
    return url, key


def sb(method, table, params=None, body=None):
    import requests
    url, key = sb_creds()
    if not (url and key):
        return None, "Supabase creds not found"
    h = {"apikey": key, "Authorization": f"Bearer {key}",
         "Content-Type": "application/json", "Prefer": "return=representation"}
    fn = getattr(requests, method)
    r = fn(f"{url}/rest/v1/{table}", headers=h, params=params,
           data=json.dumps(body) if body is not None else None, timeout=30)
    return r, None


def mask(url: str) -> str:
    m = re.match(r"(https?://[^/]+).*?(/[^/]*)?$", url)
    host = m.group(1) if m else url[:24]
    tail = url.rstrip("/").split("/")[-1]
    return f"{host}/.../{tail}"


def classify(url: str) -> str:
    u = url.lower()
    if any(d in u for d in ("sjv.io", "/aff", "affiliate", "ref=", "?ref", "impact.com", "partner")):
        return "affiliate"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube_video"
    if "github.com" in u:
        return "repo_link"
    return "unknown"


def resolve_campaign(name: str) -> str | None:
    if not name or name.lower() == "auto":
        return None
    return CAMPAIGN_ALIASES.get(name.lower(), name)


def main():
    ap = argparse.ArgumentParser(description="Nexus link intake router (dry-run by default)")
    ap.add_argument("--url", required=True)
    ap.add_argument("--type", default="auto",
                    choices=["auto", "affiliate", "landing_page", "youtube_video",
                             "youtube_channel", "source", "repo_link", "article_link", "unknown"])
    ap.add_argument("--campaign", default="auto")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    apply = args.apply and not args.dry_run
    ltype = args.type if args.type != "auto" else classify(args.url)
    campaign = resolve_campaign(args.campaign)
    print(f"Link: {mask(args.url)}")
    print(f"Type: {ltype}  Campaign: {campaign or '(auto/none)'}  Mode: {'APPLY' if apply else 'DRY-RUN'}")

    # ── affiliate / landing → Revenue Hub campaign ──
    if ltype in ("affiliate", "landing_page"):
        if not campaign:
            print("  ! affiliate/landing link needs --campaign; nothing written.")
            return
        field = "affiliate_link" if ltype == "affiliate" else "landing_page_url"
        if not apply:
            print(f"  would set {field} on campaign '{campaign}', mark disclosure_ok=false, "
                  f"compliance_ok=false, next_action=review+disclosure. (dry-run)")
            return
        r, err = sb("get", "nexus_os_revenue_campaigns",
                    params={"select": "id,program_name,affiliate_link",
                            "program_name": f"ilike.*{campaign}*", "archived": "eq.false"})
        if err or not r or r.status_code not in (200, 206) or not r.json():
            print(f"  ! campaign '{campaign}' not found ({err or (r.status_code if r else '?')})")
            return
        row = r.json()[0]
        if ltype == "affiliate" and row.get("affiliate_link") == args.url:
            print("  = already stored (idempotent, no change)")
            return
        upd = {field: args.url, "disclosure_ok": False, "compliance_ok": False,
               "next_action": f"Review disclosure and create approval-ready content using the {ltype.replace('_', ' ')}."}
        r2, _ = sb("patch", f"nexus_os_revenue_campaigns?id=eq.{row['id']}", body=upd)
        ok = r2 is not None and r2.status_code in (200, 204)
        print(f"  [{'OK' if ok else 'SKIP'}] stored {field} on {row['program_name']} (masked: {mask(args.url)}); disclosure/review flagged")
        print(f"  note: disclosure text to add — \"{DISCLOSURE}\"")
        return

    # ── youtube / source → hand off to the source intake router ──
    if ltype in ("youtube_video", "youtube_channel", "source", "article_link"):
        router = ROOT / "scripts" / "nexus_source_intake_router.py"
        flag = "--apply" if apply else "--dry-run"
        type_map = {"youtube_video": "youtube_video", "youtube_channel": "youtube_channel",
                    "article_link": "article_link", "source": "auto"}
        cmd = ["python3", str(router), "--input", args.url, "--type", type_map.get(ltype, "auto"), flag]
        if campaign:
            cmd += ["--campaign", campaign]
        print(f"  → delegating to source intake router: {' '.join(cmd[:6])} ...")
        try:
            out = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120)
            print((out.stdout or out.stderr)[-600:])
        except Exception as e:
            print(f"  ! router failed: {str(e)[:120]}")
        return

    # ── repo/tool/unknown → proposed knowledge_item (review queue) ──
    domain = "tooling" if ltype == "repo_link" else "research"
    title = f"[Proposed] Link intake: {mask(args.url)}"
    if not apply:
        print(f"  would create proposed knowledge_item (domain={domain}, status=proposed). (dry-run)")
        return
    r, err = sb("get", "knowledge_items", params={"select": "id", "source_url": f"eq.{args.url}"})
    if r and r.status_code in (200, 206) and r.json():
        print("  = already in knowledge_items (idempotent, no change)")
        return
    body = [{"domain": domain, "title": title, "content": f"Link submitted for review: {args.url}",
             "source_url": args.url, "source_type": ltype, "status": "proposed", "dry_run": False,
             "metadata": {"intake": "nexus_link_intake", "campaign": campaign}}]
    r2, _ = sb("post", "knowledge_items", body=body)
    ok = r2 is not None and r2.status_code in (200, 201)
    print(f"  [{'OK' if ok else 'SKIP'}] proposed knowledge_item created for review")


if __name__ == "__main__":
    main()
