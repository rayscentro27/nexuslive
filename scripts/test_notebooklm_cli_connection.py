#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import notebooklm_cli_adapter as adapter
from lib.hermes_internal_first import try_internal_first


def _pass(name: str) -> None:
    print(f"[PASS] {name}")


def _fail(name: str) -> None:
    print(f"[FAIL] {name}")


def _assert(name: str, cond: bool) -> bool:
    if cond:
        _pass(name)
        return True
    _fail(name)
    return False


def main() -> int:
    ok = True

    # CLI unavailable handled safely (at least no crash + structured fields)
    disc = adapter.discovery()
    ok &= _assert("discovery shape", isinstance(disc, dict) and "capabilities" in disc)

    # registry loads
    reg = adapter.load_registry()
    ok &= _assert("registry loads", isinstance(reg.get("notebooks"), list) and len(reg.get("notebooks") or []) >= 5)

    # adapter redacts credentials
    redacted = adapter._redact("token=abc access_token=123 cookie=xyz")
    ok &= _assert("adapter redacts credentials", "token" not in redacted.lower() and "cookie" not in redacted.lower())

    # dry-run does not write queue file when registry missing notebook
    tmp = tempfile.TemporaryDirectory()
    tmp_path = Path(tmp.name) / "queue.json"
    before_exists = tmp_path.exists()
    res = adapter.dry_run_sync("does-not-exist")
    after_exists = tmp_path.exists()
    ok &= _assert("dry-run safe on missing notebook", (not res.get("ok")) and before_exists == after_exists)

    # apply requires explicit flag behavior through sync_notebook helper
    res_apply_false = adapter.sync_notebook("forex", apply=False)
    ok &= _assert("apply requires explicit flag", res_apply_false.get("mode") == "dry_run" or not res_apply_false.get("ok"))

    # dedup works in normalization
    norm = adapter.normalize_notebook_export(
        {
            "ok": True,
            "registry_notebook_id": "forex",
            "notebook_name": "Nexus Trading",
            "category": "forex_trading",
            "destination_domain": "trading",
            "summary": "x",
            "sources": [
                {"id": "1", "title": "A", "url": "https://example.com/a", "type": "website"},
                {"id": "2", "title": "A", "url": "https://example.com/a", "type": "website"},
            ],
        }
    )
    ok &= _assert("dedup works", int(norm.get("source_count") or 0) == 1)

    # domain routing works
    jobs = adapter.build_ingestion_jobs(norm)
    ok &= _assert("domain routing works", bool(jobs) and jobs[0].get("domain") == "trading")

    # Hermes commands parse
    reply = try_internal_first("show notebook sync status")
    ok &= _assert("Hermes commands parse", bool(reply) and reply.matched_topic == "notebooklm")

    # no Telegram auto summary trigger marker
    text = reply.text if reply else ""
    ok &= _assert("no Telegram auto-summary triggered", "auto-summary" not in text.lower() and "broadcast" not in text.lower())

    print(json.dumps({"ok": bool(ok)}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
