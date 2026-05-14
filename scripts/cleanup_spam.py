#!/usr/bin/env python3
"""
Nexus Spam Cleanup — archive false-approved knowledge_items and recursive research_requests.

Dry-run by default. Pass --apply to execute changes.

Safe targets only:
- knowledge_items with content "No vetted Nexus knowledge found..." that were incorrectly approved
- knowledge_items with placeholder/test URLs (def12345678)
- research_requests that are recursive operational Hermes queries (never valid research topics)

Never touches: legitimate approved knowledge, valid transcript history, real research tickets.
"""

import os
import sys
import argparse
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

# IDs of false-approved knowledge_items confirmed to have empty/spam content
FALSE_APPROVED_KNOWLEDGE = [
    {"id": "e63caf61-6687-407b-976f-683babab6bb9", "title": "grants for AI education businesses", "reason": "content: No vetted Nexus knowledge found"},
    {"id": "448a0c16-8c2f-41b5-b666-5b8ee1fc1840", "title": "lenders for startups with low revenue", "reason": "content: No vetted Nexus knowledge found"},
    {"id": "f9a13fa7-6e9b-453e-b16a-9d5ab50e27fc", "title": "AI affiliate automation model", "reason": "content: No vetted Nexus knowledge found"},
    {"id": "8924346e-cb90-46aa-9164-9f010353309c", "title": "ICT silver bullet strategy", "reason": "content: No vetted Nexus knowledge found"},
    {"id": "a898a9fe-1712-41e4-a07e-3a486ac99e0e", "title": "Can Nexus research the ICT silver bullet strategy?", "reason": "content: No vetted Nexus knowledge found"},
    {"id": "00f59b29-1d0a-44f4-b4ea-b30026190b07", "title": "What does Nexus know about the ICT silver bullet strategy?", "reason": "content: No vetted Nexus knowledge found"},
    {"id": "ef7bb351-a19d-4328-a1e6-d716748f6c0b", "title": "Can Nexus review AI automation affiliate opportunities?", "reason": "content: No vetted Nexus knowledge found"},
    {"id": "221658ae-15c8-4ce8-8558-360cb2e27d16", "title": "What funding paths has Nexus researched for startups?", "reason": "content: No vetted Nexus knowledge found"},
    {"id": "bf433142-1286-454b-931e-f3c423bc6962", "title": "Can Nexus find grants for AI education businesses?", "reason": "content: No vetted Nexus knowledge found"},
    {"id": "a0a19677-4474-482c-960c-754608bc1ce6", "title": "YouTube video research: def12345678", "reason": "placeholder URL, fabricated content"},
]

# IDs of recursive operational research_requests that should never be research topics
RECURSIVE_RESEARCH_TICKETS = [
    {"id": "166ced54-9047-48df-97f0-12426f47e831", "topic": "What grant opportunities has Nexus researched?", "reason": "Hermes operational query — not a valid research topic"},
    {"id": "8b1b5fb3-e418-493b-ba58-b9e75cbfac64", "topic": "What trading research is available internally?", "reason": "Hermes operational query — not a valid research topic"},
    {"id": "32e7e595-3ed2-41f7-bb6a-c1d4d72865bf", "topic": "What opportunities are Nexus validated?", "reason": "Hermes operational query — not a valid research topic"},
    {"id": "96de6be6-9d0f-4e3d-af3d-dd0df4e79a6f", "topic": "What new knowledge was recently approved?", "reason": "Hermes operational query — not a valid research topic"},
]


def get_knowledge_item(item_id: str) -> dict | None:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/knowledge_items",
        headers=HEADERS,
        params={"id": f"eq.{item_id}", "select": "id,title,status,quality_score,content"},
    )
    rows = r.json() if r.status_code == 200 else []
    return rows[0] if rows else None


def get_research_request(req_id: str) -> dict | None:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/research_requests",
        headers=HEADERS,
        params={"id": f"eq.{req_id}", "select": "id,topic,status,department"},
    )
    rows = r.json() if r.status_code == 200 else []
    return rows[0] if rows else None


def archive_knowledge_item(item_id: str, apply: bool) -> tuple[bool, str]:
    if not apply:
        return True, "DRY-RUN"
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/knowledge_items",
        headers=HEADERS,
        params={"id": f"eq.{item_id}"},
        json={"status": "archived"},
    )
    if r.status_code in (200, 204):
        return True, "ARCHIVED"
    return False, f"HTTP {r.status_code}: {r.text[:100]}"


def reject_research_request(req_id: str, apply: bool) -> tuple[bool, str]:
    if not apply:
        return True, "DRY-RUN"
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/research_requests",
        headers=HEADERS,
        params={"id": f"eq.{req_id}"},
        json={"status": "cancelled"},
    )
    if r.status_code in (200, 204):
        return True, "CANCELLED"
    return False, f"HTTP {r.status_code}: {r.text[:100]}"


def main():
    parser = argparse.ArgumentParser(description="Archive Nexus spam knowledge_items and recursive research tickets")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        sys.exit(1)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== NEXUS SPAM CLEANUP ({mode}) ===")
    print()

    # Phase 1: knowledge_items
    print("--- PHASE 1: False-Approved Knowledge Items ---")
    print(f"Targets: {len(FALSE_APPROVED_KNOWLEDGE)} items")
    print()

    ki_success = 0
    ki_skip = 0
    ki_fail = 0
    for target in FALSE_APPROVED_KNOWLEDGE:
        row = get_knowledge_item(target["id"])
        if not row:
            print(f"  SKIP {target['id'][:8]} — not found (already cleaned or wrong ID)")
            ki_skip += 1
            continue

        current_status = row.get("status")
        if current_status == "archived":
            print(f"  SKIP {row['id'][:8]} — already archived: {row['title'][:50]}")
            ki_skip += 1
            continue

        ok, detail = archive_knowledge_item(target["id"], args.apply)
        status_sym = "✓" if ok else "✗"
        print(f"  {status_sym} {row['id'][:8]} [{current_status}→archived] q={row.get('quality_score')} | {row['title'][:50]}")
        print(f"       reason: {target['reason']}")
        print(f"       result: {detail}")
        if ok:
            ki_success += 1
        else:
            ki_fail += 1

    print()
    print(f"  Summary: {ki_success} archived, {ki_skip} skipped, {ki_fail} failed")
    print()

    # Phase 2: research_requests
    print("--- PHASE 2: Recursive Operational Research Tickets ---")
    print(f"Targets: {len(RECURSIVE_RESEARCH_TICKETS)} tickets")
    print()

    rr_success = 0
    rr_skip = 0
    rr_fail = 0
    for target in RECURSIVE_RESEARCH_TICKETS:
        row = get_research_request(target["id"])
        if not row:
            print(f"  SKIP {target['id'][:8]} — not found")
            rr_skip += 1
            continue

        current_status = row.get("status")
        if current_status in ("cancelled", "completed"):
            print(f"  SKIP {row['id'][:8]} — already {current_status}: {row['topic'][:50]}")
            rr_skip += 1
            continue

        ok, detail = reject_research_request(target["id"], args.apply)
        status_sym = "✓" if ok else "✗"
        print(f"  {status_sym} {row['id'][:8]} [{current_status}→cancelled] | {row.get('topic','?')[:55]}")
        print(f"       reason: {target['reason']}")
        print(f"       result: {detail}")
        if ok:
            rr_success += 1
        else:
            rr_fail += 1

    print()
    print(f"  Summary: {rr_success} cancelled, {rr_skip} skipped, {rr_fail} failed")
    print()

    if not args.apply:
        print("=== DRY-RUN COMPLETE — pass --apply to execute changes ===")
    else:
        print("=== CLEANUP APPLIED ===")


if __name__ == "__main__":
    main()
