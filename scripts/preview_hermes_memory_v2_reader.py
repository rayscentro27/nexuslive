"""
preview_hermes_memory_v2_reader.py
Read-only preview of active/live_answer records from hermes_memory_v2.
Shows memory_id, title, memory_type only. Never prints payload or secrets.
Does NOT modify telegram_bot.py or any other file.
"""
import argparse, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PREVIEW_COLUMNS = "memory_id,title,memory_type,priority,confidence,tags"
_SUPABASE_WRITE_ATTEMPTED = False


def _get_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview active/live_answer records in hermes_memory_v2")
    parser.add_argument("--limit", type=int, default=20, help="Max records to show (default: 20)")
    parser.add_argument("--type", dest="memory_type", default="", help="Filter by memory_type")
    args = parser.parse_args()

    print("=== Hermes Memory V2 — Reader Preview ===")
    print(f"Mode     : READ-ONLY (no writes)")
    print(f"Filter   : status=active, scope=live_answer")
    if args.memory_type:
        print(f"Type     : {args.memory_type}")
    print(f"Limit    : {args.limit}")
    print()

    try:
        client = _get_client()
    except Exception as exc:
        msg = str(exc)
        if "eyJ" in msg:
            msg = "[redacted]"
        print(f"ERROR: Cannot connect to Supabase: {msg}")
        return 1

    try:
        q = client.table("hermes_memory_v2") \
            .select(PREVIEW_COLUMNS, count="exact") \
            .eq("status", "active") \
            .eq("scope", "live_answer") \
            .order("priority", desc=True) \
            .limit(args.limit)
        if args.memory_type:
            q = q.eq("memory_type", args.memory_type)
        resp = q.execute()
    except Exception as exc:
        msg = str(exc)
        if "eyJ" in msg:
            msg = "[redacted]"
        print(f"ERROR: Query failed: {msg}")
        return 1

    records = resp.data or []
    total = resp.count if resp.count is not None else len(records)

    print(f"Total active/live_answer records: {total}")
    print(f"Showing: {len(records)}")
    print()
    print(f"{'#':<4} {'memory_id':<36} {'type':<20} {'pri':<4} {'conf':<5} title")
    print("-" * 120)
    for i, r in enumerate(records, 1):
        mid = r.get("memory_id", "?")[:35]
        mtype = r.get("memory_type", "?")[:19]
        pri = str(r.get("priority", "?"))
        conf = str(r.get("confidence", "?"))
        title = r.get("title", "?")[:55]
        print(f"{i:<4} {mid:<36} {mtype:<20} {pri:<4} {conf:<5} {title}")

    print()
    print("Read-only preview complete. Payload and summary fields not shown.")
    print("No writes performed. telegram_bot.py not modified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
