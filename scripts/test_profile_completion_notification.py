#!/usr/bin/env python3
"""
Ray-only profile-completion notification test (safe).

Verifies the portal-notification path for profile completion WITHOUT deploying
the migration and WITHOUT flipping Ray's real onboarding_complete flag (that is
part of the approved fix, not this test).

Modes:
  --dry-run                 (default) report current state + what WOULD happen, no writes
  --apply-test-notification insert ONE idempotent 'onboarding' notification for Ray only
  --cleanup                 delete test notifications created by this script (Ray only)

Safety: Ray only · no external email · no spam (idempotent) · no secrets printed ·
does not change profile/onboarding state · does not deploy.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_TITLE = "Profile completion (Ray-only notification test)"


def _load_env() -> None:
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def _client():
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def _find_ray(sb, email: str | None):
    # user_profiles has no email column; email lives in auth.users. Resolve by the
    # single super_admin (Ray) which is the safe, deterministic target here.
    rows = sb.table("user_profiles").select(
        "id,full_name,role,onboarding_complete,readiness_score,updated_at").eq(
        "role", "super_admin").execute().data
    if not rows:
        rows = sb.table("user_profiles").select(
            "id,full_name,role,onboarding_complete,readiness_score,updated_at").ilike(
            "full_name", "%Ray%").execute().data
    return rows[0] if rows else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Ray-only profile-completion notification test.")
    ap.add_argument("--email", default="rayscentro@yahoo.com")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply-test-notification", action="store_true")
    ap.add_argument("--cleanup", action="store_true")
    args = ap.parse_args()
    _load_env()
    sb = _client()

    ray = _find_ray(sb, args.email)
    if not ray:
        print("Could not find Ray's profile (super_admin). Aborting safely.")
        return 1
    uid = ray["id"]
    print(f"Target (Ray only): {ray.get('full_name')} · role={ray.get('role')} · id={uid[:8]}…")
    print(f"  onboarding_complete={ray.get('onboarding_complete')} · readiness_score={ray.get('readiness_score')} "
          f"· updated_at={ray.get('updated_at')}")

    existing = sb.table("notifications").select("id,type,title,created_at").eq(
        "user_id", uid).in_("type", ["onboarding", "onboarding_completed"]).execute().data
    print(f"  existing onboarding notifications: {len(existing)}")

    if args.cleanup:
        removed = 0
        for n in existing:
            if (n.get("title") or "").startswith("Profile completion (Ray-only"):
                sb.table("notifications").delete().eq("id", n["id"]).execute()
                removed += 1
        print(f"CLEANUP: removed {removed} test notification(s).")
        return 0

    if args.apply_test_notification and not args.dry_run:
        if existing:
            print("IDEMPOTENT: an onboarding notification already exists — not inserting a duplicate.")
            return 0
        row = {"user_id": uid, "type": "onboarding", "title": TEST_TITLE,
               "body": "Ray-only test confirming the portal notification path works.",
               "priority": 2, "action_url": "/app", "action_label": "View dashboard"}
        res = sb.table("notifications").insert(row).execute()
        nid = res.data[0]["id"] if res.data else "?"
        print(f"APPLIED: inserted Ray-only test notification id={str(nid)[:8]}… "
              f"(remove with --cleanup)")
        return 0

    # default dry-run
    print("\nDRY-RUN — would, on real completion (post-fix):")
    print("  1) complete_user_profile() sets onboarding_complete=true, readiness_score, updated_at")
    print("  2) trigger trg_user_profiles_onboarding_notification inserts ONE 'onboarding' notification")
    print("  3) portal realtime subscription surfaces it to Ray")
    print("No writes performed. Use --apply-test-notification to insert one Ray-only test notification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
