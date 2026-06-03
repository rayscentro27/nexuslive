#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "docs" / "reports" / "audits"

path = sorted(AUDIT_DIR.glob("hermes_command_inventory_*.json"))[-1]
doc = json.loads(path.read_text(encoding="utf-8"))
required_top = {"timestamp", "commands", "summary"}
required_command = {
    "category", "phrase", "normalized_intent", "handler", "file_path", "output_header",
    "read_sources", "write_targets", "safety_risk_level", "approval_required",
    "command_style", "active_in_live_telegram", "shadow_only",
    "duplicate_or_overlapping", "old_report_wrapper",
}

if not required_top.issubset(doc):
    print("Missing top-level keys.")
    sys.exit(1)
if not isinstance(doc["commands"], list) or not doc["commands"]:
    print("commands missing or empty")
    sys.exit(1)
for idx, item in enumerate(doc["commands"][:20]):
    if not required_command.issubset(item):
        print(f"Command entry {idx} missing keys")
        sys.exit(1)

print("Audit command inventory schema OK.")
