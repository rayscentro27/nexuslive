#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.notebooklm_cli_adapter import (
    DEFAULT_REGISTRY,
    REGISTRY_FILE,
    apply_sync,
    discovery,
    dry_run_sync,
    ensure_registry,
    list_notebooks,
    load_registry,
    notebook_sync_status,
    save_registry,
    sync_enabled,
)
from lib.notebooklm_ingest_adapter import QUEUE_FILE, load_dry_run_queue


def _print(payload: object) -> int:
    print(json.dumps(payload, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Nexus NotebookLM operations CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("discover")
    sub.add_parser("list")
    sub.add_parser("registry")
    st = sub.add_parser("status")
    st.add_argument("--pending-review", action="store_true")

    add = sub.add_parser("add-notebook")
    add.add_argument("--id", required=True)
    add.add_argument("--name", required=True)
    add.add_argument("--category", default="operations")
    add.add_argument("--domain", default="operations")
    add.add_argument("--max-items", type=int, default=20)

    sync_one = sub.add_parser("sync-notebook")
    sync_one.add_argument("--id", required=True)
    sync_one.add_argument("--dry-run", action="store_true")
    sync_one.add_argument("--apply", action="store_true")

    sync_all = sub.add_parser("sync-enabled")
    sync_all.add_argument("--dry-run", action="store_true")
    sync_all.add_argument("--apply", action="store_true")

    dr = sub.add_parser("dry-run")
    dr.add_argument("--id", required=True)

    ap = sub.add_parser("apply")
    ap.add_argument("--id", required=True)

    ingest = sub.add_parser("ingest-export")
    ingest.add_argument("--id", required=True)

    sub.add_parser("pending-review")
    args = p.parse_args()

    if args.cmd == "discover":
        return _print(discovery())
    if args.cmd == "list":
        return _print({"ok": True, "notebooks": list_notebooks()})
    if args.cmd == "registry":
        ensure_registry()
        return _print({"ok": True, "registry_file": str(REGISTRY_FILE), "registry": load_registry()})
    if args.cmd == "status":
        status = notebook_sync_status()
        if bool(args.pending_review):
            status["pending_review"] = load_dry_run_queue(str(QUEUE_FILE))
        return _print(status)
    if args.cmd == "add-notebook":
        reg = load_registry()
        rows = reg.get("notebooks") or []
        rows = [r for r in rows if str(r.get("notebook_id") or "") != args.id]
        rows.append(
            {
                "notebook_id": args.id,
                "notebook_name": args.name,
                "category": args.category,
                "description": "added via nexus_notebooklm_ops",
                "source_type": "notebooklm",
                "sync_status": "idle",
                "last_sync_at": None,
                "last_ingested_at": None,
                "confidence": 0.6,
                "enabled": True,
                "max_items_per_sync": max(1, min(int(args.max_items), 50)),
                "destination_domain": args.domain,
            }
        )
        reg["notebooks"] = rows
        save_registry(reg)
        return _print({"ok": True, "registry": reg})
    if args.cmd == "sync-notebook":
        apply = bool(args.apply)
        return _print(apply_sync(args.id) if apply else dry_run_sync(args.id))
    if args.cmd == "sync-enabled":
        apply = bool(args.apply)
        return _print(sync_enabled(apply=apply))
    if args.cmd == "dry-run":
        return _print(dry_run_sync(args.id))
    if args.cmd == "apply":
        return _print(apply_sync(args.id))
    if args.cmd == "ingest-export":
        return _print(dry_run_sync(args.id))
    if args.cmd == "pending-review":
        return _print({"ok": True, "queue_file": str(QUEUE_FILE), "rows": load_dry_run_queue(str(QUEUE_FILE))})

    return _print({"ok": False, "error": "unknown_command", "available_categories": [r.get("category") for r in DEFAULT_REGISTRY.get("notebooks") or []]})


if __name__ == "__main__":
    raise SystemExit(main())
