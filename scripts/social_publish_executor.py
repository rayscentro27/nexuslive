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

def main():
    ap = argparse.ArgumentParser(description="Scoped dry-run social publish gate (never posts in this build)")
    ap.add_argument("--approval-id", required=True)
    ap.add_argument("--content-id", required=True)
    ap.add_argument("--platform", required=True, choices=["youtube","tiktok","instagram"])
    ap.add_argument("--video", required=True, help="path to the local video file")
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
        params={"select":"id,status,published_at,disclosure_added","id":f"eq.{args.content_id}"}, timeout=20).json()
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

    can = scoped_ok and content_ok and video_ok and not missing and executor_on and args.apply
    print("\nDECISION:")
    if not args.apply:
        print("  DRY-RUN — path verified only. Nothing posted.")
    elif not executor_on:
        print("  REFUSED — publish executor is DISABLED (NEXUS_PUBLISH_EXECUTOR_ENABLED not true). Nothing posted.")
    elif not scoped_ok:
        print("  REFUSED — approval missing/not scoped to this content_id. Nothing posted.")
    elif not content_ok:
        print("  REFUSED — content missing disclosure or already published. Nothing posted.")
    elif not video_ok:
        print("  REFUSED — video file not found. Nothing posted.")
    elif missing:
        print(f"  REFUSED — missing platform credentials: {missing}. Nothing posted.")
    else:
        print("  (Would post — but this build never actually posts.) Nothing posted.")

    # audit (records the attempt; never a post)
    try:
        requests.post(f"{u}/rest/v1/nexus_os_approval_events", headers={**h,"Content-Type":"application/json"},
            data=json.dumps([{"approval_id":args.approval_id,"event_type":"comment","changed_by":"social_publish_gate",
            "comment":f"Publish gate dry-run for {args.content_id} -> {args.platform}. scope_ok={scoped_ok} content_ok={content_ok} video_ok={video_ok} executor_on={executor_on}. Nothing posted.",
            "telegram_sent":False}]), timeout=15)
        print("\naudit event written. No post, no upload, no credential change.")
    except Exception as e:
        print("\n(audit write skipped:", str(e)[:80], ")")

if __name__ == "__main__":
    main()
