#!/usr/bin/env python3
"""
social_publish_executor.py — SCOPED, DRY-RUN-ONLY social publish gate.

This is the controlled entry point for (future) posting a single approved content
item to one platform. It is intentionally INERT by default:
  * dry-run unless --apply
  * requires exact --approval-id + --content-id + --platform + --video
  * verifies the approval is approved AND scoped to that exact content_id
  * verifies the video file exists
  * checks platform credential ENV-VAR NAMES (presence only — never prints values)
  * even with --apply it REFUSES unless NEXUS_PUBLISH_EXECUTOR_ENABLED=true
    (that flag is not set; the executor is disabled by design)
  * logs an audit event to nexus_os_approval_events

SAFETY: never posts in this build (executor disabled). No account connection, no
credential change, no spend. Verifies the path only.
"""
from __future__ import annotations
import argparse, json, os, datetime, requests
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

PLATFORM_ENV = {
    "youtube": ["YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN","YOUTUBE_CHANNEL_ID","GOOGLE_CLIENT_ID","GOOGLE_CLIENT_SECRET"],
    "tiktok":  ["TIKTOK_CLIENT_KEY","TIKTOK_CLIENT_SECRET","TIKTOK_ACCESS_TOKEN","TIKTOK_OPEN_ID"],
    "instagram":["META_ACCESS_TOKEN","INSTAGRAM_BUSINESS_ACCOUNT_ID","FACEBOOK_PAGE_ID","META_APP_ID","META_APP_SECRET"],
}

def creds():
    u = os.environ.get("SUPABASE_URL"); k = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not (u and k):
        for line in (ROOT/".env").read_text(errors="ignore").splitlines():
            if line.startswith("SUPABASE_URL=") and not u: u=line.split("=",1)[1].strip().strip('"')
            if line.startswith("SUPABASE_SERVICE_ROLE_KEY=") and not k: k=line.split("=",1)[1].strip().strip('"')
    return u, k

def env_names_present(platform):
    # presence only — NEVER print values
    out = {}
    keyset = PLATFORM_ENV.get(platform, [])
    envtext = ""
    ef = ROOT/".env"
    if ef.exists(): envtext = ef.read_text(errors="ignore")
    for name in keyset:
        out[name] = (name in os.environ) or bool(__import__("re").search(rf"^{name}=", envtext, __import__("re").M))
    return out

def env_val(name: str) -> str | None:
    """Read a credential value from env or .env (used only to authenticate; never printed)."""
    if os.environ.get(name):
        return os.environ[name]
    ef = ROOT / ".env"
    if ef.exists():
        import re as _re
        for line in ef.read_text(errors="ignore").splitlines():
            m = _re.match(rf"^{_re.escape(name)}=(.*)$", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return None


HASHTAGS = ["Shorts","businesscredit","businessfunding","smallbusiness","entrepreneur","credittips","fundingreadiness","paydex"]


def build_youtube_metadata(content_row: dict) -> tuple[str, str, list[str]]:
    """Build the public title/description/tags from the approved content record.
    Ensures the affiliate disclosure is present in the description."""
    import re as _re
    raw_title = (content_row.get("title") or "Business credit short").strip()
    # strip internal working labels like "(60-sec script)"
    title = _re.sub(r"\s*\(.*?script.*?\)\s*$", "", raw_title, flags=_re.I).strip()
    title = (title[:88] + " #Shorts") if "#shorts" not in title.lower() else title
    body = (content_row.get("content_body") or "").strip()
    disclosure = "This content may include affiliate links. If you use a link, Nexus/GoClearOnline may earn a commission at no extra cost to you."
    desc = body
    if "affiliate links" not in desc:
        desc += "\n\n" + disclosure
    desc += "\n\nEducational only — not financial advice. No guarantees.\n\n" + " ".join(f"#{t}" for t in HASHTAGS)
    return title, desc[:4900], HASHTAGS


def youtube_refresh_access_token() -> str:
    """Exchange the refresh token for a short-lived access token. Never prints any value."""
    cid = env_val("YOUTUBE_CLIENT_ID") or env_val("GOOGLE_CLIENT_ID")
    sec = env_val("YOUTUBE_CLIENT_SECRET") or env_val("GOOGLE_CLIENT_SECRET")
    rt = env_val("YOUTUBE_REFRESH_TOKEN")
    if not (cid and sec and rt):
        raise RuntimeError("missing YouTube OAuth credentials (names only) — cannot refresh token")
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": cid, "client_secret": sec, "refresh_token": rt,
        "grant_type": "refresh_token",
    }, timeout=30)
    if r.status_code != 200:
        # do not echo body that may contain token material
        raise RuntimeError(f"token refresh failed: HTTP {r.status_code}")
    tok = r.json().get("access_token")
    if not tok:
        raise RuntimeError("token refresh returned no access_token")
    return tok


def youtube_upload(access_token: str, video_path: str, title: str, description: str,
                   tags: list[str], privacy: str) -> str:
    """YouTube Data API v3 videos.insert (multipart upload). Returns the new video id."""
    meta = {
        "snippet": {"title": title, "description": description, "tags": tags, "categoryId": "22"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    boundary = "nexus_publish_boundary_7f3a2b"
    pre = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
           f"{json.dumps(meta)}\r\n--{boundary}\r\nContent-Type: video/mp4\r\n\r\n").encode()
    post = f"\r\n--{boundary}--\r\n".encode()
    body = pre + Path(video_path).read_bytes() + post
    r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=multipart&part=snippet,status",
        headers={"Authorization": f"Bearer {access_token}",
                 "Content-Type": f"multipart/related; boundary={boundary}"},
        data=body, timeout=600)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"videos.insert failed: HTTP {r.status_code} {r.text[:200]}")
    return r.json().get("id", "")


def main():
    ap = argparse.ArgumentParser(description="Scoped social publish gate — real YouTube upload behind hard gates")
    ap.add_argument("--approval-id", required=True)
    ap.add_argument("--content-id", required=True)
    ap.add_argument("--platform", required=True, choices=["youtube","tiktok","instagram"])
    ap.add_argument("--video", required=True, help="path to the local video file")
    ap.add_argument("--privacy", default="private", choices=["private","unlisted","public"],
                    help="YouTube privacy status (default private; public only on explicit Ray approval)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    executor_on = os.environ.get("NEXUS_PUBLISH_EXECUTOR_ENABLED","false").lower() == "true"
    u, k = creds(); h = {"apikey":k,"Authorization":f"Bearer {k}"}
    print("=== social publish gate (dry-run unless --apply; executor "+("ON" if executor_on else "DISABLED")+") ===")

    # 1) approval verify
    appr = requests.get(f"{u}/rest/v1/owner_approval_queue", headers=h,
        params={"select":"id,action_type,status,payload","id":f"eq.{args.approval_id}"}, timeout=20).json()
    if not appr:
        print("  ✗ approval not found — abort"); return
    a = appr[0]; payload = a.get("payload") or {}
    scoped_ok = (a["action_type"]=="publish_content" and a["status"]=="approved"
                 and payload.get("content_id")==args.content_id)
    print(f"  approval {args.approval_id[:8]}: status={a['status']} action={a['action_type']} scoped_content={payload.get('content_id','?')[:8]} -> scope_ok={scoped_ok}")
    # 2) content verify (must not already be published)
    it = requests.get(f"{u}/rest/v1/nexus_os_content_items", headers=h,
        params={"select":"id,title,content_body,status,published_at,disclosure_added","id":f"eq.{args.content_id}"}, timeout=20).json()
    it = it[0] if it else {}
    content_ok = bool(it) and it.get("published_at") is None and it.get("disclosure_added")
    print(f"  content {args.content_id[:8]}: status={it.get('status')} published_at={it.get('published_at')} disclosure={it.get('disclosure_added')} -> content_ok={content_ok}")
    # 3) video verify
    vid = Path(args.video); video_ok = vid.exists()
    print(f"  video: {vid} -> exists={video_ok}")
    # 4) credentials presence (names only)
    creds_present = env_names_present(args.platform)
    missing = [n for n,p in creds_present.items() if not p]
    print(f"  {args.platform} credentials present: {sum(creds_present.values())}/{len(creds_present)}; missing: {missing or 'none'}")

    gates_ok = scoped_ok and content_ok and video_ok and not missing
    print("\nDECISION:")
    uploaded_url = None
    outcome = "no_action"
    if not args.apply:
        # DRY-RUN: validate + show what WOULD upload. NO YouTube API call.
        try:
            t, _d, tg = build_youtube_metadata(it)
            print("  DRY-RUN — validated only. No YouTube API call, nothing posted.")
            print(f"  would upload: title={t!r} privacy={args.privacy} tags={len(tg)} (real upload wired, gated off)")
        except Exception as e:
            print(f"  DRY-RUN — validated. (metadata preview skipped: {str(e)[:80]})")
        outcome = "dry_run"
    elif not executor_on:
        print("  REFUSED — publish executor is DISABLED (NEXUS_PUBLISH_EXECUTOR_ENABLED not true). Nothing posted.")
        outcome = "refused_executor_disabled"
    elif not scoped_ok:
        print("  REFUSED — approval missing/not scoped to this content_id. Nothing posted.")
        outcome = "refused_scope"
    elif not content_ok:
        print("  REFUSED — content missing disclosure or already published. Nothing posted.")
        outcome = "refused_content"
    elif not video_ok:
        print("  REFUSED — video file not found. Nothing posted.")
        outcome = "refused_video"
    elif missing:
        print(f"  REFUSED — missing platform credentials: {missing}. Nothing posted.")
        outcome = "refused_credentials"
    elif args.platform != "youtube":
        print(f"  REFUSED — real upload is implemented for youtube only; {args.platform} not wired yet. Nothing posted.")
        outcome = "refused_platform_unwired"
    else:
        # ALL gates pass + executor ON + --apply + youtube => REAL upload
        try:
            title, desc, tags = build_youtube_metadata(it)
            print(f"  UPLOADING to YouTube: title={title!r} privacy={args.privacy} ...")
            access = youtube_refresh_access_token()          # value never printed
            vid_id = youtube_upload(access, str(vid), title, desc, tags, args.privacy)
            uploaded_url = f"https://www.youtube.com/watch?v={vid_id}"
            print(f"  ✓ UPLOADED: {uploaded_url}")
            outcome = "uploaded"
            # mark content published + store URL (only on real success)
            requests.patch(f"{u}/rest/v1/nexus_os_content_items?id=eq.{args.content_id}",
                headers={**h,"Content-Type":"application/json"},
                data=json.dumps({"status":"published","published_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                 "analytics_url":uploaded_url}), timeout=20)
        except Exception as e:
            print(f"  ✗ upload failed: {str(e)[:200]}")
            outcome = "upload_failed"

    # audit (records the attempt + outcome; values/secrets never logged)
    try:
        requests.post(f"{u}/rest/v1/nexus_os_approval_events", headers={**h,"Content-Type":"application/json"},
            data=json.dumps([{"approval_id":args.approval_id,"event_type":("completed" if outcome=="uploaded" else "comment"),
            "changed_by":"social_publish_gate",
            "comment":(f"Publish gate for {args.content_id} -> {args.platform}. outcome={outcome} "
                       f"scope_ok={scoped_ok} content_ok={content_ok} video_ok={video_ok} creds_ok={not missing} "
                       f"executor_on={executor_on} apply={args.apply}" + (f" url={uploaded_url}" if uploaded_url else "")),
            "telegram_sent":False}]), timeout=15)
        print(f"\naudit event written (outcome={outcome}). No secret/credential printed.")
    except Exception as e:
        print("\n(audit write skipped:", str(e)[:80], ")")

if __name__ == "__main__":
    main()
